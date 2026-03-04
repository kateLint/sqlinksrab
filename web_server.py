"""
Web server for HRM timesheet automation.
Provides a web interface for uploading PDF files and automating timesheet entry.
"""

import os
import sys
import uuid
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Import our automation modules
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from pdf_extractor import PDFExtractor
from portal_client import PortalClient
from config import Config
from email_sender import EmailSender

app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')

# Configuration
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('output')
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Job storage (in-memory for simplicity)
jobs: Dict[str, dict] = {}

class JobStatus:
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


def create_job(job_id: str, filename: str, employee_id: str, password: str, user_email: str = None):
    """Create a new automation job."""
    jobs[job_id] = {
        'id': job_id,
        'status': JobStatus.QUEUED,
        'filename': filename,
        'employee_id': employee_id,
        'password': password,
        'target_month': None,  # Will be auto-detected from PDF
        'progress': 0,
        'current_status': 'ממתין להתחלה...',
        'logs': [],
        'stats': {
            'total': 0,
            'created': 0,
            'skipped': 0,
            'failed': 0
        },
        'created_at': datetime.now().isoformat(),
        'audit_report_path': None,
        'otp_code': None,  # Will be filled when user submits OTP
        'portal_client': None,  # Store client reference for OTP filling
        'user_email': user_email  # Store user email
    }
    
    # Start the automation in a background thread
    thread = threading.Thread(target=run_automation, args=(job_id,))
    thread.daemon = True
    thread.start()
    
    return jobs[job_id]


def add_log(job_id: str, message: str, log_type: str = 'info'):
    """Add a log entry to a job."""
    if job_id in jobs:
        log_entry = {
            'id': str(uuid.uuid4()),
            'message': message,
            'type': log_type,
            'timestamp': datetime.now().isoformat()
        }
        jobs[job_id]['logs'].append(log_entry)


def update_job_status(job_id: str, status: str, current_status: str = None, progress: int = None):
    """Update job status."""
    if job_id in jobs:
        jobs[job_id]['status'] = status
        if current_status:
            jobs[job_id]['current_status'] = current_status
        if progress is not None:
            jobs[job_id]['progress'] = progress


def update_job_stats(job_id: str, stats: dict):
    """Update job statistics."""
    if job_id in jobs:
        jobs[job_id]['stats'].update(stats)


