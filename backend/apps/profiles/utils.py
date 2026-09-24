from apps.resumes.models import Resume


def profile_completion(profile):
    """Return an integer 0-100 estimating how complete a student profile is."""
    checks = [
        bool(profile.full_name),
        bool(profile.phone),
        bool(profile.college),
        bool(profile.degree),
        bool(profile.branch),
        bool(profile.graduation_year),
        profile.cgpa is not None,
        bool(profile.bio),
        bool(profile.location),
        bool(profile.preferred_roles),
        bool(profile.preferred_technologies),
        profile.education.exists(),
        profile.skills.exists(),
        profile.projects.exists(),
        profile.certifications.exists(),
        Resume.objects.filter(user=profile.user).exists(),
    ]
    return round(sum(bool(c) for c in checks) / len(checks) * 100)