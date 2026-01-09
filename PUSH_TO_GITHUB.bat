@echo off
echo ========================================
echo GitHub Push Script for Chatbot
echo ========================================
echo.

echo Step 1: Initializing Git...
git init

echo.
echo Step 2: Adding all files...
git add .

echo.
echo Step 3: Creating initial commit...
git commit -m "Initial commit: QuotePlan RAG Chatbot ready for deployment"

echo.
echo Step 4: Adding remote repository...
git remote add origin https://github.com/chavhanrutamsoft/chatbot.git

echo.
echo Step 5: Setting main branch...
git branch -M main

echo.
echo Step 6: Pushing to GitHub...
echo.
echo IMPORTANT: Make sure you have:
echo 1. Created the repository at: https://github.com/chavhanrutamsoft/chatbot
echo 2. Authenticated with GitHub (username/password or token)
echo.
pause

git push -u origin main

echo.
echo ========================================
echo Done! Check your repository at:
echo https://github.com/chavhanrutamsoft/chatbot
echo ========================================
pause
