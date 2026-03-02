# מערכת מילוי נוכחות אוטומטי - HRM Portal

<div dir="rtl">

## 🎯 סקירה כללית

מערכת אוטומציה למילוי נוכחות בפורטל HRM. המערכת קוראת קובץ PDF של דוח נוכחות וממלאת אוטומטית את הנתונים בפורטל.

### ✨ תכונות עיקריות

- 📄 **קריאת PDF אוטומטית** - זיהוי אוטומטי של תאריכים, שעות כניסה ויציאה
- 🔐 **התחברות מאובטחת** - תמיכה ב-OTP (אימות דו-שלבי)
- 🤖 **מילוי אוטומטי** - מילוי כל ימי החודש בלחיצת כפתור
- 📊 **דוחות מפורטים** - סיכום מלא של הפעולות שבוצעו
- 📧 **שליחת דוח במייל** - קבלת סיכום אוטומטי למייל (אופציונלי)
- 🌐 **ממשק ידידותי** - ממשק web בעברית

---

## 🚀 דרכי שימוש

המערכת זמינה ב-3 דרכים שונות:

### 1️⃣ Desktop App (מומלץ למחשב)

**התקנה:**

**Windows:**
```batch
# הורד את הפרויקט
git clone <repository-url>
cd sqlinksrab

# הרץ את סקריפט ההתקנה
install_windows.bat
```

**Mac/Linux:**
```bash
# הורד את הפרויקט
git clone <repository-url>
cd sqlinksrab

# הרץ את סקריפט ההתקנה
chmod +x install_mac_linux.sh
./install_mac_linux.sh
```

**הפעלה:**
- Windows: לחץ פעמיים על `הפעל מערכת נוכחות.bat`
- Mac/Linux: `./run.sh`

המערכת תיפתח בדפדפן בכתובת: http://localhost:5001

---

### 2️⃣ Telegram Bot (מומלץ לפלאפון)

**הגדרה:**

