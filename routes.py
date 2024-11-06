from flask_wtf.csrf import generate_csrf
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, send_from_directory, current_app
from app import db
from app.models import User, Faculty, Course, Subject, SubjectEntry, FileEntry, Application, UserPersonalInfo, PredictedMarks, ProgramRequirement, ProgramSubjectRequirement
from app.forms import RegistrationForm, LoginForm, PersonalInfoForm, ApplicationForm, FacultyForm, CourseForm, StatusUpdateForm, ManageCourseCapacityForm
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import joinedload
import pandas as pd
import numpy as np
from ml_model import train_model, predict_percentages
from utils import calculate_points, check_qualification, extract_subjects_and_percentages, send_confirmation_email, send_status_update_email, send_registration_email

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            session['role'] = user.role
            
            # Check if the user is an applicant and has an application
            if user.role == 'applicant':
                application = Application.query.filter_by(user_id=user.id).first()
                if application:
                    # If the applicant has already submitted an application, redirect to the status page
                    return redirect(url_for('main.status_page', application_id=application.id))

                return redirect(url_for('main.step1'))
            if user.role in ['admin', 'secondary_admin']:
                return redirect(url_for('main.admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, role='applicant')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        send_registration_email(form.email.data, form.email.data)
        
        flash('You have successfully registered, please log in.', 'success')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        flash('Registration failed, username already exists', 'danger')
    return render_template('register.html', form=form)

@main.route('/step1', methods=['GET', 'POST'])
def step1():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    if session.get('role') != 'applicant':
        return redirect(url_for('main.admin_dashboard'))
    
    form = PersonalInfoForm()
    email = session.get('email', '')
    
    if form.validate_on_submit():
        if form.validate_on_submit():
            existing_user = UserPersonalInfo.query.filter_by(id_number=form.id_number.data).first()
            if existing_user:
                flash(f'The ID number {form.id_number.data} already exists in our system. Please use a different ID number.', 'danger')
                return render_template('step1.html', form=form)
        
        session.permanent = True
        
        session['first_name'] = form.first_name.data  # This should be a string
        session['last_name'] = form.last_name.data
        session['id_number'] = form.id_number.data    # This should be a string
        session['home_address'] = form.home_address.data            # This should be a string
        session['phone'] = form.phone.data            # This should be a string
        
        return redirect(url_for('main.home'))
    
    # Preload session data into the form (if available)
    form.first_name.data = session.get('first_name', '')
    form.last_name.data = session.get('last_name', '')
    form.id_number.data = session.get('id_number', '')
    form.home_address.data = session.get('home_address', '')
    form.phone.data = session.get('phone', '')
    
    return render_template('step1.html', form=form)

@main.route('/home', methods=['GET', 'POST'])
def home():
    # Ensure personal info is completed
    if not all(key in session for key in ['first_name', 'last_name', 'id_number', 'home_address', 'phone']):
        flash('Please complete your personal information first.', 'warning')
        return redirect(url_for('main.step1'))

    user_id = session['user_id']
    form = ApplicationForm()

    # Populate faculty and course choices
    faculties = Faculty.query.all()
    form.faculty.choices = [('', 'Select Faculty')] + [(f.id, f.name) for f in faculties]
    
    if form.faculty.data:
        courses = Course.query.filter_by(faculty_id=form.faculty.data).all()
        form.course.choices = [('', 'Select Course')] + [(c.id, c.name) for c in courses]
    else:
        form.course.choices = [('', 'Select Course')]
        
     
    reportCardNames = [
        "Grade 11 Final",
        "Grade 12 1st Term",
        "Grade 12 2nd Term",
        "Grade 12 3rd Term"
    ]

    if request.method == 'POST':
        if form.validate_on_submit():
            # Retrieve personal info from session
            first_name = session.get('first_name')
            last_name = session.get('last_name')
            id_number = session.get('id_number')
            home_address = session.get('home_address')
            phone = session.get('phone')
            email = User.email  # Fetch email directly from User table
            
            personal_info = UserPersonalInfo(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                id_number=id_number,
                home_address=home_address,
                phone=phone
            )
            db.session.add(personal_info)

           # Create the new application
            new_application = Application(
                user_id=user_id,
                course_id=form.course.data,
                submission_date=datetime.utcnow(),
                status='Pending'
            )
            db.session.add(new_application)
            db.session.commit()
        
            all_subjects_data = {}  # Store extracted data from all files
            for i in range(4):
                # Match the file names in request.files with the name attributes in HTML
                file = request.files.get(f'report_cards-{i}-file')

                if not file:
                    flash(f'Missing Report Card {i + 1}. Please upload all 4 files.', 'danger')
                    return render_template('home.html', form=form)

                # Save the uploaded file
                filename = secure_filename(file.filename)
                file_path = os.path.join(os.getcwd(), 'uploads', filename)
                file.save(file_path)
                
                file_entry = FileEntry(
                        user_id=user_id,
                        filename=filename,
                        report_card_number=i + 1,
                        application_id=new_application.id
                    )
                db.session.add(file_entry)

                # Extract subjects and percentages from the uploaded file
                extracted_data = extract_subjects_and_percentages(file_path)

                # Aggregate the extracted data by subject name
                for subject, percentage in extracted_data.items():
                    if subject not in all_subjects_data:
                        all_subjects_data[subject] = []
                    all_subjects_data[subject].append(percentage)

            # Ensure all subjects have exactly 4 percentages
            for subject, percentages in all_subjects_data.items():
                if len(percentages) != 4:
                    flash(f'Subject {subject} does not have 4 percentages. Please upload complete report cards.', 'danger')
                    return render_template('home.html', form=form)
                
            model = current_app.config['ML_MODEL']
            feature_names = ['Grade 11', 'March', 'June', 'September']

            # Prepare the data for the prediction model
            subjects_features = list(all_subjects_data.values())

            # Use the ML model for prediction
            subjects_df = pd.DataFrame.from_dict(all_subjects_data, orient='index', columns=feature_names)
            print(f"Subjects DataFrame:\n{subjects_df}")
            predictions = model.predict(subjects_df)
            rounded_predictions = np.round(predictions).astype(int)
            print(f"Predictions: {rounded_predictions}")
            
            course_requirements = ProgramRequirement.query.filter_by(course_id=form.course.data).first()
            subject_requirements = ProgramSubjectRequirement.query.filter_by(course_id=form.course.data).all()

            # Calculate total points and store predicted marks for all subjects
            total_points = 0            
            unmet_requirements = []

            # Loop over all predicted subjects
            for subject, prediction in zip(all_subjects_data.keys(), rounded_predictions):
                if subject != "Life Orientation":
                    subject_points = calculate_points(prediction)  # Use helper function to calculate points
                    total_points += subject_points

                # Check if the subject meets the minimum mark requirements
                required_subject = next((req for req in subject_requirements if req.subject.name == subject), None)
                if required_subject and prediction < required_subject.min_mark:
                    unmet_requirements.append(subject)

                # Save each predicted mark in the database (Ensure this part executes correctly)
                predicted_mark = PredictedMarks(
                    application_id=new_application.id,
                    subject_name=subject,
                    predicted_mark=prediction,
                    total_points=subject_points
                )
                db.session.add(predicted_mark)  # Add the predicted mark to the session

            # Check if the total points meet course requirements
            if total_points < course_requirements.total_points_required:
                unmet_requirements.append('Total Points')

            # Update the application with total points and unmet requirements
            new_application.total_points = total_points
            new_application.unmet_requirements = unmet_requirements if unmet_requirements else []

            # Approve or decline the application based on qualification
            if check_qualification(new_application):
                new_application.status = 'Approved'
            else:
                new_application.status = 'Declined'

            db.session.commit()
                
            course_name = Course.query.get(form.course.data).name
            user = User.query.get(user_id)
            recipient_email = user.email
            send_confirmation_email(recipient_email, first_name, form.course.data)

            # Clear the session data after saving
            session.pop('first_name', None)
            session.pop('last_name', None)
            session.pop('id_number', None)
            session.pop('home_address', None)
            session.pop('phone', None)

            return redirect(url_for('main.application_submitted'))

        else:
            print("Form validation failed:", form.errors)
            flash('There was an issue with your submission. Please check your inputs.', 'danger')

    return render_template('home.html', form=form, reportCardNames=reportCardNames)

@main.route('/admin_dashboard', methods=['GET'])
def admin_dashboard():
    if 'user_id' not in session or session.get('role') not in ['admin', 'secondary_admin']:
        flash('You do not have access to this page.', 'danger')
        return redirect(url_for('main.login'))
    
    form = ApplicationForm()
    
    communication_filter = request.args.get('communication')
    course_filter = request.args.get('course')
    date_filter = request.args.get('submission_date')

    # Base query to retrieve applications with user and personal_info
    query = Application.query.options(
        joinedload(Application.user).joinedload(User.personal_info)
    )
    
    # Apply communication filter
    if communication_filter == 'Yes':
        query = query.filter(Application.communicated == True)
    elif communication_filter == 'No':
        query = query.filter(Application.communicated == False)

    # Apply course filter
    if course_filter:
        query = query.filter(Application.course_id == course_filter)

    # Apply date filter
    if date_filter:
        try:
            submission_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(func.date(Application.submission_date) == submission_date)
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')

        
    sort_by = request.args.get('sort_by', 'id')  # Default sorting by 'id'
    order = request.args.get('order', 'asc')     # Default order is 'ascending'

    # Apply sorting to the query
    if sort_by == 'total_points':
        if order == 'asc':
            query = query.order_by(Application.total_points.asc())
        else:
            query = query.order_by(Application.total_points.desc())
    else:
        query = query.order_by(Application.id)  # Default sorting by ID
        
    applications = query.all()
        
    total_applications = Application.query.count()
    approved_applications = Application.query.filter_by(status='Approved').count()
    declined_applications = Application.query.filter_by(status='Declined').count()
    uncommunicated_applications = Application.query.filter_by(communicated=False).count()
        
    courses = Course.query.all()
        
    # Load personal information for each application
    application_data = []
    for application in applications:
        application.personal_info = UserPersonalInfo.query.filter_by(user_id=application.user_id).first()
        predicted_marks = PredictedMarks.query.filter_by(application_id=application.id).all()
        course_requirements = ProgramRequirement.query.filter_by(course_id=application.course_id).first()
        subject_requirements = ProgramSubjectRequirement.query.filter_by(course_id=application.course_id).all()
        total_points = sum([calculate_points(mark.predicted_mark) for mark in predicted_marks])
        
        unmet_requirements = []
        # Check total points requirement
        if total_points < course_requirements.total_points_required:
            unmet_requirements.append('Total Points')

        # Check subject-specific requirements
        for mark in predicted_marks:
            required_subject = next((req for req in subject_requirements if req.subject.name == mark.subject_name), None)
            if required_subject and mark.predicted_mark < required_subject.min_mark:
                unmet_requirements.append(mark.subject_name)
        
        application_data.append({
            'application': application,
            'predicted_marks': predicted_marks,
            'total_points': total_points,
            'unmet_requirements': unmet_requirements
        })
        
    return render_template('admin_dashboard.html', applications=applications, courses=courses,
                           total_applications=total_applications,
                           approved_applications=approved_applications,
                           declined_applications=declined_applications,
                           uncommunicated_applications=uncommunicated_applications,
                           form=form)
    
@main.route('/some_route')
def some_view_function():
    report_card_entries = get_report_card_entries()  # This returns a generator
    report_card_entries_list = list(report_card_entries)  # Convert generator to list
    return render_template('some_template.html', report_card_entries=report_card_entries_list)

@main.route('/courses/<int:faculty_id>')
def get_courses(faculty_id):
    courses = Course.query.filter_by(faculty_id=faculty_id).all()
    course_list = [{"id": course.id, "name": course.name} for course in courses]
    return jsonify({"courses": course_list})

@main.route('/admin/add_faculty', methods=['GET', 'POST'])
def add_faculty():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('main.login'))

    form = FacultyForm()
    if form.validate_on_submit():
        new_faculty = Faculty(name=form.name.data)
        db.session.add(new_faculty)
        db.session.commit()
        flash('Faculty added successfully!', 'success')
        return redirect(url_for('main.add_faculty'))
    
    return render_template('add_faculty.html', form=form)

@main.route('/admin/add_course', methods=['GET', 'POST'])
def add_course():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('main.login'))

    form = CourseForm()
    form.faculty.choices = [(faculty.id, faculty.name) for faculty in Faculty.query.all()]

    if form.validate_on_submit():
        new_course = Course(name=form.name.data, faculty_id=form.faculty.data)
        db.session.add(new_course)
        db.session.commit()
        flash('Course added successfully!', 'success')
        return redirect(url_for('main.add_course'))
    
    return render_template('add_course.html', form=form)

