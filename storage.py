import json
import os
from config import DATA_FILE, DATA_DIR, logger


class Storage:
    def __init__(self, data_file=DATA_FILE, data_dir=DATA_DIR):
        self.data_file = data_file
        self.data_dir = data_dir
        self._ensure_dir()

    def _ensure_dir(self):
        """确保存储目录存在"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建数据目录失败: {e}")

    def load_contests(self):
        """从本地加载比赛数据"""
        if not os.path.exists(self.data_file):
            return {}

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('contests', {})
        except Exception as e:
            logger.error(f"读取本地数据失败: {e}")
            return {}

    def save_contests(self, contests_dict):
        """保存比赛数据到本地"""
        try:
            data = {
                'contests': contests_dict
            }

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False

    @staticmethod
    def contests_to_dict(contests_list):
        """将比赛列表转换为以 ID 为键的字典"""
        return {str(c['id']): c for c in contests_list if c.get('id')}


# 向后兼容
_storage = Storage()


def load_contests():
    return _storage.load_contests()


def save_contests(contests_dict):
    return _storage.save_contests(contests_dict)


def contests_to_dict(contests_list):
    return _storage.contests_to_dict(contests_list)
