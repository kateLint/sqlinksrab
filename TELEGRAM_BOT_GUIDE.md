# Telegram Bot Setup Guide

## Creating Your Telegram Bot

### Step 1: Create Bot with BotFather

1. Open Telegram and search for `@BotFather`
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Choose a name (e.g., "HRM Timesheet Bot")
   - Choose a username (must end with 'bot', e.g., "hrm_timesheet_bot")
4. BotFather will give you a **token** - save this!

### Step 2: Configure the Bot

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your token:
   ```
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

### Step 3: Run the Bot

**Locally:**
```bash
python telegram_bot.py
```

**On Railway:**
- The bot will run automatically if you set the `TELEGRAM_BOT_TOKEN` environment variable
- Railway will use the `Procfile` to start the bot

### Step 4: Test the Bot

1. Find your bot in Telegram (search for the username you chose)
2. Send `/start`
3. Follow the instructions!

---

## Bot Commands

- `/start` - Start a new timesheet filling process
- `/help` - Show help message
- `/cancel` - Cancel current operation

---

## Bot Workflow

1. **User sends `/start`**
   - Bot welcomes user and asks for PDF

2. **User uploads PDF**
   - Bot downloads and processes the file
   - Extracts timesheet data
   - Auto-detects the month
   - Asks for employee ID

3. **User sends employee ID**
   - Bot stores it
   - Asks for password

4. **User sends password**
   - Bot starts automation
   - Opens browser in background
   - Logs into HRM portal
   - Asks for OTP when needed

5. **User sends OTP**
   - Bot completes login
   - Fills timesheet automatically
   - Sends progress updates
   - Sends final report

---

## Security Notes

- ✅ All user data is deleted after processing
- ✅ Passwords are never logged
- ✅ PDF files are deleted after use
- ✅ Bot runs in isolated environment

---

## Customization

### Change Bot Messages

Edit `telegram_bot.py` and modify the text in the message handlers.

### Add More Commands

Add new handlers in the `main()` function:

```python
application.add_handler(CommandHandler("mycommand", my_handler))
```

### Add Buttons

Use `InlineKeyboardMarkup` for interactive buttons:

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = [
    [InlineKeyboardButton("Option 1", callback_data='1')],
    [InlineKeyboardButton("Option 2", callback_data='2')],
]
reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text('Choose:', reply_markup=reply_markup)
```

---

## Troubleshooting

### Bot doesn't respond
- Check that the token is correct
- Make sure the bot is running
- Check Railway logs if deployed

### "Unauthorized" error
- Token is wrong or expired
- Create a new bot and get a new token

### Bot crashes during automation
- Check that Playwright is installed
- Check browser logs
- Verify credentials are correct

---

## Hosting Options

### 1. Local (Free)
```bash
python telegram_bot.py
```
- ✅ Free
- ❌ Must keep computer running
- ❌ Not accessible when computer is off

### 2. Railway (~$10-15/month)
- ✅ Always online
- ✅ Automatic restarts
- ✅ Easy deployment
- ❌ Costs money

### 3. PythonAnywhere (Free tier available)
- ✅ Free tier available
- ⚠️ Limited resources
- ⚠️ May not support Playwright

---

## Advanced: Multiple Bots

You can run multiple bots for different purposes:

1. Create multiple bots with BotFather
2. Create separate Python files for each
3. Use different tokens
4. Run them all on Railway as separate services

Example `Procfile`:
```
web: python web_server.py
bot1: python telegram_bot.py
bot2: python telegram_bot_admin.py
```
