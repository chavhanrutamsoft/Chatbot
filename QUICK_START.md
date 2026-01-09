# Quick Start Guide - GitHub & Render Deployment

## Your Repository Details
- **GitHub Username**: `chavhanrutamsoft`
- **Repository Name**: `chatbot`
- **Repository URL**: `https://github.com/chavhanrutamsoft/chatbot`

## Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: QuotePlan RAG Chatbot ready for deployment"

# Add remote repository
git remote add origin https://github.com/chavhanrutamsoft/chatbot.git

# Set main branch
git branch -M main

# Push to GitHub
git push -u origin main
```

## Step 2: Create GitHub Repository

1. Go to: https://github.com/new
2. Repository name: `chatbot`
3. Description: "RAG Chatbot for QuotePlan documentation"
4. Choose Public or Private
5. **DO NOT** check any boxes (README, .gitignore, license)
6. Click "Create repository"

## Step 3: Deploy to Render

### 3.1 Create Web Service

1. Go to: https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Connect GitHub if needed
4. Select repository: `chavhanrutamsoft/chatbot`

### 3.2 Configure Service

- **Name**: `chatbot` (or `qdrant-rag-chatbot`)
- **Environment**: `Python 3`
- **Region**: Choose closest to you
- **Branch**: `main`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --threads 4 --chdir backend app:app`
- **Plan**: Free (for testing) or Starter ($7/month for always-on)

### 3.3 Environment Variables

Add these in Render Dashboard → Environment:

| Key | Value |
|-----|-------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `QDRANT_HOST` | Your Qdrant URL (e.g., `https://your-qdrant.onrender.com`) |
| `COLLECTION_NAME` | `quoteplan_chunks` |

### 3.4 Deploy

Click "Create Web Service" and wait for deployment.

Your app will be available at: `https://chatbot.onrender.com` (or similar)

## Step 4: Set Up Qdrant

You need a Qdrant database. Options:

### Option A: Qdrant Cloud (Recommended)
1. Sign up: https://cloud.qdrant.io/
2. Create cluster
3. Get URL and API key
4. Use URL as `QDRANT_HOST`

### Option B: Deploy Qdrant on Render
1. Create new "Background Worker" on Render
2. Docker image: `qdrant/qdrant:latest`
3. Port: `6333`
4. Use Render URL as `QDRANT_HOST`

## Step 5: Ingest Data

Before using the chatbot, populate Qdrant:

1. Update `.env` with your Qdrant URL:
   ```
   QDRANT_HOST=https://your-qdrant-url
   OPENROUTER_API_KEY=your_key
   COLLECTION_NAME=quoteplan_chunks
   ```

2. Run ingestion:
   ```bash
   python backend/extract_chunks.py
   python backend/ingest_qdrant.py
   ```

## Important Files

- ✅ `.gitignore` - Excludes sensitive files
- ✅ `requirements.txt` - Python dependencies
- ✅ `render.yaml` - Render configuration
- ✅ `backend/app.py` - Flask app for Render
- ✅ `backend/server.py` - Local development server
- ✅ `env.example` - Environment variable template

## Security

⚠️ **Never commit**:
- `.env` file (contains API keys)
- Any files with passwords or secrets

## Troubleshooting

### Build fails on Render
- Check `requirements.txt` has all dependencies
- Verify Python version compatibility

### App crashes
- Check environment variables are set
- Verify Qdrant URL is accessible
- Check Render logs

### Cold starts (Free tier)
- Free tier spins down after 15 min inactivity
- First request after spin-down takes 30-60 seconds
- Upgrade to Starter plan for always-on

## Need Help?

- Full GitHub Guide: See `GITHUB_SETUP.md`
- Full Deployment Guide: See `DEPLOYMENT.md`
- Render Docs: https://render.com/docs
