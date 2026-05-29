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
input               Input file, directory, or glob pattern (required)
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
--log               Log file path (optional)
--debug             Enable DEBUG logging (verbose output)
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
# Translate single file
python translate.py book.docx

# Translate to Japanese
python translate.py book.docx --target-lang ja

# Translate with multiple API keys
python translate.py book.docx --api-keys "key1,key2,key3"

# Resume interrupted translation
python translate.py book.epub --resume

# Batch translate all docx in directory
python translate.py /path/to/books/

# Batch translate with glob pattern
python translate.py "*.docx"

# Translate with logging
python translate.py book.docx --log translate.log

# Supported formats (auto-converted to EPUB)
python translate.py book.mobi
python translate.py book.azw3
python translate.py book.pdf
```

## File Structure
- `translate.py` - CLI entry point, argument parsing
- `translator.py` - Core translation logic, API calls, key rotation, token stats
- `docx_handler.py` - DOCX processing, preserves formatting
- `epub_handler.py` - EPUB processing, preserves HTML structure
- `converter.py` - Format conversion (MOBI/AZW3/PDF → EPUB)
- `config.env.example` - Configuration template
- `requirements.txt` - Python dependencies

## Dependencies

### Python version
- Python 3.8+

### Python packages (requirements.txt)
```
python-docx>=0.8.11    # DOCX file handling
ebooklib>=0.17.1       # EPUB file handling
beautifulsoup4>=4.11.0 # HTML parsing for EPUB
openai>=1.0.0          # OpenAI API client
```

Install: `pip install -r requirements.txt`

### System packages (required for format conversion)
| Package | Purpose | Install |
|---------|---------|---------|
| calibre | MOBI/AZW3/PDF → EPUB conversion | `sudo dnf install calibre` |
| poppler-utils | PDF text extraction (pdftotext) | `sudo dnf install poppler-utils` |

```bash
# Fedora/RHEL
sudo dnf install calibre poppler-utils

# Ubuntu/Debian
sudo apt install calibre poppler-utils

# macOS
brew install calibre poppler

# Windows
# Download calibre: https://calibre-ebook.com/download_windows
# Download poppler: https://github.com/oschwartz10612/poppler-windows/releases
# Add both to PATH after installation
```

### Dependency check
```python
# In code
from converter import check_calibre, check_pdftotext
print(f"calibre: {check_calibre()}")
print(f"pdftotext: {check_pdftotext()}")
```

### Format support matrix
| Format | Direct support | Requires |
|--------|---------------|----------|
| .docx | Yes | python-docx |
| .epub | Yes | ebooklib, beautifulsoup4 |
| .mobi | No → EPUB | calibre |
| .azw/.azw3 | No → EPUB | calibre |
| .pdf | No → EPUB | calibre, poppler-utils |