def run_automation(job_id: str):
    """Run the automation process."""
    try:
        job = jobs[job_id]
        filename = job['filename']
        employee_id = job['employee_id']
        password = job['password']
        
        update_job_status(job_id, JobStatus.RUNNING, 'מתחיל תהליך...', 0)
        add_log(job_id, 'מתחיל אוטומציה', 'info')
        
        # Extract PDF
        add_log(job_id, f'קורא קובץ PDF: {filename}', 'info')
        update_job_status(job_id, JobStatus.RUNNING, 'מחלץ נתונים מ-PDF...', 10)
        
        pdf_path = UPLOAD_FOLDER / filename
        # Use a default month for initialization, will be auto-detected
        extractor = PDFExtractor(str(pdf_path), target_month="2026-01")
        records_list = extractor.extract()
        
        # Auto-detect month from PDF
        target_month = extractor.get_detected_month(records_list)
        job['target_month'] = target_month
        add_log(job_id, f'זוהה חודש יעד: {target_month}', 'success')
        
        # Convert list of TimesheetRecord objects to dict with dates as keys
        # STRICT FILTER: Discard any dates jumping to previous/next month (like December 28th captured via OCR spillover/bleed)
        records = {}
        target_year, target_month_val = target_month.split('-')
        for record in records_list:
            if record.work_date.startswith(target_month):
                try:
                    # Basic sanity check: keep only valid days up to 31
                    day = int(record.work_date.split('-')[2])
                    if 1 <= day <= 31:
                        records[record.work_date] = record
                except ValueError:
                    continue
        
        add_log(job_id, f'נמצאו {len(records)} רשומות', 'success')
        update_job_stats(job_id, {'total': len(records)})
        update_job_status(job_id, JobStatus.RUNNING, 'מתחבר לפורטל...', 20)
        
        # Create config
        config = Config()
        # Override credentials from web form (not from .env)
        config.employee_id = employee_id
        config.password = password
        # Update config values via internal dictionary
        config._config["automation"]["target_month"] = target_month
        config._config["automation"]["dry_run"] = False
        config._config["automation"]["headless"] = False  # Need visible browser for OTP
        
        # Initialize portal client
        add_log(job_id, 'מתחבר לפורטל HRM', 'info')
        add_log(job_id, '⚠️ דפדפן ייפתח - אנא המתן', 'info')
        client = PortalClient(config)
        job['portal_client'] = client  # Store for OTP filling
        
        # Start browser
        add_log(job_id, '🌐 פותח דפדפן Chrome...', 'info')
        client.start()
        
        try:
            # Login with OTP
            update_job_status(job_id, JobStatus.RUNNING, 'מתחבר...', 25)
            add_log(job_id, '🔐 מזין פרטי התחברות...', 'info')
            add_log(job_id, '📱 אם תתבקש להזין OTP - הזן אותו בדפדפן שנפתח', 'info')
            
            if not client.login():
                add_log(job_id, '✗ התחברות נכשלה - בדוק את הפרטים או את ה-OTP', 'error')
                raise Exception('התחברות נכשלה')
            
            add_log(job_id, '✓ התחברות הצליחה!', 'success')
            
            # Navigate to timesheet
            if not client.navigate_to_timesheet():
                raise Exception('ניווט לדף נוכחות נכשל')
            
            add_log(job_id, 'ניווט לדף נוכחות הצליח', 'success')
            
            # Process each day
            created = 0
            skipped = 0
            failed = 0
            
            for i, (date, record) in enumerate(records.items()):
                day_num = i + 1
                total_days = len(records)
                progress = 40 + int((day_num / total_days) * 50)
                
                update_job_status(job_id, JobStatus.RUNNING, 
                                f'מעבד יום {day_num}/{total_days}: {date}', progress)
                
                add_log(job_id, f'מעבד {date}...', 'info')
                
                action, status = client.enter_timesheet_data(record, dry_run=False)
                
                if action == 'created':
                    created += 1
                    add_log(job_id, f'✓ {date}: נוצר בהצלחה', 'success')
                elif action == 'skipped':
                    skipped += 1
                    add_log(job_id, f'⊘ {date}: דולג - {status}', 'info')
                else:
                    failed += 1
                    add_log(job_id, f'✗ {date}: נכשל - {status}', 'error')
                
                update_job_stats(job_id, {
                    'created': created,
                    'skipped': skipped,
                    'failed': failed
                })
            
            # Generate audit report
            update_job_status(job_id, JobStatus.RUNNING, 'יוצר דוח ביקורת...', 95)
            add_log(job_id, 'יוצר דוח ביקורת...', 'info')
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audit_path = OUTPUT_FOLDER / f'audit_report_{timestamp}.csv'
            
            # Save audit report (simplified version)
            with open(audit_path, 'w', encoding='utf-8-sig') as f:
                f.write('timestamp,date,action,status\\n')
                # This would normally be populated from the actual audit data
            
            jobs[job_id]['audit_report_path'] = str(audit_path)
            
            # Complete
            update_job_status(job_id, JobStatus.COMPLETED, 'הושלם בהצלחה!', 100)
            add_log(job_id, f'✓ תהליך הושלם! נוצרו: {created}, דולגו: {skipped}, נכשלו: {failed}', 'success')
            
            # Send email notification if user provided email
            if job.get('user_email'):
                add_log(job_id, f"📧 שולח דוח ל-{job.get('user_email')}...", 'info')
                try:
                    email_sender = EmailSender()
                    completion_time = datetime.now()
                    email_sent = email_sender.send_completion_report(
                        employee_id=employee_id,
                        target_month=target_month,
                        stats={
                            'total': len(records),
                            'created': created,
                            'skipped': skipped,
                            'failed': failed
                        },
                        timestamp=completion_time,
                        user_email=job.get('user_email'),
                        pdf_path=str(pdf_path)
                    )
                    
                    if email_sent:
                        add_log(job_id, f'✓ דוח נשלח בהצלחה למייל {job.get("user_email")}', 'success')
                    else:
                        add_log(job_id, '⚠️ שליחת המייל נכשלה - בדוק הגדרות SMTP', 'warning')
                except Exception as e:
                    add_log(job_id, f'⚠️ שגיאה בשליחת מייל: {str(e)}', 'warning')
            
        finally:
            # Cleanup - always close browser
            add_log(job_id, 'סוגר דפדפן...', 'info')
            client.close()
        
    except Exception as e:
        update_job_status(job_id, JobStatus.FAILED, f'שגיאה: {str(e)}', 0)
        add_log(job_id, f'שגיאה: {str(e)}', 'error')
        import traceback
        traceback.print_exc()


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle PDF file upload."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    # Save file with secure filename
    filename = secure_filename(file.filename)
    # Add timestamp to avoid conflicts
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    filepath = app.config['UPLOAD_FOLDER'] / filename
    file.save(filepath)
    
    return jsonify({'filename': filename})


