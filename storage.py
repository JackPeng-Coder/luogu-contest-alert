import json
import os
from config import DATA_FILE, DATA_DIR


def load_contests():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('contests', {})
    except Exception as e:
        print(f"读取本地数据失败: {e}")
        return {}


def save_contests(contests_dict):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)

        data = {
            'contests': contests_dict
        }

        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        print(f"保存数据失败: {e}")
        return False


def contests_to_dict(contests_list):
    return {c['id']: c for c in contests_list if c['id']}