@main.route('/admin/add_subject', methods=['GET', 'POST'])
def add_subject():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('main.login'))

    form = SubjectForm()
    if form.validate_on_submit():
        new_subject = Subject(name=form.name.data)
        db.session.add(new_subject)
        db.session.commit()
        flash('Subject added successfully!', 'success')
        return redirect(url_for('main.add_subject'))
    
    return render_template('add_subject.html', form=form)


@main.route('/analytics')
def analytics():
    # Total applications per course
    total_applications_per_course = db.session.query(
    Course.name, func.count(Application.id)
    ).select_from(Application).join(Course, Application.course_id == Course.id).group_by(Course.name).all()

    # Most popular faculty
    most_popular_faculty = db.session.query(
    Faculty.name, func.count(Application.id)
    ).select_from(Application).join(Course, Application.course_id == Course.id).join(Faculty, Course.faculty_id == Faculty.id).group_by(Faculty.name).order_by(func.count(Application.id).desc()).first()

    # Percentage of approved/declined applications
    total_applications = db.session.query(func.count(Application.id)).scalar()
    approved_applications = db.session.query(func.count(Application.id)).filter_by(status='Approved').scalar()
    declined_applications = db.session.query(func.count(Application.id)).filter_by(status='Declined').scalar()

    approved_percentage = (approved_applications / total_applications) * 100 if total_applications > 0 else 0
    declined_percentage = (declined_applications / total_applications) * 100 if total_applications > 0 else 0

    return render_template('analytics.html',
                           total_applications_per_course=total_applications_per_course,
                           most_popular_faculty=most_popular_faculty,
                           approved_percentage=approved_percentage,
                           declined_percentage=declined_percentage)

