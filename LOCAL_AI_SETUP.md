# Local AI Setup Guide for PC

This guide explains how to configure the scraper to work with local AI on PC computers.

## Configuration Options

The scraper supports both **cloud AI** (DeepSeek) and **local AI** (running on your PC). All AI configuration is in `config.yml`.

### Cloud AI (Default - DeepSeek)

```yaml
deepseek:
  api_key: "sk-your-deepseek-api-key"
  api_base: "https://api.deepseek.com"
  model: "deepseek-chat"
  chat_model: "deepseek-chat"
  temperature: 0.3
  max_tokens: 4000
```

### Local AI (PC)

For local AI running on your PC (e.g., LM Studio, Ollama, LocalAI):

```yaml
deepseek:
  api_key: "local-key"  # Can be any string for local AI
  api_base: "http://localhost:1234/v1"  # Your local AI endpoint
  model: "llama3"  # Or your local model name
  chat_model: "llama3"  # Alternative model name
  temperature: 0.3
  max_tokens: 4000
```

### Configuration Fields

- **api_key**: API key for authentication
  - Cloud: Your actual DeepSeek API key
  - Local: Any string (e.g., "local-key", "not-needed")

- **api_base**: Base URL for the AI API
  - Cloud: `https://api.deepseek.com`
  - Local: Your local endpoint (e.g., `http://localhost:1234/v1`)
  
- **model** / **chat_model**: Model name to use
  - Cloud: `deepseek-chat`
  - Local: Your model name (e.g., `llama3`, `mistral`, `qwen2`)
  - Note: Both `model` and `chat_model` are supported for compatibility

## Common Local AI Endpoints

### LM Studio
- Default: `http://localhost:1234/v1`
- Start LM Studio server and note the endpoint shown

### Ollama
- Default: `http://localhost:11434/v1` or `http://localhost:11434/api`
- Start with: `ollama serve`

### LocalAI
- Default: `http://localhost:8080/v1`
- Configure in LocalAI settings

### Text Generation WebUI (oobabooga)
- Default: `http://localhost:5000/v1`
- Enable OpenAI API extension

## Example Local Configurations

### Example 1: LM Studio with Llama 3
```yaml
deepseek:
  api_key: "not-needed"
  api_base: "http://localhost:1234/v1"
  model: "llama-3-8b-instruct"
  chat_model: "llama-3-8b-instruct"
  temperature: 0.3
  max_tokens: 4000
```

### Example 2: Ollama with Qwen2
```yaml
deepseek:
  api_key: "ollama"
  api_base: "http://localhost:11434/v1"
  model: "qwen2:7b"
  chat_model: "qwen2:7b"
  temperature: 0.3
  max_tokens: 4000
```

## How It Works

The scraper uses the **OpenAI Python client** with a custom `base_url` parameter:

```python
from openai import OpenAI

client = OpenAI(
    api_key=config['api_key'],
    base_url=config['api_base']  # Points to local or cloud endpoint
)
```

This approach works because:
1. Most local AI servers support OpenAI-compatible APIs
2. The OpenAI client can connect to any endpoint via `base_url`
3. The same code works for both cloud and local AI

## Files Modified for PC Compatibility

The following files have been updated to support local AI:

1. **config.yml** - Added `chat_model` field and comments
2. **utils/ai_categorizer.py** - Uses `base_url` for OpenAI client
3. **utils/detail_extractor.py** - Uses `base_url` for OpenAI client  
4. **utils/excel_formatter.py** - Uses `base_url` for OpenAI client

## Testing Your Local AI Setup

1. Start your local AI server (LM Studio, Ollama, etc.)
2. Update `config.yml` with your local settings
3. Run a test:

```bash
python main.py --start-date 2026-01-01 --end-date 2026-01-07 --quick
```

The `--quick` flag limits processing to 20 articles for faster testing.

## Troubleshooting

### Connection Errors
- Verify your local AI server is running
- Check the endpoint URL in `config.yml` matches your server
- Try `http://localhost` instead of `http://127.0.0.1` (or vice versa)

### Model Not Found
- Ensure the model name in `config.yml` matches your loaded model
- Check your local AI server's model list

### Slow Performance
- Local AI is slower than cloud API
- Consider using smaller models for faster processing
- Reduce `max_tokens` if responses are slow

### API Key Errors
- For local AI, the API key can be any string
- Some servers require "Bearer token" format - check your server docs

## Recommended Local Models

For Hong Kong property news (Chinese language):

1. **Qwen2** (7B or 14B) - Excellent Chinese support
2. **Llama 3** (8B) with Chinese fine-tune
3. **Yi** (6B or 34B) - Good Chinese performance
4. **ChatGLM** (6B) - Chinese-focused model

Make sure to use **instruction-tuned** or **chat** versions for best results.
