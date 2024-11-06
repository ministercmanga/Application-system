from flask import Flask
from app import create_app, db
from app.models import User
from ml_model import train_model

app = create_app()
model = train_model()
app.config['ML_MODEL'] = model

def create_tables():
    with app.app_context():  # Ensure the app context is active
        db.create_all()  # Create all database tables

        # Check if the admin user exists, if not, create one
        admin = User.query.filter_by(email='admin').first()
        if not admin:
            admin = User(email='admin', role='admin')  # Admin username
            admin.set_password('admin01')  # Admin password
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists.")
        
if __name__ == "__main__":
    # Initialize the database tables before running the app
    create_tables()
    app.run(debug=True)