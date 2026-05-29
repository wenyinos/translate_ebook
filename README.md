# 电子书翻译脚本

使用 OpenAI 兼容端点将英文技术文档翻译为简体中文。支持 .docx 和 .epub 格式。

## 快速开始

### 1. 一键设置环境
```bash
./setup_venv.sh
```

### 2. 配置 API Key
编辑 `config.env` 文件：
```bash
nano config.env
```

填入你的 API Key：
```
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### 3. 运行翻译
```bash
# 使用快捷脚本（自动激活虚拟环境）
./run.sh book.docx

# 或手动激活虚拟环境后运行
source venv/bin/activate
python translate.py book.docx
```

## 使用方法

### 基本用法
```bash
python translate.py <输入文件> [-o <输出路径>]
```

### 示例
```bash
# 翻译 DOCX 文件
python translate.py document.docx

# 翻译 EPUB 文件并指定输出路径
python translate.py book.epub -o translated_book.epub

# 使用自定义配置
python translate.py document.docx \
    --api-key "your_key" \
    --model "gpt-4o" \
    --batch-size 100
```

### 命令行参数
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | 输入文件路径 | 必需 |
| `-o, --output` | 输出文件路径 | 自动生成 |
| `--output-dir` | 输出目录 | `~/translated_books` |
| `--api-key` | OpenAI API Key | 从环境变量读取 |
| `--base-url` | API 基础 URL | `https://api.openai.com/v1` |
| `--model` | 模型名称 | `gpt-4o-mini` |
| `--batch-size` | 批量翻译大小 | `50` |
| `--max-retries` | 最大重试次数 | `3` |
| `--retry-delay` | 重试延迟（秒） | `1.0` |

## 配置说明

### 环境变量
```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
export TRANSLATE_BATCH_SIZE=50
export TRANSLATE_MAX_RETRIES=3
export TRANSLATE_RETRY_DELAY=1.0
export TRANSLATE_OUTPUT_DIR=~/translated_books
```

### 配置文件
复制 `config.env.example` 为 `config.env` 并填入实际配置。

## 依赖
- Python 3.8+
- python-docx: DOCX 文件处理
- ebooklib: EPUB 文件处理
- beautifulsoup4: HTML 解析
- openai: OpenAI API 客户端

安装依赖：
```bash
pip install -r requirements.txt
```

## 项目结构
```
translate_ebook/
├── translate.py          # 主程序
├── setup_venv.sh         # 虚拟环境设置脚本
├── run.sh               # 快捷运行脚本
├── requirements.txt     # Python 依赖
├── config.env          # 配置文件（不提交到 Git）
├── config.env.example  # 配置文件示例
└── CLAUDE.md           # Claude Code 指南
```

## 注意事项
1. 确保有足够的 API 额度
2. 大文件翻译可能需要较长时间
3. 翻译结果保存在 `~/MyWork/Books/chinese/` 目录下
4. 技术术语会尽量保留原文或使用通用译法
