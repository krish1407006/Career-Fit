"""Seed demo data: skills, a demo recruiter, and sample jobs.

Usage:
    python manage.py seed_demo [--reset]
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import RecruiterProfile, StudentProfile
from apps.assessments.models import Question, Quiz
from apps.jobs.models import Job, Skill

# Documented demo logins, printed at the end of every seed run.
DEMO_PASSWORDS = {
    "admin": "Admin@123",
    "student": "Student@123",
    "recruiter": "Recruiter@123",
}

Q = Quiz

QUIZZES = [
    {
        "title": "Python Fundamentals",
        "category": "python",
        "difficulty": "medium",
        "description": "Core Python, data structures and OOP.",
        "duration_minutes": 10,
        "questions": [
            {"text": "Which data structure is immutable in Python?",
             "options": ["list", "tuple", "dict", "set"], "correct_index": 1,
             "topic": "Data types", "difficulty": "easy",
             "explanation": "Tuples are immutable sequences."},
            {"text": "Which keyword defines a function in Python?",
             "options": ["func", "def", "define", "function"], "correct_index": 1,
             "topic": "Functions", "difficulty": "easy",
             "explanation": "Functions are defined with 'def'."},
            {"text": "What does 'self' represent inside a class method?",
             "options": ["The module", "The class", "The instance", "The parent class"], "correct_index": 2,
             "topic": "OOP", "difficulty": "medium",
             "explanation": "'self' refers to the current class instance."},
            {"text": "Which of these is a Python ORM used with Django?",
             "options": ["Hibernate", "Sequelize", "Django ORM", "Entity Framework"], "correct_index": 2,
             "topic": "Django", "difficulty": "easy",
             "explanation": "Django ships with its own ORM."},
            {"text": "What is the output of len([1, 2, [3, 4]])?",
             "options": ["3", "4", "Error", "2"], "correct_index": 0,
             "topic": "Data types", "difficulty": "medium",
             "explanation": "The outer list has 3 items (inner list counts as one)."},
        ],
    },
    {
        "title": "JavaScript Essentials",
        "category": "javascript",
        "difficulty": "easy",
        "description": "Core JavaScript language features.",
        "duration_minutes": 8,
        "questions": [
            {"text": "Which keyword declares a block-scoped variable?",
             "options": ["var", "let", "static", "int"], "correct_index": 1,
             "topic": "Variables", "difficulty": "easy",
             "explanation": "'let' is block-scoped; 'var' is function-scoped."},
            {"text": "What does typeof [] return?",
             "options": ["\"array\"", "\"object\"", "\"list\"", "\"undefined\""], "correct_index": 1,
             "topic": "Types", "difficulty": "medium",
             "explanation": "Arrays are objects in JavaScript."},
            {"text": "Which method converts a JSON string to an object?",
             "options": ["JSON.parse()", "JSON.stringify()", "Object.fromJson()", "parse()"], "correct_index": 0,
             "topic": "JSON", "difficulty": "easy",
             "explanation": "JSON.parse() parses a JSON string into a JS value."},
        ],
    },
    {
        "title": "Django + REST",
        "category": "django",
        "difficulty": "medium",
        "description": "Web framework and REST API questions.",
        "duration_minutes": 10,
        "questions": [
            {"text": "Which command applies pending migrations?",
             "options": ["makemigrations", "migrate", "collectstatic", "runserver"], "correct_index": 1,
             "topic": "Migrations", "difficulty": "easy",
             "explanation": "'migrate' applies migrations."},
            {"text": "Which DRF class provides create(), list(), retrieve()?",
             "options": ["ModelViewSet", "APIView", "GenericView", "OnlyView"], "correct_index": 0,
             "topic": "DRF", "difficulty": "medium",
             "explanation": "ModelViewSet bundles all CRUD actions."},
            {"text": "How are JWT tokens passed to a Django REST endpoint typically?",
             "options": ["Authorization: Bearer <token>", "Cookie only", "X-Auth header", "Query string"], "correct_index": 0,
             "topic": "Auth", "difficulty": "easy",
             "explanation": "The common pattern is the Authorization: Bearer header."},
            {"text": "Which HTTP method is idempotent and typically used for updates?",
             "options": ["POST", "PUT", "DELETE", "GET"], "correct_index": 1,
             "topic": "HTTP", "difficulty": "medium",
             "explanation": "PUT replaces a resource and is idempotent."},
            {"text": "CORS is needed because...",
             "options": ["The frontend and backend are on different origins", "PostgreSQL needs it", "JWT invalidates it", "It encrypts traffic"], "correct_index": 0,
             "topic": "CORS", "difficulty": "medium",
             "explanation": "Browsers block cross-origin requests without CORS headers."},
        ],
    },
    {
        "title": "SQL Query Basics",
        "category": "sql",
        "difficulty": "medium",
        "description": "Structured Query Language fundamentals.",
        "duration_minutes": 8,
        "questions": [
            {"text": "Which clause filters rows AFTER grouping?",
             "options": ["WHERE", "HAVING", "GROUP BY", "FILTER"], "correct_index": 1,
             "topic": "Grouping", "difficulty": "medium",
             "explanation": "HAVING filters groups; WHERE filters rows before grouping."},
            {"text": "Which SQL statement retrieves data?",
             "options": ["GET", "SELECT", "FETCH_ROWS", "OPEN"], "correct_index": 1,
             "topic": "Querying", "difficulty": "easy",
             "explanation": "SELECT retrieves rows from a table."},
            {"text": "What does LEFT JOIN return for non-matching right rows?",
             "options": ["NULLs in left columns", "NULLs in right columns", "The row is dropped", "An error"], "correct_index": 1,
             "topic": "Joins", "difficulty": "medium",
             "explanation": "LEFT JOIN keeps all left rows; unmatched right columns are NULL."},
            {"text": "Which keyword removes duplicate rows?",
             "options": ["UNIQUE", "DISTINCT", "DEDUPE", "SINGLE"], "correct_index": 1,
             "topic": "Queries", "difficulty": "easy",
             "explanation": "SELECT DISTINCT returns unique rows."},
        ],
    },
    {
        "title": "DBMS Concepts",
        "category": "dbms",
        "difficulty": "medium",
        "description": "Database management system theory.",
        "duration_minutes": 8,
        "questions": [
            {"text": "Which ACID property ensures a transaction succeeds fully or not at all?",
             "options": ["Atomicity", "Consistency", "Isolation", "Durability"], "correct_index": 0,
             "topic": "Transactions", "difficulty": "medium",
             "explanation": "Atomicity treats a transaction as either fully applied or not applied."},
            {"text": "The primary key must be...",
             "options": ["Nullable", "Unique and not null", "Unique and nullable", "An integer"], "correct_index": 1,
             "topic": "Keys", "difficulty": "easy",
             "explanation": "A primary key uniquely identifies rows and cannot be NULL."},
            {"text": "Normalization is mainly used to...",
             "options": ["Increase security", "Reduce redundancy and anomalies", "Speed up queries only", "Compress data"], "correct_index": 1,
             "topic": "Normalization", "difficulty": "medium",
             "explanation": "Normalization removes redundant data and update anomalies."},
        ],
    },
    {
        "title": "Aptitude — Numbers",
        "category": "aptitude",
        "difficulty": "easy",
        "description": "Quantitative aptitude practice set.",
        "duration_minutes": 10,
        "questions": [
            {"text": "A train 120 m long crosses a pole in 8 s. What is its speed in km/h?",
             "options": ["48", "54", "60", "66"], "correct_index": 1,
             "topic": "Speed & distance", "difficulty": "medium",
             "explanation": "Speed = 120/8 = 15 m/s = 15 × 18/5 = 54 km/h."},
            {"text": "If x/5 = 8, what is 3x?",
             "options": ["120", "48", "24", "40"], "correct_index": 0,
             "topic": "Algebra", "difficulty": "easy",
             "explanation": "x = 40, so 3x = 120."},
            {"text": "What is 15% of 240?",
             "options": ["24", "30", "36", "32"], "correct_index": 2,
             "topic": "Percentages", "difficulty": "easy",
             "explanation": "0.15 × 240 = 36."},
            {"text": "The average of 4 consecutive even numbers is 9. The largest is:",
             "options": ["10", "12", "14", "8"], "correct_index": 1,
             "topic": "Averages", "difficulty": "medium",
             "explanation": "Numbers are 6, 8, 10, 12; largest is 12."},
            {"text": "A shop offers 2 items for the price of 1. Effective discount?",
             "options": ["50%", "25%", "33 1/3%", "None"], "correct_index": 0,
             "topic": "Discounts", "difficulty": "medium",
             "explanation": "Pay 1, get 2 → 50% discount."},
        ],
    },
    {
        "title": "Logical Reasoning",
        "category": "logical_reasoning",
        "difficulty": "medium",
        "description": "Verbal and analytical reasoning practice.",
        "duration_minutes": 8,
        "questions": [
            {"text": "All roses are flowers. Some flowers fade quickly. Which must be true?",
             "options": ["All roses fade quickly", "Some roses fade quickly", "No conclusion is certain", "Roses are not flowers"], "correct_index": 2,
             "topic": "Syllogisms", "difficulty": "medium",
             "explanation": "The overlap between flowers that fade and roses is unknown."},
            {"text": "2, 6, 12, 20, 30, ?",
             "options": ["40", "42", "36", "44"], "correct_index": 1,
             "topic": "Number series", "difficulty": "easy",
             "explanation": "Differences are 4, 6, 8, 10 → next difference 12 → 42."},
            {"text": "Which word does not belong: Apple, Mango, Carrot, Banana?",
             "options": ["Apple", "Mango", "Carrot", "Banana"], "correct_index": 2,
             "topic": "Odd one out", "difficulty": "easy",
             "explanation": "Carrot is a vegetable; the others are fruits."},
            {"text": "If CAT is coded as DBU, how is DOG coded?",
             "options": ["EPH", "DPH", "EQH", "FQI"], "correct_index": 0,
             "topic": "Coding-decoding", "difficulty": "medium",
             "explanation": "Each letter moves +1: D→E, O→P, G→H → EPH."},
        ],
    },
]

User = get_user_model()


def ensure_skills(names):
    """Return a set of skill records matching ``names`` (reusing the catalog)."""
    return {Skill.objects.get_or_create(name=name)[0] for name in (names or []) if str(name).strip()}

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
        "preferred_skills": ["Docker", "Pytest"],
        "job_type": "full_time",
        "location": "Bengaluru",
        "salary_range": "8-14 LPA",
        "education_required": "B.E./B.Tech in CS/IT",
        "min_cgpa": 6.0,
        "experience_required": "0-2 years",
    },
    {
        "title": "Django Developer",
        "description": "Develop web applications with Django, integrate third-party APIs and optimize queries.",
        "responsibilities": ["Build Django REST Framework APIs", "Optimize database queries", "Deploy with Docker"],
        "skills_required": ["Python", "Django", "PostgreSQL", "Docker", "Git"],
        "preferred_skills": ["Redis", "AWS"],
        "job_type": "full_time",
        "location": "Hyderabad",
        "salary_range": "7-12 LPA",
        "education_required": "B.E./B.Tech preferred",
        "min_cgpa": 5.5,
        "experience_required": "0-2 years",
    },
    {
        "title": "Frontend Developer Intern",
        "description": "Create responsive React interfaces with modern tooling and great attention to UX.",
        "responsibilities": ["Build React components", "Integrate REST APIs", "Write maintainable CSS"],
        "skills_required": ["React", "JavaScript", "HTML", "CSS", "REST API"],
        "preferred_skills": ["TypeScript", "Vue.js"],
        "job_type": "internship",
        "location": "Remote",
        "salary_range": "Stipend 20k/month",
        "education_required": "Pursuing any degree",
        "min_cgpa": None,
        "experience_required": "Fresher",
    },
    {
        "title": "Machine Learning Engineer",
        "description": "Build ML pipelines for NLP products, experiment with models and deploy to production.",
        "responsibilities": ["Train and evaluate ML models", "Build data pipelines", "Deploy models with Docker"],
        "skills_required": ["Machine Learning", "Python", "NLP", "TensorFlow", "Docker", "Git"],
        "preferred_skills": ["PyTorch", "AWS"],
        "job_type": "full_time",
        "location": "Pune",
        "salary_range": "12-20 LPA",
        "education_required": "MTech/MSc or equivalent",
        "min_cgpa": 7.0,
        "experience_required": "1-3 years",
    },
    {
        "title": "Full Stack Developer",
        "description": "End-to-end feature development across Django backend and React frontend.",
        "responsibilities": ["Develop full-stack features", "Write unit tests", "Participate in code reviews"],
        "skills_required": ["Python", "Django", "React", "JavaScript", "PostgreSQL", "Git"],
        "preferred_skills": ["Docker", "TypeScript"],
        "job_type": "full_time",
        "location": "Bengaluru",
        "salary_range": "10-16 LPA",
        "education_required": "B.E./B.Tech in CS/IT",
        "min_cgpa": 6.5,
        "experience_required": "0-3 years",
    },
    {
        "title": "Data Analyst",
        "description": "Analyze business data, build dashboards and derive actionable insights.",
        "responsibilities": ["Clean and analyze data", "Build Power BI dashboards", "Write SQL queries"],
        "skills_required": ["SQL", "Power BI", "Python", "Pandas"],
        "preferred_skills": ["Tableau", "NumPy"],
        "job_type": "full_time",
        "location": "Remote",
        "salary_range": "6-9 LPA",
        "education_required": "Any degree with quantitative focus",
        "min_cgpa": 6.0,
        "experience_required": "Fresher",
    },
]


class Command(BaseCommand):
    help = "Seed demo skills, a recruiter, and sample jobs."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data first.")
        parser.add_argument(
            "--reset-passwords", action="store_true",
            help="Force the documented demo password on admin, student1 and acme_recruiter.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            Skill.objects.all().delete()
            Job.objects.all().delete()
            self.stdout.write("Cleared skills and jobs.")
        admin_user = User.objects.filter(username="admin").first()
        if admin_user is None:
            # Without this the seeded quizzes have no owner, and there is no way
            # to sign in as an admin at all on a fresh database.
            admin_user = User.objects.create_superuser(
                username="admin", email="admin@careerfit.local", password=DEMO_PASSWORDS["admin"],
            )
            self.stdout.write(f"Created admin user 'admin' ({DEMO_PASSWORDS['admin']}).")

        student, s_created = User.objects.get_or_create(            username="student1",
            defaults={
                "email": "student@careerfit.local",
                "first_name": "Sam",
                "last_name": "Student",
                "role": User.Role.STUDENT,
            },
        )
        if s_created:
            student.set_password(DEMO_PASSWORDS["student"])
            student.save()
            StudentProfile.objects.get_or_create(
                user=student,
                defaults={"full_name": "Sam Student", "college": "Demo Institute",
                          "degree": "B.Tech", "branch": "Computer Science"},
            )
            self.stdout.write(f"Created student 'student1' ({DEMO_PASSWORDS['student']}).")

        if options["reset_passwords"]:
            # Demo accounts created before this flag existed have no known
            # password, which makes the seeded app impossible to sign into.
            for username, key in (("admin", "admin"), ("student1", "student"),
                                  ("acme_recruiter", "recruiter")):
                account = User.objects.filter(username=username).first()
                if account is None:
                    continue
                account.set_password(DEMO_PASSWORDS[key])
                account.is_active = True
                account.save()
                self.stdout.write(f"Reset password for '{username}'.")

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
            recruiter.set_password(DEMO_PASSWORDS["recruiter"])
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
            job_data = dict(data)
            required_names = job_data.pop("skills_required", [])
            preferred_names = job_data.pop("preferred_skills", [])
            job, was_created = Job.objects.get_or_create(
                recruiter=recruiter, title=job_data["title"], company_name=profile.company_name,
                defaults=job_data,
            )
            if was_created:
                job.required_skills.set(ensure_skills(required_names))
                job.preferred_skills.set(ensure_skills(preferred_names))
            job_count += int(was_created)

        quiz_count = 0
        question_count = 0
        for quiz_data in QUIZZES:
            questions = quiz_data.pop("questions")
            quiz, was_created = Quiz.objects.get_or_create(
                title=quiz_data["title"], defaults={**quiz_data, "created_by": admin_user}
            )
            if not was_created:
                for field, value in quiz_data.items():
                    setattr(quiz, field, value)
                quiz.save(update_fields=list(quiz_data.keys()))
            quiz_count += int(was_created)
            existing = set(quiz.questions.values_list("text", flat=True))
            for q in questions:
                if q["text"] not in existing:
                    Question.objects.create(quiz=quiz, **q)
                    question_count += 1
            quiz_data["questions"] = questions

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {created_skills} skills, recruiter '{recruiter.username}', "
            f"{job_count} jobs, {len(QUIZZES)} quizzes (+{question_count} new questions)."
        ))
        self.stdout.write("Demo logins: " + ", ".join(
            f"{name} / {password}" for name, password in DEMO_PASSWORDS.items()
        ))