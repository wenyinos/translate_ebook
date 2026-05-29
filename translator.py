"""翻译核心逻辑 - API 调用、批量处理、断点续传、Token 统计"""

import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from pathlib import Path
import openai


class TokenStats:
    """Token 使用统计"""

    # 价格 per 1K tokens (USD)
    PRICES = {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_cost = 0.0
        self._lock = threading.Lock()

    def add(self, usage, model: str):
        """累加 token 使用量"""
        with self._lock:
            self.input_tokens += usage.prompt_tokens
            self.output_tokens += usage.completion_tokens

            # 计算费用
            prices = self.PRICES.get(model, {"input": 0.005, "output": 0.015})
            cost = (usage.prompt_tokens * prices["input"] +
                    usage.completion_tokens * prices["output"]) / 1000
            self.total_cost += cost

    def summary(self) -> str:
        """返回统计摘要"""
        total = self.input_tokens + self.output_tokens
        return (f"Token 统计: 输入 {self.input_tokens:,} | 输出 {self.output_tokens:,} | "
                f"合计 {total:,} | 预估费用 ${self.total_cost:.4f}")


def translate_text(client: openai.OpenAI, text: str, model: str,
                   max_retries: int = 3, retry_delay: float = 1.0,
                   token_stats: Optional[TokenStats] = None) -> str:
    """使用 OpenAI API 翻译文本"""
    if not text.strip():
        return text

    if text.strip().isdigit() or len(text.strip()) <= 2:
        return text

    prompt = f"""请将以下英文文本翻译为简体中文。
要求：
1. 保持原文格式和排版
2. 技术术语准确（如 SoC、CPU、GPU、API 等保留原文或使用通用译法）
3. 章节编号保持不变
4. 只输出翻译结果，不要添加解释

原文：
{text}"""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的技术文档翻译员，擅长将英文技术文档翻译为简体中文。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4096
            )

            # 统计 token
            if token_stats and response.usage:
                token_stats.add(response.usage, model)

            result = response.choices[0].message.content
            return result.strip() if result else text
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  翻译失败，重试 {attempt + 1}/{max_retries}: {e}")
                time.sleep(retry_delay)
            else:
                print(f"  翻译失败，跳过: {e}")
                return text


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.0f}秒"
    elif seconds < 3600:
        return f"{seconds/60:.1f}分钟"
    else:
        return f"{seconds/3600:.1f}小时"


def get_progress_path(output_path: str) -> str:
    """获取进度文件路径"""
    return output_path + ".progress.json"


def save_progress(output_path: str, results: Dict[int, str], total: int):
    """保存翻译进度"""
    progress_path = get_progress_path(output_path)
    data = {
        "total": total,
        "completed": {str(k): v for k, v in results.items() if v is not None}
    }
    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_progress(output_path: str) -> Optional[Dict[int, str]]:
    """加载翻译进度"""
    progress_path = get_progress_path(output_path)
    if not Path(progress_path).exists():
        return None

    try:
        with open(progress_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {int(k): v for k, v in data.get("completed", {}).items()}
    except Exception:
        return None


def clear_progress(output_path: str):
    """清除进度文件"""
    progress_path = get_progress_path(output_path)
    if Path(progress_path).exists():
        Path(progress_path).unlink()


def translate_batch(client: openai.OpenAI, texts: List[str], model: str,
                    batch_size: int = 50, max_workers: int = 4,
                    output_path: Optional[str] = None,
                    resume: bool = False,
                    token_stats: Optional[TokenStats] = None) -> List[str]:
    """批量翻译文本（支持并行、断点续传）"""
    total = len(texts)
    results = [None] * total

    # 尝试恢复进度
    if resume and output_path:
        saved = load_progress(output_path)
        if saved:
            count = len(saved)
            print(f"  检测到进度文件，已翻译 {count}/{total} 项")
            for idx, text in saved.items():
                results[idx] = text

    # 筛选需要翻译的项
    to_translate = [(i, texts[i]) for i in range(total) if results[i] is None]
    pending_count = len(to_translate)

    if pending_count == 0:
        print(f"  所有 {total} 项已翻译完成")
        return results

    print(f"  待翻译: {pending_count} 项")
    completed = total - pending_count
    lock = threading.Lock()
    start_time = time.time()
    save_interval = 5  # 每 5 项保存一次

    def translate_item(idx_text):
        idx, text = idx_text
        translated = translate_text(client, text, model, token_stats=token_stats)
        with lock:
            nonlocal completed
            completed += 1
            results[idx] = translated

            elapsed = time.time() - start_time
            speed = completed / elapsed if elapsed > 0 else 0
            remaining = (total - completed) / speed if speed > 0 else 0
            percent = (completed / total) * 100

            if completed % 10 == 0 or completed == total:
                print(f"  进度: {completed}/{total} ({percent:.1f}%) | "
                      f"速度: {speed:.2f}个/秒 | "
                      f"已用: {format_time(elapsed)} | "
                      f"剩余: {format_time(remaining)}")

            # 定期保存进度
            if output_path and completed % save_interval == 0:
                save_progress(output_path, results, total)

        return idx, translated

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(translate_item, item) for item in to_translate]
        for future in as_completed(futures):
            future.result()

    # 保存最终进度
    if output_path:
        clear_progress(output_path)

    return results
