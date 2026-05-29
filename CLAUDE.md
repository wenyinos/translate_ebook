# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
Ebook translation script that translates English technical documents to Simplified Chinese using OpenAI-compatible endpoints. Supports .docx and .epub formats.

## Quick Start
```bash
# Setup environment and run
./setup_venv.sh          # Create venv and install dependencies
source venv/bin/activate  # Activate virtual environment
nano config.env           # Configure API Key

# Run translation
./run.sh book.docx       # Quick run (auto-activates venv)
python translate.py book.docx  # Or run directly
```

## Usage
```bash
# Basic usage
python translate.py <input_file> [-o <output_path>]

# Examples
python translate.py book.docx
python translate.py book.epub -o translated_book.epub

# Resume interrupted translation
python translate.py book.docx --resume

# Custom configuration
python translate.py book.docx --api-key "your_key" --model "gpt-4o-mini"
```

## Configuration
1. Copy `config.env.example` to `config.env`
2. Fill in your API Key and settings
3. Or set via environment variables:
```bash
export OPENAI_API_KEY="your_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
export TRANSLATE_OUTPUT_DIR=~/translated_books
```

## Dependencies
```bash
# Install with requirements.txt
pip install -r requirements.txt

# Or install manually
pip install python-docx ebooklib beautifulsoup4 openai
```

## Architecture
- **translate.py**: CLI entry point, argument parsing and configuration
- **translator.py**: Core translation logic, API calls, batch processing, token stats, checkpoint saving
- **docx_handler.py**: DOCX file processing, preserves paragraph structure
- **epub_handler.py**: EPUB file processing, preserves HTML structure

## Tech Stack
- Python 3.8+
- python-docx: DOCX file handling
- ebooklib: EPUB file handling
- beautifulsoup4: HTML parsing
- openai: OpenAI API client

## Related Files
- `README.md`: English documentation
- `README_zh.md`: Chinese documentation
- `requirements.txt`: Python dependencies
- `setup_venv.sh`: Virtual environment setup script
- `run.sh`: Quick run script
- `config.env.example`: Configuration template
- `.gitignore`: Git ignore rules
