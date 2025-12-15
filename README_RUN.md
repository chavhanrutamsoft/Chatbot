# 1. Start Qdrant
docker-compose up -d

# 2. Install deps
pip install -r requirements.txt

# 3. Put your Quote Plan Help Manual.docx in the folder

# 4. Extract chunks
python extract_chunks.py

# 5. Make sure .env contains OPENROUTER_API_KEY and QDRANT_HOST

# 6. Ingest chunks -> embeddings -> Qdrant
python ingest_qdrant.py

# 7. Query the chatbot
python query_bot.py --q "How do I create a Purchase Order?"
