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

from translator import TokenStats, KeyManager, TranslationCache, SUPPORTED_LANGUAGES, DEFAULT_TARGET_LANG
from docx_handler import translate_docx
from epub_handler import translate_epub
from converter import convert_to_epub, CONVERTIBLE_FORMATS


def load_env_file(env_path: str = None):
    """加载 .env 配置文件"""
    if env_path is None:
        # 查找当前目录下的 config.env
        env_path = Path(__file__).parent / "config.env"

    if not Path(env_path).exists():
        return

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            # 解析 KEY=VALUE
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                # 移除引号
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                # 展开 ~ 为实际路径
                value = os.path.expanduser(value)
                # 设置环境变量（不覆盖已存在的）
                if key not in os.environ:
                    os.environ[key] = value


# 加载配置文件
load_env_file()


def collect_api_keys() -> List[str]:
    """收集所有 API Key（支持单个和多个独立变量）"""
    keys = []
    # 收集 OPENAI_API_KEY_1, OPENAI_API_KEY_2, ... 格式
    for i in range(1, 100):
        key = os.environ.get(f"OPENAI_API_KEY_{i}", "")
        if key:
            keys.append(key)
    # 如果没有找到编号 key，尝试 OPENAI_API_KEY
    if not keys:
        key = os.environ.get("OPENAI_API_KEY", "")
        if key:
            keys.append(key)
    # 尝试逗号分隔的 OPENAI_API_KEYS
    if not keys:
        keys_str = os.environ.get("OPENAI_API_KEYS", "")
        if keys_str:
            keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    return keys


DEFAULT_CONFIG = {
    "api_keys_list": collect_api_keys(),
    "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    "models": os.environ.get("OPENAI_MODELS", ""),
    "target_lang": os.environ.get("TRANSLATE_TARGET_LANG", DEFAULT_TARGET_LANG),
    "batch_size": int(os.environ.get("TRANSLATE_BATCH_SIZE", "50")),
    "max_retries": int(os.environ.get("TRANSLATE_MAX_RETRIES", "3")),
    "retry_delay": float(os.environ.get("TRANSLATE_RETRY_DELAY", "1.0")),
    "output_dir": os.environ.get("TRANSLATE_OUTPUT_DIR", str(Path(__file__).parent / "translated_books")),
    "max_tokens": int(os.environ.get("TRANSLATE_MAX_TOKENS", "128000")),
}

SUPPORTED_EXTENSIONS = {'.docx', '.epub'} | CONVERTIBLE_FORMATS

logger = logging.getLogger(__name__)


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def validate_config(config: dict) -> bool:
    """验证配置"""
    errors = []

    # 验证 API Key
    api_keys_list = config.get("api_keys_list", [])
    if not api_keys_list:
        errors.append("OPENAI_API_KEY_1 or --api-key required")

    # 验证 base_url
    base_url = config.get("base_url", "")
    if base_url and not base_url.startswith(("http://", "https://")):
        errors.append(f"Invalid base URL: {base_url}")

    # 验证 model
    model = config.get("model", "")
    if not model:
        errors.append("Model name required")

    # 验证 target_lang
    target_lang = config.get("target_lang", DEFAULT_TARGET_LANG)
    if target_lang not in SUPPORTED_LANGUAGES:
        errors.append(f"Unsupported language: {target_lang}")

    # 验证数值参数
    batch_size = config.get("batch_size", 50)
    if batch_size < 1 or batch_size > 1000:
        errors.append(f"Invalid batch size: {batch_size}")

    max_retries = config.get("max_retries", 3)
    if max_retries < 1 or max_retries > 10:
        errors.append(f"Invalid max retries: {max_retries}")

    if errors:
        for error in errors:
            logger.error(f"Config error: {error}")
        return False

    return True


