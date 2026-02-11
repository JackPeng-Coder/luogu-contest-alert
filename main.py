import time
import sys
import os
from datetime import datetime, timedelta

from crawler import fetch_contests
from storage import load_contests, save_contests, contests_to_dict
from notifier import notify_contest_started


def get_next_check_time():
    """获取下一个检查时间（整点或半点，延迟5秒）"""
    now = datetime.now()
    current_minute = now.minute
    current_second = now.second

    if current_minute < 30:
        target_minute = 30
    else:
        target_minute = 0
        now = now + timedelta(hours=1)

    next_check = now.replace(minute=target_minute, second=5, microsecond=0)

    if target_minute == 0 and current_minute >= 30:
        pass

    return next_check


def wait_until_next_check():
    """等待到下一个检查时间点"""
    next_check = get_next_check_time()
    now = datetime.now()

    wait_seconds = (next_check - now).total_seconds()

    if wait_seconds > 0:
        print(f"下次检查时间: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"等待 {int(wait_seconds)} 秒...")
        time.sleep(wait_seconds)


def check_contests():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在检查比赛列表...")

    current_contests = fetch_contests()
    if not current_contests:
        print("未获取到比赛数据，跳过本次检查")
        return

    current_dict = contests_to_dict(current_contests)
    saved_dict = load_contests()

    started_contests = []

    for contest_id, contest in current_dict.items():
        current_status = contest.get('status', '')

        if contest_id in saved_dict:
            saved_status = saved_dict[contest_id].get('status', '')

            if '未开始' in saved_status and '进行中' in current_status:
                started_contests.append(contest)
                print(f"检测到比赛开始: {contest['title']}")

    for contest in started_contests:
        notify_contest_started(contest)

    save_contests(current_dict)

    print(f"本次检查完成，共 {len(current_contests)} 个比赛，{len(started_contests)} 个新开始的比赛")


def main():
    print("洛谷比赛监控程序已启动")
    print("检查时间点: 每个整点和半点（延迟5秒）")
    print("-" * 50)

    check_contests()

    while True:
        wait_until_next_check()
        check_contests()


if __name__ == '__main__':
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("洛谷比赛监控")

    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已停止")
        sys.exit(0)
    except Exception as e:
        print(f"程序出错: {e}")
        sys.exit(1)
