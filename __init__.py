from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from config import Config
from flask_migrate import Migrate
from flask_mail import Mail, Message


db = SQLAlchemy()
mail = Mail()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/database_name'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.from_object(Config)
    app.config['WTF_CSRF_ENABLED'] = True
    
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = 'your_email_address'
    app.config['MAIL_PASSWORD'] = 'tanf arpq bfce zgoq'    # Your email password or app-specific password
    app.config['MAIL_USE_TLS']= True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_DEFAULT_SENDER'] = ('UNIZULU ONLINE APPLICATION SYSTEM', 'your_email_address')
    
    migrate = Migrate(app, db)
    db.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    return app