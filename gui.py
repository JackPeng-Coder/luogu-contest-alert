import sys
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSystemTrayIcon, QMenu,
    QMessageBox, QSizePolicy, QScrollArea
)
from PySide6.QtGui import QIcon, QFont, QPainter, QColor, QPen, QBrush, QPixmap
from PySide6.QtCore import Qt, QTimer, Signal, Property, QEasingCurve, QPropertyAnimation

from config import BASE_DIR, logger

# ── 全局引用，由 run_gui 创建时设置 ──
_app = None
_window = None
_settings_ref = None
_monitor_ref = None
_tray = None
_tray_menu = None


# ═══════════════════════════════════════════
#  自定义开关控件 (Toggle Switch)
# ═══════════════════════════════════════════

class ToggleSwitch(QWidget):
    """现代风格的开关控件，仿 iOS UISwitch"""
    toggled = Signal(bool)

    def __init__(self, initial=False, parent=None):
        super().__init__(parent)
        self._checked = initial
        self._anim_progress = 1.0 if initial else 0.0
        self.setFixedSize(56, 28)
        self.setCursor(Qt.PointingHandCursor)
        self._animation = QPropertyAnimation(self, b'anim_progress')
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_anim_progress(self):
        return self._anim_progress

    def set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    anim_progress = Property(float, get_anim_progress, set_anim_progress)

    def is_checked(self):
        return self._checked

    def set_checked(self, checked, animated=True):
        if self._checked == checked:
            return
        self._checked = checked
        target = 1.0 if checked else 0.0
        if animated:
            self._animation.stop()
            self._animation.setStartValue(self._anim_progress)
            self._animation.setEndValue(target)
            self._animation.start()
        else:
            self._anim_progress = target
            self.update()
        self.toggled.emit(checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.set_checked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2

        # 背景：从灰色到实心绿色渐变
        off_color = QColor(180, 185, 190)
        on_color = QColor(39, 174, 96)
        r = int(off_color.red() + (on_color.red() - off_color.red()) * self._anim_progress)
        g = int(off_color.green() + (on_color.green() - off_color.green()) * self._anim_progress)
        b = int(off_color.blue() + (on_color.blue() - off_color.blue()) * self._anim_progress)
        bg_color = QColor(r, g, b)

        p.setBrush(QBrush(bg_color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, radius, radius)

        # 滑块
        thumb_radius = radius - 3
        thumb_x = 3 + (w - 6 - thumb_radius * 2) * self._anim_progress
        thumb_y = (h - thumb_radius * 2) / 2

        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.setPen(QPen(QColor(220, 220, 220), 0.5))
        p.drawEllipse(int(thumb_x), int(thumb_y), int(thumb_radius * 2), int(thumb_radius * 2))

        # 滑块阴影
        p.setBrush(Qt.NoBrush)
        shadow_color = QColor(0, 0, 0, 30)
        p.setPen(QPen(shadow_color, 2))
        p.drawEllipse(int(thumb_x), int(thumb_y), int(thumb_radius * 2), int(thumb_radius * 2))

        p.end()


# ═══════════════════════════════════════════
#  设置页面卡片容器
# ═══════════════════════════════════════════

class SettingsCard(QFrame):
    """圆角卡片容器"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName('settingsCard')
        self.setStyleSheet("""
            #settingsCard {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e8ecf0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel(title)
        title_font = QFont('Microsoft YaHei UI', 13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1a1a2e; padding-bottom: 4px;")
        layout.addWidget(title_label)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #eef0f4; max-height: 1px;")
        layout.addWidget(line)

        self._content_layout = layout

    def add_row(self, label_text, widget):
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 4)

        label = QLabel(label_text)
        label_font = QFont('Microsoft YaHei UI', 11)
        label.setFont(label_font)
        label.setStyleSheet("color: #2d3436;")
        row.addWidget(label)
        row.addStretch()
        row.addWidget(widget)
        self._content_layout.addLayout(row)

    def add_widget(self, widget):
        self._content_layout.addWidget(widget)


# ═══════════════════════════════════════════
#  主设置窗口
# ═══════════════════════════════════════════

class SettingsWindow(QMainWindow):
    def __init__(self, settings):
        super().__init__()
        self._settings = settings
        self.setWindowTitle("洛谷比赛监控 - 设置")
        self.setWindowIcon(QIcon(os.path.join(BASE_DIR, 'luogu.ico')))
        self.setFixedSize(520, 600)

        # 去除默认标题栏（使用自定义标题栏）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._drag_pos = None
        self._build_ui()
        self._load_settings()
        self._center_on_screen()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2 + screen_geometry.x()
        y = (screen_geometry.height() - self.height()) // 2 + screen_geometry.y()
        self.move(x, y)

    def _build_ui(self):
        # 主容器 - 带圆角和阴影效果
        central = QWidget()
        central.setObjectName('central')
        central.setStyleSheet("""
            #central {
                background-color: #f0f2f5;
                border-radius: 16px;
            }
        """)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 自定义标题栏 ──
        title_bar = QFrame()
        title_bar.setObjectName('titleBar')
        title_bar.setStyleSheet("""
            #titleBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90d9, stop:1 #357abd);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
        """)
        title_bar.setFixedHeight(56)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 12, 0)

        icon_label = QLabel("🏆")
        icon_font = QFont('Segoe UI Emoji', 18)
        icon_label.setFont(icon_font)
        title_layout.addWidget(icon_label)

        title_text = QLabel("洛谷比赛监控")
        title_font = QFont('Microsoft YaHei UI', 14)
        title_font.setBold(True)
        title_text.setFont(title_font)
        title_text.setStyleSheet("color: white;")
        title_layout.addWidget(title_text)

        title_layout.addStretch()

        # 最小化按钮
        min_btn = QPushButton("─")
        min_btn.setFixedSize(32, 28)
        min_btn.setCursor(Qt.PointingHandCursor)
        min_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: white; font-size: 16px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.2); }
        """)
        min_btn.clicked.connect(self._minimize_to_tray)
        title_layout.addWidget(min_btn)

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: white; font-size: 14px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: rgba(255,0,0,0.4); }
        """)
        close_btn.clicked.connect(self._minimize_to_tray)
        title_layout.addWidget(close_btn)

        main_layout.addWidget(title_bar)

        # ── 可滚动内容区域 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                width: 6px; background: transparent; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #c0c4cc; border-radius: 3px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #909399; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        # ── 通知设置卡片 ──
        notify_card = SettingsCard("通知设置")
        self._popup_switch = ToggleSwitch()
        self._msg_switch = ToggleSwitch()
        self._notify_on_start_switch = ToggleSwitch()
        self._notify_on_end_switch = ToggleSwitch()

        notify_card.add_row("弹窗提醒（桌面弹窗）", self._popup_switch)
        notify_card.add_row("消息提醒（系统托盘通知）", self._msg_switch)
        notify_card.add_row("比赛开始时弹出通知", self._notify_on_start_switch)
        notify_card.add_row("比赛结束时弹出通知", self._notify_on_end_switch)

        # 附注说明
        note_label = QLabel("💡 至少开启一种提醒方式才能收到通知")
        note_label.setFont(QFont('Microsoft YaHei UI', 9))
        note_label.setStyleSheet("color: #888; padding-left: 2px;")
        notify_card.add_widget(note_label)

        content_layout.addWidget(notify_card)

        # ── 常规设置卡片 ──
        general_card = SettingsCard("常规设置")
        self._notify_on_startup_switch = ToggleSwitch()
        self._minimize_switch = ToggleSwitch()
        self._auto_start_switch = ToggleSwitch()

        general_card.add_row("启动时消息提醒", self._notify_on_startup_switch)
        general_card.add_row("启动时最小化到系统托盘", self._minimize_switch)
        general_card.add_row("开机自动启动", self._auto_start_switch)

        content_layout.addWidget(general_card)

        # ── 退出程序（在常规设置下方） ──
        quit_line = QFrame()
        quit_line.setFrameShape(QFrame.HLine)
        quit_line.setStyleSheet("background-color: #e0e0e0; max-height: 1px; margin: 4px 0;")
        content_layout.addWidget(quit_line)

        quit_btn = QPushButton("退出程序")
        quit_btn.setFixedHeight(44)
        quit_btn.setCursor(Qt.PointingHandCursor)
        quit_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c; color: white; border: none;
                border-radius: 10px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #c0392b; }
            QPushButton:pressed { background: #a93226; }
        """)
        quit_btn.clicked.connect(self._quit_program)
        content_layout.addWidget(quit_btn)

        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

        # ── 底部按钮 ──
        btn_bar = QFrame()
        btn_bar.setObjectName('btnBar')
        btn_bar.setStyleSheet("""
            #btnBar {
                background: #f8f9fa;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                border-top: 1px solid #e8ecf0;
            }
        """)
        btn_bar.setFixedHeight(56)

        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(20, 10, 20, 10)
        btn_layout.setSpacing(12)

        apply_btn = QPushButton("应用")
        apply_btn.setFixedHeight(36)
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9; color: white; border: none;
                border-radius: 8px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #357abd; }
            QPushButton:pressed { background: #2a6cb5; }
        """)
        apply_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(apply_btn)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedHeight(36)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #e8ecf0; color: #333; border: none;
                border-radius: 8px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #d0d5dd; }
            QPushButton:pressed { background: #b0b5bd; }
        """)
        ok_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(ok_btn)

        main_layout.addWidget(btn_bar)

    def _load_settings(self):
        s = self._settings
        self._popup_switch.set_checked(s.get('popup_enabled', True), animated=False)
        self._msg_switch.set_checked(s.get('message_enabled', True), animated=False)
        self._notify_on_start_switch.set_checked(s.get('notify_on_start', True), animated=False)
        self._notify_on_end_switch.set_checked(s.get('notify_on_end', True), animated=False)
        self._notify_on_startup_switch.set_checked(s.get('notify_on_startup', True), animated=False)
        self._minimize_switch.set_checked(s.get('minimize_to_tray', True), animated=False)
        self._auto_start_switch.set_checked(s.get('auto_start', False), animated=False)

    def _save_settings(self):
        s = self._settings
        s.set_multi({
            'popup_enabled': self._popup_switch.is_checked(),
            'message_enabled': self._msg_switch.is_checked(),
            'notify_on_start': self._notify_on_start_switch.is_checked(),
            'notify_on_end': self._notify_on_end_switch.is_checked(),
            'notify_on_startup': self._notify_on_startup_switch.is_checked(),
            'minimize_to_tray': self._minimize_switch.is_checked(),
            'auto_start': self._auto_start_switch.is_checked(),
        })

        # 处理开机自启动
        self._update_auto_start()

        logger.info("设置已保存")

    def _update_auto_start(self):
        """管理开机自启动（Windows 注册表方式）"""
        if sys.platform != 'win32':
            return

        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )

            if self._auto_start_switch.is_checked():
                pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
                cmd = f'"{pythonw_path}" "{os.path.join(BASE_DIR, "main.py")}"'
                winreg.SetValueEx(key, "LuoguContestAlert", 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(key)
                logger.info(f"已设置开机自启动: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, "LuoguContestAlert")
                    logger.info("已取消开机自启动")
                except FileNotFoundError:
                    pass  # 本来就没有
                winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"设置开机自启动失败: {e}")

    def _save_and_close(self):
        self._save_settings()
        self._minimize_to_tray()

    def _minimize_to_tray(self):
        self.hide()

    def _quit_program(self):
        """完全退出程序（调用模块级 _quit_app）"""
        _quit_app()

    # ── 窗口拖动 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 56:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


# ═══════════════════════════════════════════
#  系统托盘
# ═══════════════════════════════════════════

def _setup_tray(settings, monitor):
    global _tray, _tray_menu

    icon_path = os.path.join(BASE_DIR, 'luogu.ico')
    if not os.path.exists(icon_path):
        icon_path = os.path.join(BASE_DIR, 'luogu.png')

    icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

    _tray = QSystemTrayIcon(icon)
    _tray.setToolTip("洛谷比赛监控")

    # 构建右键菜单并持久引用（必须 setContextMenu + 全局变量，
    # 否则 Windows shell 不显示右键菜单）
    _tray_menu = QMenu()
    _build_tray_menu(_tray_menu, settings)
    _tray.setContextMenu(_tray_menu)

    # 左键/双击 → 打开主界面
    # 右键由 Windows shell 通过 setContextMenu 自动处理
    _tray.activated.connect(_on_tray_activated)

    _tray.show()

    # 首次启动提示
    if settings.get('notify_on_startup', True) and settings.get('minimize_to_tray', True):
        _tray.showMessage(
            "洛谷比赛监控",
            "程序已最小化到系统托盘，双击此图标打开设置界面",
            icon,
            3000
        )


def _on_tray_activated(reason):
    if reason == QSystemTrayIcon.ActivationReason.Trigger:
        _show_window()
    elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
        _show_window()


def _build_tray_menu(menu, settings):
    """填充右键菜单项：顶部固定操作 + 中间所有设置开关 + 底部退出"""

    # ── 主操作 ──
    menu.addAction("显示主界面", _show_window)
    menu.addSeparator()

    # ── 通知开关 ──
    popup_act = menu.addAction("弹窗提醒")
    popup_act.setCheckable(True)
    popup_act.setChecked(settings.get("popup_enabled", True))
    popup_act.triggered.connect(lambda checked: _toggle_setting("popup_enabled", checked))

    msg_act = menu.addAction("消息提醒")
    msg_act.setCheckable(True)
    msg_act.setChecked(settings.get("message_enabled", True))
    msg_act.triggered.connect(lambda checked: _toggle_setting("message_enabled", checked))

    start_act = menu.addAction("开始时提醒")
    start_act.setCheckable(True)
    start_act.setChecked(settings.get("notify_on_start", True))
    start_act.triggered.connect(lambda checked: _toggle_setting("notify_on_start", checked))

    end_act = menu.addAction("结束时提醒")
    end_act.setCheckable(True)
    end_act.setChecked(settings.get("notify_on_end", True))
    end_act.triggered.connect(lambda checked: _toggle_setting("notify_on_end", checked))

    menu.addSeparator()

    # ── 常规开关 ──
    startup_act = menu.addAction("启动时消息提醒")
    startup_act.setCheckable(True)
    startup_act.setChecked(settings.get("notify_on_startup", True))
    startup_act.triggered.connect(lambda checked: _toggle_setting("notify_on_startup", checked))

    tray_act = menu.addAction("启动时最小化到托盘")
    tray_act.setCheckable(True)
    tray_act.setChecked(settings.get("minimize_to_tray", True))
    tray_act.triggered.connect(lambda checked: _toggle_setting("minimize_to_tray", checked))

    auto_act = menu.addAction("开机自启动")
    auto_act.setCheckable(True)
    auto_act.setChecked(settings.get("auto_start", False))
    auto_act.triggered.connect(lambda checked: _toggle_setting("auto_start", checked))

    menu.addSeparator()

    menu.addAction("退出程序", _quit_app)


def _toggle_setting(key, checked):
    """修改设置并持久化"""
    if _settings_ref is not None:
        _settings_ref.set(key, checked)
    # 如果主窗口存在，同步刷新 toggle 状态
    if _window and hasattr(_window, "_load_settings"):
        _window._load_settings()


def _show_window():
    global _window
    if _window:
        _window.show()
        _window.raise_()
        _window.activateWindow()


def _quit_app():
    global _tray, _monitor_ref
    if _monitor_ref:
        _monitor_ref.running = False
    if _tray:
        _tray.hide()
    QApplication.quit()


def show_tray_notification(title, message):
    """从后台线程安全地弹出系统托盘通知。"""
    global _tray
    if _tray and _tray.isVisible():
        # showMessage 内部通过 Qt 事件队列投递到主线程，线程安全
        _tray.showMessage(title, message, QIcon(), 5000)


# ═══════════════════════════════════════════
#  入口函数
# ═══════════════════════════════════════════

def run_gui(settings, monitor=None):
    """
    启动 GUI 主循环。
    必须在主线程中调用。
    """
    global _app, _window, _settings_ref, _monitor_ref

    _settings_ref = settings
    _monitor_ref = monitor

    _app = QApplication.instance()
    if _app is None:
        _app = QApplication(sys.argv)
        _app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出

    # 全局样式
    _app.setStyle('Fusion')

    # 创建主窗口
    _window = SettingsWindow(settings)

    # 创建系统托盘
    _setup_tray(settings, monitor)

    # 根据设置决定是否显示主窗口
    if not settings.get('minimize_to_tray', True):
        _window.show()

    return _app.exec()
