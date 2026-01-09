# Render Error Fix - Step by Step

## Common Errors और Solutions:

### Error: "There's an error above. Please fix it to continue."

यह error usually इन reasons से आता है:

1. **Start Command में syntax error**
2. **Environment Variables में duplicate keys**
3. **Invalid characters in commands**
4. **Missing required fields**

## ✅ Complete Fix:

### Step 1: Render Dashboard में जाएं

### Step 2: Start Command को यह exact command use करें:

```bash
gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --threads 2 --chdir backend app:app
```

**Important:**
- Copy-paste करें (manually type न करें)
- सभी spaces check करें
- `$PORT` variable सही है (Render automatically set करता है)

### Step 3: Environment Variables Clean करें

**सभी environment variables DELETE करें** और फिर से add करें:

#### Step 3a: सभी variables delete करें
- हर variable के आगे "Delete" button click करें
- सभी को delete करें

#### Step 3b: नए variables add करें (एक-एक करके):

1. **OPENROUTER_API_KEY**
   - Key: `OPENROUTER_API_KEY`
   - Value: आपका OpenRouter API key

2. **QDRANT_HOST**
   - Key: `QDRANT_HOST`
   - Value: आपका Qdrant URL (e.g., `https://your-qdrant.onrender.com`)

3. **COLLECTION_NAME**
   - Key: `COLLECTION_NAME`
   - Value: `quoteplan_chunks`

4. (Optional) **OPENAI_API_KEY**
   - Key: `OPENAI_API_KEY`
   - Value: आपका OpenAI API key (अगर use करना है)

### Step 4: Build Command Check करें

Build Command होना चाहिए:
```bash
pip install -r requirements.txt
```

### Step 5: Other Settings:

- **Name**: `Chatbot` (या कोई भी name)
- **Language**: `Python 3`
- **Branch**: `main`
- **Region**: कोई भी (Oregon recommended)
- **Root Directory**: खाली छोड़ें
- **Instance Type**: `Free` select करें

### Step 6: Deploy

"Deploy web service" button click करें

## 🔍 अगर अभी भी Error आए:

### Check 1: Duplicate Variables
- कहीं duplicate `OPENROUTER_API_KEY` तो नहीं है?
- सभी variables unique होने चाहिए

### Check 2: Special Characters
- Environment variable values में special characters check करें
- Quotes use न करें values में

### Check 3: Empty Values
- कोई variable empty तो नहीं है?
- सभी required variables में values होनी चाहिए

### Check 4: Command Syntax
- Start Command में कोई typo तो नहीं?
- सभी dashes (`--`) सही हैं?

## 🚨 Alternative: Manual Setup (render.yaml के बिना)

अगर render.yaml से issue हो रहा है:

1. **render.yaml को ignore करें**
2. Render dashboard में manually सब कुछ fill करें:
   - Source: GitHub repo select करें
   - Name: Chatbot
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --threads 2 --chdir backend app:app`
   - Environment Variables: manually add करें (ऊपर list देखें)

## 📝 Exact Values Example:

### Start Command:
```
gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --threads 2 --chdir backend app:app
```

### Environment Variables (3 minimum):
```
OPENROUTER_API_KEY = sk-or-v1-your-key-here
QDRANT_HOST = https://your-qdrant-url.onrender.com
COLLECTION_NAME = quoteplan_chunks
```

## ✅ Final Checklist:

- [ ] Start Command exact copy-paste किया
- [ ] सभी old environment variables delete किए
- [ ] नए variables add किए (duplicate नहीं)
- [ ] Build Command: `pip install -r requirements.txt`
- [ ] Instance Type: Free selected
- [ ] Branch: main selected
- [ ] कोई empty variable नहीं है

इसके बाद deploy करें!