@app.route('/api/submit', methods=['POST'])
def submit_job():
    """Start a new automation job."""
    data = request.json
    
    required_fields = ['filename', 'employee_id', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Create job
    job_id = str(uuid.uuid4())
    job = create_job(
        job_id,
        data['filename'],
        data['employee_id'],
        data['password'],
        data.get('user_email')  # Optional user email
    )
    
    return jsonify({'job_id': job_id})


@app.route('/api/submit-otp/<job_id>', methods=['POST'])
def submit_otp(job_id: str):
    """Submit OTP code for a waiting job."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'waiting_for_otp':
        return jsonify({'error': 'Job is not waiting for OTP'}), 400
    
    data = request.json
    if 'otp_code' not in data:
        return jsonify({'error': 'Missing otp_code'}), 400
    
    # Store the OTP code - the automation thread will pick it up
    job['otp_code'] = data['otp_code']
    add_log(job_id, f'קוד OTP התקבל: {data["otp_code"]}', 'info')
    
    return jsonify({'success': True})


@app.route('/api/status/<job_id>')
def get_job_status(job_id: str):
    """Get job status and progress."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    # Return only the last 50 logs to avoid overwhelming the client
    response = {
        'status': job['status'],
        'progress': job['progress'],
        'current_status': job['current_status'],
        'stats': job['stats'],
        'logs': job['logs'][-50:] if len(job['logs']) > 50 else job['logs']
    }
    
    if job['status'] == JobStatus.FAILED:
        response['error'] = job.get('error', 'Unknown error')
    
    return jsonify(response)


@app.route('/api/report/<job_id>')
def download_report(job_id: str):
    """Download the audit report for a job."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if not job.get('audit_report_path'):
        return jsonify({'error': 'Report not available'}), 404
    
    report_path = Path(job['audit_report_path'])
    if not report_path.exists():
        return jsonify({'error': 'Report file not found'}), 404
    
    return send_file(
        report_path,
        as_attachment=True,
        download_name=f'audit_report_{job_id}.csv'
    )


if __name__ == '__main__':
    print("=" * 70)
    print("HRM PORTAL TIMESHEET AUTOMATION - WEB SERVER")
    print("=" * 70)
    print("\nServer starting...")
    print("Open your browser and navigate to: http://localhost:5001")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 70)
    
    app.run(debug=False, host='0.0.0.0', port=5001)
