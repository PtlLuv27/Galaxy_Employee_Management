// Attendance management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Date picker functionality
    const datePicker = document.getElementById('attendanceDate');
    if (datePicker) {
        const today = new Date().toISOString().split('T')[0];
        datePicker.max = today;
        
        datePicker.addEventListener('change', function() {
            window.location.href = `${window.location.pathname}?date=${this.value}`;
        });
    }
    
    // Save attendance functionality
    const saveButtons = document.querySelectorAll('.save-attendance');
    saveButtons.forEach(button => {
        button.addEventListener('click', function() {
            const employeeId = this.getAttribute('data-employee-id');
            const date = document.getElementById('attendanceDate').value;
            const status = document.querySelector(`.status-select[data-employee-id="${employeeId}"]`).value;
            const notes = document.querySelector(`.notes-input[data-employee-id="${employeeId}"]`).value;
            
            saveAttendance(employeeId, date, status, notes, this);
        });
    });
    
    // Quick save on status change
    const statusSelects = document.querySelectorAll('.status-select');
    statusSelects.forEach(select => {
        select.addEventListener('change', function() {
            const employeeId = this.getAttribute('data-employee-id');
            const date = document.getElementById('attendanceDate').value;
            const status = this.value;
            const notes = document.querySelector(`.notes-input[data-employee-id="${employeeId}"]`).value;
            const button = document.querySelector(`.save-attendance[data-employee-id="${employeeId}"]`);
            
            saveAttendance(employeeId, date, status, notes, button);
        });
    });
});

function saveAttendance(employeeId, date, status, notes, buttonElement) {
    const originalText = buttonElement.innerHTML;
    buttonElement.innerHTML = '<span class="loading-spinner"></span> Saving...';
    buttonElement.disabled = true;
    
    fetch('/attendance/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            employee_id: employeeId,
            date: date,
            status: status,
            notes: notes
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Attendance saved successfully!', 'success');
            updateButtonAppearance(buttonElement, status);
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error saving attendance. Please try again.', 'error');
    })
    .finally(() => {
        buttonElement.innerHTML = originalText;
        buttonElement.disabled = false;
    });
}

function updateButtonAppearance(button, status) {
    const statusColors = {
        'present': 'btn-success',
        'absent': 'btn-danger',
        'half_day': 'btn-warning',
        'holiday': 'btn-info'
    };
    
    button.classList.remove('btn-success', 'btn-danger', 'btn-warning', 'btn-info');
    
    if (statusColors[status]) {
        button.classList.add(statusColors[status]);
    }
}

function showNotification(message, type) {
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
    }, 3000);
}