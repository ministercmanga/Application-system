from app import db, mail
from flask_mail import Message
from app.models import Course, Subject, ProgramRequirement, ProgramSubjectRequirement, SubjectGroupRequirement, SubjectInGroup, PredictedMarks
import pdfplumber

def calculate_points(predicted_mark):
    if predicted_mark >= 80:
        return 7
    elif predicted_mark >= 70:
        return 6
    elif predicted_mark >= 60:
        return 5
    elif predicted_mark >= 50:
        return 4
    elif predicted_mark >= 40:
        return 3
    elif predicted_mark >= 30:
        return 2
    else:
        return 1
    
def check_qualification(application):
    # Retrieve the course requirements
    course_requirements = ProgramRequirement.query.filter_by(course_id=application.course_id).first()
    
    # Check if the applicant meets the total points requirement
    if application.total_points < course_requirements.total_points_required:
        return False

    # Check subject-specific requirements
    subject_requirements = ProgramSubjectRequirement.query.filter_by(course_id=application.course_id).all()
    
    # Handle subject group requirements (OR conditions)
    subject_group_requirements = SubjectGroupRequirement.query.filter_by(course_id=application.course_id).all()

    for group in subject_group_requirements:
        group_satisfied = False
        for subject_in_group in group.subjects:
            predicted_mark = PredictedMarks.query.filter_by(
                application_id=application.id, 
                subject_name=subject_in_group.subject.name
            ).first()
            
            if predicted_mark and predicted_mark.predicted_mark >= subject_in_group.min_mark:
                group_satisfied = True
                break  # One subject in the group met the condition, so we're good

        if not group_satisfied:
            return False  # If none of the subjects in the group meet the condition, fail the application

    # Check for other individual subject requirements (non-OR subjects)
    for requirement in subject_requirements:
        predicted_mark = PredictedMarks.query.filter_by(
            application_id=application.id,
            subject_name=requirement.subject.name
        ).first()

        if not predicted_mark or predicted_mark.predicted_mark < requirement.min_mark:
            return False

    return True

def extract_subjects_and_percentages(pdf_path):
    extracted_data = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    if len(row) == 2:
                        subject, percentage = row
                        subject = subject.strip()

                        try:
                            percentage = int(percentage.strip())
                        except ValueError:
                            continue

                        extracted_data[subject] = percentage
                        
    return extracted_data

def send_confirmation_email(email, first_name, course_name):
    msg = Message(
        subject="Application Confirmation",
        recipients=[email],
        body=f"Hello {first_name},\n\nYour application has been submitted successfully! We will review your application and get back to you with the results.\n\nBest regards, \nThe UNIZULU Application System",
    )
    try:
        mail.send(msg)
        print("Confirmation email sent!")
    except Exception as e:
        print(f"Error sending email: {e}")
        
def send_status_update_email(recipient_email, message):
    subject = "Application Status Update"
    msg = Message(subject=subject,
                  recipients=[recipient_email],
                  body=message)
    try:
        mail.send(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
        
def send_registration_email(recipient_email, username):
    subject = "Registration Successful"
    message_body = f"Thank you for registering. Your account has been created successfully! You can now procced with the next step of your application"

    msg = Message(subject=subject, recipients=[recipient_email], body = message_body)

    try:
        mail.send(msg)
        print("Confirmation email sent.")
    except Exception as e:
        print(f"Error sending email: {e}")