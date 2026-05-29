# Ebook Translator CLI Tool

CLI tool for translating English technical documents (.docx/.epub) to any language using OpenAI-compatible API.

## Quick Start
```bash
./setup_venv.sh
source venv/bin/activate
nano config.env  # Set OPENAI_API_KEY
python translate.py book.docx
```

## Usage Pattern
```bash
# Basic
python translate.py <input_file> [-o <output_path>]

# With options
python translate.py <input_file> [OPTIONS]
```

## Command Line Arguments
```
input               Input file path (required)
-o, --output        Output file path (auto-generated if not set)
--output-dir        Output directory (default: ~/translated_books)
--resume            Resume from last checkpoint if interrupted
--target-lang       Target language code (default: zh)
                    Supported: zh, en, ja, ko, fr, de, es, ru, pt, it
--api-key           Single OpenAI API key
--api-keys          Multiple API keys comma-separated (for rate limit rotation)
--base-url          API base URL (default: https://api.openai.com/v1)
--model             Model name (default: gpt-4o-mini)
--models            Multiple models comma-separated (for rotation)
--batch-size        Batch size (default: 50)
--max-retries       Max retry attempts (default: 3)
--retry-delay       Retry delay seconds (default: 1.0)
```

## Configuration File (config.env)
```bash
# Required
OPENAI_API_KEY=your_api_key_here

# Optional - API
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Optional - Multi-key rotation (429 triggers rotation)
OPENAI_API_KEYS=key1,key2,key3
OPENAI_MODELS=gpt-4o-mini,gpt-4o,gpt-3.5-turbo

# Optional - Translation
TRANSLATE_TARGET_LANG=zh
TRANSLATE_BATCH_SIZE=50
TRANSLATE_MAX_RETRIES=3
TRANSLATE_RETRY_DELAY=1.0
TRANSLATE_OUTPUT_DIR=~/translated_books
```

## Rate Limiting Behavior
- Normal request interval: 15-60 seconds random
- 429 Rate Limit: rotate to next API key, wait 60/120/180 seconds (linear backoff)
- Other errors: retry after 15 seconds

## Examples
```bash
# Translate to Chinese (default)
python translate.py book.docx

# Translate to Japanese
python translate.py book.docx --target-lang ja

# Translate with multiple API keys
python translate.py book.docx --api-keys "key1,key2,key3"

# Resume interrupted translation
python translate.py book.epub --resume
```

## File Structure
- `translate.py` - CLI entry point, argument parsing
- `translator.py` - Core translation logic, API calls, key rotation, token stats
- `docx_handler.py` - DOCX processing, preserves formatting
- `epub_handler.py` - EPUB processing, preserves HTML structure
- `config.env.example` - Configuration template
- `requirements.txt` - Python dependencies

## Dependencies
python-docx, ebooklib, beautifulsoup4, openai
