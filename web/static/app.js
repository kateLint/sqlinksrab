// State management
let uploadedFile = null;
let jobId = null;

// DOM Elements
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('pdf-file');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const removeFileBtn = document.getElementById('remove-file');
const credentialsForm = document.getElementById('credentials-form');
const otpSection = document.getElementById('otp-section');
const otpForm = document.getElementById('otp-form');
const submitBtn = document.getElementById('submit-btn');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const logContent = document.getElementById('log-content');
const statCreated = document.getElementById('stat-created');
const statSkipped = document.getElementById('stat-skipped');
const statFailed = document.getElementById('stat-failed');
const resultsContent = document.getElementById('results-content');
const downloadReportBtn = document.getElementById('download-report');
const startOverBtn = document.getElementById('start-over');

// File upload handling
uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type === 'application/pdf') {
        handleFileSelect(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    clearFile();
});

function handleFileSelect(file) {
    uploadedFile = file;
    fileName.textContent = file.name;
    uploadArea.querySelector('.upload-content').style.display = 'none';
    fileInfo.style.display = 'flex';
    checkFormReady();
}

function clearFile() {
    uploadedFile = null;
    fileInput.value = '';
    uploadArea.querySelector('.upload-content').style.display = 'block';
    fileInfo.style.display = 'none';
    checkFormReady();
}

// Form validation
credentialsForm.addEventListener('input', checkFormReady);

function checkFormReady() {
    const employeeId = document.getElementById('employee-id').value;
    const password = document.getElementById('password').value;

    submitBtn.disabled = !(uploadedFile && employeeId && password);
}

// Submit handling
submitBtn.addEventListener('click', async () => {
    submitBtn.disabled = true;

    const employeeId = document.getElementById('employee-id').value;
    const password = document.getElementById('password').value;

    // Hide form sections
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('credentials-section').style.display = 'none';
    document.getElementById('submit-section').style.display = 'none';

    // Show progress
    progressSection.style.display = 'block';

    try {
        // Upload file
        addLog('מעלה קובץ PDF...', 'info');
        const formData = new FormData();
        formData.append('file', uploadedFile);

        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            throw new Error('שגיאה בהעלאת הקובץ');
        }

        const { filename } = await uploadResponse.json();
        addLog('✓ קובץ הועלה בהצלחה', 'success');

        // Start automation
        addLog('מתחיל תהליך אוטומציה...', 'info');

        const userEmail = document.getElementById('user-email').value;

        const submitResponse = await fetch('/api/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename,
                employee_id: employeeId,
                password,
                user_email: userEmail
            })
        });

        if (!submitResponse.ok) {
            throw new Error('שגיאה בהתחלת האוטומציה');
        }

        const { job_id } = await submitResponse.json();
        jobId = job_id;

        addLog(`✓ משימה נוצרה: ${job_id}`, 'success');

        // Start polling for status
        pollJobStatus();

    } catch (error) {
        addLog(`✗ שגיאה: ${error.message}`, 'error');
        setTimeout(() => location.reload(), 3000);
    }
});

// OTP form handling
otpForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const otpCode = document.getElementById('otp-code').value;

    try {
        const response = await fetch(`/api/submit-otp/${jobId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                otp_code: otpCode
            })
        });

        if (!response.ok) {
            throw new Error('שגיאה בשליחת קוד OTP');
        }

        addLog('✓ קוד OTP נשלח', 'success');
        otpSection.style.display = 'none';

    } catch (error) {
        addLog(`✗ שגיאה: ${error.message}`, 'error');
    }
});

// Poll job status
async function pollJobStatus() {
    try {
        const response = await fetch(`/api/status/${jobId}`);
        const data = await response.json();

        // Update progress
        updateProgress(data);

        // Check if waiting for OTP
        if (data.status === 'waiting_for_otp') {
            otpSection.style.display = 'block';
            document.getElementById('otp-code').focus();
        }

        if (data.status === 'completed') {
            showResults(data);
        } else if (data.status === 'failed') {
            addLog(`✗ התהליך נכשל: ${data.error}`, 'error');
            setTimeout(() => location.reload(), 5000);
        } else {
            // Continue polling
            setTimeout(pollJobStatus, 1000);
        }
    } catch (error) {
        addLog(`✗ שגיאה בקבלת סטטוס: ${error.message}`, 'error');
        setTimeout(pollJobStatus, 2000);
    }
}

function updateProgress(data) {
    // Update progress bar
    const progress = data.progress || 0;
    progressBar.style.width = `${progress}%`;

    // Update status text
    if (data.current_status) {
        progressText.textContent = data.current_status;
    }

    // Update stats
    if (data.stats) {
        statCreated.textContent = data.stats.created || 0;
        statSkipped.textContent = data.stats.skipped || 0;
        statFailed.textContent = data.stats.failed || 0;
    }

    // Add new log entries
    if (data.logs && data.logs.length > 0) {
        data.logs.forEach(log => {
            if (!logContent.querySelector(`[data-log-id="${log.id}"]`)) {
                addLog(log.message, log.type, log.id);
            }
        });
    }
}

function addLog(message, type = 'info', id = null) {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    if (id) {
        entry.setAttribute('data-log-id', id);
    }
    entry.textContent = `[${new Date().toLocaleTimeString('he-IL')}] ${message}`;
    logContent.appendChild(entry);
    logContent.scrollTop = logContent.scrollHeight;
}

function showResults(data) {
    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';

    const stats = data.stats || {};
    const total = stats.total || 0;
    const created = stats.created || 0;
    const skipped = stats.skipped || 0;
    const failed = stats.failed || 0;
    const successRate = total > 0 ? ((created / total) * 100).toFixed(1) : 0;

    resultsContent.innerHTML = `
        <div class="result-item">
            <span class="result-label">סה"כ רשומות</span>
            <span class="result-value">${total}</span>
        </div>
        <div class="result-item">
            <span class="result-label">נוצרו בהצלחה</span>
            <span class="result-value">${created}</span>
        </div>
        <div class="result-item">
            <span class="result-label">דולגו</span>
            <span class="result-value">${skipped}</span>
        </div>
        <div class="result-item">
            <span class="result-label">נכשלו</span>
            <span class="result-value">${failed}</span>
        </div>
        <div class="result-item">
            <span class="result-label">אחוז הצלחה</span>
            <span class="result-value">${successRate}%</span>
        </div>
    `;
}

// Download report
downloadReportBtn.addEventListener('click', async () => {
    if (jobId) {
        window.location.href = `/api/report/${jobId}`;
    }
});

// Start over
startOverBtn.addEventListener('click', () => {
    location.reload();
});
