# -*- coding: utf-8 -*-
"""设置窗口离屏渲染测试：无横向滚动条 + 提前量输入框（QSpinBox）接线。

说明：不调用 SettingsWindow._save_settings()，因为它会通过 _update_auto_start()
操作 Windows 注册表，测试环境不应产生该副作用。
"""

import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys
import tempfile
import unittest

from PySide6.QtWidgets import QApplication, QScrollArea, QSpinBox

from settings import Settings
from gui import SettingsWindow


def _get_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class SettingsWindowOffscreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _get_app()

    def _make_window(self, data_dir, **updates):
        s = Settings(data_dir=data_dir)
        if updates:
            s.set_multi(updates)
        return s, SettingsWindow(s)

    def test_no_horizontal_scrollbar(self):
        with tempfile.TemporaryDirectory() as d:
            _, w = self._make_window(d)
            w.show()
            self.app.processEvents()
            scroll = w.findChild(QScrollArea)
            hs = scroll.horizontalScrollBar()
            # 内容宽度不得超过视口，否则会出现「左右滑动拉条」
            self.assertLessEqual(scroll.widget().sizeHint().width(),
                                 scroll.viewport().width())
            self.assertFalse(hs.isVisible())
            w.close()

    def test_advance_spinbox_loads_settings_value(self):
        with tempfile.TemporaryDirectory() as d:
            _, w = self._make_window(
                d, advance_start_minutes=30, advance_end_minutes=120)
            self.assertIsInstance(w._advance_start_spin, QSpinBox)
            self.assertEqual(w._advance_start_spin.value(), 30)
            self.assertEqual(w._advance_end_spin.value(), 120)
            w.close()

    def test_advance_spinbox_range_and_reload(self):
        with tempfile.TemporaryDirectory() as d:
            s, w = self._make_window(d)
            spin = w._advance_start_spin
            self.assertEqual(spin.minimum(), 0)
            self.assertEqual(spin.maximum(), 1440)
            # 输入框写入 -> 待保存值（与 _save_settings 中的取值来源一致）
            spin.setValue(45)
            w._advance_end_spin.setValue(0)
            self.assertEqual(w._advance_start_spin.value(), 45)
            self.assertEqual(w._advance_end_spin.value(), 0)
            # 模拟设置已保存后重新加载回读
            s.set_multi({'advance_start_minutes': 45})
            w._load_settings()
            self.assertEqual(w._advance_start_spin.value(), 45)
            w.close()


if __name__ == '__main__':
    unittest.main()
