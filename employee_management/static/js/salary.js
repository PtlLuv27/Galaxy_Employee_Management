// Salary calculation JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Salary form submission
    const salaryForm = document.getElementById('salaryForm');
    if (salaryForm) {
        salaryForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const formData = new FormData(this);
            const params = new URLSearchParams(formData);
            
            const newUrl = `${window.location.pathname}?${params.toString()}`;
            window.location.href = newUrl;
        });
    }
    
    // Salary configuration modal
    const configModal = document.getElementById('configModal');
    if (configModal) {
        const saveConfigBtn = document.getElementById('saveConfig');
        
        saveConfigBtn.addEventListener('click', function() {
            const employeeId = document.getElementById('employeeSelect').value;
            const perDaySalary = document.getElementById('perDaySalary').value;
            const workingDays = document.getElementById('workingDays').value;
            const holidayDay = document.getElementById('holidayDay').value;
            
            updateSalaryConfig(employeeId, perDaySalary, workingDays, holidayDay);
        });
    }
    
    // Auto-calculate on employee/month change
    const employeeSelect = document.getElementById('employeeSelect');
    const monthSelect = document.getElementById('monthSelect');
    
    if (employeeSelect && monthSelect) {
        [employeeSelect, monthSelect].forEach(element => {
            element.addEventListener('change', function() {
                if (employeeSelect.value && monthSelect.value) {
                    salaryForm.dispatchEvent(new Event('submit'));
                }
            });
        });
    }
});

function updateSalaryConfig(employeeId, perDaySalary, workingDays, holidayDay) {
    const saveBtn = document.getElementById('saveConfig');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<span class="loading-spinner"></span> Saving...';
    saveBtn.disabled = true;
    
    fetch('/salary/update-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            employee_id: employeeId,
            per_day_salary: parseFloat(perDaySalary),
            working_days_per_week: parseInt(workingDays),
            holiday_day: holidayDay
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Salary configuration updated successfully!', 'success');
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('configModal'));
            modal.hide();
            
            setTimeout(() => {
                document.getElementById('salaryForm').dispatchEvent(new Event('submit'));
            }, 1000);
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error updating configuration. Please try again.', 'error');
    })
    .finally(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}

function showNotification(message, type) {
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach(alert => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    });
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(notification, container.firstChild);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}