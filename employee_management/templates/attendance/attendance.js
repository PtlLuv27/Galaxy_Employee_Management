class AttendanceManager {
    constructor() {
        this.employeeChanges = new Set();
        this.notesChanges = new Set();
        this.currentEmployeeId = null;
        this.notesModal = new bootstrap.Modal(document.getElementById('notesModal'));
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateTotalAdvance();
        this.storeOriginalAdvanceValues();
        this.disableLeftEmployeeControls();
        this.updateGlobalApplyButton();
        this.formatDateDisplay();
    }

    formatDateDisplay() {
        const dateElement = document.getElementById('currentDate');
        if (dateElement) {
            const date = new Date(dateElement.textContent);
            const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            dateElement.textContent = date.toLocaleDateString('en-US', options);
        }
    }

    setupEventListeners() {
        // Date picker
        const datePicker = document.getElementById('datePicker');
        if (datePicker) {
            datePicker.addEventListener('change', () => {
                this.showLoading();
                window.location.href = `{{ url_for('attendance') }}?date=${datePicker.value}`;
            });
        }

        // Status options
        document.querySelectorAll('.status-option:not(.disabled)').forEach(option => {
            option.addEventListener('click', (e) => {
                const employeeId = e.currentTarget.dataset.employee;
                const status = e.currentTarget.dataset.status;
                this.handleStatusChange(employeeId, status);
            });
        });

        // Advance inputs
        document.querySelectorAll('.advance-input:not(:disabled)').forEach(input => {
            input.addEventListener('input', this.debounce((e) => {
                const employeeId = e.target.dataset.employee;
                this.handleAdvanceChange(employeeId);
                this.updateTotalAdvance();
            }, 300));

            input.addEventListener('blur', (e) => {
                const employeeId = e.target.dataset.employee;
                this.handleAdvanceChange(employeeId);
            });
        });

        // Individual apply buttons
        document.querySelectorAll('.btn-apply:not(:disabled)').forEach(button => {
            button.addEventListener('click', (e) => {
                this.applyAdvanceForEmployee(e.currentTarget.dataset.employee);
            });
        });

        // Global apply buttons
        document.getElementById('applyChanges').addEventListener('click', () => {
            this.applyAllChanges();
        });

        document.getElementById('applyAllChanges').addEventListener('click', () => {
            this.applyAllChanges();
        });

        // Modal events
        document.getElementById('notesModal').addEventListener('hidden.bs.modal', () => {
            if (this.currentEmployeeId) {
                this.saveNotesSilently();
            }
        });

        // Update stats when changes occur
        this.updateStats();
    }

    disableLeftEmployeeControls() {
        document.querySelectorAll('.employee-card[data-is-left="true"]').forEach(card => {
            const canMark = card.dataset.canMark === 'true';
            if (!canMark) {
                const statusOptions = card.querySelectorAll('.status-option');
                const advanceInput = card.querySelector('.advance-input');
                const applyBtn = card.querySelector('.btn-apply');
                const notesBtn = card.querySelector('.btn-notes');
                
                statusOptions.forEach(option => option.classList.add('disabled'));
                if (advanceInput) advanceInput.disabled = true;
                if (applyBtn) applyBtn.disabled = true;
                if (notesBtn) notesBtn.disabled = true;
            }
        });
    }

    storeOriginalAdvanceValues() {
        document.querySelectorAll('.advance-input').forEach(input => {
            const originalValue = input.value || '0';
            input.setAttribute('data-original-value', originalValue);
        });
    }

    handleStatusChange(employeeId, status) {
        const card = document.getElementById(`card-${employeeId}`);
        const canMark = card ? card.dataset.canMark === 'true' : true;
        
        if (!canMark) {
            this.showNotification('Cannot mark attendance for left employee', 'error');
            return;
        }
        
        const currentActive = document.querySelector(`.status-option[data-employee="${employeeId}"].active`);
        
        // Toggle behavior: click active status to remove
        if (currentActive && currentActive.dataset.status === status) {
            document.querySelectorAll(`.status-option[data-employee="${employeeId}"]`).forEach(opt => {
                opt.classList.remove('active');
            });
            this.saveStatusChange(employeeId, 'not_marked');
        } else {
            document.querySelectorAll(`.status-option[data-employee="${employeeId}"]`).forEach(opt => {
                opt.classList.remove('active');
            });
            document.querySelector(`.status-option[data-employee="${employeeId}"][data-status="${status}"]`).classList.add('active');
            this.saveStatusChange(employeeId, status);
        }
    }

    async saveStatusChange(employeeId, status) {
        const date = document.getElementById('datePicker').value;
        const notes = this.getCurrentNotesForEmployee(employeeId);
        const advance = this.getCurrentAdvance(employeeId);
        const card = document.getElementById(`card-${employeeId}`);
        const canMark = card ? card.dataset.canMark === 'true' : true;

        if (!canMark) {
            this.showNotification('Cannot mark attendance for left employee', 'error');
            return;
        }

        this.showLoading();
        
        try {
            const response = await fetch('{{ url_for("update_attendance") }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    employee_id: employeeId,
                    date: date,
                    status: status,
                    notes: notes,
                    advance: advance
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateCardStatus(employeeId, status);
                this.updateStats();
                this.showNotification('Status updated successfully', 'success');
            } else {
                this.showNotification('Error: ' + data.message, 'error');
                setTimeout(() => location.reload(), 1000);
            }
        } catch (error) {
            this.showNotification('Network error', 'error');
            setTimeout(() => location.reload(), 1000);
        } finally {
            this.hideLoading();
        }
    }

    updateCardStatus(employeeId, status) {
        const card = document.getElementById(`card-${employeeId}`);
        if (!card) return;

        // Remove all status classes
        card.classList.remove('status-present', 'status-half_day', 'status-absent', 'status-not_marked');
        
        // Add current status class
        if (status && status !== 'not_marked') {
            card.classList.add(`status-${status}`);
        }

        // Update status text
        const statusElement = card.querySelector('.employee-status');
        if (statusElement) {
            const statusText = status === 'not_marked' ? 'Not Marked' : status.replace('_', ' ').title();
            const statusIndicator = `<span class="status-indicator status-${status}"></span>`;
            const statusTextSpan = `<span class="status-text">${statusText}</span>`;
            
            statusElement.innerHTML = `${statusIndicator} ${statusTextSpan}`;
            
            // Restore notes badge if it exists
            const notes = this.getCurrentNotesForEmployee(employeeId);
            if (notes && notes.trim() !== '') {
                statusElement.innerHTML += '<span class="badge bg-warning notes-badge"><i class="fas fa-sticky-note me-1"></i>Notes</span>';
            }

            // Restore left badge if it exists
            if (card.dataset.isLeft === 'true') {
                statusElement.innerHTML += '<span class="badge bg-secondary left-badge"><i class="fas fa-sign-out-alt me-1"></i>Left</span>';
            }
        }
    }

    updateStats() {
        let presentCount = 0;
        let halfdayCount = 0;
        let absentCount = 0;
        let markedCount = 0;

        document.querySelectorAll('.employee-card').forEach(card => {
            const status = card.classList.contains('status-present') ? 'present' :
                          card.classList.contains('status-half_day') ? 'half_day' :
                          card.classList.contains('status-absent') ? 'absent' : 'not_marked';
            
            if (status === 'present') presentCount++;
            if (status === 'half_day') halfdayCount++;
            if (status === 'absent') absentCount++;
            if (status !== 'not_marked') markedCount++;
        });

        document.getElementById('presentCount').textContent = presentCount;
        document.getElementById('halfdayCount').textContent = halfdayCount;
        document.getElementById('absentCount').textContent = absentCount;
        document.getElementById('markedCount').textContent = markedCount;
    }

    handleAdvanceChange(employeeId) {
        const card = document.getElementById(`card-${employeeId}`);
        const canMark = card ? card.dataset.canMark === 'true' : true;

        if (!canMark) {
            this.showNotification('Cannot modify advance for left employee', 'error');
            return;
        }

        this.employeeChanges.add(employeeId);
        
        // Enable individual apply button
        const singleApplyBtn = document.querySelector(`.btn-apply[data-employee="${employeeId}"]`);
        if (singleApplyBtn) {
            singleApplyBtn.disabled = false;
        }

        this.updateCardAdvanceAppearance(employeeId);
        this.updateGlobalApplyButton();
    }

    updateCardAdvanceAppearance(employeeId) {
        const card = document.getElementById(`card-${employeeId}`);
        if (!card) return;

        const hasAdvanceChanges = this.employeeChanges.has(employeeId);

        // Reset advance classes
        card.classList.remove('advance-changed');

        // Add appropriate classes
        if (hasAdvanceChanges) {
            card.classList.add('advance-changed');
        }
    }

    updateGlobalApplyButton() {
        const applyBtn = document.getElementById('applyChanges');
        const floatingBtn = document.getElementById('applyAllChanges');
        const changeCount = document.querySelector('.change-count');
        const floatingBadge = document.querySelector('.floating-badge');
        const hasChanges = this.employeeChanges.size > 0;
        
        applyBtn.disabled = !hasChanges;
        floatingBtn.disabled = !hasChanges;
        
        if (hasChanges) {
            applyBtn.classList.remove('btn-light');
            applyBtn.classList.add('btn-warning');
            changeCount.textContent = this.employeeChanges.size;
            floatingBadge.textContent = this.employeeChanges.size;
        } else {
            applyBtn.classList.remove('btn-warning');
            applyBtn.classList.add('btn-light');
            changeCount.textContent = '0';
            floatingBadge.textContent = '0';
        }
    }

    getCurrentStatus(employeeId) {
        const activeOption = document.querySelector(`.status-option[data-employee="${employeeId}"].active`);
        return activeOption ? activeOption.dataset.status : 'not_marked';
    }

    getCurrentAdvance(employeeId) {
        const advanceInput = document.getElementById(`advance_${employeeId}`);
        return advanceInput ? parseFloat(advanceInput.value) || 0 : 0;
    }

    getCurrentNotesForEmployee(employeeId) {
        const card = document.getElementById(`card-${employeeId}`);
        return card ? card.getAttribute('data-original-notes') || '' : '';
    }

    updateTotalAdvance() {
        let totalAdvance = 0;
        document.querySelectorAll('.advance-input').forEach(input => {
            totalAdvance += parseFloat(input.value) || 0;
        });
        document.getElementById('totalAdvance').textContent = totalAdvance;
    }

    async showNotesModal(employeeId, employeeName) {
        const card = document.getElementById(`card-${employeeId}`);
        const canMark = card ? card.dataset.canMark === 'true' : true;

        if (!canMark) {
            this.showNotification('Cannot modify notes for left employee', 'error');
            return;
        }

        this.currentEmployeeId = employeeId;
        document.getElementById('notesModalTitle').textContent = `Notes for ${employeeName}`;
        
        this.showLoading();
        const date = document.getElementById('datePicker').value;
        
        try {
            const response = await fetch('{{ url_for("get_attendance_notes") }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    employee_id: employeeId,
                    date: date
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('notesInput').value = data.notes || '';
                document.getElementById('notesInput').setAttribute('data-original-value', data.notes || '');
            } else {
                this.showNotification('Error loading notes: ' + data.message, 'error');
                document.getElementById('notesInput').value = '';
            }
        } catch (error) {
            this.showNotification('Network error loading notes', 'error');
            document.getElementById('notesInput').value = '';
        } finally {
            this.hideLoading();
            this.notesModal.show();
        }
    }

    saveNotes() {
        if (this.currentEmployeeId) {
            this.saveNotesSilently();
            this.notesModal.hide();
            this.showNotification('Notes saved successfully', 'success');
        }
    }

    saveNotesSilently() {
        if (this.currentEmployeeId) {
            const notes = document.getElementById('notesInput').value;
            const originalNotes = document.getElementById('notesInput').getAttribute('data-original-value') || '';
            
            if (notes !== originalNotes) {
                const card = document.getElementById(`card-${this.currentEmployeeId}`);
                if (card) {
                    card.setAttribute('data-original-notes', notes);
                }
                
                this.updateNotesIndicator(this.currentEmployeeId, notes);
                this.saveNotesToDatabase(this.currentEmployeeId, notes);
                this.notesChanges.add(this.currentEmployeeId);
            }
        }
    }

    async saveNotesToDatabase(employeeId, notes) {
        const date = document.getElementById('datePicker').value;
        const status = this.getCurrentStatus(employeeId);
        const advance = this.getCurrentAdvance(employeeId);

        this.showLoading();
        try {
            const response = await fetch('{{ url_for("update_attendance") }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    employee_id: employeeId,
                    date: date,
                    status: status,
                    notes: notes,
                    advance: advance
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('notesInput').setAttribute('data-original-value', notes);
                this.notesChanges.delete(employeeId);
            } else {
                console.error('Error saving notes:', data.message);
            }
        } catch (error) {
            console.error('Network error saving notes:', error);
        } finally {
            this.hideLoading();
        }
    }

    updateNotesIndicator(employeeId, notes) {
        const card = document.getElementById(`card-${employeeId}`);
        if (!card) return;

        const statusElement = card.querySelector('.employee-status');
        if (statusElement) {
            const existingBadge = statusElement.querySelector('.notes-badge');
            if (existingBadge) {
                existingBadge.remove();
            }
            
            if (notes && notes.trim() !== '') {
                const notesBadge = document.createElement('span');
                notesBadge.className = 'badge bg-warning notes-badge';
                notesBadge.title = 'Has notes';
                notesBadge.innerHTML = '<i class="fas fa-sticky-note me-1"></i>Notes';
                statusElement.appendChild(notesBadge);
            }
        }
    }

    async applyAdvanceForEmployee(employeeId) {
        const card = document.getElementById(`card-${employeeId}`);
        const canMark = card ? card.dataset.canMark === 'true' : true;

        if (!canMark) {
            this.showNotification('Cannot apply advance for left employee', 'error');
            return;
        }

        const advance = this.getCurrentAdvance(employeeId);
        const status = this.getCurrentStatus(employeeId);
        const notes = this.getCurrentNotesForEmployee(employeeId);
        const date = document.getElementById('datePicker').value;

        this.showLoading();
        await this.updateAttendance(employeeId, date, status, notes, advance, true);
    }

    async applyAllChanges() {
        if (this.employeeChanges.size === 0) {
            this.showNotification('No changes to apply', 'warning');
            return;
        }

        this.showLoading();
        const date = document.getElementById('datePicker').value;
        const changes = Array.from(this.employeeChanges);
        let successCount = 0;

        for (const employeeId of changes) {
            const card = document.getElementById(`card-${employeeId}`);
            const canMark = card ? card.dataset.canMark === 'true' : true;

            if (!canMark) {
                continue;
            }

            const status = this.getCurrentStatus(employeeId);
            const advance = this.getCurrentAdvance(employeeId);
            const notes = this.getCurrentNotesForEmployee(employeeId);

            const success = await this.updateAttendance(employeeId, date, status, notes, advance, false);
            if (success) successCount++;
            
            // Small delay to prevent overwhelming the server
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        if (successCount === changes.length) {
            this.showNotification(`Successfully applied ${successCount} changes`, 'success');
        } else {
            this.showNotification(`Applied ${successCount} of ${changes.length} changes`, 'warning');
        }
        
        setTimeout(() => location.reload(), 1000);
    }

    async updateAttendance(employeeId, date, status, notes, advance, isSingle) {
        try {
            const response = await fetch('{{ url_for("update_attendance") }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    employee_id: employeeId,
                    date: date,
                    status: status,
                    notes: notes,
                    advance: advance
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (isSingle) {
                    const advanceInput = document.getElementById(`advance_${employeeId}`);
                    if (advanceInput) {
                        advanceInput.setAttribute('data-original-value', advance || '0');
                    }
                    
                    this.employeeChanges.delete(employeeId);
                    this.updateCardAdvanceAppearance(employeeId);
                    this.updateGlobalApplyButton();
                    this.showNotification('Advance applied successfully', 'success');
                }
                return true;
            } else {
                this.showNotification('Error: ' + data.message, 'error');
                return false;
            }
        } catch (error) {
            this.showNotification('Network error', 'error');
            return false;
        } finally {
            this.hideLoading();
        }
    }

    showNotification(message, type) {
        const icon = type === 'error' ? 'exclamation-triangle' : 
                    type === 'warning' ? 'exclamation-circle' : 
                    type === 'info' ? 'info-circle' : 'check-circle';
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show flash-message`;
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${icon} me-2"></i>
                <span class="flex-grow-1">${message}</span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        const container = document.getElementById('flashMessagesContainer') || document.body;
        container.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 4000);
    }

    showLoading() {
        document.body.classList.add('loading');
    }

    hideLoading() {
        document.body.classList.remove('loading');
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the attendance manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.attendanceManager = new AttendanceManager();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (!document.hidden && window.attendanceManager) {
        window.attendanceManager.updateTotalAdvance();
        window.attendanceManager.updateStats();
    }
});