from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from config import Config
import bcrypt
import os
from datetime import datetime, timedelta
import secrets
from werkzeug.utils import secure_filename
from PIL import Image
import math

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)
mail = Mail(app)

# Helper functions
def get_db_connection():
    return mysql.connection

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def save_profile_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        image = Image.open(file)
        image.thumbnail((300, 300))
        image.save(filepath)
        
        return filename
    return None

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        
        if user:
            if check_password(password, user[2]):  # user[2] is the password field
                session['user_id'] = user[0]
                session['user_name'] = user[3]
                session['user_email'] = user[1]
                flash('Login successful! Welcome back!', 'success')
                return redirect(url_for('dashboard'))
            else:
                # Wrong password
                flash('Invalid password. Please try again.', 'error')
        else:
            # User not found
            flash('No account found with this email address.', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        # Check if email already exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing_user = cur.fetchone()
        
        if existing_user:
            cur.close()
            flash('An account with this email already exists. Please use a different email or login.', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        hashed_password = hash_password(password)
        
        try:
            cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", 
                       (name, email, hashed_password))
            mysql.connection.commit()
            
            # Get the new user's ID
            user_id = cur.lastrowid
            cur.close()
            
            # Auto-login after registration
            session['user_id'] = user_id
            session['user_name'] = name
            session['user_email'] = email
            
            flash(f'Registration successful! Welcome to Employee Management System, {name}!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('auth/register.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if user:
            token = secrets.token_urlsafe(32)
            
            # Delete any existing reset tokens for this email
            cur.execute("DELETE FROM password_resets WHERE email = %s", (email,))
            
            # Insert new token
            cur.execute("INSERT INTO password_resets (email, token, created_at) VALUES (%s, %s, %s)", 
                       (email, token, datetime.now()))
            mysql.connection.commit()
            
            try:
                # Create reset URL
                reset_url = url_for('reset_password', token=token, _external=True)
                
                # Create email message
                msg = Message(
                    subject='Password Reset Request - Employee Management System',
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[email]
                )
                
                # HTML email content
                msg.html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: #007bff; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background: #f9f9f9; }}
                        .button {{ background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                        .footer {{ margin-top: 20px; padding: 20px; background: #eee; font-size: 12px; color: #666; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Employee Management System</h1>
                        </div>
                        <div class="content">
                            <h2>Password Reset Request</h2>
                            <p>Hello,</p>
                            <p>You requested to reset your password for the Employee Management System.</p>
                            <p>Click the button below to reset your password:</p>
                            <p style="text-align: center;">
                                <a href="{reset_url}" class="button">Reset Password</a>
                            </p>
                            <p>Or copy and paste this link in your browser:</p>
                            <p><code>{reset_url}</code></p>
                            <p><strong>This link will expire in 1 hour.</strong></p>
                            <p>If you didn't request this password reset, please ignore this email.</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # Plain text fallback
                msg.body = f"""
                Password Reset Request - Employee Management System
                
                You requested to reset your password for the Employee Management System.
                
                Click the following link to reset your password:
                {reset_url}
                
                This link will expire in 1 hour.
                
                If you didn't request this password reset, please ignore this email.
                
                This is an automated message. Please do not reply to this email.
                """
                
                # Send email
                mail.send(msg)
                print(f"Password reset email sent to: {email}")  # Debug log
                flash('Password reset link has been sent to your email.', 'success')
                
            except Exception as e:
                print(f"Email sending error: {str(e)}")  # Debug logging
                flash(f'Error sending email: {str(e)}. Please try again later.', 'error')
        else:
            # For security, don't reveal if email exists or not
            flash('If an account with that email exists, a reset link has been sent.', 'success')
        
        cur.close()
        return redirect(url_for('forgot_password'))
    
    return render_template('auth/forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    cur = mysql.connection.cursor()
    
    # Check if token exists and is not expired (1 hour limit)
    cur.execute("""
        SELECT email, created_at 
        FROM password_resets 
        WHERE token = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
    """, (token,))
    reset_request = cur.fetchone()
    
    if not reset_request:
        flash('Invalid or expired reset token. Please request a new reset link.', 'error')
        cur.close()
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validate password length
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            cur.close()
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            cur.close()
            return render_template('auth/reset_password.html', token=token)
        
        try:
            hashed_password = hash_password(password)
            email = reset_request[0]
            
            # Update user password
            cur.execute("UPDATE users SET password = %s WHERE email = %s", 
                       (hashed_password, email))
            
            # Delete the used token
            cur.execute("DELETE FROM password_resets WHERE token = %s", (token,))
            
            mysql.connection.commit()
            cur.close()
            
            # Also send confirmation email
            try:
                msg = Message(
                    subject='Password Reset Successful - Employee Management System',
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[email]
                )
                msg.body = 'Your password has been successfully reset. You can now login with your new password.'
                mail.send(msg)
            except Exception as email_error:
                print(f"Confirmation email failed: {email_error}")  # Log but don't show to user
            
            flash('Password reset successful! You can now login with your new password.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            flash('Error resetting password. Please try again.', 'error')
            return render_template('auth/reset_password.html', token=token)
    
    cur.close()
    return render_template('auth/reset_password.html', token=token)

def check_email_config():
    """Check if email configuration is properly set"""
    required_configs = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD']
    missing_configs = []
    
    for config in required_configs:
        if not app.config.get(config):
            missing_configs.append(config)
    
    if missing_configs:
        print(f"WARNING: Missing email configuration: {', '.join(missing_configs)}")
        print("Password reset functionality will not work without proper email configuration.")
    else:
        print("Email configuration found. Password reset should work.")

@app.route('/test-email')
def test_email():
    """Test email configuration"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        msg = Message(
            subject='Test Email from Employee Management System',
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[session['user_email']]  # Send to logged-in user
        )
        msg.body = 'This is a test email to verify your email configuration is working correctly.'
        msg.html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #007bff; color: white; padding: 20px; text-align: center; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Employee Management System</h1>
                </div>
                <div class="content">
                    <h2>Test Email</h2>
                    <p>This is a test email to verify your email configuration is working correctly.</p>
                    <p>If you received this email, your email settings are properly configured.</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        mail.send(msg)
        flash('Test email sent successfully! Check your inbox.', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Email error: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    
    # Total Employees (user-specific) - exclude deleted and only count active employees
    cur.execute("SELECT COUNT(*) FROM employees WHERE deleted_at IS NULL AND leaving_date IS NULL AND user_id = %s", (user_id,))
    total_employees = cur.fetchone()[0]
    
    # Present Today (user-specific) - exclude deleted and left employees
    cur.execute("""
        SELECT COUNT(DISTINCT a.employee_id) 
        FROM attendance a 
        JOIN employees e ON a.employee_id = e.id 
        WHERE a.attendance_date = %s AND a.status IN ('present', 'half_day') 
        AND e.user_id = %s AND e.deleted_at IS NULL AND e.leaving_date IS NULL
    """, (datetime.now().date(), user_id))
    present_today = cur.fetchone()[0]
    
    # Total Salary Paid This Month (user-specific) - exclude deleted and left employees
    cur.execute("""
        SELECT COALESCE(SUM(employee_salary), 0) 
        FROM (
            SELECT 
                sc.per_day_salary * 
                (COUNT(CASE WHEN a.status = 'present' THEN 1 END) + 
                 COUNT(CASE WHEN a.status = 'half_day' THEN 1 END) * 0.5) as employee_salary
            FROM employees e
            JOIN salary_config sc ON e.id = sc.employee_id
            LEFT JOIN attendance a ON e.id = a.employee_id 
                AND YEAR(a.attendance_date) = YEAR(CURDATE()) 
                AND MONTH(a.attendance_date) = MONTH(CURDATE())
            WHERE e.deleted_at IS NULL AND e.leaving_date IS NULL AND e.user_id = %s
            GROUP BY e.id, sc.per_day_salary
        ) as salary_calc
    """, (user_id,))
    salary_result = cur.fetchone()
    total_salary = float(salary_result[0]) if salary_result and salary_result[0] else 0
    
    # Recent Activity - Last 5 attendance records (user-specific) - exclude deleted and left employees
    cur.execute("""
        SELECT e.name, a.attendance_date, a.status, a.updated_at
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        WHERE e.user_id = %s AND e.deleted_at IS NULL AND e.leaving_date IS NULL
        ORDER BY a.updated_at DESC
        LIMIT 5
    """, (user_id,))
    recent_activity = cur.fetchall()
    
    cur.close()
    
    return render_template('dashboard.html', 
                         total_employees=total_employees, 
                         present_today=present_today,
                         total_salary=total_salary,
                         recent_activity=recent_activity)

@app.route('/employees')
def employees():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    
    # Get all employees for current user (exclude deleted ones)
    cur.execute("""
        SELECT e.id, e.name, e.mobile_number, e.pan_number, e.date_of_birth, 
               e.profile_image, e.joining_date, e.leaving_date,
               sc.per_day_salary, sc.monthly_salary, sc.salary_type
        FROM employees e 
        LEFT JOIN salary_config sc ON e.id = sc.employee_id 
        WHERE e.user_id = %s AND e.deleted_at IS NULL
        ORDER BY e.leaving_date IS NULL DESC, e.joining_date DESC
    """, (user_id,))
    
    # Convert to list of dictionaries for easier template access
    columns = [col[0] for col in cur.description]
    employees_data = []
    for row in cur.fetchall():
        employees_data.append(dict(zip(columns, row)))
    
    # Calculate stats (only for non-deleted employees)
    total_employees = len(employees_data)
    active_employees = len([e for e in employees_data if not e['leaving_date']])
    inactive_employees = total_employees - active_employees
    
    cur.close()
    
    return render_template('employee/employees.html', 
                         employees=employees_data,
                         total_employees=total_employees,
                         active_employees=active_employees,
                         inactive_employees=inactive_employees)

@app.route('/employee/toggle_status/<int:employee_id>')
def toggle_employee_status(employee_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    
    try:
        # Get current employee status
        cur.execute("""
            SELECT name, leaving_date 
            FROM employees 
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
        """, (employee_id, user_id))
        
        employee = cur.fetchone()
        
        if not employee:
            flash('Employee not found or access denied', 'error')
            return redirect(url_for('employees'))
        
        employee_name, leaving_date = employee
        
        if leaving_date:
            # Employee is marked as left, so mark as active (set leaving_date to NULL)
            cur.execute("""
                UPDATE employees 
                SET leaving_date = NULL 
                WHERE id = %s AND user_id = %s
            """, (employee_id, user_id))
            flash(f'Employee "{employee_name}" has been marked as active!', 'success')
        else:
            # Employee is active, so mark as left (set leaving_date to current date)
            cur.execute("""
                UPDATE employees 
                SET leaving_date = %s 
                WHERE id = %s AND user_id = %s
            """, (datetime.now().date(), employee_id, user_id))
            flash(f'Employee "{employee_name}" has been marked as left!', 'success')
        
        mysql.connection.commit()
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error updating employee status: {str(e)}', 'error')
        print(f"Toggle employee status error: {str(e)}")
    finally:
        cur.close()
    
    return redirect(url_for('employees'))

@app.route('/employee/add', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        # Get form data with proper defaults
        name = request.form.get('name', '').strip()
        mobile_number = request.form.get('mobile_number', '').strip()
        pan_number = request.form.get('pan_number', '').strip()
        date_of_birth = request.form.get('date_of_birth', '').strip()
        address = request.form.get('address', '').strip()
        joining_date = request.form.get('joining_date', '').strip()
        leaving_date = request.form.get('leaving_date', '').strip()
        
        # Validate compulsory fields
        if not name:
            flash('Name is required', 'error')
            return render_template('employee/employee_form.html', 
                                 today=datetime.now().strftime('%Y-%m-%d'))
        
        if not joining_date:
            flash('Joining date is required', 'error')
            return render_template('employee/employee_form.html', 
                                 today=datetime.now().strftime('%Y-%m-%d'))
        
        # Convert empty strings to None for optional fields
        mobile_number = mobile_number if mobile_number else None
        pan_number = pan_number if pan_number else None
        address = address if address else None
        date_of_birth = date_of_birth if date_of_birth else None
        leaving_date = leaving_date if leaving_date else None
        
        # Salary configuration with proper defaults
        salary_type = request.form.get('salary_type', 'per_day')
        per_day_salary = request.form.get('per_day_salary', 350.00) or 350.00
        monthly_salary = request.form.get('monthly_salary', 0) or 0
        working_days_per_week = request.form.get('working_days_per_week', 6) or 6
        holiday_day = request.form.get('holiday_day', 'friday') or 'friday'
        
        # Convert numeric values
        try:
            per_day_salary = float(per_day_salary)
            monthly_salary = float(monthly_salary)
            working_days_per_week = int(working_days_per_week)
        except (ValueError, TypeError):
            flash('Invalid salary values provided', 'error')
            return render_template('employee/employee_form.html', 
                                 today=datetime.now().strftime('%Y-%m-%d'))
        
        # Validate dates
        if leaving_date and joining_date:
            if leaving_date < joining_date:
                flash('Leaving date cannot be before joining date', 'error')
                return render_template('employee/employee_form.html', 
                                     today=datetime.now().strftime('%Y-%m-%d'))
        
        # Handle profile image upload
        profile_image = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename and allowed_file(file.filename):
                profile_image = save_profile_image(file)
        
        cur = mysql.connection.cursor()
        try:
            # Insert employee with user_id and new fields
            cur.execute("""
                INSERT INTO employees (user_id, name, mobile_number, pan_number, date_of_birth, 
                                     address, profile_image, joining_date, leaving_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, name, mobile_number, pan_number, date_of_birth, address, 
                  profile_image, joining_date, leaving_date))
            
            employee_id = cur.lastrowid
            
            # Insert salary configuration with user_id and new fields
            cur.execute("""
                INSERT INTO salary_config (user_id, employee_id, per_day_salary, monthly_salary, 
                                         salary_type, working_days_per_week, holiday_day)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, employee_id, per_day_salary, monthly_salary, salary_type, 
                  working_days_per_week, holiday_day))
            
            mysql.connection.commit()
            flash('Employee added successfully!', 'success')
            return redirect(url_for('employees'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error adding employee: {str(e)}', 'error')
            print(f"Database error: {str(e)}")  # For debugging
        finally:
            cur.close()
    
    return render_template('employee/employee_form.html', 
                         today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/employee/edit/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    
    # Verify employee belongs to current user and is not deleted
    cur.execute("""
        SELECT e.id, e.name, e.mobile_number, e.pan_number, e.date_of_birth, e.address, 
               e.profile_image, e.joining_date, e.leaving_date, e.user_id,
               sc.per_day_salary, sc.monthly_salary, sc.salary_type, 
               sc.working_days_per_week, sc.holiday_day
        FROM employees e 
        LEFT JOIN salary_config sc ON e.id = sc.employee_id 
        WHERE e.id = %s AND e.user_id = %s AND e.deleted_at IS NULL
    """, (employee_id, user_id))
    
    columns = [col[0] for col in cur.description]
    employee_row = cur.fetchone()
    
    if not employee_row:
        flash('Employee not found or access denied', 'error')
        cur.close()
        return redirect(url_for('employees'))
    
    # Convert to dictionary for easier access
    employee = dict(zip(columns, employee_row))
    
    if request.method == 'POST':
        # Get form data with proper defaults
        name = request.form.get('name', '').strip()
        mobile_number = request.form.get('mobile_number', '').strip()
        pan_number = request.form.get('pan_number', '').strip()
        date_of_birth = request.form.get('date_of_birth', '').strip()
        address = request.form.get('address', '').strip()
        joining_date = request.form.get('joining_date', '').strip()
        leaving_date = request.form.get('leaving_date', '').strip()
        
        # Validate compulsory fields
        if not name:
            flash('Name is required', 'error')
            return redirect(url_for('edit_employee', employee_id=employee_id))
        
        if not joining_date:
            flash('Joining date is required', 'error')
            return redirect(url_for('edit_employee', employee_id=employee_id))
        
        # Convert empty strings to None for optional fields
        mobile_number = mobile_number if mobile_number else None
        pan_number = pan_number if pan_number else None
        address = address if address else None
        date_of_birth = date_of_birth if date_of_birth else None
        leaving_date = leaving_date if leaving_date else None
        
        # Salary configuration with proper defaults
        salary_type = request.form.get('salary_type', 'per_day')
        per_day_salary = request.form.get('per_day_salary', 350.00) or 350.00
        monthly_salary = request.form.get('monthly_salary', 0) or 0
        working_days_per_week = request.form.get('working_days_per_week', 6) or 6
        holiday_day = request.form.get('holiday_day', 'friday') or 'friday'
        
        # Convert numeric values
        try:
            per_day_salary = float(per_day_salary)
            monthly_salary = float(monthly_salary)
            working_days_per_week = int(working_days_per_week)
        except (ValueError, TypeError):
            flash('Invalid salary values provided', 'error')
            return redirect(url_for('edit_employee', employee_id=employee_id))
        
        # Validate dates
        if leaving_date and joining_date:
            if leaving_date < joining_date:
                flash('Leaving date cannot be before joining date', 'error')
                return redirect(url_for('edit_employee', employee_id=employee_id))
        
        # Handle profile image upload
        profile_image = employee['profile_image']  # Keep current image by default
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename and allowed_file(file.filename):
                profile_image = save_profile_image(file)
        
        try:
            # Update employee with new fields
            cur.execute("""
                UPDATE employees 
                SET name = %s, mobile_number = %s, pan_number = %s, 
                    date_of_birth = %s, address = %s, profile_image = %s,
                    joining_date = %s, leaving_date = %s
                WHERE id = %s AND user_id = %s
            """, (name, mobile_number, pan_number, date_of_birth, address, 
                  profile_image, joining_date, leaving_date, employee_id, user_id))
            
            # Update or insert salary configuration with new fields
            cur.execute("SELECT id FROM salary_config WHERE employee_id = %s AND user_id = %s", (employee_id, user_id))
            salary_config = cur.fetchone()
            
            if salary_config:
                cur.execute("""
                    UPDATE salary_config 
                    SET per_day_salary = %s, monthly_salary = %s, salary_type = %s,
                        working_days_per_week = %s, holiday_day = %s
                    WHERE employee_id = %s AND user_id = %s
                """, (per_day_salary, monthly_salary, salary_type, working_days_per_week, holiday_day, employee_id, user_id))
            else:
                cur.execute("""
                    INSERT INTO salary_config (user_id, employee_id, per_day_salary, monthly_salary,
                                             salary_type, working_days_per_week, holiday_day)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, employee_id, per_day_salary, monthly_salary, salary_type, working_days_per_week, holiday_day))
            
            mysql.connection.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error updating employee: {str(e)}', 'error')
            print(f"Database error: {str(e)}")  # For debugging
        finally:
            cur.close()
    
    # GET request - display form with current data
    cur.close()
    
    # Prepare data for template using dictionary access
    employee_salary = float(employee.get('per_day_salary', 350.00)) if employee.get('per_day_salary') else 350.00
    monthly_salary = float(employee.get('monthly_salary', 0)) if employee.get('monthly_salary') else 0
    salary_type = employee.get('salary_type', 'per_day')
    working_days = int(employee.get('working_days_per_week', 6)) if employee.get('working_days_per_week') else 6
    holiday_day_value = employee.get('holiday_day', 'friday')
    
    return render_template('employee/employee_form.html', 
                         employee=employee,
                         employee_salary=employee_salary,
                         monthly_salary=monthly_salary,
                         salary_type=salary_type,
                         working_days=working_days,
                         holiday_day=holiday_day_value,
                         today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/employee/delete/<int:employee_id>')
def delete_employee(employee_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    
    # Verify employee belongs to current user before deletion
    cur.execute("SELECT id, name FROM employees WHERE id = %s AND user_id = %s AND deleted_at IS NULL", (employee_id, user_id))
    employee = cur.fetchone()
    
    if not employee:
        flash('Employee not found or access denied', 'error')
        cur.close()
        return redirect(url_for('employees'))
    
    employee_name = employee[1]
    
    try:
        # Soft delete: set deleted_at timestamp
        cur.execute("""
            UPDATE employees 
            SET deleted_at = %s 
            WHERE id = %s AND user_id = %s
        """, (datetime.now(), employee_id, user_id))
        
        mysql.connection.commit()
        flash(f'Employee "{employee_name}" has been deleted successfully!', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error deleting employee: {str(e)}', 'error')
        print(f"Delete employee error: {str(e)}")
    finally:
        cur.close()
    
    return redirect(url_for('employees'))

@app.route('/attendance')
def attendance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    cur = mysql.connection.cursor()
    
    # Get all employees for current user - exclude deleted ones
    # Include left employees but show their leaving date
    cur.execute("""
        SELECT id, name, leaving_date FROM employees 
        WHERE deleted_at IS NULL AND user_id = %s 
        ORDER BY name
    """, (user_id,))
    employees = cur.fetchall()
    
    # Get attendance for selected date for current user (including advance and notes) - exclude deleted employees
    cur.execute("""
        SELECT a.employee_id, a.status, a.notes, a.advance 
        FROM attendance a 
        JOIN employees e ON a.employee_id = e.id
        WHERE a.attendance_date = %s AND e.user_id = %s AND e.deleted_at IS NULL
    """, (date, user_id))
    attendance_data = {row[0]: {'status': row[1], 'notes': row[2] or '', 'advance': float(row[3] or 0)} for row in cur.fetchall()}
    
    # Get attendance summary for the date for current user - exclude deleted employees
    cur.execute("""
        SELECT 
            COUNT(DISTINCT a.employee_id) as total_marked,
            COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present_count,
            COUNT(CASE WHEN a.status = 'half_day' THEN 1 END) as half_day_count,
            COUNT(CASE WHEN a.status = 'absent' THEN 1 END) as absent_count
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        WHERE a.attendance_date = %s AND e.user_id = %s AND e.deleted_at IS NULL
    """, (date, user_id))
    summary = cur.fetchone()
    
    cur.close()
    
    return render_template('attendance/attendance.html', 
                         employees=employees, 
                         attendance_data=attendance_data,
                         selected_date=date,
                         summary=summary)

@app.route('/update_attendance', methods=['POST'])
def update_attendance():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login'})
    
    user_id = session['user_id']
    data = request.get_json()
    
    employee_id = data.get('employee_id')
    date = data.get('date')
    status = data.get('status')
    notes = data.get('notes', '')
    advance = data.get('advance', 0)
    
    if not employee_id or not date:
        return jsonify({'success': False, 'message': 'Employee ID and date are required'})
    
    cur = mysql.connection.cursor()
    
    try:
        # Check if employee belongs to current user and is not deleted
        cur.execute("""
            SELECT id, leaving_date FROM employees 
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
        """, (employee_id, user_id))
        employee = cur.fetchone()
        
        if not employee:
            return jsonify({'success': False, 'message': 'Employee not found or access denied'})
        
        employee_id_db, leaving_date = employee
        
        # Check if employee has left and the date is after leaving date
        if leaving_date and date > leaving_date.strftime('%Y-%m-%d'):
            return jsonify({'success': False, 'message': f'Cannot mark attendance after employee left on {leaving_date}'})
        
        # If status is empty or 'not_marked', delete the attendance record
        if not status or status == 'not_marked':
            cur.execute("""
                DELETE FROM attendance 
                WHERE employee_id = %s AND attendance_date = %s AND user_id = %s
            """, (employee_id, date, user_id))
        else:
            # Insert or update attendance record
            cur.execute("""
                INSERT INTO attendance (user_id, employee_id, attendance_date, status, notes, advance)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    status = VALUES(status),
                    notes = VALUES(notes),
                    advance = VALUES(advance),
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, employee_id, date, status, notes, advance))
        
        mysql.connection.commit()
        return jsonify({'success': True, 'message': 'Attendance updated successfully'})
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': f'Error updating attendance: {str(e)}'})
    finally:
        cur.close()

# New route to get notes for an employee on specific date
@app.route('/get_attendance_notes', methods=['POST'])
def get_attendance_notes():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login'})
    
    user_id = session['user_id']
    data = request.get_json()
    
    employee_id = data.get('employee_id')
    date = data.get('date')
    
    if not employee_id or not date:
        return jsonify({'success': False, 'message': 'Employee ID and date are required'})
    
    cur = mysql.connection.cursor()
    
    try:
        # Get notes for the specific employee and date
        cur.execute("""
            SELECT notes 
            FROM attendance 
            WHERE employee_id = %s AND attendance_date = %s AND user_id = %s
        """, (employee_id, date, user_id))
        
        result = cur.fetchone()
        notes = result[0] if result else ''
        
        return jsonify({'success': True, 'notes': notes})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching notes: {str(e)}'})
    finally:
        cur.close()

@app.route('/salary')
def salary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    employee_id = request.args.get('employee_id')
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    
    cur = mysql.connection.cursor()
    
    # Get all employees for dropdown for current user - exclude deleted ones
    cur.execute("""
        SELECT e.id, e.name, sc.per_day_salary, sc.salary_type, sc.monthly_salary, e.leaving_date
        FROM employees e 
        LEFT JOIN salary_config sc ON e.id = sc.employee_id 
        WHERE e.user_id = %s AND e.deleted_at IS NULL
        ORDER BY e.leaving_date IS NULL DESC, e.name
    """, (user_id,))
    employees = cur.fetchall()
    
    salary_data = None
    if employee_id and month:
        # Verify employee belongs to current user and is not deleted
        cur.execute("""
            SELECT id, leaving_date FROM employees 
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
        """, (employee_id, user_id))
        employee_info = cur.fetchone()
        
        if not employee_info:
            cur.close()
            flash('Employee not found or access denied', 'error')
            return redirect(url_for('salary'))
        
        employee_id_db, leaving_date = employee_info
        
        # Get employee salary configuration
        cur.execute("""
            SELECT e.name, sc.per_day_salary, sc.working_days_per_week, sc.holiday_day, 
                   sc.salary_type, sc.monthly_salary
            FROM employees e 
            LEFT JOIN salary_config sc ON e.id = sc.employee_id 
            WHERE e.id = %s AND e.user_id = %s
        """, (employee_id, user_id))
        employee_data = cur.fetchone()
        
        if employee_data:
            employee_name, per_day_salary, working_days_per_week, holiday_day, salary_type, monthly_salary = employee_data
            
            # If no salary config found, use defaults
            if per_day_salary is None:
                per_day_salary = 350.00
            if working_days_per_week is None:
                working_days_per_week = 6
            if holiday_day is None:
                holiday_day = 'friday'
            if salary_type is None:
                salary_type = 'per_day'
            if monthly_salary is None:
                monthly_salary = 0
            
            # Convert to float to avoid decimal issues
            per_day_salary = float(per_day_salary)
            monthly_salary = float(monthly_salary)
            
            # Calculate date range for the selected month
            year, month_num = map(int, month.split('-'))
            start_date = datetime(year, month_num, 1)
            if month_num == 12:
                end_date = datetime(year+1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month_num+1, 1) - timedelta(days=1)
            
            # Adjust end_date if employee left during the month
            if leaving_date and leaving_date < end_date.date():
                end_date = datetime.combine(leaving_date, datetime.min.time())
            
            # Get total days in month (for monthly salary calculation)
            total_days_in_month = (end_date - start_date).days + 1
            
            # Calculate effective per day salary based on salary type
            if salary_type == 'per_month' and monthly_salary > 0:
                # For monthly salary: divide monthly salary by total days in month
                effective_per_day_salary = monthly_salary / total_days_in_month
                salary_calculation_note = f"Monthly Salary: ₹{monthly_salary:,.2f} ÷ {total_days_in_month} days = ₹{effective_per_day_salary:.2f}/day"
            else:
                # For per day salary: use the fixed per_day_salary
                effective_per_day_salary = per_day_salary
                salary_calculation_note = f"Per Day Salary: ₹{effective_per_day_salary:.2f}"
            
            # Get attendance records for the month (including advance)
            cur.execute("""
                SELECT attendance_date, status, advance 
                FROM attendance 
                WHERE employee_id = %s AND user_id = %s AND attendance_date BETWEEN %s AND %s
                ORDER BY attendance_date
            """, (employee_id, user_id, start_date.date(), end_date.date()))
            attendance_records = {record[0]: {'status': record[1], 'advance': float(record[2] or 0)} for record in cur.fetchall()}
            
            # Calculate working days, holidays, and attendance
            total_days = 0
            working_days = 0
            weekly_holidays = 0
            worked_holidays = 0
            unmarked_days = 0
            present_days = 0
            half_days = 0
            absent_days = 0
            total_advance = 0.0  # Track total advance for the month
            
            daily_attendance = []
            weekly_summary = []
            current_date = start_date
            current_week = []
            week_number = 1
            
            while current_date <= end_date:
                day_name = current_date.strftime('%A').lower()
                is_weekly_holiday = (day_name == holiday_day.lower())
                
                # Check if this is the leaving date
                is_leaving_date = (leaving_date and current_date.date() == leaving_date)
                
                # Check if attendance is marked for this day
                attendance_info = attendance_records.get(current_date.date())
                attendance_status = attendance_info['status'] if attendance_info else None
                advance_amount = float(attendance_info['advance']) if attendance_info else 0.0
                
                total_advance += advance_amount
                
                # Handle leaving date specially
                if is_leaving_date:
                    if attendance_status:
                        # Employee worked on their last day
                        if attendance_status == 'present':
                            day_salary = float(effective_per_day_salary)
                            present_days += 1
                            status = 'present_left'
                        elif attendance_status == 'half_day':
                            day_salary = float(effective_per_day_salary / 2)
                            half_days += 1
                            status = 'half_day_left'
                        else:  # absent on last day
                            day_salary = 0.0
                            absent_days += 1
                            status = 'absent_left'
                    else:
                        # No attendance marked on leaving date
                        day_salary = 0.0
                        unmarked_days += 1
                        status = 'unmarked_left'
                    
                    working_days += 1
                    
                elif is_weekly_holiday:
                    if attendance_status:
                        # Weekly holiday but attendance marked - employee worked on holiday
                        working_days += 1
                        worked_holidays += 1
                        
                        if attendance_status == 'present':
                            day_salary = float(effective_per_day_salary)
                            present_days += 1
                            status = 'worked_holiday_present'
                        elif attendance_status == 'half_day':
                            day_salary = float(effective_per_day_salary / 2)
                            half_days += 1
                            status = 'worked_holiday_half'
                        else:  # absent on holiday (shouldn't normally happen)
                            day_salary = 0.0
                            absent_days += 1
                            status = 'worked_holiday_absent'
                    else:
                        # Weekly holiday with no attendance marked
                        day_salary = 0.0
                        weekly_holidays += 1
                        status = 'weekly_holiday'
                        
                elif attendance_status is None:
                    # Regular day with no attendance marked - treat as holiday (salary = 0)
                    status = 'unmarked'
                    day_salary = 0.0
                    unmarked_days += 1
                else:
                    # Regular working day with attendance marked
                    working_days += 1
                    status = attendance_status
                    
                    if status == 'present':
                        day_salary = float(effective_per_day_salary)
                        present_days += 1
                    elif status == 'half_day':
                        day_salary = float(effective_per_day_salary / 2)
                        half_days += 1
                    else:  # absent
                        day_salary = 0.0
                        absent_days += 1
                
                # Calculate net salary for the day (ensure both are floats)
                day_salary_float = float(day_salary)
                advance_amount_float = float(advance_amount)
                net_salary = day_salary_float - advance_amount_float
                
                # Add to daily attendance (include advance)
                daily_attendance.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day': current_date.strftime('%A'),
                    'status': status,
                    'salary': day_salary_float,
                    'advance': advance_amount_float,
                    'net_salary': net_salary,  # Net for the day
                    'is_holiday': is_weekly_holiday,
                    'is_leaving_date': is_leaving_date
                })
                
                # Add to current week for weekly calculation
                current_week.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day': current_date.strftime('%A'),
                    'status': status,
                    'salary': day_salary_float,
                    'advance': advance_amount_float,
                    'net_salary': net_salary,
                    'is_holiday': is_weekly_holiday,
                    'is_leaving_date': is_leaving_date
                })
                
                # If it's the weekly holiday or end of month or leaving date, finalize the week
                if (is_weekly_holiday and len(current_week) > 0) or current_date == end_date or is_leaving_date:
                    week_salary = sum(float(day['salary']) for day in current_week)
                    week_advance = sum(float(day['advance']) for day in current_week)
                    week_net_salary = week_salary - week_advance
                    week_working_days = len([day for day in current_week if day['status'] in ['present', 'half_day', 'absent', 'worked_holiday_present', 'worked_holiday_half', 'worked_holiday_absent', 'present_left', 'half_day_left', 'absent_left']])
                    week_present = len([day for day in current_week if day['status'] in ['present', 'worked_holiday_present', 'present_left']])
                    week_half = len([day for day in current_week if day['status'] in ['half_day', 'worked_holiday_half', 'half_day_left']])
                    week_absent = len([day for day in current_week if day['status'] in ['absent', 'worked_holiday_absent', 'absent_left']])
                    week_unmarked = len([day for day in current_week if day['status'] in ['unmarked', 'unmarked_left']])
                    week_holidays = len([day for day in current_week if day['status'] == 'weekly_holiday'])
                    week_worked_holidays = len([day for day in current_week if day['status'] in ['worked_holiday_present', 'worked_holiday_half', 'worked_holiday_absent']])
                    week_leaving_days = len([day for day in current_week if day['is_leaving_date']])
                    
                    weekly_summary.append({
                        'week': week_number,
                        'start_date': current_week[0]['date'],
                        'end_date': current_week[-1]['date'],
                        'working_days': week_working_days,
                        'present_days': week_present,
                        'half_days': week_half,
                        'absent_days': week_absent,
                        'unmarked_days': week_unmarked,
                        'holidays': week_holidays,
                        'worked_holidays': week_worked_holidays,
                        'leaving_days': week_leaving_days,
                        'salary': week_salary,
                        'advance': week_advance,
                        'net_salary': week_net_salary
                    })
                    
                    current_week = []
                    week_number += 1
                
                total_days += 1
                current_date += timedelta(days=1)
            
            # Calculate total salary (include worked holidays in calculation)
            total_salary = (present_days * effective_per_day_salary) + (half_days * (effective_per_day_salary / 2))
            net_salary = float(total_salary) - float(total_advance)  # Subtract total advances
            
            salary_data = {
                'employee_id': employee_id,
                'employee_name': employee_name,
                'month': month,
                'salary_type': salary_type,
                'per_day_salary': effective_per_day_salary,
                'monthly_salary': monthly_salary,
                'working_days_per_week': working_days_per_week,
                'leaving_date': leaving_date,
                'total_days': total_days,
                'total_days_in_month': total_days_in_month,
                'working_days': working_days,
                'weekly_holidays': weekly_holidays,
                'worked_holidays': worked_holidays,
                'unmarked_days': unmarked_days,
                'present_days': present_days,
                'half_days': half_days,
                'absent_days': absent_days,
                'total_salary': total_salary,
                'total_advance': total_advance,
                'net_salary': net_salary,  # Salary after advance deduction
                'daily_attendance': daily_attendance,
                'weekly_summary': weekly_summary,
                'holiday_day': holiday_day,
                'salary_calculation_note': salary_calculation_note
            }
    
    cur.close()
    
    return render_template('salary/salary.html', 
                         employees=employees, 
                         salary_data=salary_data,
                         selected_employee=employee_id,
                         selected_month=month)

@app.route('/report')
def report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    report_type = request.args.get('type', 'weekly_salary')
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    employee_id = request.args.get('employee_id', '')
    
    cur = mysql.connection.cursor()
    
    # Get employees for dropdown - exclude deleted
    cur.execute("""
        SELECT id, name, leaving_date
        FROM employees 
        WHERE user_id = %s AND deleted_at IS NULL
        ORDER BY leaving_date IS NULL DESC, name
    """, (user_id,))
    employees = cur.fetchall()
    
    # Initialize report_data with default values
    report_data = {
        'weekly_data': {},
        'employee_summary': [],
        'total_employees': 0,
        'active_employees': 0,
        'total_paid': 0,
        'total_advance': 0,
        'total_net_paid': 0
    }
    
    def calculate_daily_rate(monthly_salary, year, month_num):
        """Calculate daily rate for monthly salary employees"""
        year_int, month_int = int(year), int(month_num)
        start_date = datetime(year_int, month_int, 1)
        
        if month_int == 12:
            end_date = datetime(year_int + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year_int, month_int + 1, 1) - timedelta(days=1)
        
        total_days_in_month = (end_date - start_date).days + 1
        daily_rate = float(monthly_salary) / total_days_in_month
        return daily_rate, total_days_in_month

    if report_type == 'weekly_salary':
        # Weekly Salary Report - include both active and left employees
        year, month_num = month.split('-')
    
        print(f"DEBUG: Generating weekly report for {year}-{month_num}")
    
        # Get employee if specified
        employee_filter = ""
        params = [user_id, int(year), int(month_num)]
        if employee_id:
            employee_filter = " AND e.id = %s"
            params.append(int(employee_id))
    
        # Get all attendance records for the month (including advance) - exclude deleted employees
        cur.execute(f"""
            SELECT 
                e.id,
                e.name,
                e.leaving_date,
                COALESCE(sc.per_day_salary, 350.00) as per_day_salary,
                COALESCE(sc.salary_type, 'per_day') as salary_type,
                COALESCE(sc.monthly_salary, 0) as monthly_salary,
                COALESCE(sc.holiday_day, 'friday') as holiday_day,
                a.attendance_date,
                a.status,
                a.advance
            FROM employees e
            LEFT JOIN salary_config sc ON e.id = sc.employee_id AND sc.user_id = e.user_id
            INNER JOIN attendance a ON e.id = a.employee_id AND a.user_id = e.user_id
            WHERE e.user_id = %s AND e.deleted_at IS NULL
            AND YEAR(a.attendance_date) = %s 
            AND MONTH(a.attendance_date) = %s
            {employee_filter}
            ORDER BY e.leaving_date IS NULL DESC, e.name, a.attendance_date
        """, params)
    
        weekly_records = cur.fetchall()
        print(f"DEBUG: Found {len(weekly_records)} attendance records for weekly report")
    
        # Organize data by employee and week
        weekly_data = {}
        
        # Initialize totals
        total_employees = 0
        total_weeks = set()
        total_present_days = 0
        total_salary_amount = 0
        total_advance_amount = 0

        for row in weekly_records:
            emp_id, name, leaving_date, per_day_salary, salary_type, monthly_salary, holiday_day, attendance_date, status, advance = row
        
            if emp_id not in weekly_data:
                # Calculate effective per day salary
                if salary_type == 'per_month' and float(monthly_salary) > 0:
                    effective_per_day, total_days_in_month = calculate_daily_rate(monthly_salary, year, month_num)
                else:
                    effective_per_day = float(per_day_salary)
                    total_days_in_month = 0
            
                weekly_data[emp_id] = {
                    'name': name,
                    'leaving_date': leaving_date,
                    'status': 'Active' if not leaving_date else 'Left',
                    'effective_per_day': effective_per_day,
                    'salary_type': salary_type,
                    'monthly_salary': float(monthly_salary),
                    'total_days_in_month': total_days_in_month,
                    'weekly_data': {}
                }
                total_employees += 1
        
            if attendance_date:
                # Convert to datetime if string
                if isinstance(attendance_date, str):
                    attendance_date = datetime.strptime(attendance_date, '%Y-%m-%d')
            
                week_number = attendance_date.isocalendar()[1]
                week_year = attendance_date.isocalendar()[0]
                week_key = f"Week {week_number}"
                
                # Add to total weeks
                total_weeks.add(week_key)
            
                # Calculate week start and end dates
                week_start = attendance_date - timedelta(days=attendance_date.weekday())
                week_end = week_start + timedelta(days=6)
            
                if week_key not in weekly_data[emp_id]['weekly_data']:
                    weekly_data[emp_id]['weekly_data'][week_key] = {
                        'week_number': week_number,
                        'week_start': week_start.strftime('%Y-%m-%d'),
                        'week_end': week_end.strftime('%Y-%m-%d'),
                        'present_days': 0,
                        'half_days': 0,
                        'absent_days': 0,
                        'salary': 0,
                        'advance': 0,
                        'net_salary': 0,
                        'days': []
                    }
            
                # Calculate day salary
                if status == 'present':
                    weekly_data[emp_id]['weekly_data'][week_key]['present_days'] += 1
                    day_salary = weekly_data[emp_id]['effective_per_day']
                    total_present_days += 1
                elif status == 'half_day':
                    weekly_data[emp_id]['weekly_data'][week_key]['half_days'] += 1
                    day_salary = weekly_data[emp_id]['effective_per_day'] / 2
                elif status == 'absent':
                    weekly_data[emp_id]['weekly_data'][week_key]['absent_days'] += 1
                    day_salary = 0
                else:
                    day_salary = 0
            
                # Add advance
                advance_amount = float(advance or 0)
                net_salary = day_salary - advance_amount
                
                weekly_data[emp_id]['weekly_data'][week_key]['salary'] += day_salary
                weekly_data[emp_id]['weekly_data'][week_key]['advance'] += advance_amount
                weekly_data[emp_id]['weekly_data'][week_key]['net_salary'] += net_salary
                
                total_salary_amount += day_salary
                total_advance_amount += advance_amount
                
                weekly_data[emp_id]['weekly_data'][week_key]['days'].append({
                    'date': attendance_date.strftime('%Y-%m-%d'),
                    'day': attendance_date.strftime('%A'),
                    'status': status,
                    'salary': day_salary,
                    'advance': advance_amount,
                    'net_salary': net_salary
                })
    
        # If no attendance records found, at least show employees
        if not weekly_records and not employee_id:
            cur.execute("""
                SELECT 
                    e.id,
                    e.name,
                    e.leaving_date,
                    COALESCE(sc.per_day_salary, 350.00) as per_day_salary,
                    COALESCE(sc.salary_type, 'per_day') as salary_type,
                    COALESCE(sc.monthly_salary, 0) as monthly_salary,
                    COALESCE(sc.holiday_day, 'friday') as holiday_day
                FROM employees e
                LEFT JOIN salary_config sc ON e.id = sc.employee_id AND sc.user_id = e.user_id
                WHERE e.user_id = %s AND e.deleted_at IS NULL
            """, (user_id,))
        
            employees_without_attendance = cur.fetchall()
            for emp_row in employees_without_attendance:
                emp_id, name, leaving_date, per_day_salary, salary_type, monthly_salary, holiday_day = emp_row
                weekly_data[emp_id] = {
                    'name': name,
                    'leaving_date': leaving_date,
                    'status': 'Active' if not leaving_date else 'Left',
                    'effective_per_day': float(per_day_salary),
                    'salary_type': salary_type,
                    'monthly_salary': float(monthly_salary),
                    'total_days_in_month': 0,
                    'weekly_data': {}
                }
                total_employees += 1

        report_data = {
            'weekly_data': weekly_data,
            'selected_employee': employee_id,
            'total_employees': total_employees,
            'active_employees': len([e for e in weekly_data.values() if not e['leaving_date']]),
            'total_weeks': len(total_weeks),
            'total_present_days': total_present_days,
            'total_salary': total_salary_amount,
            'total_advance': total_advance_amount,
            'total_net_salary': total_salary_amount - total_advance_amount
        }
    
        print(f"DEBUG: Weekly report generated with {len(weekly_data)} employees")
        
    elif report_type == 'employee_summary':
        # Employee Summary Report - include both active and inactive employees
        print("DEBUG: Generating employee summary report")
        
        cur.execute("""
            SELECT 
                e.id,
                e.name,
                e.joining_date,
                e.leaving_date,
                COALESCE(sc.per_day_salary, 350.00) as per_day_salary,
                COALESCE(sc.salary_type, 'per_day') as salary_type,
                COALESCE(sc.monthly_salary, 0) as monthly_salary,
                (SELECT COUNT(*) FROM attendance a WHERE a.employee_id = e.id AND a.user_id = e.user_id AND a.status = 'present') as total_present,
                (SELECT COUNT(*) FROM attendance a WHERE a.employee_id = e.id AND a.user_id = e.user_id AND a.status = 'half_day') as total_half_days,
                (SELECT COUNT(*) FROM attendance a WHERE a.employee_id = e.id AND a.user_id = e.user_id AND a.status = 'absent') as total_absent,
                (SELECT COALESCE(SUM(
                    CASE 
                        WHEN sc.salary_type = 'per_month' AND sc.monthly_salary > 0 THEN
                            CASE 
                                WHEN a.status = 'present' THEN sc.monthly_salary / DAY(LAST_DAY(a.attendance_date))
                                WHEN a.status = 'half_day' THEN (sc.monthly_salary / DAY(LAST_DAY(a.attendance_date))) / 2
                                ELSE 0 
                            END
                        ELSE
                            CASE 
                                WHEN a.status = 'present' THEN sc.per_day_salary 
                                WHEN a.status = 'half_day' THEN sc.per_day_salary / 2 
                                ELSE 0 
                            END
                    END
                ), 0) FROM attendance a WHERE a.employee_id = e.id AND a.user_id = e.user_id) as total_earned,
                (SELECT COALESCE(SUM(advance), 0) FROM attendance a WHERE a.employee_id = e.id AND a.user_id = e.user_id) as total_advance
            FROM employees e
            LEFT JOIN salary_config sc ON e.id = sc.employee_id AND sc.user_id = e.user_id
            WHERE e.user_id = %s AND e.deleted_at IS NULL
            ORDER BY e.leaving_date IS NULL DESC, e.name
        """, (user_id,))
        
        summary_data = []
        total_paid = 0
        total_advance = 0
        total_net_paid = 0
        
        for row in cur.fetchall():
            total_earned = float(row[10] or 0)
            total_advance_emp = float(row[11] or 0)
            net_earned = total_earned - total_advance_emp
            
            total_paid += total_earned
            total_advance += total_advance_emp
            total_net_paid += net_earned
            
            summary_data.append({
                'id': row[0],
                'name': row[1],
                'joining_date': row[2],
                'leaving_date': row[3],
                'status': 'Active' if not row[3] else 'Left',
                'per_day_salary': float(row[4] or 0),
                'salary_type': row[5] or 'per_day',
                'monthly_salary': float(row[6] or 0),
                'total_present': row[7] or 0,
                'total_half_days': row[8] or 0,
                'total_absent': row[9] or 0,
                'total_earned': total_earned,
                'total_advance': total_advance_emp,
                'net_earned': net_earned
            })
        
        report_data = {
            'employee_summary': summary_data,
            'total_employees': len(summary_data),
            'active_employees': len([e for e in summary_data if e['status'] == 'Active']),
            'total_paid': total_paid,
            'total_advance': total_advance,
            'total_net_paid': total_net_paid
        }
        
        print(f"DEBUG: Employee summary generated with {len(summary_data)} employees")
    
    # Get available months for dropdown
    cur.execute("""
        SELECT DISTINCT DATE_FORMAT(attendance_date, '%%Y-%%m') as month 
        FROM attendance 
        WHERE user_id = %s 
        UNION
        SELECT DATE_FORMAT(NOW(), '%%Y-%%m') as month
        ORDER BY month DESC
        LIMIT 12
    """, (user_id,))
    months_result = cur.fetchall()
    months = [row[0] for row in months_result] if months_result else [datetime.now().strftime('%Y-%m')]
    
    cur.close()
    
    current_datetime = datetime.now()
    
    return render_template('report/report.html',
                         report_type=report_type,
                         report_data=report_data,
                         employees=employees,
                         months=months,
                         selected_month=month,
                         selected_employee=employee_id,
                         current_datetime=current_datetime)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# Error handlers
# Add this route for favicon (prevents 500 errors)
@app.route('/favicon.ico')
@app.route('/favicon.jpg')
def favicon():
    # Determine which file to serve based on the route
    if request.path.endswith('.jpg'):
        filename = 'favicon.jpg'
        mimetype = 'image/jpeg'
    else:
        filename = 'favicon.ico' 
        mimetype = 'image/vnd.microsoft.icon'
    
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'images'),
        filename,
        mimetype=mimetype
    )

# Update the 404 error handler
@app.errorhandler(404)
def not_found_error(error):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page Not Found</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f8f9fa; }
            .error-container { margin-top: 100px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center error-container">
                <div class="col-md-6 text-center">
                    <h1 class="display-1 text-primary">404</h1>
                    <h2 class="mb-3">Oops! Page not found</h2>
                    <p class="lead text-muted mb-4">
                        The page you're looking for doesn't exist or has been moved.
                    </p>
                    <div class="d-grid gap-2 d-sm-flex justify-content-sm-center">
                        <a href="/dashboard" class="btn btn-primary btn-lg px-4">Dashboard</a>
                        <a href="/employees" class="btn btn-outline-secondary btn-lg px-4">Employees</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """, 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.route('/debug-email-config')
def debug_email_config():
    """Debug email configuration"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    config_info = {
        'MAIL_SERVER': app.config.get('MAIL_SERVER'),
        'MAIL_PORT': app.config.get('MAIL_PORT'),
        'MAIL_USE_TLS': app.config.get('MAIL_USE_TLS'),
        'MAIL_USERNAME': app.config.get('MAIL_USERNAME'),
        'MAIL_PASSWORD': '***' if app.config.get('MAIL_PASSWORD') else 'Not set',
        'MAIL_DEFAULT_SENDER': app.config.get('MAIL_DEFAULT_SENDER')
    }
    
    return f"""
    <h1>Email Configuration Debug</h1>
    <pre>{config_info}</pre>
    <p><a href="{url_for('test_email')}">Test Email</a></p>
    <p><a href="{url_for('dashboard')}">Back to Dashboard</a></p>
    """

if __name__ == '__main__':
    check_email_config()

    # Create upload folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Create necessary directories
    os.makedirs('templates/errors', exist_ok=True)
    os.makedirs('templates/auth', exist_ok=True)
    os.makedirs('templates/employee', exist_ok=True)
    os.makedirs('templates/attendance', exist_ok=True)
    os.makedirs('templates/salary', exist_ok=True)
    os.makedirs('templates/report', exist_ok=True)
    
    app.run(debug=True)