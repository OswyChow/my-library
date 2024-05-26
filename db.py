from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.schema import CheckConstraint

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    @property
    def password(self):
        raise AttributeError('password: write-only field')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Book(db.Model):
    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    author = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String)

class UserBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.String, db.ForeignKey('book.id'), nullable=False)
    status = db.Column(db.Enum('Read', 'Unread', 'Reading'), default='Unread')
    rating = db.Column(db.Integer, nullable=True)
    user = db.relationship('User', backref=db.backref('user_books', lazy=True))
    book = db.relationship('Book', backref=db.backref('user_books', lazy=True))

    __table_args__ = (
        CheckConstraint('rating>=1 AND rating<=10', name='rating_range'),
    )