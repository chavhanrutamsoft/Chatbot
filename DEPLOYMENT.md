# Deployment Guide for Render

This guide will help you deploy the QuotePlan RAG Chatbot to Render.

## Prerequisites

1. **GitHub Account**: Your code needs to be on GitHub
2. **Render Account**: Sign up at https://render.com/ (free tier available)
3. **Qdrant Instance**: You need a Qdrant vector database running
4. **OpenRouter API Key**: Get from https://openrouter.ai/

## Step 1: Prepare Your Repository

### 1.1 Initialize Git (if not already done)

```bash
git init
git add .
git commit -m "Initial commit: Ready for Render deployment"
```

### 1.2 Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository (don't initialize with README)
3. Copy the repository URL

### 1.3 Push to GitHub

```bash
git remote add origin https://github.com/chavhanrutamsoft/chatbot.git
git branch -M main
git push -u origin main
```

**Your Repository**: `https://github.com/chavhanrutamsoft/chatbot`

## Step 2: Set Up Qdrant Database

You have three options:

### Option A: Qdrant Cloud (Recommended)
1. Sign up at https://cloud.qdrant.io/
2. Create a cluster
3. Get your cluster URL and API key
4. Use the URL as your `QDRANT_HOST`

### Option B: Deploy Qdrant on Render
1. In Render Dashboard, create a new "Background Worker"
2. Use Docker image: `qdrant/qdrant:latest`
3. Expose port 6333
4. Use the Render-provided URL as your `QDRANT_HOST`

### Option C: Self-Hosted
- Deploy Qdrant on your own server
- Ensure it's accessible via HTTPS

## Step 3: Ingest Data to Qdrant

Before deploying the web service, populate your Qdrant instance:

1. **Update `.env` file** with your cloud Qdrant URL:
   ```bash
   OPENROUTER_API_KEY=your_key_here
   QDRANT_HOST=https://your-qdrant-instance.onrender.com
   COLLECTION_NAME=quoteplan_chunks
   ```

2. **Run ingestion scripts locally**:
   ```bash
   python backend/extract_chunks.py
   python backend/ingest_qdrant.py
   ```

   Or if using Qdrant Cloud, you may need to add authentication:
   ```bash
   QDRANT_API_KEY=your_qdrant_api_key python backend/ingest_qdrant.py
   ```

## Step 4: Deploy to Render

### 4.1 Create Web Service

1. Go to https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Connect your GitHub account if not already connected
4. Select your repository

### 4.2 Configure Service

Use these settings:

- **Name**: `qdrant-rag-chatbot` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)
- **Root Directory**: Leave empty (root of repo)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --threads 4 --chdir backend app:app`
- **Plan**: 
  - **Free**: Good for testing (spins down after inactivity)
  - **Starter ($7/month)**: Better for production (always on)

### 4.3 Set Environment Variables

In the Render dashboard, go to "Environment" tab and add:

| Key | Value | Notes |
|-----|-------|-------|
| `OPENROUTER_API_KEY` | `your_openrouter_api_key` | Get from OpenRouter |
| `QDRANT_HOST` | `https://your-qdrant-url` | Your Qdrant instance URL |
| `COLLECTION_NAME` | `quoteplan_chunks` | Your collection name |
| `PORT` | (auto-set) | Don't change this - Render sets it |

### 4.4 Deploy

1. Click "Create Web Service"
2. Render will:
   - Clone your repo
   - Install dependencies
   - Start your application
3. Wait for "Live" status (green indicator)

### 4.5 Get Your URL

Once deployed, you'll get a URL like:
```
https://qdrant-rag-chatbot.onrender.com
```

## Step 5: Verify Deployment

1. Visit your Render URL
2. Test the chatbot interface
3. Check Render logs for any errors

## Troubleshooting

### Common Issues

1. **Build Fails**
   - Check `requirements.txt` has all dependencies
   - Verify Python version compatibility
   - Check Render build logs

2. **Application Crashes**
   - Check environment variables are set correctly
   - Verify Qdrant URL is accessible
   - Check application logs in Render dashboard

3. **Timeout Errors**
   - Increase timeout in start command: `--timeout 180`
   - Check Qdrant connection speed
   - Verify OpenRouter API key is valid

4. **Cold Start Issues**
   - Free tier services spin down after 15 minutes of inactivity
   - First request after spin-down takes 30-60 seconds
   - Consider upgrading to Starter plan for always-on service

5. **Memory Issues**
   - Sentence-transformers models need memory
   - Upgrade to a plan with more RAM if needed
   - Check Render logs for OOM (Out of Memory) errors

### Checking Logs

In Render dashboard:
1. Go to your service
2. Click "Logs" tab
3. View real-time logs
4. Look for errors or warnings

## Updating Your Deployment

1. Make changes to your code
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update description"
   git push
   ```
3. Render automatically detects changes and redeploys
4. Monitor the "Events" tab in Render dashboard

## Using render.yaml (Alternative Method)

If you prefer infrastructure-as-code:

1. The `render.yaml` file is already in your repo
2. In Render Dashboard, select "Apply render.yaml" when creating service
3. Update environment variables in the YAML or via dashboard
4. Render will use the configuration from the file

## Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore`
2. **Use environment variables** for all secrets
3. **Enable HTTPS** - Render provides this automatically
4. **Rotate API keys** regularly
5. **Monitor usage** to prevent unexpected costs

## Cost Estimation

- **Free Tier**: $0/month (with limitations)
- **Starter Plan**: $7/month (always on, better performance)
- **Qdrant Cloud**: Free tier available, paid plans start at $25/month
- **OpenRouter**: Pay-per-use pricing

## Next Steps

- Set up custom domain (optional)
- Configure auto-scaling (if needed)
- Set up monitoring and alerts
- Implement CI/CD pipeline

## Support

- Render Docs: https://render.com/docs
- Qdrant Docs: https://qdrant.tech/documentation/
- OpenRouter Docs: https://openrouter.ai/docs
