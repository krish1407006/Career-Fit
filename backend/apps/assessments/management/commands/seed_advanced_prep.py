"""Seed tough Amazon/Google style questions for DSA/OOPS/DBMS with difficulty levels."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.assessments.models import Question, Quiz

User = get_user_model()

QUIZZES = [
    {
        "title": "DSA Advanced (FAANG Style)",
        "category": "dsa",
        "difficulty": "hard",
        "description": "Tough array, string, stack/queue, recursion, tree, graph, DP style questions.",
        "duration_minutes": 60,
        "questions": [
            {"text": "Minimum window substring: when is a window valid?", "options": ["All required chars present with counts", "Any char present", "Length smallest", "Only first char"], "correct_index": 0, "topic": "Strings/Sliding Window", "difficulty": "hard", "explanation": "Valid when frequency map matches required."},
            {"text": "Trapping rain water uses which approach optimally?", "options": ["Brute force", "Two pointers with max left/right", "Stack only", "Recursion"], "correct_index": 1, "topic": "Arrays/Two Pointers", "difficulty": "hard", "explanation": "Two pointers with prefix/suffix max is efficient."},
            {"text": "Median of two sorted arrays requires?", "options": ["Merge and sort O((m+n)log(m+n)) trivial", "Binary search on smaller array O(log min(m,n))", "Linear scan always", "Heap only"], "correct_index": 1, "topic": "Arrays/Binary Search", "difficulty": "hard", "explanation": "Optimal uses binary search to find partition."},
            {"text": "Longest valid parentheses is best solved by?", "options": ["Stack", "Brute force only", "Hash table only", "Sorting"], "correct_index": 0, "topic": "Stack", "difficulty": "hard", "explanation": "Stack tracks indices of brackets."},
            {"text": "LRU Cache design needs?", "options": ["Array only", "HashMap + Doubly Linked List", "Stack", "Queue"], "correct_index": 1, "topic": "Design/Hashing", "difficulty": "hard", "explanation": "O(1) get/put with DLL + map."},
            {"text": "Serialize and Deserialize Binary Tree common method?", "options": ["Preorder with null markers", "Inorder only", "Level order no markers", "Sorting"], "correct_index": 0, "topic": "Trees/Serialization", "difficulty": "hard", "explanation": "Preorder + nulls allows reconstruction."},
            {"text": "Word Break II requires?", "options": ["DP table + backtracking with memo", "Greedy only", "Stack only", "Sorting"], "correct_index": 0, "topic": "DP/Trie", "difficulty": "hard", "explanation": "Need memoization for overlapping subproblems."},
            {"text": "Number of Islands uses?", "options": ["BFS/DFS on grid", "Sorting", "Binary search", "Stack only"], "correct_index": 0, "topic": "Graph/Grid", "difficulty": "medium", "explanation": "Explore connected land components."},
            {"text": "Course Schedule detects?", "options": ["Cycle in directed graph", "Cycle in undirected only", "Sorting", "BST property"], "correct_index": 0, "topic": "Graph/Topological", "difficulty": "hard", "explanation": "Kahn's or DFS cycle detection."},
            {"text": "Merge Intervals is solved by?", "options": ["Sort by start then merge", "Stack only", "Heap only", "Recursion"], "correct_index": 0, "topic": "Intervals", "difficulty": "medium", "explanation": "Sort by start time and merge overlaps."},
            {"text": "Largest rectangle in histogram uses?", "options": ["Monotonic stack", "Brute force O(n^3) only", "Queue", "Heap"], "correct_index": 0, "topic": "Stack", "difficulty": "hard", "explanation": "Monotonic stack gives O(n)."},
            {"text": "Edit Distance is classic?", "options": ["Greedy", "DP (Levenshtein)", "Sorting", "Two pointers"], "correct_index": 1, "topic": "DP", "difficulty": "hard", "explanation": "Standard 2D DP for insert/delete/replace."},
            {"text": "N-Queens problem approach?", "options": ["Backtracking with pruning", "Greedy only", "DP only", "Sorting"], "correct_index": 0, "topic": "Backtracking", "difficulty": "hard", "explanation": "Backtrack with column/diagonal checks."},
            {"text": "Sliding window maximum uses?", "options": ["Deque", "Stack", "Array", "Queue"], "correct_index": 0, "topic": "Sliding Window/Deque", "difficulty": "hard", "explanation": "Monotonic deque gives O(n)."},
            {"text": "Rotten Oranges uses?", "options": ["Multi-source BFS", "DFS only", "Binary search", "Stack"], "correct_index": 0, "topic": "Graph/BFS", "difficulty": "medium", "explanation": "Spread rot level by level."},
            {"text": "Word Ladder shortest path in terms of?", "options": ["Minimum number of transformations (BFS)", "Max length", "DFS depth", "Sorting"], "correct_index": 0, "topic": "Graph/BFS", "difficulty": "hard", "explanation": "BFS gives shortest path in unweighted."},
            {"text": "The Painter's Partition / Book Allocation similar to?", "options": ["Aggressive cows style binary search on answer", "Linear scan", "Sorting only", "Heap"], "correct_index": 0, "topic": "Binary Search/Greedy", "difficulty": "hard", "explanation": "Minimize max pages with binary search + greedy."},
            {"text": "Next Greater Element uses?", "options": ["Stack from right to left", "Queue", "Heap", "Array sort"], "correct_index": 0, "topic": "Stack", "difficulty": "medium", "explanation": "Monotonic stack gives next greater."},
            {"text": "Subsets with duplicates requires?", "options": ["Sort + skip duplicates", "No sort", "Stack only", "Queue"], "correct_index": 0, "topic": "Backtracking", "difficulty": "hard", "explanation": "Avoid duplicates by skipping when same as previous."},
            {"text": "Jump Game II uses?", "options": ["Greedy O(n)", "DP O(n^2)", "Brute force only", "Sorting"], "correct_index": 0, "topic": "Greedy/Array", "difficulty": "hard", "explanation": "Track end and farthest with jumps."},
            {"text": "Validate Binary Search Tree needs?", "options": ["Inorder must be sorted", "Preorder only", "Level order", "Postorder only"], "correct_index": 0, "topic": "Trees/BST", "difficulty": "medium", "explanation": "Inorder traversal gives sorted values."},
            {"text": "Diameter of Binary Tree uses?", "options": ["DFS returning height", "BFS only", "Inorder only", "Sorting"], "correct_index": 0, "topic": "Trees", "difficulty": "hard", "explanation": "Track max diameter via height."},
            {"text": "Best time to buy/sell stock IV is?", "options": ["State DP (hold/sell)", "Greedy only", "Sorting", "Stack"], "correct_index": 0, "topic": "DP/Stocks", "difficulty": "hard", "explanation": "Track states with k transactions."},
            {"text": "Implement Trie needs?", "options": ["Nodes with children map/array", "Array only", "Stack only", "Queue"], "correct_index": 0, "topic": "Trie", "difficulty": "medium", "explanation": "Trie node has children and end flag."},
            {"text": "Top K Frequent Elements uses?", "options": ["Hash map + heap/bucket sort", "Stack", "Queue", "Sorting array directly"], "correct_index": 0, "topic": "Heap/Hashing", "difficulty": "hard", "explanation": "Use min-heap or bucket sort by frequency."},
        ],
    },
    {
        "title": "OOPS Advanced (Amazon/Google Style)",
        "category": "oops",
        "difficulty": "hard",
        "description": "Design patterns, SOLID, real OOP interview questions.",
        "duration_minutes": 40,
        "questions": [
            {"text": "SOLID principle S means?", "options": ["Single Responsibility", "Singleton", "Static", "Simple"], "correct_index": 0, "topic": "SOLID", "difficulty": "medium", "explanation": "A class should have one reason to change."},
            {"text": "OCP states?", "options": ["Open for extension, closed for modification", "Open class only", "Overload/Override combined", "None"], "correct_index": 0, "topic": "SOLID", "difficulty": "medium", "explanation": "Extend behavior without modifying existing code."},
            {"text": "LSP means?", "options": ["Liskov Substitution Principle", "Least Square Principle", "Local Scope Principle", "None"], "correct_index": 0, "topic": "SOLID", "difficulty": "medium", "explanation": "Subtypes must be substitutable for base types."},
            {"text": "ISP means?", "options": ["Interface Segregation Principle", "Instance Segregation", "Internal State Principle", "None"], "correct_index": 0, "topic": "SOLID", "difficulty": "medium", "explanation": "No client should depend on unused interfaces."},
            {"text": "DIP means?", "options": ["Dependency Inversion Principle", "Data Inversion", "Direct Injection Principle", "None"], "correct_index": 0, "topic": "SOLID", "difficulty": "medium", "explanation": "Depend on abstractions, not concretions."},
            {"text": "Singleton pattern ensures?", "options": ["Only one instance", "Multiple instances", "No instances", "None"], "correct_index": 0, "topic": "Design Patterns", "difficulty": "medium", "explanation": "Single instance with global access point."},
            {"text": "Factory pattern is used for?", "options": ["Object creation without exposing logic", "Inheritance only", "Polymorphism only", "None"], "correct_index": 0, "topic": "Design Patterns", "difficulty": "medium", "explanation": "Creates objects via factory method/interface."},
            {"text": "Strategy pattern allows?", "options": ["Interchangeable algorithms", "Fixed algorithm", "Singleton only", "None"], "correct_index": 0, "topic": "Design Patterns", "difficulty": "hard", "explanation": "Define family of algorithms and make them interchangeable."},
            {"text": "Observer pattern is?", "options": ["Publish-subscribe", "Singleton", "Factory", "Builder"], "correct_index": 0, "topic": "Design Patterns", "difficulty": "hard", "explanation": "One-to-many dependency for notifications."},
            {"text": "Builder pattern solves?", "options": ["Complex object construction", "Simple objects only", "Singleton", "None"], "correct_index": 0, "topic": "Design Patterns", "difficulty": "hard", "explanation": "Step by step construction of complex objects."},
            {"text": "Difference between abstract class and interface?", "options": ["Abstract can have state/constructors; interface mostly contract", "Same always", "Interface has constructors", "None"], "correct_index": 0, "topic": "Abstraction", "difficulty": "hard", "explanation": "Key differences in state, constructors, multiple inheritance."},
            {"text": "Composition vs inheritance - prefer?", "options": ["Composition over inheritance", "Inheritance always", "None", "Both same"], "correct_index": 0, "topic": "Design", "difficulty": "hard", "explanation": "More flexible and avoids tight coupling."},
            {"text": "Method hiding vs overriding?", "options": ["Static method hiding, instance overriding", "Same", "None", "All"], "correct_index": 0, "topic": "Polymorphism", "difficulty": "hard", "explanation": "Hiding is compile-time for static."},
            {"text": "Can we override static method?", "options": ["No, method hiding occurs", "Yes always", "Yes in interfaces", "None"], "correct_index": 0, "topic": "Polymorphism", "difficulty": "hard", "explanation": "Static methods are not overridden."},
            {"text": "Encapsulation vs abstraction difference?", "options": ["Encapsulation = data hiding; abstraction = implementation hiding", "Same", "None", "All"], "correct_index": 0, "topic": "Concepts", "difficulty": "hard", "explanation": "Different purposes, often used together."},
            {"text": "What is cohesion?", "options": ["Degree of focus/responsibility", "Coupling", "Inheritance", "None"], "correct_index": 0, "topic": "OOD", "difficulty": "medium", "explanation": "High cohesion is desirable."},
            {"text": "What is coupling?", "options": ["Degree of dependency between classes", "Cohesion", "Polymorphism", "None"], "correct_index": 0, "topic": "OOD", "difficulty": "medium", "explanation": "Loose coupling is desirable."},
            {"text": "Real world example of polymorphism?", "options": ["A person as employee/student/parent", "Only one role", "None", "All"], "correct_index": 0, "topic": "Polymorphism", "difficulty": "medium", "explanation": "Same object behaves differently in contexts."},
            {"text": "Why use interfaces?", "options": ["Achieve abstraction and multiple inheritance", "Store data", "None", "All"], "correct_index": 0, "topic": "Interface", "difficulty": "medium", "explanation": "Define contracts."},
            {"text": "Constructor chaining?", "options": ["One constructor calls another", "Multiple classes", "None", "All"], "correct_index": 0, "topic": "Constructor", "difficulty": "medium", "explanation": "Using this() or super()."},
            {"text": "Object cloning types?", "options": ["Shallow and Deep", "Light and Dark", "Fast and Slow", "None"], "correct_index": 0, "topic": "Object", "difficulty": "hard", "explanation": "Shallow copies references, deep copies objects."},
            {"text": "Immutable class requirements?", "options": ["final class, final fields, no setters", "Only setters", "Public fields", "None"], "correct_index": 0, "topic": "Design", "difficulty": "hard", "explanation": "Prevent modification after creation."},
            {"text": "Exception handling in OOP?", "options": ["Try/catch, custom exceptions for domain", "Ignore", "None", "All"], "correct_index": 0, "topic": "Exceptions", "difficulty": "medium", "explanation": "Proper exception hierarchy."},
            {"text": "DRY principle?", "options": ["Don't Repeat Yourself", "Do Repeat Yourself", "None", "All"], "correct_index": 0, "topic": "Principles", "difficulty": "medium", "explanation": "Avoid code duplication."},
            {"text": "KISS principle?", "options": ["Keep It Simple Stupid", "Keep It Smart Stupid", "None", "All"], "correct_index": 0, "topic": "Principles", "difficulty": "medium", "explanation": "Prefer simplicity over complexity."},
        ],
    },
    {
        "title": "DBMS Advanced (Amazon/Google Style)",
        "category": "dbms",
        "difficulty": "hard",
        "description": "Transactions, concurrency, indexing, normalization, NoSQL.",
        "duration_minutes": 45,
        "questions": [
            {"text": "Dirty read occurs when?", "options": ["Read uncommitted data", "Read committed", "Serializable only", "None"], "correct_index": 0, "topic": "Concurrency", "difficulty": "hard", "explanation": "Transaction reads data from uncommitted transaction."},
            {"text": "Non-repeatable read?", "options": ["Different values on re-read in same transaction", "Same values", "None", "All"], "correct_index": 0, "topic": "Concurrency", "difficulty": "hard", "explanation": "Data changed by another committed transaction."},
            {"text": "Phantom read?", "options": ["New rows appear on re-execution", "Same rows", "None", "All"], "correct_index": 0, "topic": "Concurrency", "difficulty": "hard", "explanation": "Insert/delete by other transaction affects result set."},
            {"text": "Transaction isolation levels include?", "options": ["Read Uncommitted, Read Committed, Repeatable Read, Serializable", "Only Serializable", "None", "All"], "correct_index": 0, "topic": "Isolation", "difficulty": "hard", "explanation": "SQL standard isolation levels."},
            {"text": "Locking prevents?", "options": ["Concurrent conflicts", "Indexing", "Normalization", "None"], "correct_index": 0, "topic": "Locking", "difficulty": "medium", "explanation": "Ensures consistency under concurrency."},
            {"text": "Deadlock occurs when?", "options": ["Circular wait for locks", "Linear wait", "No locks", "None"], "correct_index": 0, "topic": "Deadlock", "difficulty": "hard", "explanation": "Two+ transactions wait for each other's locks."},
            {"text": "2PL (Two Phase Locking)?", "options": ["Growing then shrinking phase", "Single phase", "None", "All"], "correct_index": 0, "topic": "Concurrency Control", "difficulty": "hard", "explanation": "Ensures serializability."},
            {"text": "B+ Tree index is used because?", "options": ["Balanced, range queries efficient", "Unbalanced only", "Linear", "None"], "correct_index": 0, "topic": "Indexing", "difficulty": "hard", "explanation": "B+ trees good for range scans and disk."},
            {"text": "Clustered vs non-clustered index?", "options": ["Clustered sorts data rows; non-clustered points to them", "Same", "None", "All"], "correct_index": 0, "topic": "Indexing", "difficulty": "hard", "explanation": "One clustered per table usually."},
            {"text": "Covering index means?", "options": ["All columns in query covered by index", "Covers table", "None", "All"], "correct_index": 0, "topic": "Indexing", "difficulty": "hard", "explanation": "Avoids accessing base table."},
            {"text": "Denormalization is used for?", "options": ["Read performance", "Write normalization", "None", "All"], "correct_index": 0, "topic": "Normalization", "difficulty": "medium", "explanation": "Trade redundancy for faster reads."},
            {"text": "BCNF is stricter than 3NF?", "options": ["Yes in some cases", "No always", "Same", "None"], "correct_index": 0, "topic": "Normalization", "difficulty": "hard", "explanation": "Every determinant must be candidate key."},
            {"text": "Functional dependency X->Y means?", "options": ["Y determined by X", "X by Y", "None", "All"], "correct_index": 0, "topic": "Normalization", "difficulty": "medium", "explanation": "For same X, Y same."},
            {"text": "Multivalued dependency leads to?", "options": ["4NF", "1NF", "2NF", "3NF"], "correct_index": 0, "topic": "Normalization", "difficulty": "hard", "explanation": "4NF deals with MVDs."},
            {"text": "Lossless join decomposition means?", "options": ["Natural join gives original relation", "Loses data", "None", "All"], "correct_index": 0, "topic": "Decomposition", "difficulty": "hard", "explanation": "No spurious tuples, no loss."},
            {"text": "CAP theorem?", "options": ["Consistency, Availability, Partition tolerance - pick 2", "CAP only", "None", "All"], "correct_index": 0, "topic": "Distributed DB", "difficulty": "hard", "explanation": "In distributed systems tradeoffs."},
            {"text": "Sharding vs replication?", "options": ["Sharding = horizontal partition; replication = copies", "Same", "None", "All"], "correct_index": 0, "topic": "Distributed DB", "difficulty": "hard", "explanation": "Different scaling strategies."},
            {"text": "ACID vs BASE?", "options": ["ACID strong consistency; BASE eventual consistency", "Same", "None", "All"], "correct_index": 0, "topic": "NoSQL", "difficulty": "hard", "explanation": "BASE for NoSQL scalability."},
            {"text": "Document DB (MongoDB) stores?", "options": ["JSON-like documents", "Rows only", "Columns only", "Graphs"], "correct_index": 0, "topic": "NoSQL", "difficulty": "medium", "explanation": "BSON documents."},
            {"text": "Column family store example?", "options": ["Cassandra", "MySQL", "Postgres", "SQLite"], "correct_index": 0, "topic": "NoSQL", "difficulty": "medium", "explanation": "Wide-column stores."},
            {"text": "Graph DB example?", "options": ["Neo4j", "MongoDB", "Cassandra", "Redis"], "correct_index": 0, "topic": "NoSQL", "difficulty": "medium", "explanation": "Nodes and relationships."},
            {"text": "Materialized view vs view?", "options": ["Materialized stored physically; view virtual", "Same", "None", "All"], "correct_index": 0, "topic": "Views", "difficulty": "medium", "explanation": "Materialized can be refreshed."},
            {"text": "Cursor in SQL used for?", "options": ["Row by row processing", "Bulk only", "None", "All"], "correct_index": 0, "topic": "PL/SQL", "difficulty": "medium", "explanation": "Process result set row by row."},
            {"text": "Optimistic vs pessimistic locking?", "options": ["Optimistic assumes no conflict; pessimistic locks early", "Same", "None", "All"], "correct_index": 0, "topic": "Locking", "difficulty": "hard", "explanation": "Different concurrency strategies."},
            {"text": "Query optimization goal?", "options": ["Minimize I/O and response time", "Maximize I/O", "None", "All"], "correct_index": 0, "topic": "Optimization", "difficulty": "medium", "explanation": "Efficient execution plans."},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed tough Amazon/Google style questions for DSA/OOPS/DBMS grouped by difficulty."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing questions in these advanced quizzes first.")

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
            easy = sum(1 for q in questions if q.get("difficulty") == "easy")
            med = sum(1 for q in questions if q.get("difficulty") == "medium")
            hard = sum(1 for q in questions if q.get("difficulty") == "hard")
            self.stdout.write(f"{quiz.title}: +{added} (E:{easy} M:{med} H:{hard})")

        self.stdout.write(self.style.SUCCESS(f"Done. Added {total_q} tough questions with difficulty split."))
