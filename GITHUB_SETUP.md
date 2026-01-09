# GitHub Setup Guide

This guide will help you push your project to GitHub.

## Step 1: Initialize Git Repository

If you haven't already initialized git:

```bash
git init
```

## Step 2: Add All Files

```bash
git add .
```

This will add all files except those in `.gitignore`:
- ✅ Code files
- ✅ Configuration files
- ✅ Documentation
- ❌ `.env` (sensitive - not included)
- ❌ `__pycache__/` (generated files - not included)
- ❌ Virtual environments (not included)

## Step 3: Create Initial Commit

```bash
git commit -m "Initial commit: QuotePlan RAG Chatbot ready for deployment"
```

## Step 4: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `chatbot`
3. Description: "RAG Chatbot for QuotePlan documentation using Qdrant and OpenRouter"
4. Visibility: Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

**Your Repository**: `https://github.com/chavhanrutamsoft/chatbot`

## Step 5: Connect and Push

GitHub will show you commands. Use these:

```bash
git remote add origin https://github.com/chavhanrutamsoft/chatbot.git
git branch -M main
git push -u origin main
```

**Your Repository URL**: `https://github.com/chavhanrutamsoft/chatbot`

## Step 6: Verify

1. Go to your GitHub repository page
2. Verify all files are there
3. Check that `.env` is NOT visible (it should be ignored)

## Files Included in Repository

✅ **Included:**
- All Python scripts (`backend/`)
- Frontend files (`frontend/`)
- Configuration files (`requirements.txt`, `render.yaml`, `docker-compose.yml`)
- Documentation (`README.md`, `DEPLOYMENT.md`)
- Data structure files (but not large binary files if you add them)
- `.gitignore`
- `env.example` (template for environment variables)

❌ **Excluded (via .gitignore):**
- `.env` (contains API keys - NEVER commit this!)
- `__pycache__/` (Python cache)
- Virtual environments
- IDE files
- OS files (`.DS_Store`, `Thumbs.db`)
- Log files

## Next Steps

After pushing to GitHub:

1. **Deploy to Render**: Follow `DEPLOYMENT.md`
2. **Set up environment variables** in Render dashboard
3. **Test your deployment**

## Security Reminder

⚠️ **IMPORTANT**: Never commit:
- `.env` files
- API keys
- Passwords
- Private keys

If you accidentally committed sensitive data:
1. Remove it from git history
2. Rotate your API keys
3. Update `.gitignore` to prevent future commits

## Troubleshooting

### "Repository not found"
- Check repository name and username
- Verify you have access to the repository

### "Permission denied"
- Make sure you're authenticated with GitHub
- Use GitHub CLI or SSH keys

### Large files
- If you have large files (>100MB), consider Git LFS
- Or exclude them from the repository

## Repository Structure on GitHub

Your repository should look like:

```
chatbot/
├── .gitignore
├── .gitattributes
├── README.md
├── DEPLOYMENT.md
├── GITHUB_SETUP.md
├── requirements.txt
├── render.yaml
├── docker-compose.yml
├── env.example
├── backend/
│   ├── app.py (Flask app for Render)
│   ├── server.py (Local development server)
│   ├── query_bot.py
│   ├── ingest_qdrant.py
│   └── ...
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
└── data/
    └── ...
```

## Need Help?

- GitHub Docs: https://docs.github.com/
- Git Basics: https://git-scm.com/doc
