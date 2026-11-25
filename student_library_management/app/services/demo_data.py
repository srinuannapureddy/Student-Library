from datetime import datetime, timedelta
from decimal import Decimal
from app.extensions import db
from app.models.user import User, ROLE_ADMIN, ROLE_LIBRARIAN, ROLE_STUDENT, STATUS_ACTIVE
from app.models.category import Category
from app.models.book import Book
from app.models.book_copy import BookCopy, COPY_AVAILABLE, COPY_ISSUED, COPY_MAINTENANCE
from app.models.borrow_request import BorrowRequest, REQ_PENDING
from app.models.loan import Loan, LOAN_ACTIVE
from app.models.fine import Fine, FINE_UNPAID
from app.models.library_setting import LibrarySetting
from app.models.notification import Notification


def seed(password="Pass1234"):
    """Populate database with rich demo data for instant testing."""
    LibrarySetting.seed_defaults()

    # 1. Categories
    category_map = {}
    categories_data = [
        ("Computer Science", "Software engineering, algorithms, architectures, and programming languages."),
        ("Mathematics & Physics", "Foundational mathematics, calculus, linear algebra, and physics."),
        ("Literature & Fiction", "Classic literature, modern fiction, drama, and anthologies."),
        ("History & Philosophy", "World history, philosophical treatises, and civilizations."),
        ("Science & Nature", "Cosmology, evolutionary biology, chemistry, and environmental science."),
    ]
    for name, desc in categories_data:
        cat = Category.query.filter_by(category_name=name).first()
        if not cat:
            cat = Category(category_name=name, description=desc)
            db.session.add(cat)
            db.session.flush()
        category_map[name] = cat

    # 2. Users
    users_data = [
        ("admin@library.edu", "System Administrator", ROLE_ADMIN, None, "+15550000001"),
        ("librarian@library.edu", "Eleanor Vance (Librarian)", ROLE_LIBRARIAN, None, "+15550000002"),
        ("alice@student.edu", "Alice Johnson", ROLE_STUDENT, "STU-1001", "+15550001001"),
        ("bob@student.edu", "Bob Smith", ROLE_STUDENT, "STU-1002", "+15550001002"),
        ("charlie@student.edu", "Charlie Davis", ROLE_STUDENT, "STU-1003", "+15550001003"),
    ]
    created_users = {}
    for email, name, role, stu_id, phone in users_data:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                full_name=name,
                email=email,
                role=role,
                student_id=stu_id,
                phone=phone,
                account_status=STATUS_ACTIVE
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
        created_users[email] = user

    admin_user = created_users["admin@library.edu"]
    librarian_user = created_users["librarian@library.edu"]
    alice = created_users["alice@student.edu"]
    bob = created_users["bob@student.edu"]
    charlie = created_users["charlie@student.edu"]

    # 3. Books
    books_data = [
        {
            "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
            "author": "Robert C. Martin",
            "isbn": "9780132350884",
            "publisher": "Prentice Hall",
            "edition": "1st Edition",
            "year": 2008,
            "category": "Computer Science",
            "copies": 3,
            "description": "Even bad code can function. But if code isn't clean, it can bring a development organization to its knees. Every year, countless hours and significant resources are lost because of poorly written code."
        },
        {
            "title": "Introduction to Algorithms",
            "author": "Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein",
            "isbn": "9780262033848",
            "publisher": "MIT Press",
            "edition": "3rd Edition",
            "year": 2009,
            "category": "Computer Science",
            "copies": 4,
            "description": "A comprehensive textbook covering the modern study of computer algorithms with depth, rigor, and elementary explanations."
        },
        {
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "isbn": "9781449373320",
            "publisher": "O'Reilly Media",
            "edition": "1st Edition",
            "year": 2017,
            "category": "Computer Science",
            "copies": 3,
            "description": "The definitive guide to the architecture of data systems, covering transactions, replication, partitioning, and stream processing."
        },
        {
            "title": "The Pragmatic Programmer",
            "author": "Andrew Hunt, David Thomas",
            "isbn": "9780201616224",
            "publisher": "Addison-Wesley",
            "edition": "20th Anniversary Edition",
            "year": 2019,
            "category": "Computer Science",
            "copies": 3,
            "description": "One of the most significant books in computer science, detailing classic philosophies and practical software development wisdom."
        },
        {
            "title": "Linear Algebra and Its Applications",
            "author": "Gilbert Strang",
            "isbn": "9780030105678",
            "publisher": "Cengage Learning",
            "edition": "4th Edition",
            "year": 2005,
            "category": "Mathematics & Physics",
            "copies": 2,
            "description": "Renowned professor Gilbert Strang presents a lucid, conceptual foundation for linear algebra and its wide-ranging modern applications."
        },
        {
            "title": "A Brief History of Time",
            "author": "Stephen Hawking",
            "isbn": "9780553380163",
            "publisher": "Bantam Books",
            "edition": "Updated Edition",
            "year": 1998,
            "category": "Science & Nature",
            "copies": 3,
            "description": "Hawking's worldwide bestseller explores profound questions about time, the universe, black holes, and the origins of space."
        },
        {
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "isbn": "9780061120084",
            "publisher": "Harper Perennial",
            "edition": "50th Anniversary Edition",
            "year": 2006,
            "category": "Literature & Fiction",
            "copies": 3,
            "description": "The Pulitzer Prize-winning masterpiece set in the American South, examining racial injustice and childhood empathy."
        },
        {
            "title": "1984",
            "author": "George Orwell",
            "isbn": "9780451524935",
            "publisher": "Signet Classics",
            "edition": "Reprint Edition",
            "year": 1950,
            "category": "Literature & Fiction",
            "copies": 4,
            "description": "The seminal dystopian classic that introduced Big Brother, the Thought Police, and totalitarian warnings that resonate through the ages."
        },
        {
            "title": "Sapiens: A Brief History of Humankind",
            "author": "Yuval Noah Harari",
            "isbn": "9780062316097",
            "publisher": "Harper",
            "edition": "1st Edition",
            "year": 2015,
            "category": "History & Philosophy",
            "copies": 3,
            "description": "An ambitious and accessible overview of human evolution, cognition, agriculture, capitalism, and technological futures."
        }
    ]

    all_copies = []
    for bdata in books_data:
        book = Book.query.filter_by(isbn=bdata["isbn"]).first()
        if not book:
            cat = category_map[bdata["category"]]
            book = Book(
                title=bdata["title"],
                author=bdata["author"],
                isbn=bdata["isbn"],
                publisher=bdata["publisher"],
                edition=bdata["edition"],
                publication_year=bdata["year"],
                category_id=cat.id,
                description=bdata["description"]
            )
            db.session.add(book)
            db.session.flush()

            for i in range(1, bdata["copies"] + 1):
                acc = f"{book.isbn[:5]}-{book.id:04d}-{i:03d}"
                copy = BookCopy(book_id=book.id, accession_number=acc, status=COPY_AVAILABLE)
                db.session.add(copy)
                db.session.flush()
                all_copies.append(copy)

    # 4. Create sample interactions if no loans exist yet
    if Loan.query.count() == 0 and len(all_copies) >= 3:
        now = datetime.utcnow()

        # Active normal loan for Alice (due in 10 days)
        c1 = all_copies[0]
        c1.status = COPY_ISSUED
        loan1 = Loan(
            student_id=alice.id,
            book_copy_id=c1.id,
            issued_by=librarian_user.id,
            issued_at=now - timedelta(days=4),
            due_date=now + timedelta(days=10),
            status=LOAN_ACTIVE,
            active_copy_key=c1.id
        )
        db.session.add(loan1)

        # Overdue loan for Bob (due 3 days ago -> fine)
        c2 = all_copies[1]
        c2.status = COPY_ISSUED
        due_overdue = now - timedelta(days=3)
        loan2 = Loan(
            student_id=bob.id,
            book_copy_id=c2.id,
            issued_by=librarian_user.id,
            issued_at=now - timedelta(days=17),
            due_date=due_overdue,
            status=LOAN_ACTIVE,
            active_copy_key=c2.id
        )
        db.session.add(loan2)
        db.session.flush()

        fine = Fine(
            loan_id=loan2.id,
            amount=Decimal("15.00"),
            days_overdue=3,
            payment_status=FINE_UNPAID,
            created_at=now
        )
        db.session.add(fine)

        # Pending borrow request for Charlie
        b3 = all_copies[2].book
        req = BorrowRequest(
            student_id=charlie.id,
            book_id=b3.id,
            status=REQ_PENDING,
            request_date=now - timedelta(hours=5)
        )
        db.session.add(req)

        # Welcome notifications
        for s in [alice, bob, charlie]:
            db.session.add(Notification(
                user_id=s.id,
                title="Welcome to Student Library",
                message="Your library membership is active! Explore books and submit borrow requests online.",
                notification_type="success"
            ))

    db.session.commit()
    return f"Demo data seeded successfully! Accounts created with password '{password}' (admin@library.edu, librarian@library.edu, alice@student.edu)."

