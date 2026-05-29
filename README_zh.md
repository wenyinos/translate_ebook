# 电子书翻译 CLI 工具

CLI 工具，使用 OpenAI 兼容 API 将英文技术文档 (.docx/.epub) 翻译为任意语言。

## 快速开始
```bash
./setup_venv.sh
source venv/bin/activate
nano config.env  # 设置 OPENAI_API_KEY
python translate.py book.docx
```

## 使用模式
```bash
# 基本用法
python translate.py <输入文件> [-o <输出路径>]

# 带参数
python translate.py <输入文件> [选项]
```

## 命令行参数
```
input               输入文件、目录或通配符模式（必需）
-o, --output        输出文件路径（不设置则自动生成）
--output-dir        输出目录（默认: ~/translated_books）
--resume            从上次中断处继续
--target-lang       目标语言代码（默认: zh）
                    支持: zh, en, ja, ko, fr, de, es, ru, pt, it
--api-key           单个 API Key
--api-keys          多个 API Key 逗号分隔（用于 429 轮换）
--base-url          API 基础 URL（默认: https://api.openai.com/v1）
--model             模型名称（默认: gpt-4o-mini）
--models            多个模型逗号分隔（用于轮换）
--batch-size        批量大小（默认: 50）
--max-retries       最大重试次数（默认: 3）
--retry-delay       重试延迟秒数（默认: 1.0）
--log               日志文件路径（可选）
```

## 配置文件 (config.env)
```bash
# 必需
OPENAI_API_KEY=your_api_key_here

# 可选 - API
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# 可选 - 多 Key 轮换（429 触发轮换）
OPENAI_API_KEYS=key1,key2,key3
OPENAI_MODELS=gpt-4o-mini,gpt-4o,gpt-3.5-turbo

# 可选 - 翻译设置
TRANSLATE_TARGET_LANG=zh
TRANSLATE_BATCH_SIZE=50
TRANSLATE_MAX_RETRIES=3
TRANSLATE_RETRY_DELAY=1.0
TRANSLATE_OUTPUT_DIR=~/translated_books
```

## 限流行为
- 正常请求间隔: 15-60 秒随机
- 429 Rate Limit: 切换到下一个 API Key，等待 60/120/180 秒（线性退避）
- 其他错误: 15 秒后重试

## 示例
```bash
# 翻译单个文件
python translate.py book.docx

# 翻译为日语
python translate.py book.docx --target-lang ja

# 使用多 API Key 翻译
python translate.py book.docx --api-keys "key1,key2,key3"

# 断点续传
python translate.py book.epub --resume

# 批量翻译目录中所有 docx
python translate.py /path/to/books/

# 使用通配符批量翻译
python translate.py "*.docx"

# 带日志翻译
python translate.py book.docx --log translate.log

# 支持的格式（自动转换为 EPUB）
python translate.py book.mobi
python translate.py book.azw3
python translate.py book.pdf
```

## 文件结构
- `translate.py` - CLI 入口，参数解析
- `translator.py` - 翻译核心逻辑，API 调用，Key 轮换，Token 统计
- `docx_handler.py` - DOCX 处理，保留格式
- `epub_handler.py` - EPUB 处理，保留 HTML 结构
- `converter.py` - 格式转换（MOBI/AZW3/PDF → EPUB）
- `config.env.example` - 配置文件模板
- `requirements.txt` - Python 依赖

## 依赖

### Python 包
```bash
pip install -r requirements.txt
```

### 系统包（格式转换需要）
```bash
# Fedora/RHEL
sudo dnf install calibre poppler-utils

# Ubuntu/Debian
sudo apt install calibre poppler-utils

# macOS
brew install calibre poppler
```