@main.route('/update_application_status/<int:application_id>', methods=['POST'])
def update_application_status(application_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    application = Application.query.get_or_404(application_id)
    data = request.json
    status = data.get('status')
    
    if status in ['Pending', 'Approved', 'Declined']:
        application.status = status
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400

UPLOAD_FOLDER = 'uploads/'  # This should be the path where files are stored, relative to the app root

@main.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
UPLOAD_FOLDER = 'uploads/'

@main.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main.route('/application_submitted')
def application_submitted():
    return render_template('application_submitted.html')

@main.route('/submit_application', methods=['POST'])
def submit_application():
    form = ApplicationForm()
    if form.validate_on_submit():

        flash('Application submitted successfully!', 'success')
        return redirect(url_for('main.application_submitted'))  # Redirect to the confirmation page
    
    return render_template('home.html', form=form)

@main.route('/status/<int:application_id>', methods=['GET'])
def status_page(application_id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    # Retrieve the application and ensure it belongs to the logged-in user
    application = Application.query.filter_by(id=application_id, user_id=session['user_id']).first()

    if not application:
        flash('Application not found or you are not authorized to view this application.', 'danger')
        return redirect(url_for('main.home'))

    # Determine the status to show to the applicant
    if application.status_communication:
        displayed_status = application.status  # Show actual status if communication has been sent
    else:
        displayed_status = 'Pending'  # Always show pending if no communication is sent

    return render_template('status.html', application=application, displayed_status=displayed_status)

@main.route('/update_status/<int:application_id>', methods=['POST'])
def update_status(application_id):
    if 'user_id' not in session or session['role'] not in ['admin', 'secondary_admin']:
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('main.admin_dashboard'))
    
    # Only allow primary admins (role = 'admin') to update statuses
    if session['role'] == 'secondary_admin':
        flash('You do not have permission to update application statuses.', 'warning')
        return redirect(url_for('main.admin_dashboard'))

    form = StatusUpdateForm()

    if form.validate_on_submit():
        # Fetch the application
        application = Application.query.get(application_id)
        if not application:
            flash('Application not found.', 'danger')
            return redirect(url_for('main.admin_dashboard'))
        
        application.communicated = True
        
         # Fetch the user's personal information and email
        user_personal_info = UserPersonalInfo.query.filter_by(user_id=application.user_id).first()
        user = User.query.get(application.user_id)

        # Automatically generate status communication messages
        if form.status.data == 'Approved':
            message = f"Congratulations {user_personal_info.first_name}, \n\nYou have been conditionally accepted for {application.course.name}."
        elif form.status.data == 'Declined':
            message = f"Dear {user_personal_info.first_name}, \n\nWe regret to inform you that your application for {application.course.name} has been declined."
        else:
            message = None

        # Update the status and communication message on the database
        application.status = form.status.data
        application.status_communication = message
        db.session.commit()
        
        recipient_email =  user.email  # Fetch applicant's email
        send_status_update_email(recipient_email, message)
        
        flash('Application status and communication updated successfully.', 'success')
        return redirect(url_for('main.admin_dashboard'))
    
    return redirect(url_for('main.admin_dashboard'))

@main.route('/manage_course_capacity', methods=['GET', 'POST'])
def manage_course_capacity():
    form = ManageCourseCapacityForm()  # Instantiate your form

    if form.validate_on_submit():
        # Handle form submission
        courses = Course.query.all()
        for course in courses:
            max_applicants = request.form.get(f'max_applicants_{course.id}', 0)
            course.max_applicants = int(max_applicants)
            db.session.commit()

        flash('Course capacities updated successfully!', 'success')
        return redirect(url_for('main.manage_course_capacity'))

    # Fetch courses and accepted applications count
    courses = Course.query.all()
    accepted_counts = {course.id: Application.query.filter_by(course_id=course.id, status='Approved').count() for course in courses}
    
    progress_data = {}
    for course in courses:
        accepted = accepted_counts.get(course.id, 0)
        max_capacity = course.max_applicants
        if max_capacity > 0:
            percentage_filled = (accepted / max_capacity) * 100
        else:
            percentage_filled = 0
            
        progress_data[course.id] = {
            'accepted': accepted,
            'max_capacity': max_capacity,
            'percentage_filled': percentage_filled
        }

    return render_template('manage_course_capacity.html', form=form, courses=courses,
                           accepted_counts=accepted_counts, progress_data=progress_data)
    
@main.route('/check_username', methods=['POST'])
def check_username():
    data = request.get_json()
    email = data.get('email')

    if User.query.filter_by(email=email).first():
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False})
    
@main.route('/check_id_number', methods=['POST'])
def check_id_number():
    data = request.get_json()
    id_number = data.get('id_number')

    if UserPersonalInfo.query.filter_by(id_number=id_number).first():
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False})

@main.route('/get-csrf-token', methods=['GET'])
def get_csrf_token():
    token = generate_csrf()
    return jsonify({'csrf_token': token})

@main.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))