"""DOCX 文件处理 - 保留段落结构和内联格式"""

from typing import Optional
from docx import Document
from translator import translate_batch, format_time, TokenStats


def copy_run_format(src_run, dst_run):
    """复制单个 run 的格式（粗体、斜体、下划线等）"""
    if src_run.bold:
        dst_run.bold = True
    if src_run.italic:
        dst_run.italic = True
    if src_run.underline:
        dst_run.underline = True
    if src_run.font.size:
        dst_run.font.size = src_run.font.size
    if src_run.font.name:
        dst_run.font.name = src_run.font.name


def copy_paragraph_format(src_para, dst_para):
    """复制段落格式（对齐、缩进等）"""
    if src_para.alignment:
        dst_para.alignment = src_para.alignment
    pf = src_para.paragraph_format
    if pf.first_line_indent:
        dst_para.paragraph_format.first_line_indent = pf.first_line_indent
    if pf.left_indent:
        dst_para.paragraph_format.left_indent = pf.left_indent
    if pf.right_indent:
        dst_para.paragraph_format.right_indent = pf.right_indent


def translate_docx(input_path: str, output_path: str, client, model: str,
                   batch_size: int = 50, resume: bool = False,
                   token_stats: Optional[TokenStats] = None):
    """翻译 DOCX 文件，保留样式和内联格式"""
    print(f"\n处理 DOCX: {input_path}")

    src_doc = Document(input_path)
    total_paragraphs = len(src_doc.paragraphs)
    print(f"  总段落数: {total_paragraphs}")

    paragraphs_to_translate = []
    for i, para in enumerate(src_doc.paragraphs):
        if para.text.strip():
            paragraphs_to_translate.append((i, para.text))

    total_to_translate = len(paragraphs_to_translate)
    print(f"  非空段落数: {total_to_translate}")

    texts = [p[1] for p in paragraphs_to_translate]
    translated_texts = translate_batch(client, texts, model, batch_size,
                                       output_path=output_path, resume=resume,
                                       token_stats=token_stats)

    dst_doc = Document()

    translation_idx = 0
    for i, para in enumerate(src_doc.paragraphs):
        new_para = dst_doc.add_paragraph()

        if para.text.strip():
            new_para.text = translated_texts[translation_idx]
            translation_idx += 1
        else:
            new_para.text = ""

        # 复制段落样式
        if para.style:
            new_para.style = para.style

        # 复制段落格式
        copy_paragraph_format(para, new_para)

    dst_doc.save(output_path)
    total_time = time.time() - start_time
    print(f"  翻译完成: {output_path}")
    print(f"  总耗时: {format_time(total_time)}")
