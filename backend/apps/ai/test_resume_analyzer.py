"""Phase 6 tests for the AI resume analysis service layer.

The external provider is always mocked: no test in this module performs a
network call.
"""

from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.ai import providers
from apps.ai.errors import AiParseError, ProviderUnavailable
from apps.ai.resume_analyzer import (
    analyze_resume_text,
    is_ai_configured,
    validate_analysis,
    validate_resume_text,
)

RESUME_TEXT = (
    "Jane Doe\nB.Tech Computer Science and Engineering\n"
    "Skills: Python, Django, PostgreSQL, Git, Docker, REST API\n"
    "Projects: CareerAI placement platform built with Django and React.\n"
    "Internship: backend developer intern, improved API latency by 40%.\n"
)

AI_PAYLOAD = {
    "summary": "Final-year CSE student with a Django and React project base.",
    "detected_skills": ["Python", "Django", "React", "PostgreSQL"],
    "strengths": ["Backend project with measurable outcome", "Clean tech stack"],
    "skill_gaps": ["No cloud or Docker experience evidenced"],
    "improvements": ["Add measurable results to each project bullet"],
    "recommended_roles": ["Backend Developer", "Full Stack Developer"],
    "education": ["B.Tech CSE"],
    "experience": ["Backend developer intern"],
    "score": 72,
}


class ResumeTextValidationTests(SimpleTestCase):
    """Empty / too-short / unusable extracted text is rejected clearly."""

    def test_blank_text_is_rejected(self):
        for value in ("", "   ", None, "\n\t"):
            with self.assertRaises(AiParseError) as ctx:
                validate_resume_text(value)
            self.assertIn("readable text", str(ctx.exception).lower())

    def test_too_short_text_is_rejected(self):
        with self.assertRaises(AiParseError):
            validate_resume_text("Jane Doe CV")

    def test_valid_text_is_normalised(self):
        cleaned = validate_resume_text("  " + RESUME_TEXT + "  ")
        self.assertTrue(cleaned.startswith("Jane Doe"))
        self.assertNotIn("\n", cleaned)


class StructuredOutputValidationTests(SimpleTestCase):
    """Malformed provider output is never trusted or stored."""

    def test_valid_payload_is_normalised(self):
        result = validate_analysis(AI_PAYLOAD, provider="openai")
        self.assertEqual(result["summary"], AI_PAYLOAD["summary"])
        self.assertEqual(result["detected_skills"], AI_PAYLOAD["detected_skills"])
        self.assertEqual(result["score"], 72)
        self.assertEqual(result["source"], "ai")
        self.assertEqual(result["provider"], "openai")

    def test_non_dict_payload_is_rejected(self):
        for value in (None, [], "text", 42):
            with self.assertRaises(AiParseError):
                validate_analysis(value)

    def test_payload_without_usable_fields_is_rejected(self):
        with self.assertRaises(AiParseError):
            validate_analysis({"summary": "", "detected_skills": [], "strengths": []})

    def test_wrong_types_are_coerced_or_dropped(self):
        result = validate_analysis({
            "summary": {"unexpected": "dict"},
            "detected_skills": "Python",
            "strengths": [{"name": "Python"}, "  ", 12, None, {"unknown": "key"}],
            "score": "not-a-number",
        })
        self.assertEqual(result["summary"], "")
        self.assertEqual(result["detected_skills"], ["Python"])
        self.assertEqual(result["strengths"], ["Python"])
        self.assertEqual(result["score"], 0)

    def test_score_is_clamped(self):
        self.assertEqual(validate_analysis({**AI_PAYLOAD, "score": 4800})["score"], 100)
        self.assertEqual(validate_analysis({**AI_PAYLOAD, "score": -20})["score"], 0)

    def test_lists_are_capped_and_deduplicated(self):
        result = validate_analysis({
            **AI_PAYLOAD,
            "strengths": [f"item {i}" for i in range(40)],
            "skill_gaps": ["Docker", "docker", "DOCKER", "AWS"],
        })
        self.assertEqual(len(result["strengths"]), 12)
        self.assertEqual(result["skill_gaps"], ["Docker", "AWS"])

    def test_only_contract_keys_are_kept(self):
        result = validate_analysis({**AI_PAYLOAD, "evil_key": "x", "api_key": "leak"})
        self.assertNotIn("api_key", result)
        self.assertEqual(result["raw"], {**AI_PAYLOAD, "evil_key": "x", "api_key": "leak"})


