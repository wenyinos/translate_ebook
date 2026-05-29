"""单元测试"""

import os
import tempfile
import unittest
from pathlib import Path

from translator import (
    TranslationCache, TokenStats, KeyManager,
    format_time, SUPPORTED_LANGUAGES, DEFAULT_TARGET_LANG
)


class TestTranslationCache(unittest.TestCase):
    """翻译记忆缓存测试"""

    def setUp(self):
        self.cache = TranslationCache()

    def test_set_and_get(self):
        """测试设置和获取缓存"""
        self.cache.set("Hello", "zh", "你好")
        self.assertEqual(self.cache.get("Hello", "zh"), "你好")

    def test_get_missing(self):
        """测试获取不存在的缓存"""
        self.assertIsNone(self.cache.get("Missing", "zh"))

    def test_different_languages(self):
        """测试不同语言的缓存"""
        self.cache.set("Hello", "zh", "你好")
        self.cache.set("Hello", "ja", "こんにちは")
        self.assertEqual(self.cache.get("Hello", "zh"), "你好")
        self.assertEqual(self.cache.get("Hello", "ja"), "こんにちは")

    def test_size(self):
        """测试缓存大小"""
        self.assertEqual(self.cache.size, 0)
        self.cache.set("Hello", "zh", "你好")
        self.assertEqual(self.cache.size, 1)

    def test_save_and_load(self):
        """测试保存和加载缓存"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_path = f.name

        try:
            cache1 = TranslationCache(cache_path)
            cache1.set("Hello", "zh", "你好")
            cache1.save()

            cache2 = TranslationCache(cache_path)
            self.assertEqual(cache2.get("Hello", "zh"), "你好")
        finally:
            os.unlink(cache_path)


class TestTokenStats(unittest.TestCase):
    """Token 统计测试"""

    def test_initial_state(self):
        """测试初始状态"""
        stats = TokenStats()
        self.assertEqual(stats.input_tokens, 0)
        self.assertEqual(stats.output_tokens, 0)
        self.assertEqual(stats.total_cost, 0.0)

    def test_summary(self):
        """测试摘要输出"""
        stats = TokenStats()
        summary = stats.summary()
        self.assertIn("Token 统计", summary)
        self.assertIn("输入", summary)
        self.assertIn("输出", summary)


class TestFormatTime(unittest.TestCase):
    """时间格式化测试"""

    def test_seconds(self):
        """测试秒数格式化"""
        result = format_time(30)
        self.assertIn("30", result)

    def test_minutes(self):
        """测试分钟格式化"""
        result = format_time(90)
        self.assertIn("1.5", result)

    def test_hours(self):
        """测试小时格式化"""
        result = format_time(3600)
        self.assertIn("1.0", result)


class TestSupportedLanguages(unittest.TestCase):
    """支持的语言测试"""

    def test_default_language(self):
        """测试默认语言"""
        self.assertEqual(DEFAULT_TARGET_LANG, "zh")

    def test_supported_languages(self):
        """测试支持的语言列表"""
        self.assertIn("zh", SUPPORTED_LANGUAGES)
        self.assertIn("en", SUPPORTED_LANGUAGES)
        self.assertIn("ja", SUPPORTED_LANGUAGES)

    def test_language_names(self):
        """测试语言名称"""
        self.assertEqual(SUPPORTED_LANGUAGES["zh"], "简体中文")
        self.assertEqual(SUPPORTED_LANGUAGES["en"], "English")


class TestKeyManager(unittest.TestCase):
    """Key 管理器测试"""

    def test_single_key(self):
        """测试单个 Key"""
        manager = KeyManager(["key1"], ["model1"], "http://test.com")
        self.assertEqual(manager.key_count, 1)
        self.assertEqual(manager.model_count, 1)

    def test_multiple_keys(self):
        """测试多个 Key"""
        manager = KeyManager(["key1", "key2"], ["model1", "model2"], "http://test.com")
        self.assertEqual(manager.key_count, 2)
        self.assertEqual(manager.model_count, 2)

    def test_key_preview(self):
        """测试 Key 预览"""
        manager = KeyManager(["sk-1234567890"], ["model1"], "http://test.com")
        preview = manager.get_current_key_preview()
        self.assertTrue(preview.endswith("..."))
        self.assertEqual(len(preview), 11)  # 8 chars + "..."


if __name__ == '__main__':
    unittest.main()
