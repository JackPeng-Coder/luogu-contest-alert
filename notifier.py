import tkinter as tk
from tkinter import font as tkfont
import threading
import webbrowser
from config import logger


# 用于追踪已显示的通知，防止重复弹出
_shown_contests = set()


def show_notification(title, message, contest_link=None, contest_id=None):
    if contest_id and contest_id in _shown_contests:
        return
    
    if contest_id:
        _shown_contests.add(contest_id)

    def _show():
        try:
            root = tk.Tk()
            root.title(title)
            root.geometry("450x280")
            root.resizable(False, False)
            root.attributes('-topmost', True)
            root.configure(bg='#f5f5f5')

            # 居中显示
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width - 450) // 2
            y = (screen_height - 280) // 2
            root.geometry(f"450x280+{x}+{y}")

            # 顶部蓝色栏
            header_frame = tk.Frame(root, bg='#4a90d9', height=60)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)

            title_font = tkfont.Font(family='Microsoft YaHei', size=16, weight='bold')
            title_label = tk.Label(
                header_frame,
                text='🏆 比赛开始提醒',
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
    message += f"\n状态：🔴 进行中"

    contest_link = contest.get('link', '')
    contest_id = contest.get('id')
    
    show_notification(title, message, contest_link, contest_id)
