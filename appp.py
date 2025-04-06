from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from datetime import datetime, timedelta
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key')

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Lakshith007?',  # Update with your MySQL password
    'database': 'library_db'
}

# Connect to MySQL
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            logger.info("Successfully connected to the database.")
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Database connection failed: {err}")
        raise

# Test database connection on startup
try:
    conn = get_db_connection()
    conn.close()
except mysql.connector.Error as err:
    logger.error(f"Failed to connect to the database on startup: {err}")
    raise SystemExit("Cannot start the application due to database connection failure.")

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, role, password FROM user WHERE username = %s', (username,))
            user = cursor.fetchone()

            # Compare passwords directly as plain text
            if user and user[2] == password:
                session['user_id'] = user[0]
                session['role'] = user[1]
                flash('Login successful!', 'success')
                # Redirect based on role
                if user[1] == 'member':
                    return redirect(url_for('member_dashboard'))
                elif user[1] == 'librarian':
                    return redirect(url_for('librarian_dashboard'))
            else:
                flash('Invalid username or password.', 'error')
        except mysql.connector.Error as err:
            logger.error(f"Database error during login: {err}")
            flash(f'Database error: {err}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('login.html')

# Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if not username or not password or not role:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Store password as plain text
            cursor.execute('INSERT INTO user (username, password, role) VALUES (%s, %s, %s)', 
                          (username, password, role))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            logger.error(f"Database error during registration: {err}")
            flash(f'Registration failed: {err}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('register.html')

# Member Dashboard Page
@app.route('/member_dashboard')
def member_dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'error')
        return redirect(url_for('login'))
    if session['role'] != 'member':
        flash('Access denied. Members only.', 'error')
        return redirect(url_for('login'))
    return render_template('member_dashboard.html')

# Librarian Dashboard Page
@app.route('/librarian_dashboard')
def librarian_dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'error')
        return redirect(url_for('login'))
    if session['role'] != 'librarian':
        flash('Access denied. Librarians only.', 'error')
        return redirect(url_for('login'))
    return render_template('librarian_dashboard.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# Add Book Page
@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if 'user_id' not in session:
        flash('Please login to add a book.', 'error')
        return redirect(url_for('login'))
    if session['role'] != 'librarian':
        flash('Access denied. Librarians only.', 'error')
        return redirect(url_for('member_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        barcode = request.form.get('barcode')

        if not title or not author or not barcode:
            flash('All fields are required.', 'error')
            return render_template('add_book.html')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO books (title, author, barcode) VALUES (%s, %s, %s)', 
                          (title, author, barcode))
            conn.commit()
            flash('Book added successfully!', 'success')
            return redirect(url_for('librarian_dashboard'))
        except mysql.connector.Error as err:
            logger.error(f"Database error while adding book: {err}")
            flash(f'Error adding book: {err}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error while adding book: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('add_book.html')

# View Books Page
@app.route('/view_books')
def view_books():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM books WHERE available = TRUE')
        books = cursor.fetchall()
    except mysql.connector.Error as err:
        logger.error(f"Database error while viewing books: {err}")
        flash(f'Database error: {err}', 'error')
        books = []
    except Exception as e:
        logger.error(f"Unexpected error while viewing books: {e}")
        flash('An unexpected error occurred. Please try again.', 'error')
        books = []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
    return render_template('view_books.html', books=books)

# Borrow Book 
@app.route('/borrow_book', methods=['GET', 'POST'])
def borrow_book():
    if 'user_id' not in session:
        flash('Please login to borrow a book.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        barcode = request.form.get('barcode')

        if not barcode:
            flash('Barcode is required.', 'error')
            return render_template('borrow_book.html')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, available FROM books WHERE barcode = %s', (barcode,))
            book = cursor.fetchone()

            if book:
                book_id, available = book
                if available:
                    borrow_date = datetime.now().date()
                    due_date = borrow_date + timedelta(days=14)
                    cursor.execute('INSERT INTO borrowed_books (user_id, book_id, borrow_date, due_date) VALUES (%s, %s, %s, %s)', 
                                  (user_id, book_id, borrow_date, due_date))
                    cursor.execute('UPDATE books SET available = FALSE WHERE id = %s', (book_id,))
                    conn.commit()
                    flash('Book borrowed successfully!', 'success')
                    return redirect(url_for('member_dashboard'))
                else:
                    flash('Book is not available.', 'error')
            else:
                flash('Book not found.', 'error')
        except mysql.connector.Error as err:
            logger.error(f"Database error while borrowing book: {err}")
            flash(f'Database error: {err}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error while borrowing book: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('borrow_book.html')

# Return Book
@app.route('/return_book', methods=['GET', 'POST'])
def return_book():
    if 'user_id' not in session:
        flash('Please login to return a book.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        barcode = request.form.get('barcode')

        if not barcode:
            flash('Barcode is required.', 'error')
            return render_template('return_book.html')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM books WHERE barcode = %s', (barcode,))
            book = cursor.fetchone()

            if book:
                book_id = book[0]
                cursor.execute('SELECT due_date FROM borrowed_books WHERE user_id = %s AND book_id = %s AND returned = FALSE', 
                              (user_id, book_id))
                borrowed_book = cursor.fetchone()

                if borrowed_book:
                    due_date = borrowed_book[0]
                    today = datetime.now().date()

                    if today > due_date:
                        days_late = (today - due_date).days
                        late_fee = days_late * 1
                        flash(f'Book returned {days_late} days late. Late fee: ${late_fee}', 'warning')

                    cursor.execute('UPDATE borrowed_books SET returned = TRUE WHERE user_id = %s AND book_id = %s', 
                                  (user_id, book_id))
                    cursor.execute('UPDATE books SET available = TRUE WHERE id = %s', (book_id,))
                    conn.commit()
                    flash('Book returned successfully!', 'success')
                    return redirect(url_for('member_dashboard'))
                else:
                    flash('You have not borrowed this book.', 'error')
            else:
                flash('Book not found.', 'error')
        except mysql.connector.Error as err:
            logger.error(f"Database error while returning book: {err}")
            flash(f'Database error: {err}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error while returning book: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('return_book.html')

# View Borrowed Books Page
@app.route('/borrowed_books')
def borrowed_books():
    if 'user_id' not in session:
        flash('Please login to view borrowed books.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT books.title, books.author, borrowed_books.borrow_date, borrowed_books.due_date 
            FROM borrowed_books
            JOIN books ON borrowed_books.book_id = books.id
            WHERE borrowed_books.user_id = %s AND returned = FALSE
        ''', (user_id,))
        borrowed_books = cursor.fetchall()
    except mysql.connector.Error as err:
        logger.error(f"Database error while viewing borrowed books: {err}")
        flash(f'Database error: {err}', 'error')
        borrowed_books = []
    except Exception as e:
        logger.error(f"Unexpected error while viewing borrowed books: {e}")
        flash('An unexpected error occurred. Please try again.', 'error')
        borrowed_books = []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
    return render_template('borrowed_books.html', borrowed_books=borrowed_books)

# Index Page
@app.route('/')
def index():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
