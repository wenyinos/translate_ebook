"""翻译核心逻辑 - API 调用、批量处理、断点续传、Token 统计、Key 轮换"""

import json
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from pathlib import Path
import openai


class KeyManager:
    """API Key 和模型轮换管理器"""

    def __init__(self, api_keys: List[str], models: List[str],
                 base_url: str = "https://api.openai.com/v1"):
        self.api_keys = api_keys
        self.models = models
        self.base_url = base_url
        self._current_key_idx = 0
        self._current_model_idx = 0
        self._lock = threading.Lock()
        self._clients: Dict[str, openai.OpenAI] = {}

    def get_client_and_model(self) -> tuple[openai.OpenAI, str]:
        """获取当前的客户端和模型（线程安全）"""
        with self._lock:
            api_key = self.api_keys[self._current_key_idx]
            model = self.models[self._current_model_idx]

            # 缓存客户端
            if api_key not in self._clients:
                self._clients[api_key] = openai.OpenAI(
                    api_key=api_key,
                    base_url=self.base_url
                )

            return self._clients[api_key], model

    def rotate_key(self):
        """轮换到下一个 API Key"""
        with self._lock:
            self._current_key_idx = (self._current_key_idx + 1) % len(self.api_keys)
            key_preview = self.api_keys[self._current_key_idx][:8] + "..."
            print(f"  Switched to API key: {key_preview}")

    def rotate_model(self):
        """轮换到下一个模型"""
        with self._lock:
            self._current_model_idx = (self._current_model_idx + 1) % len(self.models)
            print(f"  Switched to model: {self.models[self._current_model_idx]}")

    def get_current_key_preview(self) -> str:
        """获取当前 key 的预览"""
        return self.api_keys[self._current_key_idx][:8] + "..."

    @property
    def key_count(self) -> int:
        return len(self.api_keys)

    @property
    def model_count(self) -> int:
        return len(self.models)


# 支持的语言配置
SUPPORTED_LANGUAGES = {
    "zh": "简体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "ru": "Русский",
    "pt": "Português",
    "it": "Italiano",
}

DEFAULT_TARGET_LANG = "zh"


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
                   target_lang: str = DEFAULT_TARGET_LANG,
                   max_retries: int = 3, retry_delay: float = 1.0,
                   token_stats: Optional[TokenStats] = None,
                   key_manager: Optional[KeyManager] = None) -> str:
    """使用 OpenAI API 翻译文本"""
    if not text.strip():
        return text

    if text.strip().isdigit() or len(text.strip()) <= 2:
        return text

    lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)

    prompt = f"""Please translate the following English text to {lang_name}.
Requirements:
1. Preserve the original formatting and layout
2. Keep technical terms accurate (e.g., SoC, CPU, GPU, API should be kept in original or use common translations)
3. Keep chapter numbers unchanged
4. Output only the translation, no explanations

Original text:
{text}"""

    system_msg = f"You are a professional technical document translator, skilled at translating English technical documents to {lang_name}."

    for attempt in range(max_retries):
        try:
            # 如果有 key_manager，使用轮换的客户端和模型
            if key_manager:
                current_client, current_model = key_manager.get_client_and_model()
            else:
                current_client, current_model = client, model

            response = current_client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4096
            )

            # 统计 token
            if token_stats and response.usage:
                token_stats.add(response.usage, current_model)

            # 请求间隔（15-60秒随机延迟，避免触发风控）
            delay = random.uniform(15, 60)
            time.sleep(delay)

            result = response.choices[0].message.content
            return result.strip() if result else text
        except openai.RateLimitError as e:
            # 429 Rate Limit Error - 轮换 key 并延长等待时间
            if key_manager and key_manager.key_count > 1:
                key_manager.rotate_key()
                wait_time = 60 * (attempt + 1)  # 60s, 120s, 180s
                print(f"  Rate limited, waiting {wait_time:.0f}s before retry...")
                time.sleep(wait_time)
            elif attempt < max_retries - 1:
                wait_time = 60 * (attempt + 1)
                print(f"  Rate limited, waiting {wait_time:.0f}s...")
                time.sleep(wait_time)
            else:
                print(f"  Rate limited, skipping: {e}")
                return text
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Translation failed, retry {attempt + 1}/{max_retries}: {e}")
                time.sleep(15)
            else:
                print(f"  Translation failed, skipping: {e}")
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
                    target_lang: str = DEFAULT_TARGET_LANG,
                    batch_size: int = 50, max_workers: int = 4,
                    output_path: Optional[str] = None,
                    resume: bool = False,
                    token_stats: Optional[TokenStats] = None,
                    key_manager: Optional[KeyManager] = None) -> List[str]:
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
        translated = translate_text(client, text, model, target_lang,
                                    token_stats=token_stats, key_manager=key_manager)
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
