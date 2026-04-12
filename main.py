import time
import sys
import os
import signal
from datetime import datetime, timedelta

from config import logger, CHECK_INTERVAL
from crawler import LuoguCrawler
from storage import Storage
from notifier import notify_contest_started


class ContestMonitor:
    def __init__(self):
        self.crawler = LuoguCrawler()
        self.storage = Storage()
        self.running = True

    def get_next_check_time(self):
        """获取下一个检查时间（整点或半点，延迟5秒）"""
        now = datetime.now()
        current_minute = now.minute

        if current_minute < 30:
            target_minute = 30
        else:
            target_minute = 0
            now = now + timedelta(hours=1)

        next_check = now.replace(minute=target_minute, second=5, microsecond=0)
        return next_check

    def wait_until_next_check(self):
        """等待到下一个检查时间点"""
        next_check = self.get_next_check_time()
        now = datetime.now()
        wait_seconds = (next_check - now).total_seconds()

        if wait_seconds > 0:
            logger.info(f"下次检查时间: {next_check.strftime('%Y-%m-%d %H:%M:%S')}，等待 {int(wait_seconds)} 秒...")
            
            # 使用分段睡眠，以便能够响应退出信号
            end_time = time.time() + wait_seconds
            while time.time() < end_time and self.running:
                sleep_time = min(1, end_time - time.time())
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def check_contests(self):
        """核心检查逻辑"""
        logger.info("正在从洛谷抓取比赛列表...")

        current_contests = self.crawler.fetch_contests()
        if not current_contests:
            logger.warning("未获取到比赛数据，跳过本次检查")
            return

        current_dict = self.storage.contests_to_dict(current_contests)
        saved_dict = self.storage.load_contests()

        started_contests = []

        for contest_id, contest in current_dict.items():
            current_status = contest.get('status', '')

            if contest_id in saved_dict:
                saved_status = saved_dict[contest_id].get('status', '')

                # 如果之前是 '未开始'，现在是 '进行中'，则触发提醒
                if '未开始' in saved_status and '进行中' in current_status:
                    started_contests.append(contest)
                    logger.info(f"🚩 比赛已开始: {contest['title']}")

        # 发送通知
        for contest in started_contests:
            try:
                notify_contest_started(contest)
            except Exception as e:
                logger.error(f"发送通知失败: {e}")

        # 保存当前数据
        self.storage.save_contests(current_dict)
        logger.info(f"检查完成: 共 {len(current_contests)} 个比赛，{len(started_contests)} 个新开始")

    def stop(self, signum=None, frame=None):
        """停止运行"""
        logger.info("正在停止监控程序...")
        self.running = False

    def run(self):
        """启动监控程序"""
        logger.info("洛谷比赛监控程序已启动")
        logger.info(f"检查频率: 整点和半点，或每 {CHECK_INTERVAL} 秒")
        logger.info("-" * 50)

        # 首次启动立即检查
        self.check_contests()

        while self.running:
            self.wait_until_next_check()
            if self.running:
                self.check_contests()


def main():
    # 标题设置 (仅限 Windows)
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.kernel32.SetConsoleTitleW("洛谷比赛监控")
        except:
            pass

    monitor = ContestMonitor()

    # 信号处理
    signal.signal(signal.SIGINT, monitor.stop)
    signal.signal(signal.SIGTERM, monitor.stop)

    try:
        monitor.run()
    except Exception as e:
        logger.critical(f"程序遇到致命错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
