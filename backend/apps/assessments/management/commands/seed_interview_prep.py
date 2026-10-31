"""Seed technical interview prep question banks (DSA, OOPS, DBMS)."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.assessments.models import Question, Quiz

User = get_user_model()

QUIZZES = [
    {
        "title": "DSA Fundamentals",
        "category": "dsa",
        "difficulty": "medium",
        "description": "Arrays, stacks, queues, recursion, sorting and searching.",
        "duration_minutes": 40,
        "questions": [
            {"text": "What is the time complexity of binary search?", "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"], "correct_index": 1, "topic": "Search", "difficulty": "easy", "explanation": "Binary search halves the range each step."},
            {"text": "Which data structure uses LIFO?", "options": ["Queue", "Stack", "Heap", "Tree"], "correct_index": 1, "topic": "Stack", "difficulty": "easy", "explanation": "Stack follows Last In First Out."},
            {"text": "Which traversal of BST gives sorted order?", "options": ["Preorder", "Inorder", "Postorder", "Level order"], "correct_index": 1, "topic": "Trees", "difficulty": "medium", "explanation": "Inorder traversal of BST is ascending."},
            {"text": "Time complexity of bubble sort in worst case?", "options": ["O(n)", "O(log n)", "O(n^2)", "O(n log n)"], "correct_index": 2, "topic": "Sorting", "difficulty": "easy", "explanation": "Bubble sort does O(n^2) comparisons in worst case."},
            {"text": "Which data structure is best for BFS?", "options": ["Stack", "Queue", "Priority Queue", "Hash Table"], "correct_index": 1, "topic": "Graph", "difficulty": "medium", "explanation": "BFS uses a queue."},
            {"text": "What is the space complexity of merge sort?", "options": ["O(1)", "O(n)", "O(log n)", "O(n^2)"], "correct_index": 1, "topic": "Sorting", "difficulty": "medium", "explanation": "Merge sort needs O(n) auxiliary space."},
            {"text": "Recursion uses which memory?", "options": ["Heap", "Stack", "Queue", "Cache"], "correct_index": 1, "topic": "Recursion", "difficulty": "easy", "explanation": "Recursive calls go on call stack."},
            {"text": "Which is not a linear data structure?", "options": ["Array", "Stack", "Tree", "Queue"], "correct_index": 2, "topic": "Basics", "difficulty": "easy", "explanation": "Tree is non-linear."},
            {"text": "Hash table average lookup time?", "options": ["O(n)", "O(log n)", "O(1)", "O(n^2)"], "correct_index": 2, "topic": "Hashing", "difficulty": "medium", "explanation": "Hash table gives O(1) average lookup."},
            {"text": "Which sorting is in-place and unstable?", "options": ["Merge sort", "Bubble sort", "Quick sort", "Insertion sort"], "correct_index": 2, "topic": "Sorting", "difficulty": "hard", "explanation": "Quick sort is in-place but not stable."},
            {"text": "Stack operation to remove top element?", "options": ["push", "pop", "peek", "top"], "correct_index": 1, "topic": "Stack", "difficulty": "easy", "explanation": "pop removes top element."},
            {"text": "Queue follows which principle?", "options": ["LIFO", "FIFO", "FILO", "LILO"], "correct_index": 1, "topic": "Queue", "difficulty": "easy", "explanation": "FIFO - First In First Out."},
            {"text": "Which is used for priority-based processing?", "options": ["Stack", "Queue", "Heap/Priority Queue", "Array"], "correct_index": 2, "topic": "Heap", "difficulty": "medium", "explanation": "Priority queue uses heap structure."},
            {"text": "Best case of insertion sort?", "options": ["O(n^2)", "O(n log n)", "O(n)", "O(1)"], "correct_index": 2, "topic": "Sorting", "difficulty": "medium", "explanation": "Already sorted array gives O(n)."},
            {"text": "Number of edges in a tree with n nodes?", "options": ["n", "n-1", "n+1", "2n"], "correct_index": 1, "topic": "Trees", "difficulty": "easy", "explanation": "Tree has n-1 edges."},
            {"text": "Which traversal uses stack?", "options": ["BFS", "Level order", "DFS", "None"], "correct_index": 2, "topic": "Traversal", "difficulty": "medium", "explanation": "DFS uses stack (implicit/explicit)."},
            {"text": "Dynamic array is also called?", "options": ["Linked list", "Vector/ArrayList", "Stack", "Queue"], "correct_index": 1, "topic": "Arrays", "difficulty": "easy", "explanation": "Vector/ArrayList is dynamic array."},
            {"text": "Which is true about linked list vs array?", "options": ["Array has better insert/delete at middle", "Linked list has fixed size", "Linked list allows dynamic size", "Array elements not contiguous"], "correct_index": 2, "topic": "Linked List", "difficulty": "medium", "explanation": "Linked list is dynamic in size."},
            {"text": "Time complexity of accessing array element by index?", "options": ["O(n)", "O(log n)", "O(1)", "O(n^2)"], "correct_index": 2, "topic": "Arrays", "difficulty": "easy", "explanation": "Direct indexing gives O(1)."},
            {"text": "Which structure is used for function calls?", "options": ["Queue", "Stack", "Heap", "Graph"], "correct_index": 1, "topic": "Stack", "difficulty": "easy", "explanation": "Call stack manages function calls."},
            {"text": "Dijkstra's algorithm finds?", "options": ["MST", "Shortest path from source", "Sorting", "DFS order"], "correct_index": 1, "topic": "Graph", "difficulty": "hard", "explanation": "Dijkstra finds shortest paths from single source."},
            {"text": "Which is a self-balancing BST?", "options": ["Binary Tree", "AVL Tree", "Linked List", "Array"], "correct_index": 1, "topic": "Trees", "difficulty": "medium", "explanation": "AVL is self-balancing BST."},
            {"text": "Worst case for linear search?", "options": ["Element found first", "O(1)", "O(n)", "O(log n)"], "correct_index": 2, "topic": "Search", "difficulty": "easy", "explanation": "Linear search scans all in worst case."},
            {"text": "Heap is used to implement?", "options": ["Stack", "Queue", "Priority Queue", "Linked List"], "correct_index": 2, "topic": "Heap", "difficulty": "medium", "explanation": "Heap efficiently implements priority queue."},
            {"text": "Kruskal's algorithm is used for?", "options": ["Shortest path", "Minimum Spanning Tree", "Sorting", "Searching"], "correct_index": 1, "topic": "Graph", "difficulty": "hard", "explanation": "Kruskal finds MST."},
        ],
    },
    {
        "title": "OOPS Concepts",
        "category": "oops",
        "difficulty": "medium",
        "description": "Encapsulation, inheritance, polymorphism, abstraction.",
        "duration_minutes": 35,
        "questions": [
            {"text": "OOPS stands for?", "options": ["Object Oriented Programming System", "Object Oriented Programming Structure", "Oriented Object Programming System", "None"], "correct_index": 0, "topic": "Basics", "difficulty": "easy", "explanation": "Object Oriented Programming System/Structure."},
            {"text": "Which is not a pillar of OOPS?", "options": ["Encapsulation", "Compilation", "Polymorphism", "Inheritance"], "correct_index": 1, "topic": "Pillars", "difficulty": "easy", "explanation": "Four pillars: Encapsulation, Abstraction, Inheritance, Polymorphism."},
            {"text": "Wrapping data and methods together is?", "options": ["Abstraction", "Encapsulation", "Inheritance", "Polymorphism"], "correct_index": 1, "topic": "Encapsulation", "difficulty": "easy", "explanation": "Encapsulation binds data and methods."},
            {"text": "Hiding implementation details is?", "options": ["Abstraction", "Encapsulation", "Inheritance", "Overloading"], "correct_index": 0, "topic": "Abstraction", "difficulty": "easy", "explanation": "Abstraction hides complexity."},
            {"text": "Acquiring properties of parent class?", "options": ["Polymorphism", "Inheritance", "Encapsulation", "Abstraction"], "correct_index": 1, "topic": "Inheritance", "difficulty": "easy", "explanation": "Inheritance reuses parent properties."},
            {"text": "Many forms of same method is?", "options": ["Inheritance", "Polymorphism", "Encapsulation", "Abstraction"], "correct_index": 1, "topic": "Polymorphism", "difficulty": "easy", "explanation": "Polymorphism means one interface many forms."},
            {"text": "Method overloading is?", "options": ["Same method different params", "Same method same params", "Different classes", "None"], "correct_index": 0, "topic": "Overloading", "difficulty": "medium", "explanation": "Compile-time polymorphism via overloading."},
            {"text": "Method overriding is?", "options": ["Same signature in child", "Different signature", "Same class", "None"], "correct_index": 0, "topic": "Overriding", "difficulty": "medium", "explanation": "Runtime polymorphism via overriding."},
            {"text": "Which allows multiple inheritance in Java?", "options": ["Classes", "Interfaces", "Objects", "Arrays"], "correct_index": 1, "topic": "Inheritance", "difficulty": "medium", "explanation": "Java allows multiple inheritance via interfaces."},
            {"text": "Class can have objects?", "options": ["Yes", "No", "Only once", "Never"], "correct_index": 0, "topic": "Class/Object", "difficulty": "easy", "explanation": "Objects are instances of class."},
            {"text": "Blueprint of an object is?", "options": ["Object", "Class", "Method", "Variable"], "correct_index": 1, "topic": "Class/Object", "difficulty": "easy", "explanation": "Class is blueprint."},
            {"text": "Which keyword prevents inheritance?", "options": ["static", "final", "this", "super"], "correct_index": 1, "topic": "Inheritance", "difficulty": "medium", "explanation": "final class cannot be inherited."},
            {"text": "Constructor is called when?", "options": ["Class created", "Object created", "Method called", "Program ends"], "correct_index": 1, "topic": "Constructor", "difficulty": "easy", "explanation": "Constructor runs on object creation."},
            {"text": "this keyword refers to?", "options": ["Parent class", "Current object", "Static method", "Interface"], "correct_index": 1, "topic": "Keywords", "difficulty": "easy", "explanation": "this refers to current instance."},
            {"text": "super keyword refers to?", "options": ["Child", "Parent", "Current", "None"], "correct_index": 1, "topic": "Keywords", "difficulty": "easy", "explanation": "super refers to parent class."},
            {"text": "Abstract class can have?", "options": ["Only abstract methods", "Abstract and concrete methods", "Only variables", "None"], "correct_index": 1, "topic": "Abstraction", "difficulty": "medium", "explanation": "Abstract class can have both."},
            {"text": "Interface methods are by default?", "options": ["private", "public abstract", "protected", "static only"], "correct_index": 1, "topic": "Interface", "difficulty": "medium", "explanation": "Interface methods are public abstract by default."},
            {"text": "Access specifier visible everywhere?", "options": ["private", "protected", "public", "default"], "correct_index": 2, "topic": "Access", "difficulty": "easy", "explanation": "public has widest access."},
            {"text": "private members accessible in?", "options": ["Same class only", "Child class", "Same package", "All"], "correct_index": 0, "topic": "Access", "difficulty": "easy", "explanation": "private is class-level only."},
            {"text": "static keyword means?", "options": ["Per object", "Class level", "Instance only", "Local"], "correct_index": 1, "topic": "Static", "difficulty": "easy", "explanation": "static belongs to class."},
            {"text": "Which is runtime polymorphism?", "options": ["Overloading", "Overriding", "Casting", "None"], "correct_index": 1, "topic": "Polymorphism", "difficulty": "medium", "explanation": "Overriding is resolved at runtime."},
            {"text": "Which is compile-time polymorphism?", "options": ["Overriding", "Overloading", "Inheritance", "None"], "correct_index": 1, "topic": "Polymorphism", "difficulty": "medium", "explanation": "Overloading resolved at compile time."},
            {"text": "Can we create object of abstract class?", "options": ["Yes", "No", "Sometimes", "Always"], "correct_index": 1, "topic": "Abstraction", "difficulty": "medium", "explanation": "Abstract class cannot be instantiated."},
            {"text": "Composition is?", "options": ["is-a", "has-a", "was-a", "does-a"], "correct_index": 1, "topic": "Relationships", "difficulty": "medium", "explanation": "Composition is has-a relationship."},
            {"text": "Aggregation is?", "options": ["Strong has-a", "Weak has-a", "is-a", "None"], "correct_index": 1, "topic": "Relationships", "difficulty": "medium", "explanation": "Aggregation is weak association."},
        ],
    },
    {
        "title": "DBMS Interview Prep",
        "category": "dbms",
        "difficulty": "medium",
        "description": "Keys, normalization, transactions, SQL concepts.",
        "duration_minutes": 40,
        "questions": [
            {"text": "DBMS stands for?", "options": ["Database Management System", "Data Base Management Software", "Digital Base Management System", "None"], "correct_index": 0, "topic": "Basics", "difficulty": "easy", "explanation": "Database Management System."},
            {"text": "Which is not a DBMS?", "options": ["MySQL", "Oracle", "MS Word", "Postgres"], "correct_index": 2, "topic": "Basics", "difficulty": "easy", "explanation": "MS Word is not a DBMS."},
            {"text": "Primary key does not allow?", "options": ["Duplicates and NULL", "Duplicates only", "NULL only", "None"], "correct_index": 0, "topic": "Keys", "difficulty": "easy", "explanation": "PK is unique and not null."},
            {"text": "Foreign key refers to?", "options": ["Same table", "Primary key of another table", "Index", "View"], "correct_index": 1, "topic": "Keys", "difficulty": "easy", "explanation": "FK references PK of parent table."},
            {"text": "Candidate key is?", "options": ["Minimal super key", "Foreign key", "Composite only", "None"], "correct_index": 0, "topic": "Keys", "difficulty": "medium", "explanation": "Candidate key is minimal set of attributes uniquely identifying tuple."},
            {"text": "Super key may have?", "options": ["Extra attributes", "Only PK", "No attributes", "None"], "correct_index": 0, "topic": "Keys", "difficulty": "medium", "explanation": "Super key can have redundant attributes."},
            {"text": "Normalization reduces?", "options": ["Redundancy", "Speed", "Size only", "None"], "correct_index": 0, "topic": "Normalization", "difficulty": "easy", "explanation": "Normalization removes redundancy."},
            {"text": "1NF requires?", "options": ["Atomic values", "No transitive dependency", "BCNF", "None"], "correct_index": 0, "topic": "Normalization", "difficulty": "medium", "explanation": "1NF needs atomic (indivisible) values."},
            {"text": "2NF is in 1NF and no?", "options": ["Partial dependency", "Transitive", "Multivalued", "None"], "correct_index": 0, "topic": "Normalization", "difficulty": "medium", "explanation": "2NF removes partial dependencies."},
            {"text": "3NF removes?", "options": ["Transitive dependency", "Partial", "Atomic", "None"], "correct_index": 0, "topic": "Normalization", "difficulty": "medium", "explanation": "3NF removes transitive dependencies."},
            {"text": "ACID stands for?", "options": ["Atomicity Consistency Isolation Durability", "Accuracy Consistency Integrity Durability", "None", "All"], "correct_index": 0, "topic": "Transactions", "difficulty": "easy", "explanation": "ACID properties of transactions."},
            {"text": "Atomicity means?", "options": ["All or nothing", "Consistent", "Isolated", "Durable"], "correct_index": 0, "topic": "Transactions", "difficulty": "easy", "explanation": "Transaction fully done or rolled back."},
            {"text": "Durability means?", "options": ["Permanent after commit", "Temporary", "Isolated", "None"], "correct_index": 0, "topic": "Transactions", "difficulty": "easy", "explanation": "Changes persist after commit."},
            {"text": "DDL stands for?", "options": ["Data Definition Language", "Data Design Language", "None", "All"], "correct_index": 0, "topic": "SQL", "difficulty": "easy", "explanation": "DDL defines schema (CREATE/ALTER/DROP)."},
            {"text": "DML stands for?", "options": ["Data Manipulation Language", "Data Model Language", "None", "All"], "correct_index": 0, "topic": "SQL", "difficulty": "easy", "explanation": "DML manipulates data (INSERT/UPDATE/DELETE)."},
            {"text": "TRUNCATE is?", "options": ["DDL", "DML", "DCL", "TCL"], "correct_index": 0, "topic": "SQL", "difficulty": "medium", "explanation": "TRUNCATE is DDL (auto-commits)."},
            {"text": "DELETE vs TRUNCATE?", "options": ["DELETE can have WHERE", "TRUNCATE can have WHERE", "Same", "None"], "correct_index": 0, "topic": "SQL", "difficulty": "medium", "explanation": "DELETE supports WHERE, TRUNCATE doesn't."},
            {"text": "Index is used for?", "options": ["Faster search", "Slower", "Storage only", "None"], "correct_index": 0, "topic": "Indexing", "difficulty": "easy", "explanation": "Indexes speed up queries."},
            {"text": "View is?", "options": ["Virtual table", "Real table", "Index", "Trigger"], "correct_index": 0, "topic": "Views", "difficulty": "easy", "explanation": "View is a stored query (virtual table)."},
            {"text": "Trigger is?", "options": ["Automatic action", "Manual", "None", "All"], "correct_index": 0, "topic": "Triggers", "difficulty": "medium", "explanation": "Trigger fires on events."},
            {"text": "JOIN returns?", "options": ["Combined rows", "Deleted", "None", "All"], "correct_index": 0, "topic": "Joins", "difficulty": "easy", "explanation": "JOIN combines related tables."},
            {"text": "Cartesian product comes from?", "options": ["CROSS JOIN", "INNER JOIN", "LEFT JOIN", "None"], "correct_index": 0, "topic": "Joins", "difficulty": "medium", "explanation": "CROSS JOIN gives Cartesian product."},
            {"text": "Unique constraint allows?", "options": ["One NULL", "Many NULLs", "No NULLs", "None"], "correct_index": 1, "topic": "Constraints", "difficulty": "medium", "explanation": "UNIQUE allows multiple NULLs in most DBs."},
            {"text": "Entity Relationship model uses?", "options": ["Entities and relationships", "Tables only", "Files", "None"], "correct_index": 0, "topic": "ER Model", "difficulty": "easy", "explanation": "ER model uses entities/relationships/attributes."},
            {"text": "Which is NoSQL?", "options": ["MongoDB", "MySQL", "Postgres", "Oracle"], "correct_index": 0, "topic": "NoSQL", "difficulty": "easy", "explanation": "MongoDB is document NoSQL."},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed DSA, OOPS, and DBMS interview prep question banks (100+ questions)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing questions in these quizzes first.")

    def handle(self, *args, **options):
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.filter(username="admin").first()
        if admin_user is None:
            self.stdout.write(self.style.ERROR("No admin user found. Run seed_demo first."))
            return

        total_q = 0
        for quiz_data in QUIZZES:
            questions = quiz_data.pop("questions")
            quiz, created = Quiz.objects.get_or_create(
                title=quiz_data["title"], defaults={**quiz_data, "created_by": admin_user}
            )
            if not created:
                for field, value in quiz_data.items():
                    setattr(quiz, field, value)
                quiz.is_active = True
                quiz.save(update_fields=list(quiz_data.keys()) + ["is_active"])
                if options["reset"]:
                    quiz.questions.all().delete()
            existing = set(quiz.questions.values_list("text", flat=True))
            added = 0
            for q in questions:
                if q["text"] not in existing:
                    Question.objects.create(quiz=quiz, **q)
                    added += 1
            total_q += added
            quiz_data["questions"] = questions
            self.stdout.write(f"{quiz.title}: +{added} questions")

        self.stdout.write(self.style.SUCCESS(f"Done. Added {total_q} new questions across DSA/OOPS/DBMS."))
