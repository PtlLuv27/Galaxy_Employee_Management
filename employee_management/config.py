import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

class Config:
    # MySQL Configuration - from environment variables
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))  # Default MySQL port is 3306
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'Luvp@tel-270705')
    MYSQL_DB = os.getenv('MYSQL_DB', 'employee_management')
    
    # Secret Key - from environment variable
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key-change-this')
    
    # File Upload
    UPLOAD_FOLDER = 'static/images/uploads'
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB max file size
    
    # Email Configuration - from environment variables
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'luvpatel2707@gmail.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'sjom tnkn atbx qisb')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'luvpatel2707@gmail.com')