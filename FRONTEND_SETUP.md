# QuotePlan RAG Chatbot - Frontend Setup

A modern web-based chatbot interface for the QuotePlan RAG (Retrieval-Augmented Generation) system.

## Features

- 💬 Real-time chat interface
- 🎨 Modern, responsive UI design
- ⚡ Fast semantic search powered by Qdrant
- 🤖 AI-powered answers using free OpenRouter models
- 📱 Mobile-friendly design
- 🔄 Auto-scrolling chat messages
- ⌨️ Quick prompt buttons for common questions

## Files Created

- **index.html** - Main chatbot interface
- **style.css** - Modern styling with gradients and animations
- **script.js** - Frontend JavaScript (message handling, API calls)
- **api.php** - PHP backend API that calls Python query_bot.py

## Requirements

- PHP 7.2+ with shell_exec enabled
- Python environment set up (as per RAG system)
- Qdrant running (docker-compose up -d)
- Web server (Apache, Nginx, or PHP built-in server)

## Quick Start

### Option 1: Using PHP Built-in Server

```bash
cd d:\qdrant-rag
php -S localhost:8000
```

Then open your browser to: http://localhost:8000

### Option 2: Using Apache/Nginx

1. Copy all files to your web server's document root
2. Ensure the directory has proper permissions
3. Make sure `shell_exec()` is enabled in php.ini
4. Access via http://your-domain/

### Option 3: Using Windows IIS

1. Create a new website pointing to `d:\qdrant-rag`
2. Ensure IIS has permission to execute PHP
3. Enable CGI feature for PHP
4. Access via http://localhost/

## How It Works

1. **Frontend (index.html + script.js)**
   - User types a question
   - JavaScript sends it to the API via AJAX

2. **Backend (api.php)**
   - Receives the question
   - Calls Python script: `python query_bot.py --q "question"`
   - Parses the output and extracts the answer
   - Returns JSON response to frontend

3. **Python RAG System (query_bot.py)**
   - Embeds the question using local all-MiniLM-L6-v2 model
   - Searches Qdrant for relevant chunks
   - Sends context + question to free OpenRouter LLM
   - Returns formatted answer

## API Endpoint

**POST /api.php**

Request body:
```json
{
  "question": "How do I create a Purchase Order?"
}
```

Response:
```json
{
  "success": true,
  "question": "How do I create a Purchase Order?",
  "answer": "To create a Purchase Order in QuotePlan..."
}
```

## Troubleshooting

### Issue: "Failed to execute query bot"

**Solution:** 
- Verify `shell_exec()` is enabled in php.ini
- Check that Python is in your system PATH
- Run `python query_bot.py --q "test"` manually to verify it works
- Check file permissions in the `d:\qdrant-rag` directory

### Issue: No response from API

**Solution:**
- Check that Qdrant is running: `docker-compose ps`
- Verify `OPENROUTER_API_KEY` is set in `.env`
- Check PHP error logs for details
- Test the Python script directly: `python query_bot.py --q "test"`

### Issue: Slow responses

**Solution:**
- This is normal - the first request loads the embedding model (~5-10 seconds)
- Subsequent requests should be faster
- The LLM response time depends on OpenRouter's free tier load

## Customization

### Change Colors

Edit `style.css`:
```css
background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
```

### Add More Quick Prompts

Edit `index.html` in the `quick-prompts` section:
```html
<button class="quick-prompt" onclick="sendQuickPrompt('Your question here?')">
    Button Label
</button>
```

### Change Model

Edit `.env`:
```bash
CHAT_MODEL=mistralai/devstral-2512:free  # Change this
```

## Performance Notes

- First request: 5-15 seconds (loads embedding model)
- Subsequent requests: 2-5 seconds (API calls + LLM generation)
- Free tier may have rate limiting - spread requests over time

## Security Notes

⚠️ **Important for Production:**
- Add authentication to `api.php`
- Implement rate limiting
- Validate and sanitize all inputs
- Use HTTPS (especially with API key)
- Don't expose `.env` file
- Consider using an API gateway

## Support

For issues with:
- **Chatbot UI**: Check `script.js` and `style.css`
- **API calls**: Check `api.php` and web server logs
- **Python RAG**: Check `query_bot.py` and ensure Qdrant is running
- **OpenRouter**: Check your API key and free tier balance

## License

This project uses free OpenRouter models. Respect their terms of service.
