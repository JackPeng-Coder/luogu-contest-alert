import time
import sys
import os
import signal
from datetime import datetime, timedelta

from config import logger
from crawler import LuoguCrawler
from storage import Storage
from notifier import notify_contest_started, notify_contest_ended
from settings import Settings


class ContestMonitor:
    def __init__(self, settings=None):
        self.crawler = LuoguCrawler()
        self.storage = Storage()
        self.settings = settings or Settings()
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
                sleep_time = min(0.2, end_time - time.time())
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def check_contests(self):
        """核心检查逻辑：检测比赛开始和结束"""
        logger.info("正在从洛谷抓取比赛列表...")

        current_contests = self.crawler.fetch_contests()
        if not current_contests:
            logger.warning("未获取到比赛数据，跳过本次检查")
            return

        current_dict = self.storage.contests_to_dict(current_contests)
        saved_dict = self.storage.load_contests()

        started_contests = []
        ended_contests = []

        popup_enabled = self.settings.get('popup_enabled', True)
        message_enabled = self.settings.get('message_enabled', True)
        notify_on_start = self.settings.get('notify_on_start', True)
        notify_on_end = self.settings.get('notify_on_end', True)

        for contest_id, contest in current_dict.items():
            current_status = contest.get('status', '')

            if contest_id in saved_dict:
                saved_status = saved_dict[contest_id].get('status', '')

                # 检测比赛开始：从 '未开始' -> '进行中'
                if notify_on_start and '未开始' in saved_status and '进行中' in current_status:
                    started_contests.append(contest)
                    logger.info(f"🚩 比赛已开始: {contest['title']}")

                # 检测比赛结束：从 '进行中' -> '已结束'
                if notify_on_end and '进行中' in saved_status and '已结束' in current_status:
                    ended_contests.append(contest)
                    logger.info(f"🏁 比赛已结束: {contest['title']}")

        # 发送通知（分别尝试弹窗和托盘消息）
        if not popup_enabled and not message_enabled:
            if started_contests or ended_contests:
                logger.info("通知已禁用，跳过所有提醒")
        else:
            # 尝试导入托盘通知函数（仅在 GUI 模式下可用）
            _tray_notify = None
            if message_enabled:
                try:
                    from gui import show_tray_notification
                    _tray_notify = show_tray_notification
                except ImportError:
                    pass

            def _notify_start(contest):
                name = contest.get('title', '未知比赛')
                time_str = contest.get('time', '')
                msg = f"比赛名称：{name}"
                if time_str:
                    msg += f"\n比赛时间：{time_str}"
                msg += "\n状态：🔵 进行中"
                if popup_enabled:
                    try:
                        notify_contest_started(contest)
                    except Exception as e:
                        logger.error(f"弹窗通知失败: {e}")
                if _tray_notify:
                    _tray_notify("洛谷比赛开始提醒", msg)

            def _notify_end(contest):
                name = contest.get('title', '未知比赛')
                time_str = contest.get('time', '')
                msg = f"比赛名称：{name}"
                if time_str:
                    msg += f"\n比赛时间：{time_str}"
                msg += "\n状态：🔴 已结束"
                if popup_enabled:
                    try:
                        notify_contest_ended(contest)
                    except Exception as e:
                        logger.error(f"弹窗通知失败: {e}")
                if _tray_notify:
                    _tray_notify("洛谷比赛结束提醒", msg)

            for contest in started_contests:
                _notify_start(contest)
            for contest in ended_contests:
                _notify_end(contest)

        # 保存当前数据
        self.storage.save_contests(current_dict)
        logger.info(f"检查完成: 共 {len(current_contests)} 个比赛，"
                    f"{len(started_contests)} 个新开始，{len(ended_contests)} 个新结束")

    def stop(self, signum=None, frame=None):
        """停止运行"""
        logger.info("正在停止监控程序...")
        self.running = False

    def run(self):
        """启动监控程序"""
        logger.info("洛谷比赛监控程序已启动")
        logger.info("检查频率: 每整点和半点（延迟5秒）")
        logger.info(f"弹窗: {'启用' if self.settings.get('popup_enabled', True) else '禁用'}"
                    f"，消息: {'启用' if self.settings.get('message_enabled', True) else '禁用'}"
                    f"，开始提醒: {'启用' if self.settings.get('notify_on_start', True) else '禁用'}"
                    f"，结束提醒: {'启用' if self.settings.get('notify_on_end', True) else '禁用'}")
        logger.info("-" * 50)

        # 首次启动立即检查
        self.check_contests()

        while self.running:
            self.wait_until_next_check()
            if self.running:
                self.check_contests()


def run_with_gui():
    """启动 GUI 模式（带系统托盘和设置窗口）"""
    from gui import run_gui

    settings = Settings()
    monitor = ContestMonitor(settings=settings)

    # 启动监控线程
    import threading
    monitor_thread = threading.Thread(target=monitor.run, daemon=True)
    monitor_thread.start()

    # 启动 GUI（在主线程中运行 Qt 事件循环）
    logger.info("GUI 模式启动")
    run_gui(settings, monitor=monitor)


def main():
    if '--cli' in sys.argv:
        # 标题设置 (仅限 Windows)
        if sys.platform == 'win32':
            import ctypes
            try:
                ctypes.windll.kernel32.SetConsoleTitleW("洛谷比赛监控")
            except:
                pass

        settings = Settings()
        monitor = ContestMonitor(settings=settings)

        # SIGTERM 仍保留（用于外部 kill），
        # SIGINT 不接管让 Python 默认触发 KeyboardInterrupt
        signal.signal(signal.SIGTERM, monitor.stop)

        try:
            monitor.run()
        except KeyboardInterrupt:
            logger.info("用户中断，正在退出...")
            monitor.stop()
            sys.exit(0)
        except Exception as e:
            logger.critical(f"程序遇到致命错误: {e}", exc_info=True)
            sys.exit(1)
    else:
        run_with_gui()


if __name__ == '__main__':
    main()
