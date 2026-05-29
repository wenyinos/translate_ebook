"""EPUB 文件处理 - 保留原始 HTML 结构"""

import json
import time
from typing import Optional
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from translator import translate_text, format_time, TokenStats, KeyManager, DEFAULT_TARGET_LANG, get_progress_path, load_progress, save_progress, clear_progress


def extract_text_from_html(html_content: str) -> str:
    """从 HTML 提取纯文本"""
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator='\n', strip=True)


def replace_html_text(html_content: str, translated_text: str) -> str:
    """替换 HTML 中的文本内容，保留原始标签结构和图片"""
    soup = BeautifulSoup(html_content, 'html.parser')
    body = soup.find('body')
    if not body:
        return html_content

    # 按段落分割翻译后的文本
    paragraphs = [p.strip() for p in translated_text.split('\n') if p.strip()]

    # 收集所有需要替换的文本节点（跳过图片和脚本）
    text_nodes = []
    for node in body.descendants:
        if isinstance(node, str) and node.strip():
            # 跳过图片 alt 文本和脚本内容
            parent = node.parent
            if parent and parent.name in ('img', 'script', 'style'):
                continue
            text_nodes.append(node)

    # 按段落分组文本节点
    para_groups = []
    current_group = []

    for node in text_nodes:
        parent = node.parent
        if parent and parent.name in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'blockquote', 'caption', 'dt', 'dd'):
            if current_group:
                para_groups.append(current_group)
                current_group = []
            current_group.append(node)
        else:
            current_group.append(node)

    if current_group:
        para_groups.append(current_group)

    # 替换每个段落组的文本
    for i, group in enumerate(para_groups):
        if i < len(paragraphs):
            translated = paragraphs[i]

            for j, node in enumerate(group):
                if j == 0:
                    parent = node.parent
                    if parent:
                        for k, child in enumerate(parent.contents):
                            if child is node:
                                parent.contents[k] = soup.new_string(translated)
                                break
                else:
                    parent = node.parent
                    if parent:
                        for k, child in enumerate(parent.contents):
                            if child is node:
                                parent.contents[k] = soup.new_string('')
                                break

    return str(soup)


def translate_epub(input_path: str, output_path: str, client, model: str,
                   batch_size: int = 50, resume: bool = False,
                   token_stats: Optional[TokenStats] = None,
                   target_lang: str = DEFAULT_TARGET_LANG,
                   key_manager: Optional[KeyManager] = None):
    """翻译 EPUB 文件，保留原始 HTML 结构"""
    print(f"\nProcessing EPUB: {input_path}")

    book = epub.read_epub(input_path)
    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    total_items = len(items)
    print(f"  文档项数量: {total_items}")

    # 加载进度
    completed_items = {}
    if resume:
        completed_items = load_progress(output_path) or {}
        if completed_items:
            print(f"  检测到进度文件，已翻译 {len(completed_items)}/{total_items} 项")

    start_time = time.time()
    pending_count = sum(1 for i in range(total_items) if i not in completed_items)

    for idx, item in enumerate(items):
        if idx in completed_items:
            # 使用已翻译的内容
            item.set_content(completed_items[idx].encode('utf-8'))
            continue

        elapsed = time.time() - start_time
        speed = (idx + 1 - (total_items - pending_count)) / elapsed if elapsed > 0 else 0
        remaining = (pending_count - (idx - (total_items - pending_count))) / speed if speed > 0 else 0
        percent = ((idx + 1) / total_items) * 100

        print(f"  处理文档项 {idx + 1}/{total_items} ({percent:.1f}%) | "
              f"速度: {speed:.2f}个/秒 | "
              f"已用: {format_time(elapsed)} | "
              f"剩余: {format_time(remaining)}")

        html_content = item.get_content().decode('utf-8')
        text = extract_text_from_html(html_content)

        if not text.strip():
            completed_items[idx] = html_content
            continue

        translated_text = translate_text(client, text, model, target_lang,
                                         token_stats=token_stats, key_manager=key_manager)
        new_html = replace_html_text(html_content, translated_text)
        item.set_content(new_html.encode('utf-8'))
        completed_items[idx] = new_html

        # 定期保存进度
        if (idx + 1) % 5 == 0:
            save_progress(output_path, completed_items, total_items)

    epub.write_epub(output_path, book)
    clear_progress(output_path)

    total_time = time.time() - start_time
    print(f"  翻译完成: {output_path}")
    print(f"  总耗时: {format_time(total_time)}")
