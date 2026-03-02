"""
Email sender utility for sending completion reports.
Sends automated notifications to hours@sqlink.com after successful timesheet automation.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EmailSender:
    """Handles sending email notifications via SMTP."""
    
    def __init__(self):
        """Initialize email sender with configuration from environment variables."""
        self.enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('SMTP_FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('SMTP_FROM_NAME', 'HRM Automation System')
        
        if not self.enabled:
            logger.info("Email notifications are disabled (EMAIL_ENABLED=false)")
        elif not self.smtp_username or not self.smtp_password:
            logger.warning("Email is enabled but SMTP credentials are missing")
            self.enabled = False
    
    def send_completion_report(
        self,
        employee_id: str,
        target_month: str,
        stats: Dict[str, int],
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Send a completion report email to hours@sqlink.com.
        
        Args:
            employee_id: Employee ID (will be partially masked for privacy)
            target_month: Target month (e.g., "2026-01")
            stats: Dictionary with 'created', 'skipped', 'failed' counts
            timestamp: Completion timestamp (defaults to now)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info("Email sending skipped - not enabled")
            return False
        
        try:
            # Mask employee ID for privacy (show last 6 digits only)
            masked_id = f"***{employee_id[-6:]}" if len(employee_id) > 6 else "***"
            
            # Use provided timestamp or current time
            if timestamp is None:
                timestamp = datetime.now()
            
            # Format timestamp in Hebrew-friendly format
            timestamp_str = timestamp.strftime('%d/%m/%Y %H:%M:%S')
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'דוח מילוי נוכחות - {target_month}'
            msg['From'] = f'{self.from_name} <{self.from_email}>'
            msg['To'] = 'hours@sqlink.com'
            
            # Create plain text version
            text_content = f"""
דוח מילוי נוכחות אוטומטי
{'=' * 50}

מספר עובד: {masked_id}
חודש יעד: {target_month}
זמן השלמה: {timestamp_str}

סטטיסטיקות:
- נוצרו בהצלחה: {stats.get('created', 0)}
- דולגו: {stats.get('skipped', 0)}
- נכשלו: {stats.get('failed', 0)}
- סה"כ: {stats.get('total', 0)}

{'=' * 50}
מערכת אוטומציה למילוי נוכחות - HRM Portal
"""
            
            # Create HTML version
            html_content = f"""
<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            padding: 30px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #eee;
        }}
        .info-label {{
            font-weight: 600;
            color: #666;
        }}
        .info-value {{
            color: #333;
        }}
        .stats {{
            margin-top: 20px;
            background-color: #f9f9f9;
            border-radius: 6px;
            padding: 20px;
        }}
        .stats h2 {{
            margin-top: 0;
            font-size: 18px;
            color: #333;
        }}
        .stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
        }}
        .stat-value {{
            font-weight: bold;
            font-size: 18px;
        }}
        .stat-value.success {{ color: #10b981; }}
        .stat-value.warning {{ color: #f59e0b; }}
        .stat-value.error {{ color: #ef4444; }}
        .footer {{
            background-color: #f9f9f9;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 דוח מילוי נוכחות אוטומטי</h1>
        </div>
        <div class="content">
            <div class="info-row">
                <span class="info-label">מספר עובד:</span>
                <span class="info-value">{masked_id}</span>
            </div>
            <div class="info-row">
                <span class="info-label">חודש יעד:</span>
                <span class="info-value">{target_month}</span>
            </div>
            <div class="info-row">
                <span class="info-label">זמן השלמה:</span>
                <span class="info-value">{timestamp_str}</span>
            </div>
            
            <div class="stats">
                <h2>סטטיסטיקות</h2>
                <div class="stat-item">
                    <span>✅ נוצרו בהצלחה:</span>
                    <span class="stat-value success">{stats.get('created', 0)}</span>
                </div>
                <div class="stat-item">
                    <span>⏭️ דולגו:</span>
                    <span class="stat-value warning">{stats.get('skipped', 0)}</span>
                </div>
                <div class="stat-item">
                    <span>❌ נכשלו:</span>
                    <span class="stat-value error">{stats.get('failed', 0)}</span>
                </div>
                <div class="stat-item" style="border-top: 2px solid #ddd; margin-top: 10px; padding-top: 10px;">
                    <span><strong>סה"כ:</strong></span>
                    <span class="stat-value">{stats.get('total', 0)}</span>
                </div>
            </div>
        </div>
        <div class="footer">
            מערכת אוטומציה למילוי נוכחות - HRM Portal
        </div>
    </div>
</body>
</html>
"""
            
            # Attach both versions
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            logger.info(f"Sending completion report to hours@sqlink.com via {self.smtp_host}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info("Email sent successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
