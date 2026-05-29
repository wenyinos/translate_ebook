#!/usr/bin/env python3
"""
电子书翻译脚本 - 使用 OpenAI 兼容端点
支持 .docx .epub .mobi .azw .azw3 .pdf 格式
"""

import glob
import logging
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List

import openai

from translator import TokenStats, KeyManager, SUPPORTED_LANGUAGES, DEFAULT_TARGET_LANG
from docx_handler import translate_docx
from epub_handler import translate_epub
from converter import convert_to_epub, CONVERTIBLE_FORMATS


DEFAULT_CONFIG = {
    "api_key": os.environ.get("OPENAI_API_KEY", ""),
    "api_keys": os.environ.get("OPENAI_API_KEYS", ""),
    "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    "models": os.environ.get("OPENAI_MODELS", ""),
    "target_lang": os.environ.get("TRANSLATE_TARGET_LANG", DEFAULT_TARGET_LANG),
    "batch_size": int(os.environ.get("TRANSLATE_BATCH_SIZE", "50")),
    "max_retries": int(os.environ.get("TRANSLATE_MAX_RETRIES", "3")),
    "retry_delay": float(os.environ.get("TRANSLATE_RETRY_DELAY", "1.0")),
    "output_dir": os.environ.get("TRANSLATE_OUTPUT_DIR", str(Path.home() / "translated_books")),
}

SUPPORTED_EXTENSIONS = {'.docx', '.epub'} | CONVERTIBLE_FORMATS

logger = logging.getLogger(__name__)


def setup_logging(log_file: str = None):
    """配置日志系统"""
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )


def collect_input_files(input_path: str) -> List[str]:
    """收集输入文件（支持通配符、目录、单文件）"""
    input_path = os.path.abspath(input_path)

    # 单个文件
    if os.path.isfile(input_path):
        ext = Path(input_path).suffix.lower()
        if ext in SUPPORTED_EXTENSIONS:
            return [input_path]
        else:
            logger.warning(f"Unsupported format: {ext} - {input_path}")
            return []

    # 目录
    if os.path.isdir(input_path):
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(glob.glob(os.path.join(input_path, f"*{ext}")))
        return sorted(files)

    # 通配符
    files = glob.glob(input_path)
    return [f for f in files if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS]


def translate_single_file(input_path: str, output_path: str, client,
                          config: dict, key_manager: KeyManager,
                          token_stats: TokenStats, args) -> bool:
    """翻译单个文件"""
    file_ext = Path(input_path).suffix.lower()
    temp_epub = None

    try:
        # 需要转换的格式
        if file_ext in CONVERTIBLE_FORMATS:
            logger.info(f"Converting {file_ext} to EPUB...")
            temp_epub = str(Path(output_path).with_suffix('.epub'))
            convert_to_epub(input_path, temp_epub)
            input_path = temp_epub
            file_ext = '.epub'
            logger.info(f"Conversion complete: {temp_epub}")

        if file_ext == '.docx':
            translate_docx(
                input_path, output_path, client,
                config["model"], config["batch_size"],
                resume=args.resume, token_stats=token_stats,
                target_lang=config["target_lang"],
                key_manager=key_manager
            )
        elif file_ext == '.epub':
            translate_epub(
                input_path, output_path, client,
                config["model"], config["batch_size"],
                resume=args.resume, token_stats=token_stats,
                target_lang=config["target_lang"],
                key_manager=key_manager
            )
        else:
            logger.error(f"Unsupported file format: {file_ext}")
            return False

        return True

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return False

    finally:
        # 清理临时文件
        if temp_epub and os.path.exists(temp_epub):
            os.remove(temp_epub)


def main():
    parser = argparse.ArgumentParser(description='Ebook Translator - OpenAI Compatible')
    parser.add_argument('input', help='Input file, directory, or glob pattern')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--output-dir', help='Output directory (default: ~/translated_books)')
    parser.add_argument('--api-key', help='OpenAI API Key')
    parser.add_argument('--api-keys', help='Multiple API keys (comma separated)')
    parser.add_argument('--base-url', help='OpenAI API Base URL')
    parser.add_argument('--model', help='Model name')
    parser.add_argument('--models', help='Multiple models (comma separated)')
    parser.add_argument('--batch-size', type=int, help='Batch size')
    parser.add_argument('--max-retries', type=int, help='Max retry attempts')
    parser.add_argument('--retry-delay', type=float, help='Retry delay (seconds)')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--target-lang', default=DEFAULT_TARGET_LANG,
                        choices=list(SUPPORTED_LANGUAGES.keys()),
                        help=f'Target language (default: {DEFAULT_TARGET_LANG})')
    parser.add_argument('--log', help='Log file path')

    args = parser.parse_args()

    # 配置日志
    setup_logging(args.log)
    logger.info(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    config = DEFAULT_CONFIG.copy()
    if args.api_key:
        config["api_key"] = args.api_key
    if args.api_keys:
        config["api_keys"] = args.api_keys
    if args.base_url:
        config["base_url"] = args.base_url
    if args.model:
        config["model"] = args.model
    if args.models:
        config["models"] = args.models
    if args.batch_size:
        config["batch_size"] = args.batch_size
    if args.max_retries:
        config["max_retries"] = args.max_retries
    if args.retry_delay:
        config["retry_delay"] = args.retry_delay
    if args.output_dir:
        config["output_dir"] = args.output_dir
    if args.target_lang != DEFAULT_TARGET_LANG:
        config["target_lang"] = args.target_lang

    # 解析多 key 和模型列表
    api_keys = [k.strip() for k in config["api_keys"].split(",") if k.strip()] if config["api_keys"] else []
    models = [m.strip() for m in config["models"].split(",") if m.strip()] if config["models"] else []

    if not api_keys and config["api_key"]:
        api_keys = [config["api_key"]]
    if not models and config["model"]:
        models = [config["model"]]

    if not api_keys:
        logger.error("Please set OPENAI_API_KEY or --api-key / --api-keys")
        sys.exit(1)

    # 收集输入文件
    input_files = collect_input_files(args.input)
    if not input_files:
        logger.error(f"No supported files found: {args.input}")
        sys.exit(1)

    logger.info(f"Found {len(input_files)} file(s) to translate")

    # 创建 KeyManager
    key_manager = KeyManager(api_keys, models, config["base_url"])
    client = openai.OpenAI(api_key=api_keys[0], base_url=config["base_url"])
    token_stats = TokenStats()

    lang_name = SUPPORTED_LANGUAGES.get(config["target_lang"], config["target_lang"])
    logger.info(f"Target language: {lang_name}")
    logger.info(f"API keys: {key_manager.key_count} | Models: {key_manager.model_count}")

    # 翻译文件
    success_count = 0
    fail_count = 0

    for i, input_path in enumerate(input_files, 1):
        logger.info(f"[{i}/{len(input_files)}] Processing: {Path(input_path).name}")

        # 确定输出路径
        if args.output and len(input_files) == 1:
            output_path = args.output
        else:
            input_name = Path(input_path).name
            output_path = str(Path(config["output_dir"]) / input_name)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if translate_single_file(input_path, output_path, client, config,
                                 key_manager, token_stats, args):
            success_count += 1
            logger.info(f"Complete: {output_path}")
        else:
            fail_count += 1

    # 显示统计
    logger.info(f"\n{'='*50}")
    logger.info(f"Total: {len(input_files)} | Success: {success_count} | Failed: {fail_count}")
    logger.info(f"{token_stats.summary()}")
    logger.info(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
