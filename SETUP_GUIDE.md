# Setup Guide - Mac vs Windows Configuration

This scraper is designed to work on both Mac and Windows with different AI configurations.

## 🍎 Mac Setup (DeepSeek Cloud API)

### Step 1: Get DeepSeek API Key
1. Visit https://platform.deepseek.com
2. Sign up / log in
3. Generate an API key

### Step 2: Update config.yml

Use the Mac example configuration:

```bash
# Copy the Mac example
cp config.yml.mac_example config.yml
```

Then edit `config.yml` and replace the API key:

```yaml
deepseek:
  api_key: "sk-YOUR-ACTUAL-KEY-HERE"  # ← Replace this
  api_base: "https://api.deepseek.com"
  model: "deepseek-chat"
  chat_model: "deepseek-chat"
  temperature: 0.3
  max_tokens: 4000
```

### Step 3: Test Connection

```bash
python test_ai_connection.py
```

If successful, run the scraper:

```bash
python main.py --quick  # Quick test with 20 articles
python main.py          # Full run
```

---

## 🪟 Windows Setup (Local AI)

### Step 1: Install Local AI Server

Choose one:

**Option A: LM Studio** (Recommended - easiest)
1. Download from https://lmstudio.ai/
2. Install and open LM Studio
3. Download a model (recommended: Qwen2-7B-Instruct or Llama-3-8B-Instruct)
4. Click "Local Server" tab
5. Click "Start Server" (it will show the endpoint, usually `http://localhost:1234/v1`)

**Option B: Ollama**
1. Download from https://ollama.ai/
2. Install and run: `ollama serve`
3. Pull a model: `ollama pull qwen2:7b`
4. Default endpoint: `http://localhost:11434/v1`

### Step 2: Update config.yml

Use the Windows example configuration:

```bash
# Copy the Windows example
copy config.yml.windows_example config.yml
```

Then edit `config.yml` to match your setup:

**For LM Studio:**
```yaml
deepseek:
  api_key: "local-key"
  api_base: "http://localhost:1234/v1"
  model: "qwen2-7b-instruct"  # ← Your model name from LM Studio
  chat_model: "qwen2-7b-instruct"
  temperature: 0.3
  max_tokens: 4000
```

**For Ollama:**
```yaml
deepseek:
  api_key: "local-key"
  api_base: "http://localhost:11434/v1"
  model: "qwen2:7b"  # ← Your model name from Ollama
  chat_model: "qwen2:7b"
  temperature: 0.3
  max_tokens: 4000
```

### Step 3: Test Connection

```bash
python test_ai_connection.py
```

If successful, run the scraper:

```bash
python main.py --quick  # Quick test with 20 articles
python main.py          # Full run
```

---

## 🔧 Current Issue (Your Mac)

Your current `config.yml` has an **invalid API key**:
```yaml
api_key: "sk-sk-44bd1f1e05224223bb83f011c5f2b72e"  # ❌ INVALID
```

### Quick Fix for Mac:

1. Get a new API key from https://platform.deepseek.com
2. Update `config.yml` line 7 with the new key
3. Run `python test_ai_connection.py` to verify
4. Run `python main.py` once verified

---

## 📊 Testing Your Setup

Always test your AI connection first:

```bash
python test_ai_connection.py
```

This will:
- ✅ Show your current configuration
- ✅ Test the AI connection
- ✅ Verify the API key works
- ✅ Show if you're using cloud or local AI

---

## 🚀 Quick Start

### Mac (Cloud):
```bash
# 1. Update API key in config.yml
# 2. Test connection
python test_ai_connection.py

# 3. Run scraper
python main.py --quick
```

### Windows (Local AI):
```bash
# 1. Start your local AI server (LM Studio / Ollama)
# 2. Update config.yml with local endpoint
# 3. Test connection
python test_ai_connection.py

# 4. Run scraper
python main.py --quick
```

---

## 📁 Example Config Files

- `config.yml.mac_example` - For Mac with DeepSeek cloud
- `config.yml.windows_example` - For Windows with local AI
- `config_local_ai_example.yml` - Another local AI example

Copy the appropriate one to `config.yml` and customize.

---

## ✅ What Got Fixed

All 4 issues have been resolved:

1. ✅ **Trans_Commercial floor/unit for 洋房** - Now parses correctly
2. ✅ **News deduplication** - Better AI-based deduplication
3. ✅ **Midland ICI dates** - Now in DD/MM/YYYY format
4. ✅ **PC compatibility** - Full local AI support with OpenAI base_url

The code works on both Mac and Windows - just use the right config!

---

## 📚 Full Documentation

- **QUICK_START.md** - Quick reference for PC/local AI
- **LOCAL_AI_SETUP.md** - Detailed local AI configuration
- **CHANGES_SUMMARY.md** - All fixes applied
- **SETUP_GUIDE.md** - This file (Mac vs Windows)

---

## ❓ Need Help?

**Mac users**: Just update the API key in config.yml
**Windows users**: Install LM Studio or Ollama first, then update config.yml

**Test first**: Always run `python test_ai_connection.py` before the main scraper!
