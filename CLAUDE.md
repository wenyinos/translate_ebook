# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述
电子书翻译脚本，使用 OpenAI 兼容端点将英文技术文档翻译为简体中文。支持 .docx 和 .epub 格式。

## 快速开始
```bash
# 一键设置环境并运行
./setup_venv.sh          # 创建虚拟环境并安装依赖
source venv/bin/activate  # 激活虚拟环境
nano config.env           # 配置 API Key

# 运行翻译
./run.sh book.docx       # 快捷运行（自动激活虚拟环境）
python translate.py book.docx  # 或直接运行
```

## 使用方法
```bash
# 基本用法
python translate.py <input_file> [-o <output_path>]

# 示例
python translate.py book.docx
python translate.py book.epub -o translated_book.epub

# 使用自定义配置
python translate.py book.docx --api-key "your_key" --model "gpt-4o-mini"
```

## 配置
1. 复制 `config.env.example` 为 `config.env`
2. 填入实际的 API Key 和配置
3. 或通过环境变量设置：
```bash
export OPENAI_API_KEY="your_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
export TRANSLATE_OUTPUT_DIR=~/translated_books
```

## 依赖
```bash
# 使用 requirements.txt 安装
pip install -r requirements.txt

# 或手动安装
pip install python-docx ebooklib beautifulsoup4 openai
```

## 架构说明
- **translate_text()**: 核心翻译函数，调用 OpenAI API
- **translate_batch()**: 并行批量翻译，使用线程池
- **translate_docx()**: DOCX 文件处理，保持段落结构
- **translate_epub()**: EPUB 文件处理，保持 HTML 结构
- **main()**: 命令行入口，参数解析和配置管理

## 技术栈
- Python 3.8+
- python-docx: DOCX 文件处理
- ebooklib: EPUB 文件处理
- beautifulsoup4: HTML 解析
- openai: OpenAI API 客户端

## 相关文件
- `README.md`: 详细的使用说明和文档
- `requirements.txt`: Python 依赖列表
- `setup_venv.sh`: 虚拟环境设置脚本
- `run.sh`: 快捷运行脚本
- `config.env.example`: 配置文件示例
- `.gitignore`: Git 忽略文件配置
