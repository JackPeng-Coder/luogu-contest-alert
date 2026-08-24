import tkinter as tk
from tkinter import font as tkfont
import threading
import webbrowser
from config import logger


# 用于追踪已显示的通知，防止重复弹出
_shown_contests = set()


def show_notification(title, message, contest_link=None, contest_id=None,
                      header='🏆 比赛开始提醒'):
    if contest_id and contest_id in _shown_contests:
        return

    if contest_id:
        _shown_contests.add(contest_id)

    def _show():
        try:
            root = tk.Tk()
            root.title(title)
            root.resizable(False, False)
            root.attributes('-topmost', True)
            root.configure(bg='#f5f5f5')

            # 顶部蓝色栏
            header_frame = tk.Frame(root, bg='#4a90d9', height=60)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)

            title_font = tkfont.Font(family='Microsoft YaHei', size=16, weight='bold')
            title_label = tk.Label(
                header_frame,
                text=header,
                font=title_font,
                bg='#4a90d9',
                fg='white'
            )
            title_label.pack(expand=True)

            # 内容区域
            content_frame = tk.Frame(root, bg='#f5f5f5', padx=20, pady=20)
            content_frame.pack(fill='both', expand=True)

            msg_font = tkfont.Font(family='Microsoft YaHei', size=11)
            msg_label = tk.Label(
                content_frame,
                text=message,
                font=msg_font,
                bg='#f5f5f5',
                fg='#333333',
                justify='left',
                wraplength=400
            )
            msg_label.pack(fill='both', expand=True)

            # 按钮区域
            button_frame = tk.Frame(root, bg='#f5f5f5', padx=20, pady=15)
            button_frame.pack(fill='x')

            btn_font = tkfont.Font(family='Microsoft YaHei', size=10)

            if contest_link:
                def open_link():
                    webbrowser.open(contest_link)
                    root.destroy()

                link_btn = tk.Button(
                    button_frame,
                    text='打开比赛页面',
                    font=btn_font,
                    bg='#4a90d9',
                    fg='white',
                    activebackground='#357abd',
                    activeforeground='white',
                    relief='flat',
                    padx=20,
                    pady=8,
                    cursor='hand2',
                    command=open_link
                )
                link_btn.pack(side='left', padx=(0, 10))

            def close_window():
                root.destroy()

            close_btn = tk.Button(
                button_frame,
                text='知道了',
                font=btn_font,
                bg='#e0e0e0',
                fg='#333333',
                activebackground='#d0d0d0',
                activeforeground='#333333',
                relief='flat',
                padx=20,
                pady=8,
                cursor='hand2',
                command=close_window
            )
            close_btn.pack(side='right')

            # 动态计算窗口尺寸：宽度下限 450（上限 560），高度按内容自适应，
            # 避免长文本被截断显示不全；并封顶到屏幕可用区域，防止超出屏幕
            root.update_idletasks()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            w = max(450, min(root.winfo_reqwidth(), 560))
            h = max(280, root.winfo_reqheight())
            w = min(w, max(320, screen_width - 40))
            h = min(h, max(200, screen_height - 60))
            x = max(0, (screen_width - w) // 2)
            y = max(0, (screen_height - h) // 2)
            root.geometry(f"{w}x{h}+{x}+{y}")

            root.mainloop()
        except Exception as e:
            logger.error(f"显示通知窗口出错: {e}")

    thread = threading.Thread(target=_show)
    thread.daemon = True
    thread.start()


def notify_contest_started(contest):
    title = "洛谷比赛开始提醒"
    contest_name = contest.get('title', '未知比赛')
    message = f"比赛名称：{contest_name}\n\n"

    if contest.get('time'):
        message += f"比赛时间：{contest['time']}\n"
    message += f"\n状态：🔵 进行中"

    contest_link = contest.get('link', '')
    contest_id = contest.get('id')

    show_notification(title, message, contest_link, contest_id,
                      header='🏆 比赛开始提醒')


def notify_contest_ended(contest):
    """比赛结束提醒通知"""
    title = "洛谷比赛结束提醒"
    contest_name = contest.get('title', '未知比赛')
    message = f"比赛名称：{contest_name}\n\n"

    if contest.get('time'):
        message += f"比赛时间：{contest['time']}\n"
    message += f"\n状态：🔴 已结束"

    contest_link = contest.get('link', '')
    contest_id = contest.get('id')
    # 使用 "ended_" 前缀区分 ID，防止与开始通知冲突
    ended_id = f"ended_{contest_id}" if contest_id else None

    show_notification(title, message, contest_link, ended_id,
                      header='🏁 比赛结束提醒')


def notify_contest_about_to_start(contest, minutes):
    """比赛开始前提前提醒通知"""
    title = "洛谷比赛即将开始提醒"
    contest_name = contest.get('title', '未知比赛')
    message = f"比赛名称：{contest_name}\n\n"

    if contest.get('time'):
        message += f"比赛时间：{contest['time']}\n"
    message += f"\n状态：⏰ 即将开始（约 {minutes} 分钟后开赛）"

    contest_link = contest.get('link', '')
    contest_id = contest.get('id')
    start_advance_id = f"start_advance_{contest_id}" if contest_id else None

    show_notification(title, message, contest_link, start_advance_id,
                      header='⏰ 比赛即将开始提醒')


def notify_contest_about_to_end(contest, minutes):
    """比赛结束前提前提醒通知"""
    title = "洛谷比赛即将结束提醒"
    contest_name = contest.get('title', '未知比赛')
    message = f"比赛名称：{contest_name}\n\n"

    if contest.get('time'):
        message += f"比赛时间：{contest['time']}\n"
    message += f"\n状态：⏰ 即将结束（约 {minutes} 分钟后结束）"

    contest_link = contest.get('link', '')
    contest_id = contest.get('id')
    end_advance_id = f"end_advance_{contest_id}" if contest_id else None

    show_notification(title, message, contest_link, end_advance_id,
                      header='⏰ 比赛即将结束提醒')
