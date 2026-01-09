# QuotePlan RAG Chatbot

A production-ready Retrieval-Augmented Generation (RAG) chatbot system for QuotePlan documentation.

## 📁 Project Structure

```
qdrant-rag/
├── frontend/          # Frontend files (HTML, CSS, JS)
├── backend/           # Backend Python scripts
├── data/              # Data files (chunks.json, .docx documents)
├── docs/              # Documentation
├── .env               # Environment variables (create this)
├── docker-compose.yml # Qdrant container configuration
└── requirements.txt   # Python dependencies
```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Qdrant:**
   ```bash
   docker-compose up -d
   ```

3. **Configure `.env` file** (create in root directory):
   ```bash
   OPENROUTER_API_KEY=your_key_here
   QDRANT_HOST=http://localhost:6333
   COLLECTION_NAME=quoteplan_chunks
   ```

4. **Extract and ingest data:**
   ```bash
   python backend/extract_chunks.py
   python backend/ingest_qdrant.py
   ```

5. **Start the server:**
   ```bash
   python backend/server.py
   ```

6. **Open browser:** http://localhost:8000

## 📚 Documentation

- **[Full Documentation](docs/README.md)** - Complete setup and usage guide
- **[Quick Start Guide](docs/README_RUN.md)** - Fast setup instructions
- **[Frontend Setup](docs/FRONTEND_SETUP.md)** - Frontend-specific details

## 🔧 Key Features

- Modern web-based chatbot interface
- Semantic search using Qdrant vector database
- AI-powered answers using OpenAI/OpenRouter
- Auto-ingestion watcher for document updates
- Responsive design for all devices

## 📝 Notes

- All frontend files are in `frontend/`
- All backend scripts are in `backend/`
- Data files (documents, chunks) are in `data/`
- Documentation is in `docs/`
- Configuration (`.env`, `docker-compose.yml`, `requirements.txt`) stays in root

## 🚀 Deployment on Render

### Prerequisites

1. **Qdrant Database**: You need a Qdrant instance running. Options:
   - Use Qdrant Cloud (https://cloud.qdrant.io/)
   - Deploy Qdrant separately on Render as a background service
   - Use a self-hosted Qdrant instance

2. **OpenRouter API Key**: Get your API key from https://openrouter.ai/

### Deployment Steps

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/your-repo-name.git
   git push -u origin main
   ```

2. **Create Render Account**: Sign up at https://render.com/

3. **Create New Web Service**:
   - Go to Render Dashboard → New → Web Service
   - Connect your GitHub repository
   - Use the following settings:
     - **Name**: qdrant-rag-chatbot (or your preferred name)
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --threads 4 --chdir backend app:app`
     - **Plan**: Starter (or higher)

4. **Configure Environment Variables** in Render Dashboard:
   - `OPENROUTER_API_KEY`: Your OpenRouter API key
   - `QDRANT_HOST`: Your Qdrant instance URL (e.g., `https://your-qdrant-instance.onrender.com`)
   - `COLLECTION_NAME`: `quoteplan_chunks` (or your collection name)
   - `PORT`: Automatically set by Render (don't change this)

5. **Deploy**: Click "Create Web Service" and wait for deployment

6. **Access Your App**: Once deployed, you'll get a URL like `https://your-app.onrender.com`

### Alternative: Using render.yaml

If you prefer using `render.yaml`:
1. Push your code with `render.yaml` to GitHub
2. In Render Dashboard, select "Apply render.yaml" when creating the service
3. Update the `QDRANT_HOST` value in `render.yaml` or set it as an environment variable

### Important Notes for Render Deployment

- **Qdrant Setup**: Qdrant must be deployed separately. You can:
  - Use Qdrant Cloud (recommended for production)
  - Deploy Qdrant on Render as a background service
  - Use docker-compose locally and expose via ngrok for testing

- **Data Ingestion**: Before deploying, make sure your Qdrant instance has the data ingested:
  ```bash
  python backend/extract_chunks.py
  python backend/ingest_qdrant.py
  ```
  Update `QDRANT_HOST` in your `.env` to point to your cloud Qdrant instance before running these commands.

- **Cold Starts**: Render free tier services spin down after inactivity. First request may take 30-60 seconds.

- **Memory**: Ensure your Render plan has enough memory for sentence-transformers model loading.

### Local Development vs Production

- **Local**: Uses `backend/server.py` (SimpleHTTPRequestHandler)
- **Production (Render)**: Uses `backend/app.py` (Flask + Gunicorn)

Both use the same `query_bot.py` logic, so functionality is identical.