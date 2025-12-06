import sqlite3
from datetime import datetime, timedelta

# Database setup
def init_db():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # Books Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY,
        title TEXT,
        author TEXT,
        genre TEXT,
        isbn TEXT,
        quantity INTEGER
    )''')

    # Members Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY,
        name TEXT,
        membership_date TEXT
    )''')


    # Transactions Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        book_id INTEGER,
        member_id INTEGER,
        issue_date TEXT,
        return_date TEXT,
        fine REAL,
        FOREIGN KEY(book_id) REFERENCES books(id),
        FOREIGN KEY(member_id) REFERENCES members(id)
    )''')
    conn.commit()
    conn.close()

# Utility Functions
def calculate_fine(transaction_id, current_date=None):
    """Calculate fine with optional simulated time input."""
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # fetch transaction details
    cursor.execute("SELECT book_id, issue_date FROM transactions WHERE id = ?", (transaction_id,))
    transaction = cursor.fetchone()
    if not transaction:
        conn.close()
        return 0

    book_id, issue_date = transaction
    issue_date = datetime.strptime(issue_date, "%Y-%m-%d")
    return_date = datetime.now() if current_date is None else datetime.strptime(current_date, "%Y-%m-%d")

    overdue_days = (return_date - issue_date).days - 3 # First three days are free
    if overdue_days > 0:
        cursor.execute("SELECT genre FROM books WHERE id = ?", (book_id,))
        genre = cursor.fetchone()[0]
        fine_rate = 2 if genre.lower() == "fiction" else 1
        fine = overdue_days * fine_rate
    else:
        fine = 0

    conn.close()
    return fine

def can_borrow_more_books(member_id):
    """Check if the member has already borrowed the maximum number of books."""
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ? AND return_date IS NULL", (member_id,))
    borrowed_count = cursor.fetchone()[0]
    conn.close()

    return borrowed_count < 3 # Specify the number of books that can be borrowed

def has_unpaid_fines(member_id):
    """Check if the member has unpaid fines."""
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("SELECT fine FROM transactions WHERE member_id = ? AND fine > 0 AND return_date IS NOT NULL", (member_id,))
    unpaid_fines = cursor.fetchall()
    conn.close()

    return len(unpaid_fines) > 0

# Book Management
def add_book(title, author, genre, isbn, quantity):
    if quantity <= 0:
        print("Error: Quantity must be greater than 0!")
        return
    if quantity > 10:
        print("Error: Quantity cannot exceed 10 for each book!")
        return

    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO books (title, author, genre, isbn, quantity) VALUES (?, ?, ?, ?, ?)",
                   (title, author, genre, isbn, quantity))
    conn.commit()
    conn.close()
    print("Book added successfully!")

def view_all_books():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    conn.close()

    if books:
        print("\nBooks in Library:")
        print("ID | Title | Author | Genre | ISBN | Quantity")
        print("-" * 50)
        for book in books:
            print(f"{book[0]} | {book[1]} | {book[2]} | {book[3]} | {book[4]} | {book[5]}")
    else:
        print("No books found in the library!")

def delete_book(book_id):
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # Check if any member has borrowed this book
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE book_id = ? AND return_date IS NULL", (book_id,))
    borrowed_count = cursor.fetchone()[0]
    
    if borrowed_count > 0:
        print("Cannot delete the book, it is currently borrowed by a member!")
        conn.close()
        return

    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    if not book:
        print("Book not found!")
        conn.close()
        return

    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    print("Book deleted successfully!")

def add_book_quantity(book_id, quantity):
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("SELECT quantity FROM books WHERE id = ?", (book_id,))
    current_quantity = cursor.fetchone()
    if current_quantity:
        new_quantity = current_quantity[0] + quantity
        if new_quantity > 10:
            print("Error: Total quantity cannot exceed 10!")
            conn.close()
            return
        cursor.execute("UPDATE books SET quantity = ? WHERE id = ?", (new_quantity, book_id))
        conn.commit()
        conn.close()
        print(f"Quantity updated successfully! New quantity: {new_quantity}")
    else:
        print("Book not found!")
        conn.close()

# Issue and Return Management
def issue_book(book_id, member_id):
    if has_unpaid_fines(member_id):
        print("Error: Member has unpaid fines. Clear fines before borrowing more books!")
        return
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # Check book availability
    cursor.execute("SELECT quantity FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    if not book or book[0] < 1:
        print("Book not available!")
        conn.close()
        return

    # Issue book
    issue_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO transactions (book_id, member_id, issue_date) VALUES (?, ?, ?)",
                   (book_id, member_id, issue_date))
    cursor.execute("UPDATE books SET quantity = quantity - 1 WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    print("Book issued successfully!")

def return_book():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # Ask for member ID
    member_id = int(input("Enter your Member ID: "))

    # Fetch all transactions for the member and book
    cursor.execute("SELECT id, book_id, issue_date FROM transactions WHERE member_id = ? AND return_date IS NULL", (member_id,))
    transactions = cursor.fetchall()

    if not transactions:
        print("No outstanding transactions for this member!")
        conn.close()
        return

    print(f"Total borrowed books: {len(transactions)}")
    for transaction in transactions:
        transaction_id, book_id, issue_date = transaction
        print(f"Transaction ID: {transaction_id}, Book ID: {book_id}, Issue Date: {issue_date}")

    transaction_id = int(input("Enter the Transaction ID of the book you're returning: "))

    # Check if the entered transaction ID exists
    cursor.execute("SELECT id FROM transactions WHERE id = ? AND member_id = ? AND return_date IS NULL", (transaction_id, member_id))
    existing_transaction = cursor.fetchone()

    # If the transaction ID doesn't exist for the member
    if not existing_transaction:
        print("Error: Transaction ID does not exist or is not associated with this member!")
        conn.close()
        return

    # Calculate fine for this return
    fine = calculate_fine(transaction_id)

    # Update return date and fine
    return_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("UPDATE transactions SET return_date = ?, fine = ? WHERE id = ?",
                   (return_date, fine, transaction_id))

    # Update book quantity
    cursor.execute("SELECT book_id FROM transactions WHERE id = ?", (transaction_id,))
    book_id = cursor.fetchone()[0]
    cursor.execute("UPDATE books SET quantity = quantity + 1 WHERE id = ?", (book_id,))
    
    conn.commit()
    conn.close()

    print(f"Book returned successfully! Fine: PhP {fine:.2f}")

# Member Borrowed Books
def view_borrowed_books(member_id):
    """View all books currently borrowed by a specific member, including the book ID and quantity."""
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute(''' 
        SELECT b.id, b.title, b.author, COUNT(t.id) AS quantity_borrowed, t.issue_date 
        FROM transactions t 
        JOIN books b ON t.book_id = b.id 
        WHERE t.member_id = ? AND t.return_date IS NULL 
        GROUP BY b.id, b.title, b.author, t.issue_date 
    ''', (member_id,))

    borrowed_books = cursor.fetchall()
    conn.close()

    if borrowed_books:
        print("\nBorrowed Books:")
        print("Book ID | Title | Author | Quantity Borrowed | Issue Date")
        print("-" * 70)
        for book in borrowed_books:
            print(f"{book[0]} | {book[1]} | {book[2]} | {book[3]} | {book[4]}")
    else:
        print(f"No books currently borrowed by Member ID {member_id}!")

# Main Menu
def main_menu():
    while True:
        print("\nLibrary Management System")
        print("1. Member Management")
        print("2. Book Management")
        print("3. Simulate Time for Fine Calculation")
        print("4. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            print("\nMember Management")
            print("1. Issue Book")
            print("2. Return Book")
            print("3. View All Books")
            print("4. Exit")
            member_choice = input("Enter your choice: ")
            if member_choice == "1":
                book_id = int(input("Book ID: "))
                member_id = int(input("Member ID: "))
                issue_book(book_id, member_id)
            elif member_choice == "2":
                return_book()
            elif member_choice == "3":
                view_all_books()
            elif member_choice == "4":
                print("Exiting Member Management...")
                continue
            else:
                print("Invalid choice!")

        elif choice == "2":
            print("\nBook Management")
            print("1. Add Book")
            print("2. View All Books")
            print("3. View Borrowed Books by Member")
            print("4. Delete Book")
            print("5. Add Quantity for Existing Book")
            book_choice = input("Enter your choice: ")
            if book_choice == "1":
                title = input("Title: ")
                author = input("Author: ")
                genre = input("Genre: ")
                isbn = input("ISBN: ")
                quantity = int(input("Quantity: "))
                add_book(title, author, genre, isbn, quantity)
            elif book_choice == "2":
                view_all_books()
            elif book_choice == "3":
                member_id = int(input("Enter Member ID to view borrowed books: "))
                view_borrowed_books(member_id)
            elif book_choice == "4":
                book_id = int(input("Enter Book ID to delete: "))
                delete_book(book_id)
            elif book_choice == "5":
                book_id = int(input("Enter Book ID to add quantity: "))
                quantity = int(input("Quantity to add: "))
                add_book_quantity(book_id, quantity)
            else:
                print("Invalid choice!")

        elif choice == "3":
            transaction_id = int(input("Transaction ID: "))
            simulated_date = input("Enter simulated current date (YYYY-MM-DD): ")
            fine = calculate_fine(transaction_id, simulated_date)
            print(f"Simulated Fine for Transaction ID {transaction_id}: PhP {fine:.2f}")
        elif choice == "4":
            print("Exiting the system...")
            break
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    init_db()
    main_menu()
