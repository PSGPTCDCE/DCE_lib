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

# Helper function to get dashboard URL based on role
def get_dashboard_url():
    if 'role' in session:
        if session['role'] == 'member':
            return url_for('member_dashboard')
        elif session['role'] == 'librarian':
            return url_for('librarian_dashboard')
    return url_for('login')  # Default to login if no role

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
    logger.debug("Entering /login route")
    if request.method == 'POST':
        logger.debug("Processing POST request")
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required.', 'error')
            logger.debug("Missing username or password")
            return render_template('login.html', dashboard_url=get_dashboard_url())

        try:
            logger.debug("Attempting database connection")
            conn = get_db_connection()
            cursor = conn.cursor()
            logger.debug(f"Querying user: {username}")
            cursor.execute('SELECT id, role, password FROM user WHERE username = %s', (username,))
            user = cursor.fetchone()
            logger.debug(f"User fetched: {user}")

            if user and user[2] == password:
                session['user_id'] = user[0]
                session['role'] = user[1]
                flash('Login successful!', 'success')
                logger.debug("Login successful, redirecting to dashboard")
                if user[1] == 'member':
                    return redirect(url_for('member_dashboard'))
                elif user[1] == 'librarian':
                    return redirect(url_for('librarian_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
                logger.debug("Invalid credentials")
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
    logger.debug("Rendering login.html for GET request")
    return render_template('login.html', dashboard_url=get_dashboard_url())

# Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if not username or not password or not role:
            flash('All fields are required.', 'error')
            return render_template('register.html', dashboard_url=get_dashboard_url())

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
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
    return render_template('register.html', dashboard_url=get_dashboard_url())

# Member Dashboard Page
@app.route('/member_dashboard')
def member_dashboard():
    logger.debug("Entering /member_dashboard")
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'error')
        return redirect(url_for('login'))
    if session['role'] != 'member':
        flash('Access denied. Members only.', 'error')
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM user WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        username = user[0] if user else "Unknown Member"
    except mysql.connector.Error as err:
        logger.error(f"Database error fetching username: {err}")
        flash(f'Database error: {err}', 'error')
        username = "Unknown Member"
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

    quizzes = [
        {"name": "Ethical Hacking Quiz", "url": url_for('static', filename='eh_lib.html')},
        {"name": "Professional IQ Test", "url": url_for('static', filename='IQ_lib.html')},
        {"name": "Python Quiz", "url": url_for('static', filename='py_lib.html')},
        {"name": "PC Hardware Quiz", "url": url_for('static', filename='pchw_lib.html')},
        {"name": "Networking Quiz", "url": url_for('static', filename='net_lib.html')}
    ]

    logger.debug("Rendering member_dashboard.html")
    return render_template('member_dashboard.html', username=username, quizzes=quizzes, dashboard_url=get_dashboard_url())

# Librarian Dashboard Page
# Librarian Dashboard Page
@app.route('/librarian_dashboard')
def librarian_dashboard():
    logger.debug("Entering /librarian_dashboard")
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'error')
        return redirect(url_for('login'))
    if session['role'] != 'librarian':
        flash('Access denied. Librarians only.', 'error')
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT books.title, books.author, borrowed_books.borrow_date, borrowed_books.due_date, user.username
            FROM borrowed_books
            JOIN books ON borrowed_books.book_id = books.id
            JOIN user ON borrowed_books.user_id = user.id
            WHERE borrowed_books.returned = FALSE
        ''')
        all_borrowed_books = cursor.fetchall()
    except mysql.connector.Error as err:
        logger.error(f"Database error while fetching all borrowed books: {err}")
        flash(f'Database error: {err}', 'error')
        all_borrowed_books = []
    except Exception as e:
        logger.error(f"Unexpected error while fetching all borrowed books: {e}")
        flash('An unexpected error occurred. Please try again.', 'error')
        all_borrowed_books = []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

    # Get the current date
    current_date = datetime.now().date()

    logger.debug("Rendering all_borrowed_books.html")
    return render_template('all_borrowed_books.html', 
                          borrowed_books=all_borrowed_books, 
                          current_date=current_date, 
                          dashboard_url=get_dashboard_url())
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

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        barcode = request.form.get('barcode')

        if not title or not author or not barcode:
            flash('All fields are required.', 'error')
            return render_template('add_book.html', dashboard_url=get_dashboard_url())

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO books (title, author, barcode) VALUES (%s, %s, %s)', 
                          (title, author, barcode))
            conn.commit()
            flash('Book added successfully!', 'success')
            return redirect(url_for('ibrarian_dashboard'))
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
    return render_template('add_book.html', dashboard_url=get_dashboard_url())

# View Books Page
@app.route('/view_books', methods=['GET', 'POST'])
def view_books():
    books = []
    search_query = None

    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        if search_query:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                query = '''
                    SELECT * FROM books 
                    WHERE available = TRUE 
                    AND (title LIKE %s OR author LIKE %s OR barcode LIKE %s)
                '''
                search_term = f'%{search_query}%'
                cursor.execute(query, (search_term, search_term, search_term))
                books = cursor.fetchall()
            except mysql.connector.Error as err:
                logger.error(f"Database error while searching books: {err}")
                flash(f'Database error: {err}', 'error')
            except Exception as e:
                logger.error(f"Unexpected error while searching books: {e}")
                flash('An unexpected error occurred. Please try again.', 'error')
            finally:
                if 'conn' in locals() and conn.is_connected():
                    cursor.close()
                    conn.close()
        else:
            flash('Please enter a search term.', 'error')
    else:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM books WHERE available = TRUE')
            books = cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Database error while viewing books: {err}")
            flash(f'Database error: {err}', 'error')
        except Exception as e:
            logger.error(f"Unexpected error while viewing books: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()

    return render_template('view_books.html', books=books, search_query=search_query, dashboard_url=get_dashboard_url())

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
            return render_template('borrow_book.html', dashboard_url=get_dashboard_url())

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
    return render_template('borrow_book.html', dashboard_url=get_dashboard_url())
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
            return render_template('return_book.html', dashboard_url=get_dashboard_url())

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
    return render_template('return_book.html', dashboard_url=get_dashboard_url())

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
            SELECT books.title, books.author, borrowed_books.borrow_date, borrowed_books.due_date, user.username
            FROM borrowed_books
            JOIN books ON borrowed_books.book_id = books.id
            JOIN user ON borrowed_books.user_id = user.id
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
    return render_template('borrowed_books.html', borrowed_books=borrowed_books, dashboard_url=get_dashboard_url())

# Index Page
@app.route('/')
def index():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=50068, debug=True)
