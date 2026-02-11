import requests
import json
import re
from datetime import datetime
from config import LUOGU_CONTEST_URL, HEADERS


def fetch_contests():
    try:
        response = requests.get(LUOGU_CONTEST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return parse_contests(response.text)
    except Exception as e:
        print(f"获取比赛列表失败: {e}")
        return []


def parse_contests(html):
    contests = []

    try:
        match = re.search(r'window\._feInjection\s*=\s*JSON\.parse\(decodeURIComponent\("([^"]+)"\)\)', html)
        if match:
            encoded_data = match.group(1)
            decoded_data = requests.utils.unquote(encoded_data)
            data = json.loads(decoded_data)

            contests_data = data.get('currentData', {}).get('contests', {}).get('result', [])

            for contest in contests_data:
                contest_id = str(contest.get('id', ''))
                title = contest.get('name', '未知比赛')

                start_time = contest.get('startTime', 0)
                end_time = contest.get('endTime', 0)
                current_time = int(datetime.now().timestamp())

                if current_time < start_time:
                    status = '未开始'
                elif start_time <= current_time <= end_time:
                    status = '进行中'
                else:
                    status = '已结束'

                start_str = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M') if start_time else ''
                end_str = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M') if end_time else ''
                time_str = f"{start_str} ~ {end_str}" if start_str and end_str else ''

                link = f"https://www.luogu.com.cn/contest/{contest_id}" if contest_id else ''

                contests.append({
                    'id': contest_id,
                    'title': title,
                    'status': status,
                    'time': time_str,
                    'link': link,
                    'startTime': start_time,
                    'endTime': end_time
                })
        else:
            print("未找到比赛数据")
    except Exception as e:
        print(f"解析比赛数据时出错: {e}")

    return contests