class ProviderConfigurationTests(SimpleTestCase):
    """Missing configuration fails gracefully with a useful message."""

    @override_settings(AI_PROVIDER="", AI_API_KEY="", AI_REQUIRED=False)
    def test_offline_fallback_when_provider_missing(self):
        self.assertFalse(is_ai_configured())
        result = analyze_resume_text(RESUME_TEXT)
        self.assertEqual(result["source"], "offline")
        self.assertIn("not configured", result["notice"])
        self.assertTrue(result["detected_skills"])

    @override_settings(AI_PROVIDER="", AI_API_KEY="", AI_REQUIRED=False)
    def test_require_ai_raises_clear_error(self):
        with self.assertRaises(ProviderUnavailable) as ctx:
            analyze_resume_text(RESUME_TEXT, require_ai=True)
        message = str(ctx.exception)
        self.assertIn("AI_PROVIDER", message)
        self.assertIn("AI_API_KEY", message)
        self.assertNotIn("Traceback", message)

    @override_settings(AI_REQUIRED=True)
    def test_ai_required_setting_raises_when_unconfigured(self):
        with mock.patch.object(providers, "is_configured", return_value=False):
            with self.assertRaises(ProviderUnavailable):
                analyze_resume_text(RESUME_TEXT)

    @override_settings(AI_PROVIDER="openai", AI_API_KEY="test-key", AI_REQUIRED=True)
    def test_no_real_network_call_in_tests(self):
        """The provider call is mocked; a real call would raise."""
        with mock.patch.object(providers, "chat_json", return_value=AI_PAYLOAD) as call:
            result = analyze_resume_text(RESUME_TEXT)
        call.assert_called_once()
        self.assertEqual(result["source"], "ai")

    @override_settings(AI_PROVIDER="openai", AI_API_KEY="test-key", AI_REQUIRED=True)
    def test_ai_prompt_requests_structured_json(self):
        with mock.patch.object(providers, "chat_json", return_value=AI_PAYLOAD) as call:
            analyze_resume_text(RESUME_TEXT)
        messages = call.call_args[0][0]
        system = messages[0]["content"]
        for field in ("summary", "detected_skills", "strengths", "skill_gaps",
                      "improvements", "recommended_roles"):
            self.assertIn(field, system)

    @override_settings(AI_PROVIDER="openai", AI_API_KEY="test-key", AI_REQUIRED=True)
    def test_ai_failure_raises_when_required(self):
        for error in (ProviderUnavailable("AI provider unreachable (ConnectError)"),
                      AiParseError("AI returned invalid JSON: oops")):
            with mock.patch.object(providers, "chat_json", side_effect=error):
                with self.assertRaises(type(error)):
                    analyze_resume_text(RESUME_TEXT)

    @override_settings(AI_PROVIDER="openai", AI_API_KEY="test-key", AI_REQUIRED=False)
    def test_ai_failure_falls_back_offline_with_notice(self):
        with mock.patch.object(providers, "chat_json",
                               side_effect=ProviderUnavailable("AI provider unreachable (ConnectError)")):
            result = analyze_resume_text(RESUME_TEXT)
        self.assertEqual(result["source"], "offline")
        self.assertIn("could not be reached", result["notice"])

    @override_settings(AI_PROVIDER="openai", AI_API_KEY="test-key", AI_REQUIRED=True)
    def test_malformed_ai_output_is_rejected(self):
        for bad in (None, [], "not json", {"unrelated": "payload"}):
            with mock.patch.object(providers, "chat_json", return_value=bad):
                with self.assertRaises(AiParseError):
                    analyze_resume_text(RESUME_TEXT)

    @override_settings(AI_PROVIDER="openai", AI_API_KEY="test-key", AI_REQUIRED=True)
    def test_ai_error_messages_do_not_leak_key_or_traceback(self):
        with mock.patch.object(providers, "chat_json",
                               side_effect=ProviderUnavailable("AI provider rejected the configured API key")):
            with self.assertRaises(ProviderUnavailable) as ctx:
                analyze_resume_text(RESUME_TEXT)
        self.assertNotIn("test-key", str(ctx.exception))
