# Ebook Translator

Translate English technical documents to Simplified Chinese using OpenAI-compatible endpoints. Supports .docx and .epub formats.

## Features

- **DOCX Translation**: Preserve paragraph structure and inline formatting
- **EPUB Translation**: Maintain original HTML structure
- **Parallel Processing**: Multi-threaded translation for faster execution
- **Resume Support**: Continue from where you left off if interrupted
- **Token Statistics**: Track API usage and estimated costs

## Quick Start

### 1. Setup Environment
```bash
./setup_venv.sh
```

### 2. Configure API Key
Edit `config.env`:
```bash
nano config.env
```

Add your API credentials:
```
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### 3. Run Translation
```bash
# Using the shortcut script (auto-activates venv)
./run.sh book.docx

# Or manually activate and run
source venv/bin/activate
python translate.py book.docx
```

## Usage

### Basic Usage
```bash
python translate.py <input_file> [-o <output_path>]
```

### Examples
```bash
# Translate DOCX file
python translate.py document.docx

# Translate EPUB with custom output path
python translate.py book.epub -o translated_book.epub

# Resume interrupted translation
python translate.py book.docx --resume

# Use custom configuration
python translate.py document.docx \
    --api-key "your_key" \
    --model "gpt-4o" \
    --batch-size 100
```

### Command Line Options
| Parameter | Description | Default |
|-----------|-------------|---------|
| `input` | Input file path | Required |
| `-o, --output` | Output file path | Auto-generated |
| `--output-dir` | Output directory | `~/translated_books` |
| `--resume` | Resume from last checkpoint | `false` |
| `--api-key` | OpenAI API Key | From environment |
| `--base-url` | API base URL | `https://api.openai.com/v1` |
| `--model` | Model name | `gpt-4o-mini` |
| `--batch-size` | Batch size for translation | `50` |
| `--max-retries` | Maximum retry attempts | `3` |
| `--retry-delay` | Retry delay (seconds) | `1.0` |

## Configuration

### Environment Variables
```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
export TRANSLATE_BATCH_SIZE=50
export TRANSLATE_MAX_RETRIES=3
export TRANSLATE_RETRY_DELAY=1.0
export TRANSLATE_OUTPUT_DIR=~/translated_books
```

### Config File
Copy `config.env.example` to `config.env` and fill in your settings.

## Dependencies
- Python 3.8+
- python-docx: DOCX file handling
- ebooklib: EPUB file handling
- beautifulsoup4: HTML parsing
- openai: OpenAI API client

Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure
```
translate_ebook/
├── translate.py          # CLI entry point
├── translator.py         # Core translation logic
├── docx_handler.py       # DOCX file processing
├── epub_handler.py       # EPUB file processing
├── setup_venv.sh         # Virtual environment setup
├── run.sh                # Quick run script
├── requirements.txt      # Python dependencies
├── config.env            # Configuration (not in Git)
├── config.env.example    # Configuration template
├── CLAUDE.md             # Claude Code guidelines
├── README.md             # English documentation
└── README_zh.md          # Chinese documentation
```

## Notes
1. Ensure sufficient API quota
2. Large files may take a while to translate
3. Output is saved to `~/translated_books` by default
4. Technical terms are preserved or use common translations
5. Progress files (`.progress.json`) are created during translation and removed on completion
