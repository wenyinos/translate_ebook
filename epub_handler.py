"""EPUB 文件处理 - 保留原始 HTML 结构"""

import json
import time
from typing import Optional
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from translator import translate_text, format_time, TokenStats, KeyManager, TranslationCache, DEFAULT_TARGET_LANG, get_progress_path, load_progress, save_progress, clear_progress


def extract_text_from_html(html_content: str) -> str:
    """从 HTML 提取纯文本（只从 body 提取）"""
    soup = BeautifulSoup(html_content, 'html.parser')
    body = soup.find('body')
    if not body:
        return soup.get_text(separator='\n', strip=True)
    return body.get_text(separator='\n', strip=True)


def create_translated_html(original_html: str, translated_text: str) -> str:
    """创建翻译后的 HTML 文档"""
    soup = BeautifulSoup(original_html, 'html.parser')
    body = soup.find('body')
    if not body:
        return original_html

    # 清空 body 内容
    body.clear()

    # 按段落分割翻译后的文本
    paragraphs = [p.strip() for p in translated_text.split('\n') if p.strip()]

    # 添加翻译后的内容
    for para_text in paragraphs:
        # 检测是否为标题
        if para_text.startswith(('第', '章', '节')):
            # 可能是标题
            if '章' in para_text[:5] or '节' in para_text[:5]:
                h_tag = soup.new_tag('h2')
                h_tag.string = para_text
                body.append(h_tag)
            else:
                p_tag = soup.new_tag('p')
                p_tag.string = para_text
                body.append(p_tag)
        else:
            p_tag = soup.new_tag('p')
            p_tag.string = para_text
            body.append(p_tag)

    return str(soup)


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
                   max_tokens: int = 128000,
                   key_manager: Optional[KeyManager] = None,
                   cache: Optional[TranslationCache] = None):
    """翻译 EPUB 文件，创建新的中文文档"""
    print(f"\nProcessing EPUB: {input_path}")

    book = epub.read_epub(input_path)
    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    total_items = len(items)
    print(f"  Items: {total_items}")

    # 加载进度
    completed_items = {}
    if resume:
        completed_items = load_progress(output_path) or {}
        if completed_items:
            print(f"  Resumed: {len(completed_items)}/{total_items} items")

    start_time = time.time()
    pending_count = sum(1 for i in range(total_items) if i not in completed_items)

    for idx, item in enumerate(items):
        if idx in completed_items:
            item.set_content(completed_items[idx].encode('utf-8'))
            continue

        elapsed = time.time() - start_time
        processed = idx + 1 - (total_items - pending_count)
        speed = processed / elapsed if elapsed > 0 else 0
        remaining = (pending_count - processed) / speed if speed > 0 else 0
        percent = ((idx + 1) / total_items) * 100

        print(f"  [{idx + 1}/{total_items}] {percent:.0f}% | {format_time(elapsed)} elapsed | {format_time(remaining)} remaining")

        html_content = item.get_content().decode('utf-8')
        text = extract_text_from_html(html_content)

        if not text.strip():
            completed_items[idx] = html_content
            continue

        translated_text = translate_text(client, text, model, target_lang,
                                         max_tokens=max_tokens,
                                         token_stats=token_stats, key_manager=key_manager,
                                         cache=cache)

        # 创建新的 HTML 文档
        new_html = create_translated_html(html_content, translated_text)
        item.set_content(new_html.encode('utf-8'))
        completed_items[idx] = new_html

        # 定期保存进度
        if (idx + 1) % 5 == 0:
            save_progress(output_path, completed_items, total_items)

    # 确保 toc 中的 Link 对象有 uid 属性
    for i, item in enumerate(book.toc):
        if hasattr(item, 'uid') and item.uid is None:
            item.uid = f'navpoint-{i + 1}'

    # 确保 spine 包含所有文档项目
    if not book.spine:
        book.spine = ['nav']
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            if item.get_name() != 'nav.xhtml':
                book.spine.append(item)

    # 确保 manifest 包含 nav 项目
    nav_item = book.get_item_with_id('nav')
    if not nav_item:
        # 创建 nav.xhtml 如果不存在
        nav_xhtml = epub.EpubHtml(title='Navigation', file_name='nav.xhtml', lang='en')
        nav_xhtml.id = 'nav'  # 设置正确的 id
        nav_xhtml.content = b'''<?xml version=\"1.0\" encoding=\"utf-8\"?>
<!DOCTYPE html>
<html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\">
<head><title>Navigation</title></head>
<body>
<nav epub:type=\"toc\">
<h1>Table of Contents</h1>
<ol>
<li><a href=\"chap_01.xhtml\">Chapter 1</a></li>
</ol>
</nav>
</body>
</html>'''
        book.add_item(nav_xhtml)

    epub.write_epub(output_path, book)
    clear_progress(output_path)

    total_time = time.time() - start_time
    print(f"  Complete: {output_path} ({format_time(total_time)})")
