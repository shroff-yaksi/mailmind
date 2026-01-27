// MailMind Frontend JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tabs
    const tabElements = document.querySelectorAll('a[data-bs-toggle="tab"]');
    tabElements.forEach(tabEl => {
        tabEl.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all tabs
            tabElements.forEach(tab => {
                tab.classList.remove('active');
                const tabContent = document.querySelector(tab.getAttribute('href'));
                tabContent.classList.remove('show', 'active');
            });
            
            // Add active class to clicked tab
            this.classList.add('active');
            const targetTab = document.querySelector(this.getAttribute('href'));
            targetTab.classList.add('show', 'active');
            
            // Load tab-specific content
            if (this.getAttribute('href') === '#emails') {
                loadEmails();
            } else if (this.getAttribute('href') === '#logs') {
                loadLogs();
            } else if (this.getAttribute('href') === '#settings') {
                loadSettings();
            }
        });
    });
    
    // Initialize buttons
    document.getElementById('fetch-btn').addEventListener('click', fetchEmails);
    document.getElementById('respond-btn').addEventListener('click', respondToEmails);
    document.getElementById('monitor-toggle').addEventListener('click', toggleMonitoring);
    document.getElementById('refresh-emails').addEventListener('click', loadEmails);
    document.getElementById('refresh-logs').addEventListener('click', loadLogs);
    document.getElementById('save-settings').addEventListener('click', saveSettings);
    
    // Initialize modal functionality for email details
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('view-email-btn')) {
            const emailId = e.target.getAttribute('data-email-id');
            showEmailDetails(emailId);
        }
    });
    
    document.getElementById('generateResponseBtn').addEventListener('click', function() {
        const emailId = this.getAttribute('data-email-id');
        generateResponse(emailId);
    });
    
    // Load initial data
    checkStatus();
    loadEmails();
    loadLogs();
    
    // Check status every 10 seconds
    setInterval(checkStatus, 10000);
});

// API Endpoints
const API = {
    EMAILS: '/api/emails',
    FETCH: '/api/fetch',
    RESPOND: '/api/respond',
    MONITORING: '/api/monitoring',
    STATUS: '/api/status',
    LOGS: '/api/logs',
    SETTINGS: '/api/settings'
};

// Helper function for API calls
async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        console.log(`Making API call to ${url}`, { method, data });
        const response = await fetch(url, options);
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const responseData = await response.json();
            
            if (!response.ok) {
                throw new Error(responseData.error || `API error: ${response.status}`);
            }
            
            console.log(`API response from ${url}:`, responseData);
            return responseData;
        } else {
            // Handle non-JSON response (like HTML error pages)
            const textResponse = await response.text();
            console.error(`Non-JSON response from ${url}:`, textResponse);
            throw new Error(`Server returned non-JSON response: ${response.status}`);
        }
    } catch (error) {
        console.error(`API call to ${url} failed:`, error);
        showNotification('Error', error.message, 'danger');
        return null;
    }
}

// Check monitoring status
async function checkStatus() {
    const status = await apiCall(API.STATUS);
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const monitorToggle = document.getElementById('monitor-toggle');
    
    if (status) {
        // Update processor status
        if (!status.processor_configured) {
            statusText.textContent = 'Not Configured';
            statusIndicator.classList.remove('online');
            statusIndicator.classList.add('offline');
            monitorToggle.disabled = true;
            monitorToggle.innerHTML = '<i class="bi bi-play-circle me-1"></i>Configure Settings First';
            
            // Show configuration warning if needed
            if (!status.email_configured) {
                showNotification('Warning', 'Email settings not configured. Please configure your email settings.', 'warning', false);
            } else if (!status.api_key_configured) {
                showNotification('Warning', 'OpenRouter API key not configured. Please configure your API key.', 'warning', false);
            }
            
            return;
        } else {
            monitorToggle.disabled = false;
        }
        
        // Update monitoring status
        if (status.monitoring) {
            statusIndicator.classList.remove('offline');
            statusIndicator.classList.add('online', 'status-change');
            statusText.textContent = 'Online - Monitoring';
            monitorToggle.innerHTML = '<i class="bi bi-stop-circle me-1"></i>Stop Monitoring';
        } else {
            statusIndicator.classList.remove('online');
            statusIndicator.classList.add('offline');
            statusText.textContent = 'Offline';
            monitorToggle.innerHTML = '<i class="bi bi-play-circle me-1"></i>Start Monitoring';
        }
        
        // Remove animation class after animation completes
        setTimeout(() => {
            statusIndicator.classList.remove('status-change');
        }, 500);
    }
}

