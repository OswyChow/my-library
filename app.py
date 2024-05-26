from functools import wraps
from flask import Flask, redirect, url_for, render_template, request, flash
import requests
from werkzeug.security import check_password_hash, generate_password_hash
from db import db, User, Book, UserBook
from flask_login import LoginManager, current_user, login_user, logout_user
from wtforms import Form, StringField, PasswordField, validators, ValidationError
from dotenv import load_dotenv
import os

class UniqueUsernameValidator:
    def __call__(self, form, field):
        user = User.query.filter_by(username=field.data).first()
        if user is not None:
            raise ValidationError('This username is already taken.')

class PasswordValidator:
    def __init__(self, min=-1, max=-1):
        self.min = min
        self.max = max

    def __call__(self, form, field):
        password = field.data
        length = len(password)
        if length < self.min or (self.max != -1 and length > self.max):
            raise ValidationError('Password must be at least %i characters long.' % (self.min,))
        if " " in password:
            raise ValidationError('Password must not contain any whitespace characters.')

class RegistrationForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25), UniqueUsernameValidator()])
    password = PasswordField('Password', [
        validators.DataRequired(),
        PasswordValidator(min=6),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')

def init_app_env():
    load_dotenv()
    app.config['SERVER_NAME'] = os.getenv('SERVER_NAME')
    app.config['APPLICATION_ROOT'] = os.getenv('APPLICATION_ROOT')
    app.config['PREFERRED_URL_SCHEME'] = os.getenv('PREFERRED_URL_SCHEME')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.secret_key = os.getenv('SECRET_KEY')

app = Flask(__name__)
login_manager = LoginManager()
init_app_env()
db.init_app(app)
login_manager.init_app(app)

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
@login_required
def index():
    return render_template('index.html', username=current_user.username)
@app.route("/auth")
def auth():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('auth.html')
@app.route("/auth", methods=['POST'])
def authpost():
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if user is None or not check_password_hash(user.password_hash, password):
        flash('Invalid username or password')
        return redirect(url_for('auth'))
    
    remember = 'remember' in request.form
    login_user(user, remember=remember)
    return redirect(url_for('index'))
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password = form.password.data
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.')
            return redirect(url_for('signup'))

        new_user = User(username=username, password_hash=generate_password_hash(password))

        db.session.add(new_user)
        db.session.commit()
        flash('Thanks for registering')
        return redirect(url_for('auth'))
    return render_template('signup.html', form=form)

@app.route('/search')
def search():
    query = request.args.get('q')
    response = requests.get('https://www.googleapis.com/books/v1/volumes', params={'q': query})
    results = response.json().get('items', [])
    return render_template('index.html', results=results)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth'))

@app.route('/add_to_library', methods=['POST'])
@login_required
def add_to_library():
    book_id = request.form.get('book_id')
    book_title = request.form.get('book_title')
    book_author = request.form.get('book_author')
    book_year = request.form.get('book_year')
    book_image_url = request.form.get('book_image_url')

    if not all([book_id, book_title, book_author, book_year, book_image_url]):
        return "Error: Missing book data", 400

    book = Book.query.get(book_id)
    if not book:
        book = Book(id=book_id, title=book_title, author=book_author, year=book_year, image_url=book_image_url)
        db.session.add(book)

    if current_user.is_authenticated:
        new_user_book = UserBook(user_id=current_user.id, book_id=book.id, status='Unread', rating=1)
        db.session.add(new_user_book)
        db.session.commit()
        return redirect(url_for('my_library'))
    else:
        return "Error: User not logged in", 400
    
@app.route('/library')
@login_required
def my_library():
    user_books = UserBook.query.filter_by(user_id=current_user.id).all()
    return render_template('library.html', user_books=user_books)

@app.route('/update_status/<book_id>', methods=['POST'])
@login_required
def update_status(book_id):
    # Get the new status from the form data
    new_status = request.form.get('status')

    # Find the UserBook record for the current user and the specified book
    user_book = UserBook.query.filter_by(user_id=current_user.id, book_id=book_id).first()

    if user_book and new_status in ['Read', 'Unread', 'Reading']:
        # Update the status
        user_book.status = new_status
        db.session.commit()
        return redirect(url_for('my_library'))
    else:
        return "Error: Invalid status or book not found", 400
    
@app.route('/rate_book', methods=['POST'])
@login_required
def rate_book():
    data = request.get_json()
    book_id = data['bookId']
    rating = data['rating']

    user_book = UserBook.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if user_book:
        user_book.rating = rating
        db.session.commit()

    return '', 204
    
@app.route('/delete_book/<book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    # Find the UserBook record for the current user and the specified book
    user_book = UserBook.query.filter_by(user_id=current_user.id, book_id=book_id).first()

    if user_book:
        # Delete the record
        db.session.delete(user_book)
        db.session.commit()
        return redirect(url_for('my_library'))
    else:
        return "Error: Book not found", 400