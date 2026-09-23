"""Seed demo data: skills, a demo recruiter, and sample jobs.

Usage:
    python manage.py seed_demo [--reset]
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import RecruiterProfile
from apps.assessments.models import Question, Quiz
from apps.jobs.models import Job, Skill

Q = Quiz

QUIZZES = [
    {
        "title": "Python Fundamentals",
        "category": "technical",
        "description": "Core Python, data structures and OOP.",
        "duration_minutes": 10,
        "questions": [
            {"text": "Which data structure is immutable in Python?",
             "options": ["list", "tuple", "dict", "set"], "correct_index": 1,
             "explanation": "Tuples are immutable sequences."},
            {"text": "Which keyword defines a function in Python?",
             "options": ["func", "def", "define", "function"], "correct_index": 1,
             "explanation": "Functions are defined with 'def'."},
            {"text": "What does 'self' represent inside a class method?",
             "options": ["The module", "The class", "The instance", "The parent class"], "correct_index": 2,
             "explanation": "'self' refers to the current class instance."},
            {"text": "Which of these is a Python ORM used with Django?",
             "options": ["Hibernate", "Sequelize", "Django ORM", "Entity Framework"], "correct_index": 2,
             "explanation": "Django ships with its own ORM."},
            {"text": "What is the output of len([1, 2, [3, 4]])?",
             "options": ["3", "4", "Error", "2"], "correct_index": 0,
             "explanation": "The outer list has 3 items (inner list counts as one)."},
        ],
    },
    {
        "title": "Aptitude — Numbers",
        "category": "aptitude",
        "description": "Quantitative aptitude practice set.",
        "duration_minutes": 10,
        "questions": [
            {"text": "A train 120 m long crosses a pole in 8 s. What is its speed in km/h?",
             "options": ["48", "54", "60", "66"], "correct_index": 1,
             "explanation": "Speed = 120/8 = 15 m/s = 15 × 18/5 = 54 km/h."},
            {"text": "If x/5 = 8, what is 3x?",
             "options": ["120", "48", "24", "40"], "correct_index": 0,
             "explanation": "x = 40, so 3x = 120."},
            {"text": "What is 15% of 240?",
             "options": ["24", "30", "36", "32"], "correct_index": 2,
             "explanation": "0.15 × 240 = 36."},
            {"text": "The average of 4 consecutive even numbers is 9. The largest is:",
             "options": ["10", "12", "14", "8"], "correct_index": 1,
             "explanation": "Numbers are 6, 8, 10, 12; largest is 12."},
            {"text": "A shop offers 2 items for the price of 1. Effective discount?",
             "options": ["50%", "25%", "33 1/3%", "None"], "correct_index": 0,
             "explanation": "Pay 1, get 2 → 50% discount."},
        ],
    },
    {
        "title": "Django + Web Basics",
        "category": "technical",
        "description": "Web framework and REST API questions.",
        "duration_minutes": 10,
        "questions": [
            {"text": "Which command applies pending migrations?",
             "options": ["makemigrations", "migrate", "collectstatic", "runserver"], "correct_index": 1,
             "explanation": "'migrate' applies migrations."},
            {"text": "Which DRF mixin provides create(), list(), retrieve()?",
             "options": ["ModelViewSet", "APIView", "GenericView", "OnlyView"], "correct_index": 0,
             "explanation": "ModelViewSet bundles all CRUD actions."},
            {"text": "How are JWT tokens passed to a Django REST endpoint typically?",
             "options": ["Authorization: Bearer <token>", "Cookie only", "X-Auth header", "Query string"], "correct_index": 0,
             "explanation": "The common pattern is the Authorization: Bearer header."},
            {"text": "Which HTTP method is idempotent and typically used for updates?",
             "options": ["POST", "PUT", "DELETE", "GET"], "correct_index": 1,
             "explanation": "PUT replaces a resource and is idempotent."},
            {"text": "CORS is needed because...",
             "options": ["The frontend and backend are on different origins", "PostgreSQL needs it", "JWT invalidates it", "It encrypts traffic"], "correct_index": 0,
             "explanation": "Browsers block cross-origin requests without CORS headers."},
        ],
    },
]

User = get_user_model()

SKILLS = [
    ("Python", "language"), ("JavaScript", "language"), ("TypeScript", "language"),
    ("Java", "language"), ("C++", "language"), ("Go", "language"), ("SQL", "database"),
    ("Django", "backend"), ("Flask", "backend"), ("FastAPI", "backend"),
    ("Node.js", "backend"), ("Express", "backend"), ("React", "frontend"),
    ("Vue.js", "frontend"), ("Angular", "frontend"), ("HTML", "frontend"),
    ("CSS", "frontend"), ("PostgreSQL", "database"), ("MySQL", "database"),
    ("MongoDB", "database"), ("Redis", "database"), ("Docker", "devops"),
    ("Kubernetes", "devops"), ("AWS", "cloud"), ("Azure", "cloud"), ("Git", "devops"),
    ("GitHub", "devops"), ("Linux", "devops"), ("REST API", "backend"),
    ("GraphQL", "backend"), ("Machine Learning", "ai"), ("Deep Learning", "ai"),
    ("TensorFlow", "ai"), ("PyTorch", "ai"), ("NLP", "ai"), ("Computer Vision", "ai"),
    ("Pandas", "data"), ("NumPy", "data"), ("Tableau", "data"), ("Power BI", "data"),
    ("Data Structures", "fundamentals"), ("Algorithms", "fundamentals"),
    ("DBMS", "fundamentals"), ("Operating Systems", "fundamentals"),
    ("Networking", "fundamentals"), ("System Design", "fundamentals"),
    ("Agile", "management"), ("Scrum", "management"), ("JIRA", "tools"),
    ("Selenium", "testing"), ("Pytest", "testing"), ("Jest", "testing"),
    ("Postman", "testing"), ("Kotlin", "mobile"), ("Flutter", "mobile"),
]

JOBS = [
    {
        "title": "Python Developer",
        "description": "Build and maintain Python services, REST APIs and backend features for our SaaS product.",
        "responsibilities": ["Write clean, testable Python code", "Design REST APIs", "Work with PostgreSQL schemas"],
        "skills_required": ["Python", "Django", "PostgreSQL", "REST API", "Git"],
        "job_type": "full_time",
        "location": "Bengaluru",
        "salary_range": "8-14 LPA",
    },
    {
        "title": "Django Developer",
        "description": "Develop web applications with Django, integrate third-party APIs and optimize queries.",
        "responsibilities": ["Build Django REST Framework APIs", "Optimize database queries", "Deploy with Docker"],
        "skills_required": ["Python", "Django", "PostgreSQL", "Docker", "Git"],
        "job_type": "full_time",
        "location": "Hyderabad",
        "salary_range": "7-12 LPA",
    },
    {
        "title": "Frontend Developer Intern",
        "description": "Create responsive React interfaces with modern tooling and great attention to UX.",
        "responsibilities": ["Build React components", "Integrate REST APIs", "Write maintainable CSS"],
        "skills_required": ["React", "JavaScript", "HTML", "CSS", "REST API"],
        "job_type": "internship",
        "location": "Remote",
        "salary_range": "Stipend 20k/month",
    },
    {
        "title": "Machine Learning Engineer",
        "description": "Build ML pipelines for NLP products, experiment with models and deploy to production.",
        "responsibilities": ["Train and evaluate ML models", "Build data pipelines", "Deploy models with Docker"],
        "skills_required": ["Machine Learning", "Python", "NLP", "TensorFlow", "Docker", "Git"],
        "job_type": "full_time",
        "location": "Pune",
        "salary_range": "12-20 LPA",
    },
    {
        "title": "Full Stack Developer",
        "description": "End-to-end feature development across Django backend and React frontend.",
        "responsibilities": ["Develop full-stack features", "Write unit tests", "Participate in code reviews"],
        "skills_required": ["Python", "Django", "React", "JavaScript", "PostgreSQL", "Git"],
        "job_type": "full_time",
        "location": "Bengaluru",
        "salary_range": "10-16 LPA",
    },
    {
        "title": "Data Analyst",
        "description": "Analyze business data, build dashboards and derive actionable insights.",
        "responsibilities": ["Clean and analyze data", "Build Power BI dashboards", "Write SQL queries"],
        "skills_required": ["SQL", "Power BI", "Python", "Pandas"],
        "job_type": "full_time",
        "location": "Remote",
        "salary_range": "6-9 LPA",
    },
]


class Command(BaseCommand):
    help = "Seed demo skills, a recruiter, and sample jobs."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data first.")

    def handle(self, *args, **options):
        if options["reset"]:
            Skill.objects.all().delete()
            Job.objects.all().delete()
            self.stdout.write("Cleared skills and jobs.")
        admin_user = User.objects.filter(username="admin").first()

        created_skills = 0
        for name, category in SKILLS:
            _, was_created = Skill.objects.get_or_create(name=name, defaults={"category": category})
            created_skills += int(was_created)

        recruiter, r_created = User.objects.get_or_create(
            username="acme_recruiter",
            defaults={
                "email": "recruiter@acmehr.local",
                "first_name": "Acme",
                "last_name": "Hiring",
                "role": User.Role.RECRUITER,
            },
        )
        if r_created:
            recruiter.set_password("Recruiter@123")
            recruiter.save()

        profile, _ = RecruiterProfile.objects.get_or_create(
            user=recruiter,
            defaults={"company_name": "Acme Tech Solutions", "location": "Bengaluru",
                      "website": "https://acme.example", "description": "Demo recruiting company"},
        )
        profile.company_name = profile.company_name or "Acme Tech Solutions"
        profile.save()

        job_count = 0
        for data in JOBS:
            _, was_created = Job.objects.get_or_create(
                recruiter=recruiter, title=data["title"], company_name=profile.company_name,
                defaults={**data},
            )
            job_count += int(was_created)

        quiz_count = 0
        for quiz_data in QUIZZES:
            questions = quiz_data.pop("questions")
            quiz, was_created = Quiz.objects.get_or_create(
                title=quiz_data["title"], defaults={**quiz_data, "created_by": admin_user}
            )
            quiz_count += int(was_created)
            existing = set(quiz.questions.values_list("text", flat=True))
            for q in questions:
                if q["text"] not in existing:
                    Question.objects.create(quiz=quiz, **q)
            quiz_data["questions"] = questions

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {created_skills} skills, recruiter '{recruiter.username}', "
            f"{job_count} jobs, {len(QUIZZES)} quizzes."
        ))