// Load emails from the API
async function loadEmails() {
    const emails = await apiCall(API.EMAILS);
    const tableBody = document.getElementById('email-table-body');
    tableBody.innerHTML = '';
    
    if (emails && emails.length > 0) {
        document.getElementById('pending-count').textContent = emails.filter(email => !email.is_replied).length;
        document.getElementById('responded-count').textContent = emails.filter(email => email.is_replied).length;
        
        emails.forEach(email => {
            const row = document.createElement('tr');
            
            // Format date
            const date = new Date(email.timestamp);
            const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
            
            // Status badge
            const statusBadge = email.is_replied ? 
                '<span class="badge bg-success">Replied</span>' : 
                '<span class="badge bg-warning text-dark">Pending</span>';
            
            row.innerHTML = `
                <td>${email.sender}</td>
                <td>${email.subject}</td>
                <td>${formattedDate}</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-email-btn" data-email-id="${email.msg_id}">
                        <i class="bi bi-eye"></i> View
                    </button>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    } else {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center">No emails found</td>
            </tr>
        `;
        document.getElementById('pending-count').textContent = '0';
        document.getElementById('responded-count').textContent = '0';
    }
}

// Show email details in modal
async function showEmailDetails(emailId) {
    const emails = await apiCall(API.EMAILS);
    const email = emails.find(e => e.msg_id === emailId);
    
    if (email) {
        document.getElementById('emailSubject').textContent = email.subject;
        document.getElementById('emailSender').textContent = email.sender;
        document.getElementById('emailDate').textContent = new Date(email.timestamp).toLocaleString();
        document.getElementById('emailBody').textContent = email.body;
        
        // Set email ID for response generation
        document.getElementById('generateResponseBtn').setAttribute('data-email-id', emailId);
        
        // Show or hide response based on status
        if (email.is_replied) {
            // We would need to fetch the response from the API
            document.getElementById('emailResponse').innerHTML = '<em>Loading response...</em>';
            // This is a placeholder - you would need to add an API endpoint to fetch responses
        } else {
            document.getElementById('emailResponse').innerHTML = '<em>No response generated yet.</em>';
        }
        
        // Show modal
        const emailModal = new bootstrap.Modal(document.getElementById('emailDetailModal'));
        emailModal.show();
    }
}

// Fetch new emails
async function fetchEmails() {
    const button = document.getElementById('fetch-btn');
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Fetching...';
    
    const result = await apiCall(API.FETCH, 'POST');
    
    button.disabled = false;
    button.innerHTML = '<i class="bi bi-download me-1"></i>Fetch Emails';
    
    if (result) {
        showNotification('Success', `Fetched ${result.fetched} new emails`, 'success');
        loadEmails();
    }
}

// Respond to all unreplied emails
async function respondToEmails() {
    const button = document.getElementById('respond-btn');
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    
    const result = await apiCall(API.RESPOND, 'POST');
    
    button.disabled = false;
    button.innerHTML = '<i class="bi bi-reply me-1"></i>Respond to All';
    
    if (result) {
        showNotification('Success', `Responded to ${result.responded} emails`, 'success');
        loadEmails();
    }
}

// Toggle email monitoring
async function toggleMonitoring() {
    const status = await apiCall(API.STATUS);
    const action = status && status.monitoring ? 'stop' : 'start';
    
    const monitorToggle = document.getElementById('monitor-toggle');
    monitorToggle.disabled = true;
    monitorToggle.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    
    const result = await apiCall(API.MONITORING, 'POST', { action });
    
    monitorToggle.disabled = false;
    
    if (result) {
        await checkStatus(); // Refresh status immediately
        
        if (result.success) {
            showNotification(
                'Monitoring Status', 
                `Email monitoring ${action === 'start' ? 'started' : 'stopped'}`,
                'info'
            );
        } else {
            showNotification(
                'Monitoring Error', 
                `Failed to ${action} monitoring. Please check the logs.`,
                'danger'
            );
        }
    }
}

// Generate response for a specific email
async function generateResponse(emailId) {
    const button = document.getElementById('generateResponseBtn');
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
    
    // This is a placeholder - you would need to add an API endpoint to generate responses
    // For now, we'll simulate a response
    setTimeout(() => {
        document.getElementById('emailResponse').innerHTML = 
            '<p>Thank you for your email. I have received your message and will get back to you shortly with more information.</p>' +
            '<p>Best regards,<br>MailMind AI</p>';
        
        button.disabled = false;
        button.innerHTML = 'Generate Response';
    }, 2000);
}

// Load system logs
async function loadLogs() {
    const result = await apiCall(API.LOGS);
    
    if (result && result.logs) {
        document.getElementById('logs-content').textContent = result.logs.join('');
        
        // Scroll to bottom of logs
        const logsContainer = document.querySelector('.logs-container');
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }
}

// Load settings
async function loadSettings() {
    const config = await apiCall(API.SETTINGS);
    
    if (config) {
        if (config.email) {
            document.getElementById('email-address').value = config.email.email_address || '';
            document.getElementById('email-password').value = config.email.password === '********' ? '' : (config.email.password || '');
            document.getElementById('imap-server').value = config.email.imap_server || '';
            document.getElementById('imap-port').value = config.email.imap_port || '';
            document.getElementById('smtp-server').value = config.email.smtp_server || '';
            document.getElementById('smtp-port').value = config.email.smtp_port || '';
        }
        
        if (config.openrouter) {
            document.getElementById('openrouter-api-key').value = config.openrouter.api_key === '********' ? '' : (config.openrouter.api_key || '');
        }
        
        if (config.settings) {
            document.getElementById('email-signature').value = config.settings.signature || '';
            document.getElementById('check-interval').value = config.settings.check_interval || 300;
        }
    }
}

// Save settings
async function saveSettings() {
    const button = document.getElementById('save-settings');
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    
    const config = {
        email: {
            email_address: document.getElementById('email-address').value,
            imap_server: document.getElementById('imap-server').value,
            imap_port: parseInt(document.getElementById('imap-port').value),
            smtp_server: document.getElementById('smtp-server').value,
            smtp_port: parseInt(document.getElementById('smtp-port').value),
            use_ssl: true
        },
        openrouter: {
            model: "mistralai/mistral-7b-instruct:free"
        },
        settings: {
            signature: document.getElementById('email-signature').value,
            check_interval: parseInt(document.getElementById('check-interval').value)
        }
    };
    
    // Only include password if provided (not empty)
    const password = document.getElementById('email-password').value;
    if (password) {
        config.email.password = password;
    }
    
    // Only include API key if provided (not empty)
    const apiKey = document.getElementById('openrouter-api-key').value;
    if (apiKey) {
        config.openrouter.api_key = apiKey;
    }
    
    const result = await apiCall(API.SETTINGS, 'POST', config);
    
    button.disabled = false;
    button.innerHTML = 'Save Settings';
    
    if (result && result.success) {
        showNotification('Settings Saved', 'Your settings have been saved successfully', 'success');
        // Refresh status to reflect new settings
        checkStatus();
    }
}

// Show notification
function showNotification(title, message, type = 'info', autoHide = true) {
    // This is a placeholder for a notification system
    // You could use a library like toastr or implement your own
    console.log(`${title}: ${message} (${type})`);
    
    // Create a Bootstrap toast
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.setAttribute('id', toastId);
    if (autoHide) {
        toast.setAttribute('data-bs-delay', '5000');
        toast.setAttribute('data-bs-autohide', 'true');
    }
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong>: ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to container (create if doesn't exist)
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.appendChild(toast);
    
    // Show the toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove from DOM after hidden
    toast.addEventListener('hidden.bs.toast', function () {
        toast.remove();
    });
} 