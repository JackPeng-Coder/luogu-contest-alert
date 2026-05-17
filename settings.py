import json
import os
from config import DATA_DIR, logger

DEFAULT_SETTINGS = {
    'popup_enabled': True,
    'message_enabled': True,
    'notify_on_start': True,
    'notify_on_end': True,
    'notify_on_startup': True,
    'minimize_to_tray': True,
    'auto_start': False
}


class Settings:
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = data_dir
        self.settings_file = os.path.join(data_dir, 'settings.json')
        self._settings = dict(DEFAULT_SETTINGS)
        self._ensure_dir()
        self.load()

    def _ensure_dir(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建设置目录失败: {e}")

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value):
        self._settings[key] = value
        self.save()

    def set_multi(self, updates):
        self._settings.update(updates)
        self.save()

    def get_all(self):
        return dict(self._settings)

    def load(self):
        if not os.path.exists(self.settings_file):
            self._settings = dict(DEFAULT_SETTINGS)
            return

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            self._settings = merged
        except Exception as e:
            logger.error(f"读取设置失败: {e}")
            self._settings = dict(DEFAULT_SETTINGS)

    def save(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            return False


# 向后兼容：模块级函数
_settings = Settings()


def get_setting(key, default=None):
    return _settings.get(key, default)


def set_setting(key, value):
    _settings.set(key, value)


def get_all_settings():
    return _settings.get_all()


def load_settings():
    _settings.load()


def save_settings():
    _settings.save()