def setup_logging(log_file: str = None, debug: bool = False):
    """配置日志系统"""
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
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
                          token_stats: TokenStats, args,
                          cache: TranslationCache = None) -> bool:
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
                max_tokens=config["max_tokens"],
                key_manager=key_manager, cache=cache
            )
        elif file_ext == '.epub':
            translate_epub(
                input_path, output_path, client,
                config["model"], config["batch_size"],
                resume=args.resume, token_stats=token_stats,
                target_lang=config["target_lang"],
                max_tokens=config["max_tokens"],
                key_manager=key_manager, cache=cache
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
    parser.add_argument('--max-tokens', type=int, help='Max tokens for API response')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--target-lang', default=DEFAULT_TARGET_LANG,
                        choices=list(SUPPORTED_LANGUAGES.keys()),
                        help=f'Target language (default: {DEFAULT_TARGET_LANG})')
    parser.add_argument('--log', help='Log file path')
    parser.add_argument('--debug', action='store_true', help='Enable DEBUG logging')
    parser.add_argument('--cache', help='Translation cache file path')

    args = parser.parse_args()

    # 配置日志
    setup_logging(args.log, args.debug)
    logger.info(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    config = DEFAULT_CONFIG.copy()
    # 命令行 --api-key 添加到列表开头
    if args.api_key:
        config["api_keys_list"] = [args.api_key] + config["api_keys_list"]
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
    if args.max_tokens:
        config["max_tokens"] = args.max_tokens
    if args.output_dir:
        config["output_dir"] = args.output_dir
    if args.target_lang != DEFAULT_TARGET_LANG:
        config["target_lang"] = args.target_lang

    # 使用 collect_api_keys() 已收集的 keys
    api_keys = config["api_keys_list"]
    models = [m.strip() for m in config["models"].split(",") if m.strip()] if config["models"] else []
    if not models and config["model"]:
        models = [config["model"]]

    # 验证配置
    config["models_list"] = models
    if not validate_config(config):
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

    # 创建翻译缓存
    cache = TranslationCache(args.cache) if args.cache else None
    if cache:
        logger.info(f"Translation cache: {cache.size} entries")

    lang_name = SUPPORTED_LANGUAGES.get(config["target_lang"], config["target_lang"])
    logger.info(f"Target language: {lang_name}")
    logger.info(f"API keys: {key_manager.key_count} | Models: {key_manager.model_count}")

    # 翻译文件
    success_count = 0
    fail_count = 0
    start_time = datetime.now()

    for i, input_path in enumerate(input_files, 1):
        file_start_time = datetime.now()
        elapsed_total = (file_start_time - start_time).total_seconds()
        logger.info(f"\n{'='*50}")
        logger.info(f"[{i}/{len(input_files)}] Processing: {Path(input_path).name}")
        logger.info(f"Elapsed: {format_time(elapsed_total)} | Remaining files: {len(input_files) - i}")

        # 确定输出路径（按语言分目录）
        if args.output and len(input_files) == 1:
            output_path = args.output
        else:
            input_name = Path(input_path).name
            lang_dir = Path(config["output_dir"]) / config["target_lang"]
            output_path = str(lang_dir / input_name)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if translate_single_file(input_path, output_path, client, config,
                                 key_manager, token_stats, args, cache):
            success_count += 1
            file_elapsed = (datetime.now() - file_start_time).total_seconds()
            logger.info(f"Complete: {output_path} ({format_time(file_elapsed)})")
        else:
            fail_count += 1

    # 保存缓存
    if cache:
        cache.save()

    # 显示统计
    end_time = datetime.now()
    total_elapsed = (end_time - start_time).total_seconds()
    logger.info(f"\n{'='*50}")
    logger.info(f"Total: {len(input_files)} | Success: {success_count} | Failed: {fail_count}")
    logger.info(f"Total time: {format_time(total_elapsed)}")
    if cache:
        logger.info(f"Cache: {cache.size} translations")
    logger.info(f"{token_stats.summary()}")
    logger.info(f"End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
