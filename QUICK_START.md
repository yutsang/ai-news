# Quick Start Guide - PC Local AI Configuration

## For PC Users with Local AI

### Step 1: Configure Local AI in config.yml

Replace the `deepseek` section in `config.yml` with your local AI settings:

```yaml
deepseek:
  api_key: "local-key"
  api_base: "http://localhost:1234/v1"  # Your local AI endpoint
  model: "your-model-name"
  chat_model: "your-model-name"
  temperature: 0.3
  max_tokens: 4000
```

### Step 2: Common Local AI Endpoints

**LM Studio**:
```yaml
api_base: "http://localhost:1234/v1"
```

**Ollama**:
```yaml
api_base: "http://localhost:11434/v1"
```

**LocalAI**:
```yaml
api_base: "http://localhost:8080/v1"
```

### Step 3: Run the Scraper

```bash
# Quick test (20 articles only)
python main.py --start-date 2026-01-10 --end-date 2026-01-17 --quick

# Full run with date range
python main.py --start-date 2026-01-10 --end-date 2026-01-17

# Interactive mode (prompts for dates)
python main.py --interactive
```

## What's Been Fixed

✅ **Trans_Commercial Floor/Unit** - Now correctly parses 洋房 (house) properties  
✅ **News Deduplication** - Better AI-based deduplication, keeps 15-20 most relevant articles  
✅ **Midland ICI Dates** - All dates now in DD/MM/YYYY format  
✅ **PC Compatibility** - Full support for local AI servers

## Recommended Models for Chinese Content

1. **Qwen2** (7B/14B) - Best for Chinese
2. **Llama 3** (8B) - Good general purpose
3. **Yi** (6B/34B) - Strong Chinese support

## Example Local AI Setup (LM Studio)

1. Download and install LM Studio
2. Download a model (e.g., Qwen2-7B-Instruct)
3. Start the local server (it will show the endpoint)
4. Update config.yml:
   ```yaml
   deepseek:
     api_key: "lm-studio"
     api_base: "http://localhost:1234/v1"
     model: "qwen2-7b-instruct"
     chat_model: "qwen2-7b-instruct"
     temperature: 0.3
     max_tokens: 4000
   ```
5. Run: `python main.py --quick`

## Testing Your Setup

Run a quick test to verify everything works:

```bash
python main.py --start-date 2026-01-15 --end-date 2026-01-17 --quick
```

This will:
- Process only 20 articles (faster)
- Test AI categorization
- Test detail extraction
- Generate Excel output

Check the output Excel file in the `output/` folder.

## Troubleshooting

**"Connection refused"**:
- Make sure your local AI server is running
- Check the endpoint URL matches your server

**"Model not found"**:
- Verify the model name in config.yml matches your loaded model

**Slow performance**:
- Normal for local AI (much slower than cloud)
- Use smaller models (7B instead of 70B)
- Use `--quick` flag for testing

## Full Documentation

- **LOCAL_AI_SETUP.md** - Detailed local AI configuration guide
- **CHANGES_SUMMARY.md** - Complete list of all fixes and changes
- **README.md** - Original project documentation

## Need Help?

1. Check LOCAL_AI_SETUP.md for detailed configuration
2. Verify your local AI server is running
3. Test with --quick flag first
4. Check config.yml settings match your setup
