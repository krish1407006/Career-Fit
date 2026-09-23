class AiError(Exception):
    """Base class for AI service failures."""


class ProviderUnavailable(AiError):
    """No provider/key configured or provider call failed."""


class AiParseError(AiError):
    """Provider responded, but output could not be parsed as expected."""