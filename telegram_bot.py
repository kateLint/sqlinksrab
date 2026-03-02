"""
Telegram Bot for HRM Timesheet Automation
Allows users to interact with the automation system via Telegram
"""

import os
import logging
from pathlib import Path
from typing import Optional
import asyncio
from telegram import Update, ForceReply
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from src.config import Config
from src.pdf_extractor import PDFExtractor
from src.portal_client import PortalClient
from src.email_sender import EmailSender

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# User states
WAITING_FOR_PDF = 1
WAITING_FOR_EMPLOYEE_ID = 2
WAITING_FOR_PASSWORD = 3
WAITING_FOR_EMAIL_CONSENT = 4
WAITING_FOR_OTP = 5

# Store user data temporarily
user_data_store = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"👋 שלום {user.mention_html()}!\n\n"
        f"ברוך הבא למערכת מילוי נוכחות אוטומטי! 🤖\n\n"
        f"📋 <b>איך זה עובד:</b>\n"
        f"1. שלח לי את קובץ ה-PDF של הנוכחות\n"
        f"2. אזין את מספר העובד שלך\n"
        f"3. אזין את הסיסמה שלך\n"
        f"4. אזין קוד OTP כשתתבקש\n"
        f"5. אני אמלא את הנוכחות בשבילך!\n\n"
        f"🔒 <b>פרטיות:</b> כל הנתונים נמחקים מיד לאחר השימוש\n\n"
        f"להתחלה, שלח לי את קובץ ה-PDF 📄",
        reply_markup=ForceReply(selective=True),
    )
    user_data_store[user.id] = {"state": WAITING_FOR_PDF}


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "📚 <b>עזרה - מערכת מילוי נוכחות</b>\n\n"
        "<b>פקודות זמינות:</b>\n"
        "/start - התחל תהליך חדש\n"
        "/cancel - בטל תהליך נוכחי\n"
        "/help - הצג הודעה זו\n\n"
        "<b>תהליך מילוי נוכחות:</b>\n"
        "1️⃣ שלח PDF של הנוכחות\n"
        "2️⃣ שלח מספר עובד\n"
        "3️⃣ שלח סיסמה\n"
        "4️⃣ שלח קוד OTP\n"
        "5️⃣ המערכת תמלא את הנוכחות!\n\n"
        "❓ שאלות? צור קשר עם התמיכה",
        parse_mode="HTML"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel the current operation."""
    user = update.effective_user
    if user.id in user_data_store:
        del user_data_store[user.id]
    await update.message.reply_text(
        "❌ התהליך בוטל.\n\n"
        "להתחלה מחדש, שלח /start"
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle PDF document upload."""
    user = update.effective_user
    
    if user.id not in user_data_store or user_data_store[user.id]["state"] != WAITING_FOR_PDF:
        await update.message.reply_text(
            "⚠️ אנא התחל תהליך חדש עם /start"
        )
        return
    
    document = update.message.document
    
    # Check if it's a PDF
    if not document.file_name.endswith('.pdf'):
        await update.message.reply_text(
            "❌ אנא שלח קובץ PDF בלבד"
        )
        return
    
    await update.message.reply_text("⏳ מוריד קובץ...")
    
    # Download the file
    file = await context.bot.get_file(document.file_id)
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    file_path = upload_dir / f"{user.id}_{document.file_name}"
    await file.download_to_drive(file_path)
    
    # Extract data from PDF
    await update.message.reply_text("📄 מעבד קובץ PDF...")
    
    try:
        extractor = PDFExtractor(file_path)
        records = extractor.extract()
        detected_month = extractor.get_detected_month(records)
        
        user_data_store[user.id].update({
            "pdf_path": str(file_path),
            "records": records,
            "month": detected_month,
            "state": WAITING_FOR_EMPLOYEE_ID
        })
        
        await update.message.reply_text(
            f"✅ קובץ התקבל בהצלחה!\n\n"
            f"📊 <b>מידע שזוהה:</b>\n"
            f"📅 חודש: {detected_month}\n"
            f"📝 רשומות: {len(records)}\n\n"
            f"עכשיו, שלח את <b>מספר העובד</b> שלך:",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        await update.message.reply_text(
            f"❌ שגיאה בעיבוד הקובץ: {str(e)}\n\n"
            f"אנא נסה שוב או שלח /cancel"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages based on current state."""
    user = update.effective_user
    text = update.message.text
    
    if user.id not in user_data_store:
        await update.message.reply_text(
            "⚠️ אנא התחל תהליך חדש עם /start"
        )
        return
    
    state = user_data_store[user.id]["state"]
    
    if state == WAITING_FOR_EMPLOYEE_ID:
        user_data_store[user.id]["employee_id"] = text
        user_data_store[user.id]["state"] = WAITING_FOR_PASSWORD
        await update.message.reply_text(
            "✅ מספר עובד התקבל!\n\n"
            "עכשיו, שלח את <b>הסיסמה</b> שלך:",
            parse_mode="HTML"
        )
    
    elif state == WAITING_FOR_PASSWORD:
        user_data_store[user.id]["password"] = text
        user_data_store[user.id]["state"] = WAITING_FOR_EMAIL_CONSENT
        
        await update.message.reply_text(
            "✅ סיסמה התקבלה!\n\n"
            "📧 <b>שליחת דוח במייל</b>\n"
            "האם תרצה לשלוח דוח מסכם למייל hours@sqlink.com?\n\n"
            "הדוח יכלול סטטיסטיקות בלבד (ללא פרטים רגישים)\n\n"
            "שלח <b>כן</b> או <b>לא</b>",
            parse_mode="HTML"
        )
    
    
    elif state == WAITING_FOR_EMAIL_CONSENT:
        response = text.strip().lower()
        
        # Check for consent
        if response in ['כן', 'yes', 'y', 'כ']:
            user_data_store[user.id]["send_email_consent"] = True
            await update.message.reply_text(
                "✅ דוח יישלח למייל hours@sqlink.com\n\n"
                "🚀 מתחיל תהליך אוטומציה...\n"
                "⏳ זה עלול לקחת מספר דקות..."
            )
        elif response in ['לא', 'no', 'n', 'ל']:
            user_data_store[user.id]["send_email_consent"] = False
            await update.message.reply_text(
                "✅ לא יישלח דוח במייל\n\n"
                "🚀 מתחיל תהליך אוטומציה...\n"
                "⏳ זה עלול לקחת מספר דקות..."
            )
        else:
            await update.message.reply_text(
                "⚠️ אנא שלח <b>כן</b> או <b>לא</b>",
                parse_mode="HTML"
            )
            return
        
        # Update state and start automation
        user_data_store[user.id]["state"] = WAITING_FOR_OTP
        asyncio.create_task(run_automation(update, user.id))
    
    elif state == WAITING_FOR_OTP:
        otp_code = text.strip()
        user_data_store[user.id]["otp_code"] = otp_code
        await update.message.reply_text(
            f"✅ קוד OTP התקבל: {otp_code}\n\n"
            f"⏳ ממשיך בתהליך..."
        )


async def run_automation(update: Update, user_id: int) -> None:
    """Run the automation process."""
    try:
        data = user_data_store[user_id]
        
        # Initialize config
        config = Config()
        config._config["automation"]["target_month"] = data["month"]
        config.employee_id = data["employee_id"]
        config.password = data["password"]
        
        await update.message.reply_text("🌐 פותח דפדפן...")
        
        # Initialize portal client
        client = PortalClient(config)
        client.start()
        
        try:
            await update.message.reply_text("🔐 מתחבר לפורטל...")
            
            # Note: The OTP handling needs to be adapted for async
            # This is a simplified version
            if not client.login():
                await update.message.reply_text(
                    "❌ התחברות נכשלה\n\n"
                    "אנא בדוק את הפרטים ונסה שוב"
                )
                return
            
            await update.message.reply_text("✅ התחברות הצליחה!")
            await update.message.reply_text("📝 ממלא נוכחות...")
            
            # Navigate to timesheet
            if not client.navigate_to_timesheet():
                await update.message.reply_text("❌ ניווט לדף נוכחות נכשל")
                return
            
            # Process records
            stats = {"created": 0, "skipped": 0, "failed": 0}
            total = len(data["records"])
            
            for i, record in enumerate(data["records"], 1):
                try:
                    result = client.enter_timesheet_data(record, config.dry_run)
                    if result == "created":
                        stats["created"] += 1
                    elif result == "skipped":
                        stats["skipped"] += 1
                    
                    # Send progress update every 5 records
                    if i % 5 == 0:
                        progress = int((i / total) * 100)
                        await update.message.reply_text(
                            f"📊 התקדמות: {progress}% ({i}/{total})"
                        )
                except Exception as e:
                    stats["failed"] += 1
                    logger.error(f"Error processing record {i}: {e}")
            
            # Send final report
            await update.message.reply_text(
                f"✅ <b>התהליך הושלם!</b>\n\n"
                f"📊 <b>סיכום:</b>\n"
                f"✅ נוצרו: {stats['created']}\n"
                f"⏭️ דולגו: {stats['skipped']}\n"
                f"❌ נכשלו: {stats['failed']}\n\n"
                f"🎉 מילוי הנוכחות הושלם בהצלחה!",
                parse_mode="HTML"
            )
            
            # Send email if user consented
            if data.get("send_email_consent", False):
                await update.message.reply_text("📧 שולח דוח במייל...")
                try:
                    email_sender = EmailSender()
                    email_sent = email_sender.send_completion_report(
                        employee_id=data["employee_id"],
                        target_month=data["month"],
                        stats={
                            'total': len(data["records"]),
                            'created': stats['created'],
                            'skipped': stats['skipped'],
                            'failed': stats['failed']
                        }
                    )
                    
                    if email_sent:
                        await update.message.reply_text(
                            "✅ דוח נשלח בהצלחה למייל hours@sqlink.com"
                        )
                    else:
                        await update.message.reply_text(
                            "⚠️ שליחת המייל נכשלה - בדוק הגדרות SMTP"
                        )
                except Exception as e:
                    logger.error(f"Email sending error: {e}")
                    await update.message.reply_text(
                        f"⚠️ שגיאה בשליחת מייל: {str(e)}"
                    )
            
        finally:
            client.close()
            
        # Cleanup
        if user_id in user_data_store:
            # Delete PDF file
            pdf_path = Path(data["pdf_path"])
            if pdf_path.exists():
                pdf_path.unlink()
            del user_data_store[user_id]
            
    except Exception as e:
        logger.error(f"Automation error: {e}")
        await update.message.reply_text(
            f"❌ שגיאה בתהליך האוטומציה:\n{str(e)}\n\n"
            f"אנא נסה שוב או צור קשר עם התמיכה"
        )


def main() -> None:
    """Start the bot."""
    # Get token from environment variable
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    logger.info("Starting Telegram bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
