#!/usr/bin/env python3
"""
电子书翻译脚本 - 使用 OpenAI 兼容端点
支持 .docx 和 .epub 格式
"""

import os
import sys
import argparse
from pathlib import Path

import openai

from translator import TokenStats, KeyManager, SUPPORTED_LANGUAGES, DEFAULT_TARGET_LANG
from docx_handler import translate_docx
from epub_handler import translate_epub


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


def main():
    parser = argparse.ArgumentParser(description='电子书翻译脚本 - 使用 OpenAI 兼容端点')
    parser.add_argument('input', help='输入文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('--output-dir', help='输出目录（默认: ~/translated_books）')
    parser.add_argument('--api-key', help='OpenAI API Key')
    parser.add_argument('--api-keys', help='Multiple API keys (comma separated)')
    parser.add_argument('--base-url', help='OpenAI API Base URL')
    parser.add_argument('--model', help='Model name')
    parser.add_argument('--models', help='Multiple models (comma separated)')
    parser.add_argument('--batch-size', type=int, help='批量翻译大小')
    parser.add_argument('--max-retries', type=int, help='最大重试次数')
    parser.add_argument('--retry-delay', type=float, help='重试延迟（秒）')
    parser.add_argument('--resume', action='store_true', help='从上次中断处继续翻译')
    parser.add_argument('--target-lang', default=DEFAULT_TARGET_LANG,
                        choices=list(SUPPORTED_LANGUAGES.keys()),
                        help=f'目标语言 (默认: {DEFAULT_TARGET_LANG})')

    args = parser.parse_args()

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

    # 如果没有多 key，使用单个 key
    if not api_keys and config["api_key"]:
        api_keys = [config["api_key"]]

    # 如果没有多模型，使用单个模型
    if not models and config["model"]:
        models = [config["model"]]

    if not api_keys:
        print("Error: Please set OPENAI_API_KEY or --api-key / --api-keys")
        sys.exit(1)

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        input_name = Path(input_path).name
        output_path = str(Path(config["output_dir"]) / input_name)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 创建 KeyManager（支持多 key 轮换）
    key_manager = KeyManager(api_keys, models, config["base_url"])

    # 创建默认客户端（兼容单 key 模式）
    client = openai.OpenAI(
        api_key=api_keys[0],
        base_url=config["base_url"]
    )

    # 创建 token 统计器
    token_stats = TokenStats()

    file_ext = Path(input_path).suffix.lower()

    lang_name = SUPPORTED_LANGUAGES.get(config["target_lang"], config["target_lang"])
    print(f"Target language: {lang_name}")
    print(f"API keys: {key_manager.key_count} | Models: {key_manager.model_count}")

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
        print(f"错误: 不支持的文件格式: {file_ext}")
        sys.exit(1)

    # 显示 token 统计
    print(f"\n{token_stats.summary()}")
    print(f"翻译完成!")


if __name__ == "__main__":
    main()
