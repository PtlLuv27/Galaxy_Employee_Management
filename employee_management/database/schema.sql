-- Create new database
CREATE DATABASE IF NOT EXISTS employee_management;
USE employee_management;

-- Users table for authentication (multi-tenant foundation)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Employees table with user_id for multi-tenancy
CREATE TABLE employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,  -- Links to users table for data isolation
    name VARCHAR(255) NOT NULL,
    mobile_number VARCHAR(15) NULL,  -- Changed to NULLABLE and NOT UNIQUE
    pan_number VARCHAR(20),
    date_of_birth DATE,
    address TEXT,
    profile_image VARCHAR(255),
    joining_date DATE NOT NULL,  -- Added as compulsory field
    leaving_date DATE NULL,  -- Added for employee status tracking
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    -- Removed the UNIQUE KEY constraint for mobile_number
);

-- Salary configuration table with individual settings per employee
CREATE TABLE salary_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,  -- For multi-tenancy
    employee_id INT NOT NULL,
    salary_type ENUM('per_day', 'per_month') DEFAULT 'per_day',
    per_day_salary DECIMAL(10,2) DEFAULT 350.00,
    monthly_salary DECIMAL(10,2) DEFAULT 0.00,
    working_days_per_week INT DEFAULT 6,
    holiday_day VARCHAR(20) DEFAULT 'friday',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    UNIQUE KEY unique_employee_config (user_id, employee_id)  -- One config per employee per user
);

-- Attendance table with user_id for data isolation
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,  -- For multi-tenancy
    employee_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status ENUM('present', 'absent', 'half_day') NOT NULL,
    notes TEXT,
    advance DECIMAL(10,2) DEFAULT 0.00,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_attendance (user_id, employee_id, attendance_date)  -- One entry per day per employee per user
);

-- Add indexes for better performance
CREATE INDEX idx_attendance_employee_date ON attendance(employee_id, attendance_date);
CREATE INDEX idx_attendance_user_date ON attendance(user_id, attendance_date);
CREATE INDEX idx_attendance_date ON attendance(attendance_date);
CREATE INDEX idx_attendance_status ON attendance(status);


-- Password reset table
CREATE TABLE password_resets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE employees ADD COLUMN deleted_at TIMESTAMP NULL DEFAULT NULL;