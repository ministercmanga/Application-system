from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, RadioField, SelectField, FieldList, IntegerField, FormField, DateField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, ValidationError, NumberRange, Length, Regexp, Email
from app.models import User, Faculty, Course, Subject
from flask_wtf.file import FileField, FileAllowed, FileRequired

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already exists. Please use a different email.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
    
class PersonalInfoForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    id_number = StringField('ID Number', validators=[
        DataRequired(),
        Length(min=13, max=13, message='ID number must be exactly 13 digits.'),
        Regexp('^[0-9]*$', message='ID number must contain only digits.')
    ])
    home_address = StringField('Home Adress', validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=10, message='Phone number must be exactly 10 digits.')])
    submit = SubmitField('Next') 
    
class ReportCardForm(FlaskForm):
    file = FileField('Upload Report Card', validators=[FileRequired(), FileAllowed(['pdf'], 'Documents only!')])
    
class ApplicationForm(FlaskForm):
    faculty = SelectField('Faculty', choices=[('', 'Select Faculty')], validators=[DataRequired()])
    course = SelectField('Course', choices=[('', 'Select Course')], validators=[DataRequired()])
    report_cards = FieldList(FormField(ReportCardForm), min_entries=4, max_entries=4)
    submit = SubmitField('Submit')
    
class FacultyForm(FlaskForm):
    name = StringField('Faculty Name', validators=[DataRequired()])
    submit = SubmitField('Add Faculty')

class CourseForm(FlaskForm):
    name = StringField('Course Name', validators=[DataRequired()])
    faculty = SelectField('Faculty', choices=[], coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Course')
    
class StatusUpdateForm(FlaskForm):
    status = SelectField('Status', choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Declined', 'Declined')], validators=[DataRequired()])
    status_communication = TextAreaField('Status Communication', render_kw={'readonly': True})  # Read-only field for automated message
    submit = SubmitField('Update Status')
    
class ManageCourseCapacityForm(FlaskForm):
    pass
    
