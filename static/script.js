// Global JavaScript for SkillShare Scheduler

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if Bootstrap tooltip is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        if (alert.classList.contains('alert-success')) {
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });

    // Form validation improvements
    const forms = document.querySelectorAll('form[novalidate]');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Time input validation
    const timeInputs = document.querySelectorAll('input[type="time"]');
    timeInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            validateTimeRange(this);
        });
    });

    // Date input validation
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            validateDate(this);
        });
    });

    // Smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Lazy load Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
});

// Utility Functions

function validateTimeRange(timeInput) {
    const timeRow = timeInput.closest('.time-range-row');
    if (!timeRow) return;

    const startInput = timeRow.querySelector('input[name="start_time"]');
    const endInput = timeRow.querySelector('input[name="end_time"]');

    if (startInput && endInput && startInput.value && endInput.value) {
        const startTime = new Date('1970-01-01T' + startInput.value + ':00');
        const endTime = new Date('1970-01-01T' + endInput.value + ':00');

        if (startTime >= endTime) {
            endInput.setCustomValidity('End time must be after start time');
            endInput.classList.add('is-invalid');
        } else {
            endInput.setCustomValidity('');
            endInput.classList.remove('is-invalid');
            endInput.classList.add('is-valid');
            startInput.classList.remove('is-invalid');
            startInput.classList.add('is-valid');
        }
    }
}

function validateDate(dateInput) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const selectedDate = new Date(dateInput.value);
    
    if (selectedDate < today) {
        dateInput.setCustomValidity('Cannot select dates in the past');
        dateInput.classList.add('is-invalid');
        return false;
    } else {
        dateInput.setCustomValidity('');
        dateInput.classList.remove('is-invalid');
        dateInput.classList.add('is-valid');
        return true;
    }
}

function showLoading(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    button.disabled = true;
    
    // Store original text for restoration
    button.dataset.originalText = originalText;
}

function hideLoading(button) {
    if (button.dataset.originalText) {
        button.innerHTML = button.dataset.originalText;
        button.disabled = false;
        delete button.dataset.originalText;
    }
}

// Debounce function for search inputs
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction() {
        const context = this;
        const args = arguments;
        const later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

// Format date for display
function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

// Format time for display
function formatTime(timeString) {
    const [hours, minutes] = timeString.split(':');
    const time = new Date();
    time.setHours(parseInt(hours), parseInt(minutes));
    
    return time.toLocaleTimeString(undefined, {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

// Copy to clipboard functionality
function copyToClipboard(text, button) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('Copied to clipboard!', 'success');
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showToast('Copied to clipboard!', 'success');
        } catch (err) {
            showToast('Failed to copy', 'error');
        }
        document.body.removeChild(textArea);
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            const bsAlert = new bootstrap.Alert(toast);
            bsAlert.close();
        }
    }, 3000);
}

// Enhanced form submission with loading states
function enhanceFormSubmission() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton && form.checkValidity()) {
                showLoading(submitButton);
            }
        });
    });
}

// Initialize enhanced features
document.addEventListener('DOMContentLoaded', function() {
    enhanceFormSubmission();
});
