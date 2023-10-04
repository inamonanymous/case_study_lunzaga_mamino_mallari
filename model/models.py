from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash

db = SQLAlchemy()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    student_number = db.Column(db.String(20), unique=True, nullable=False)
    year = db.Column(db.String(20))
    section = db.Column(db.String(20))
    department = db.Column(db.String(50))
    qrcode = db.Column(db.String(255), nullable=True)

    def __init__(self, firstname, surname, student_number, year, section=None, department=None, qrcode=None):
        self.firstname = firstname
        self.surname = surname
        self.student_number = student_number
        self.year = year
        self.section = section
        self.department = department
        self.qrcode = qrcode


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), unique=True, nullable=False)

    @classmethod
    def login_true(cls, param_username, param_password):
        admin = cls.query.filter_by(username=param_username).first()
        return admin and check_password_hash(admin.password, param_password)
