from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='applicant')
    
    personal_info = db.relationship('UserPersonalInfo', uselist=False, backref='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class UserPersonalInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    id_number = db.Column(db.String(13), unique=True, nullable=False)
    home_address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserPersonalInfo {self.first_name} {self.last_name}>"
    
class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    faculty = db.relationship('Faculty', backref=db.backref('courses', lazy=True))
    max_applicants = db.Column(db.Integer, nullable=False)
    
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    
class SubjectEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    percentage = db.Column(db.Integer, nullable=False)
    report_card_number = db.Column(db.Integer, nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)  # Foreign key to Application

    subject = db.relationship('Subject', backref=db.backref('entries', lazy=True))
    application = db.relationship('Application', backref=db.backref('subject_entries', lazy=True))
    user = db.relationship('User', backref=db.backref('subject_entries', lazy=True))
    
class FileEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    report_card_number = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)  # Foreign key to Application

    application = db.relationship('Application', backref=db.backref('file_entries', lazy=True))
    user = db.relationship('User', backref=db.backref('file_uploads', lazy=True))
    
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    total_points = db.Column(db.Integer)
    status = db.Column(db.String(50), default='Pending')  # e.g., 'Approved', 'Declined', 'Pending'
    status_communication = db.Column(db.Text)  # Admin can communicate status to the applicant
    communicated = db.Column(db.Boolean, default=False)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    unmet_requirements = db.Column(db.JSON, nullable=True)

    course = db.relationship('Course', backref=db.backref('applications', lazy=True))
    user = db.relationship('User', backref=db.backref('applications', lazy=True), foreign_keys=[user_id])
    
class PredictedMarks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    subject_name = db.Column(db.String(150), nullable=False)
    predicted_mark = db.Column(db.Integer, nullable=False)
    total_points = db.Column(db.Integer, nullable=False)

    application = db.relationship('Application', backref=db.backref('predicted_marks', lazy=True))
    
class ProgramRequirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    total_points_required = db.Column(db.Integer, nullable=False)

    course = db.relationship('Course', backref=db.backref('requirements', lazy=True))
    
class ProgramSubjectRequirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    min_mark = db.Column(db.Integer, nullable=False)  # Minimum mark required for this subject

    course = db.relationship('Course', backref=db.backref('subject_requirements', lazy=True))
    subject = db.relationship('Subject', backref=db.backref('subject_requirements', lazy=True))
    
class SubjectGroupRequirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    group_name = db.Column(db.String(150), nullable=False) 
    course = db.relationship('Course', backref=db.backref('subject_group_requirements', lazy=True))

class SubjectInGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('subject_group_requirement.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    min_mark = db.Column(db.Integer, nullable=False)
    group = db.relationship('SubjectGroupRequirement', backref=db.backref('subjects', lazy=True))
    subject = db.relationship('Subject', backref=db.backref('subject_groups', lazy=True))
    