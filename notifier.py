import tkinter as tk
from tkinter import font as tkfont
import threading
import webbrowser


def show_notification(title, message, contest_link=None):
    def _show():
        root = tk.Tk()
        root.title(title)
        root.geometry("450x280")
        root.resizable(False, False)
        root.attributes('-topmost', True)
        root.configure(bg='#f5f5f5')

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - 450) // 2
        y = (screen_height - 280) // 2
        root.geometry(f"450x280+{x}+{y}")

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

    thread = threading.Thread(target=_show)
    thread.daemon = True
    thread.start()


def notify_contest_started(contest):
    title = "洛谷比赛开始提醒"
    message = f"比赛名称：{contest['title']}\n\n"
    if contest.get('time'):
        message += f"比赛时间：{contest['time']}\n"
    message += f"\n状态：🔴 进行中"

    contest_link = contest.get('link', '')
    show_notification(title, message, contest_link)
