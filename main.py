import time
import sys
import signal

from config import logger, CHECK_INTERVAL
from crawler import LuoguCrawler
from storage import Storage
from notifier import (
    notify_contest_started,
    notify_contest_ended,
    notify_contest_about_to_start,
    notify_contest_about_to_end,
)
from settings import Settings
from monitor_logic import (
    decide_reminders,
    merge_sent_reminders,
    seconds_until_next_check,
    REMINDER_START_ADVANCE,
    REMINDER_START,
    REMINDER_END_ADVANCE,
    REMINDER_END,
)


def _minutes_left(target_ts, now_ts):
    """距离目标时刻还剩多少分钟（向上取整，至少 1）。"""
    return max(1, (int(target_ts) - int(now_ts) + 59) // 60)


class ContestMonitor:
    def __init__(self, settings=None):
        self.crawler = LuoguCrawler()
        self.storage = Storage()
        self.settings = settings or Settings()
        self.running = True
        self._last_contests = []

    def _sleep_seconds(self, seconds):
        """分段睡眠，以便能够响应退出信号"""
        end_time = time.time() + seconds
        while time.time() < end_time and self.running:
            sleep_time = min(0.2, end_time - time.time())
            if sleep_time > 0:
                time.sleep(sleep_time)

    def check_contests(self):
        """核心检查逻辑：检测提前提醒、比赛开始和结束"""
        logger.info("正在从洛谷抓取比赛列表...")

        current_contests = self.crawler.fetch_contests()
        self._last_contests = current_contests or []
        if not current_contests:
            logger.warning("未获取到比赛数据，跳过本次检查")
            return

        now_ts = int(time.time())
        current_dict = self.storage.contests_to_dict(current_contests)
        saved_dict = self.storage.load_contests()

        # 继承上一轮已发送提醒记录，保证跨重启不重复提醒
        merge_sent_reminders(current_dict, saved_dict)

        popup_enabled = self.settings.get('popup_enabled', True)
        message_enabled = self.settings.get('message_enabled', True)
        notify_on_start = self.settings.get('notify_on_start', True)
        notify_on_end = self.settings.get('notify_on_end', True)
        advance_start = self.settings.get('advance_start_minutes', 0)
        advance_end = self.settings.get('advance_end_minutes', 0)

        to_notify = []  # [(reminder_type, contest)]

        for contest_id, contest in current_dict.items():
            saved_status = saved_dict.get(contest_id, {}).get('status', '')
            sent = contest.get('sent_reminders', [])

            fired = decide_reminders(
                contest, saved_status, sent, now_ts,
                advance_start_minutes=advance_start,
                advance_end_minutes=advance_end,
                notify_on_start=notify_on_start,
                notify_on_end=notify_on_end,
            )
            for reminder_type in fired:
                to_notify.append((reminder_type, contest))
                contest.setdefault('sent_reminders', []).append(reminder_type)
                logger.info(f"🎯 触发提醒 [{reminder_type}]: {contest['title']}")

        if not popup_enabled and not message_enabled:
            if to_notify:
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

            for reminder_type, contest in to_notify:
                self._emit_notification(reminder_type, contest, now_ts,
                                        popup_enabled, _tray_notify)

        # 保存当前数据
        self.storage.save_contests(current_dict)

        started_cnt = sum(1 for r, _ in to_notify
                          if r in (REMINDER_START_ADVANCE, REMINDER_START))
        ended_cnt = sum(1 for r, _ in to_notify
                        if r in (REMINDER_END_ADVANCE, REMINDER_END))
        logger.info(f"检查完成: 共 {len(current_contests)} 个比赛，"
                    f"{started_cnt} 个开始类提醒，{ended_cnt} 个结束类提醒")

    def _emit_notification(self, reminder_type, contest, now_ts,
                           popup_enabled, tray_notify):
        """按提醒类型发送弹窗与托盘通知"""
        title = contest.get('title', '未知比赛')
        time_str = contest.get('time', '')

        if reminder_type == REMINDER_START_ADVANCE:
            minutes = _minutes_left(contest.get('startTime', now_ts), now_ts)
            msg = f"比赛名称：{title}"
            if time_str:
                msg += f"\n比赛时间：{time_str}"
            msg += f"\n状态：⏰ 即将开始（约 {minutes} 分钟后开赛）"
            if popup_enabled:
                try:
                    notify_contest_about_to_start(contest, minutes)
                except Exception as e:
                    logger.error(f"弹窗通知失败: {e}")
            if tray_notify:
                tray_notify("洛谷比赛即将开始提醒", msg)

        elif reminder_type == REMINDER_START:
            msg = f"比赛名称：{title}"
            if time_str:
                msg += f"\n比赛时间：{time_str}"
            msg += "\n状态：🔵 进行中"
            if popup_enabled:
                try:
                    notify_contest_started(contest)
                except Exception as e:
                    logger.error(f"弹窗通知失败: {e}")
            if tray_notify:
                tray_notify("洛谷比赛开始提醒", msg)

        elif reminder_type == REMINDER_END_ADVANCE:
            minutes = _minutes_left(contest.get('endTime', now_ts), now_ts)
            msg = f"比赛名称：{title}"
            if time_str:
                msg += f"\n比赛时间：{time_str}"
            msg += f"\n状态：⏰ 即将结束（约 {minutes} 分钟后结束）"
            if popup_enabled:
                try:
                    notify_contest_about_to_end(contest, minutes)
                except Exception as e:
                    logger.error(f"弹窗通知失败: {e}")
            if tray_notify:
                tray_notify("洛谷比赛即将结束提醒", msg)

        elif reminder_type == REMINDER_END:
            msg = f"比赛名称：{title}"
            if time_str:
                msg += f"\n比赛时间：{time_str}"
            msg += "\n状态：🔴 已结束"
            if popup_enabled:
                try:
                    notify_contest_ended(contest)
                except Exception as e:
                    logger.error(f"弹窗通知失败: {e}")
            if tray_notify:
                tray_notify("洛谷比赛结束提醒", msg)

    def stop(self, signum=None, frame=None):
        """停止运行"""
        logger.info("正在停止监控程序...")
        self.running = False

    def run(self):
        """启动监控程序"""
        logger.info("洛谷比赛监控程序已启动")
        logger.info(f"检查策略: 动态调度（按比赛触发点对齐），"
                    f"无近触发点时每 {CHECK_INTERVAL} 秒轮询")
        logger.info(f"弹窗: {'启用' if self.settings.get('popup_enabled', True) else '禁用'}"
                    f"，消息: {'启用' if self.settings.get('message_enabled', True) else '禁用'}"
                    f"，开始提醒: {'启用' if self.settings.get('notify_on_start', True) else '禁用'}"
                    f"，结束提醒: {'启用' if self.settings.get('notify_on_end', True) else '禁用'}"
                    f"，开始前提前: {self.settings.get('advance_start_minutes', 0)} 分钟"
                    f"，结束前提前: {self.settings.get('advance_end_minutes', 0)} 分钟")
        logger.info("-" * 50)

        # 首次启动立即检查
        self.check_contests()

        while self.running:
            now_ts = int(time.time())
            wait = seconds_until_next_check(
                self._last_contests, now_ts,
                self.settings.get('advance_start_minutes', 0),
                self.settings.get('advance_end_minutes', 0),
                CHECK_INTERVAL,
            )
            logger.info(f"下次检查: {wait} 秒后")
            self._sleep_seconds(wait)
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

        # CLI 模式下用日志行体现「启动时消息提醒」
        if settings.get('notify_on_startup', True):
            logger.info("启动提醒: 洛谷比赛监控已启动，将在比赛开始/结束时通知你")

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