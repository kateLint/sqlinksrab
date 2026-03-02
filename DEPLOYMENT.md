# Railway Deployment Guide

## Quick Deploy to Railway

### Prerequisites
- GitHub account
- Railway account (free tier available)

### Steps

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo>
   git push -u origin main
   ```

2. **Deploy on Railway**
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will automatically detect the configuration

3. **Set Environment Variables**
   In Railway dashboard, go to Variables and add:
   ```
   PORT=5001
   TELEGRAM_BOT_TOKEN=<your-bot-token>  # Optional, only for Telegram bot
   ```

4. **Deploy**
   - Railway will automatically build and deploy
   - You'll get a public URL like: `https://your-app.railway.app`

### Running Both Web and Bot

Railway supports multiple processes via the `Procfile`:

```
web: python web_server.py
bot: python telegram_bot.py
```

To run both:
1. In Railway dashboard, create two services
2. One for web, one for bot
3. Both will use the same codebase

### Cost Estimation

- **Free tier**: $5 credit per month
- **Paid**: ~$10-15/month for both services
- **Shared cost**: If 10 users, only $1-1.5 per person!

### Monitoring

Railway provides:
- Real-time logs
- Resource usage metrics
- Deployment history
- Automatic restarts on failure

### Updating

Simply push to GitHub:
```bash
git add .
git commit -m "Update"
git push
```

Railway will automatically redeploy!

---

## Alternative: Render.com

Similar process, but:
- Go to [render.com](https://render.com)
- Create "New Web Service"
- Connect GitHub
- Set build command: `pip install -r requirements.txt && playwright install chromium`
- Set start command: `python web_server.py`

Cost: ~$25/month (more expensive than Railway)

---

## Alternative: Fly.io

More technical, but cheaper:

1. Install Fly CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. Login:
   ```bash
   fly auth login
   ```

3. Launch:
   ```bash
   fly launch
   ```

4. Deploy:
   ```bash
   fly deploy
   ```

Cost: ~$5-10/month
