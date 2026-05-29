"""格式转换模块 - MOBI/AZW3/PDF 转 EPUB"""

import logging
import os
import platform
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


# 支持转换的格式
CONVERTIBLE_FORMATS = {'.mobi', '.azw', '.azw3', '.pdf'}

# 获取系统信息
IS_WINDOWS = platform.system() == 'Windows'


def check_calibre() -> bool:
    """检查 calibre 是否安装"""
    try:
        result = subprocess.run(['ebook-convert', '--version'],
                                capture_output=True, timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_pdftotext() -> bool:
    """检查 pdftotext 是否安装"""
    try:
        result = subprocess.run(['pdftotext', '-v'],
                                capture_output=True, timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_install_instructions() -> str:
    """获取安装说明"""
    if IS_WINDOWS:
        return (
            "Windows: Download calibre from https://calibre-ebook.com/download_windows\n"
            "         Download poppler from https://github.com/oschwartz10612/poppler-windows/releases\n"
            "         Add both to PATH after installation."
        )
    else:
        return (
            "Linux/macOS: sudo dnf install calibre poppler-utils\n"
            "             or: sudo apt install calibre poppler-utils\n"
            "             or: brew install calibre poppler"
        )


def is_scanned_pdf(pdf_path: str) -> bool:
    """检测 PDF 是否为扫描版（无文本层）"""
    if not check_pdftotext():
        # 无法检测，假定不是扫描版
        return False

    try:
        result = subprocess.run(
            ['pdftotext', pdf_path, '-'],
            capture_output=True, text=True, timeout=30
        )
        text = result.stdout.strip()
        # 如果提取的文本很少（少于 50 个字符），可能是扫描版
        return len(text) < 50
    except (subprocess.TimeoutExpired, Exception):
        return False


def convert_to_epub(input_path: str, output_path: str = None) -> str:
    """
    将 MOBI/AZW3/PDF 转换为 EPUB

    Args:
        input_path: 输入文件路径
        output_path: 输出 EPUB 路径（可选）

    Returns:
        转换后的 EPUB 文件路径

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的格式或转换失败
    """
    input_path = os.path.abspath(input_path)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    file_ext = Path(input_path).suffix.lower()
    if file_ext not in CONVERTIBLE_FORMATS:
        raise ValueError(f"Unsupported format: {file_ext}")

    # 检查 calibre
    if not check_calibre():
        raise ValueError(f"calibre not found.\n{get_install_instructions()}")

    # PDF 扫描版检测
    if file_ext == '.pdf':
        if is_scanned_pdf(input_path):
            raise ValueError(
                "This PDF appears to be scanned (no text layer). "
                "OCR is not supported. Please use a text-based PDF."
            )

    # 确定输出路径
    if output_path is None:
        output_path = str(Path(input_path).with_suffix('.epub'))

    # 执行转换
    cmd = ['ebook-convert', input_path, output_path]
    logger.debug(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        # 输出 calibre 日志到 DEBUG
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.debug(f"calibre: {line}")
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                logger.debug(f"calibre: {line}")

        if result.returncode != 0:
            logger.error(f"calibre exit code: {result.returncode}")
            raise ValueError(f"Conversion failed with exit code {result.returncode}")
        return output_path
    except subprocess.TimeoutExpired:
        raise ValueError("Conversion timed out (5 minutes)")
    except Exception as e:
        raise ValueError(f"Conversion error: {e}")