1. צור בוט חדש ב-Telegram דרך [@BotFather](https://t.me/botfather)
2. קבל את ה-token
3. הוסף את ה-token לקובץ `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   ```
4. הרץ את הבוט:
   ```bash
   python telegram_bot.py
   ```

**שימוש:**
1. פתח את הבוט ב-Telegram
2. שלח `/start`
3. שלח את קובץ ה-PDF
4. שלח מספר עובד
5. שלח סיסמה
6. שלח קוד OTP כשתתבקש
7. הבוט ימלא את הנוכחות!

---

### 3️⃣ Web App (Railway)

**Deploy ל-Railway:**

1. צור חשבון ב-[Railway.app](https://railway.app)
2. התחבר עם GitHub
3. לחץ "New Project" → "Deploy from GitHub repo"
4. בחר את הפרויקט
5. Railway יזהה אוטומטית את הקבצים ויעשה deploy

**הגדרת משתני סביבה ב-Railway:**
```
PORT=5001
TELEGRAM_BOT_TOKEN=your_token_here (אופציונלי)
```

**גישה:**
Railway ייתן לך URL ציבורי, למשל:
`https://your-app.railway.app`

---

## 📋 דרישות מערכת

- Python 3.8 ומעלה
- Chrome/Chromium (מותקן אוטומטית על ידי Playwright)
- 2GB RAM מינימום
- חיבור אינטרנט

---

## 🔧 התקנה ידנית (למפתחים)

```bash
# שכפל את הפרויקט
git clone <repository-url>
cd sqlinksrab

# צור סביבה וירטואלית
python -m venv venv

# הפעל את הסביבה
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# התקן תלויות
pip install -r requirements.txt

# התקן דפדפנים
playwright install chromium

# העתק קבצי הגדרות
cp config.example.json config.json
cp .env.example .env

# הרץ את השרת
python web_server.py
```

---

## 📧 הגדרת שליחת מייל (אופציונלי)

המערכת יכולה לשלוח דוח מסכם אוטומטית ל-hours@sqlink.com לאחר השלמת מילוי הנוכחות.

### הגדרת SMTP

ערוך את קובץ `.env` והוסף את הפרטים הבאים:

```env
# Email Notification Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=HRM Automation System
EMAIL_ENABLED=true
```

### דוגמאות לספקי SMTP פופולריים

**Gmail:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # צור App Password ב-Google Account
```
💡 [איך ליצור App Password ב-Gmail](https://support.google.com/accounts/answer/185833)

**SendGrid (חינם עד 100 מיילים ביום):**
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

**Mailgun (חינם עד 5,000 מיילים בחודש):**
```env
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=your-mailgun-username
SMTP_PASSWORD=your-mailgun-password
```

### מה כולל הדוח?

הדוח שנשלח למייל כולל:
- מספר עובד (חלקי, למשל: ***456789)
- חודש יעד
- סטטיסטיקות: נוצרו, דולגו, נכשלו
- זמן השלמה

**פרטיות:** הדוח לא כולל סיסמאות או מידע רגיש אחר.

---


## 📖 איך זה עובד?

### תהליך המילוי:

1. **העלאת PDF** 📄
   - המשתמש מעלה את דוח הנוכחות
   - המערכת מזהה אוטומטית את החודש
   - מחלצת את כל התאריכים והשעות

2. **התחברות** 🔐
   - המשתמש מזין ת.ז וסיסמה
   - המערכת פותחת דפדפן Chrome
   - מתחברת לפורטל HRM
   - מטפלת ב-OTP אוטומטית

3. **מילוי אוטומטי** 🤖
   - המערכת עוברת על כל יום בחודש
   - ממלאת שעות כניסה ויציאה
   - מדלגת על סופי שבוע
   - מטפלת בימים מיוחדים

4. **דוח** 📊
   - סיכום של כל הפעולות
   - רשימת ימים שנוצרו/דולגו/נכשלו
   - אפשרות להוריד דוח CSV

---

## 🔒 אבטחה ופרטיות

- ✅ כל הנתונים נשמרים מקומית על המחשב
- ✅ אין שמירה של סיסמאות
- ✅ הקוד פתוח לבדיקה
- ✅ אין שליחת מידע לשרתים חיצוניים (במצב Desktop)
- ✅ תמיכה ב-OTP לאבטחה מוגברת

---

## 💰 עלויות

| דרך שימוש | עלות | מתאים ל |
|-----------|------|---------|
| Desktop App | חינמי 🎉 | שימוש אישי |
| Telegram Bot (מקומי) | חינמי 🎉 | שימוש אישי |
| Railway Hosting | ~$10-15/חודש | שיתוף עם אחרים |

**טיפ:** אם 10 אנשים משתפים Railway, העלות היא רק $1-1.5 לאדם!

---

## 🐛 פתרון בעיות

### הדפדפן לא נפתח
```bash
playwright install chromium
```

### שגיאת התקנה
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### שגיאת OTP
- ודא שהזנת את הקוד בזמן (לפני שפג)
- בדוק שהקוד נכון (6 ספרות)

### שגיאת PDF
- ודא שהקובץ הוא PDF תקין
- בדוק שהקובץ מכיל טבלת נוכחות

---

## 📞 תמיכה

יש בעיה? שאלה?
- פתח issue ב-GitHub
- שלח הודעה למפתח
- בדוק את ה-FAQ

---

## 📄 רישיון

MIT License - ראה קובץ LICENSE לפרטים

---

## 🙏 תודות

- Microsoft Playwright - אוטומציית דפדפן
- pdfplumber - עיבוד PDF
- Flask - web framework
- python-telegram-bot - Telegram integration

---

## 🔄 עדכונים

### גרסה 2.0 (פברואר 2026)
- ✨ הוספת Telegram Bot
- ✨ תמיכה ב-Railway deployment
- ✨ זיהוי אוטומטי של חודש מה-PDF
- ✨ שיפור ממשק OTP
- 🐛 תיקוני באגים שונים

### גרסה 1.0 (פברואר 2026)
- 🎉 גרסה ראשונה
- ✅ מילוי נוכחות אוטומטי
- ✅ תמיכה ב-OTP
- ✅ ממשק web בעברית

</div>
