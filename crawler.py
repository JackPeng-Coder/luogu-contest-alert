import requests
import json
import re
import time
from datetime import datetime
from config import LUOGU_CONTEST_URL, HEADERS, logger


class LuoguCrawler:
    def __init__(self, url=LUOGU_CONTEST_URL, headers=HEADERS):
        self.url = url
        self.headers = headers
        self.session = requests.Session()
        self.session.headers.update(headers)

    def fetch_contests(self, retries=3, delay=5):
        """获取比赛列表，支持重试机制"""
        for i in range(retries):
            try:
                response = self.session.get(self.url, timeout=30)
                response.raise_for_status()
                return self.parse_contests(response.text)
            except Exception as e:
                logger.error(f"获取比赛列表失败 (尝试 {i+1}/{retries}): {e}")
                if i < retries - 1:
                    time.sleep(delay)
        return []

    def parse_contests(self, html):
        """解析 HTML 获取比赛列表数据"""
        contests = []

        try:
            # 洛谷新版 HTML 结构：数据存储在 id="lentille-context" 的 script 标签中
            match = re.search(r'<script id="lentille-context" type="application/json">(.*?)</script>', html)
            if not match:
                logger.warning("未找到比赛数据所在的 script 标签")
                return []

            json_data = match.group(1)
            data = json.loads(json_data)

            # 新版数据路径：data -> contests -> result
            contests_data = data.get('data', {}).get('contests', {}).get('result', [])
            if not contests_data:
                logger.info("未获取到当前比赛数据")
                return []

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
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
        except Exception as e:
            logger.error(f"解析比赛数据时出错: {e}")

        return contests


# 为了保持向后兼容性，提供一个模块级别的函数
def fetch_contests():
    crawler = LuoguCrawler()
    return crawler.fetch_contests()
