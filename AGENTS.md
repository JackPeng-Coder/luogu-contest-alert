# Luogu Contest Alert

**Generated:** 2026-05-16
**Commit:** `8a1725c`
**Branch:** `main`

## OVERVIEW

Lightweight Python desktop daemon that monitors Luogu (洛谷) competitive programming platform for contest status changes and fires desktop notifications (Tkinter or PySide6 GUI mode). Supports configurable advance reminders before contest start and end.

## STRUCTURE

```
luogu-contest-alert/
├── config.py        # Settings (URL, fallback poll interval), logging setup
├── crawler.py       # HTTP scraper + HTML/JSON parser for Luogu contest list
├── storage.py       # JSON persistence layer (contest state tracking)
├── settings.py      # App settings persistence (data/settings.json)
├── monitor_logic.py # Pure logic: reminder decisions, dedup merge, dynamic scheduling
├── notifier.py      # Tkinter desktop notification window (+ dedup)
├── gui.py           # PySide6 modern GUI (main window + tray icon + toggles)
├── main.py          # OOP entry: ContestMonitor orchestrator
├── tests/           # unittest suite for monitor_logic / settings
├── luogu.ico        # System tray icon
├── requirements.txt
└── README.md
```

Note: `main.pyw` is a **user-local copy for silent background** (`pythonw`), intentionally gitignored (`*.pyw`) and NOT part of the repo. For silent background run `pythonw main.py`.

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Change fallback poll interval / URL | `config.py` | `CHECK_INTERVAL`, `LUOGU_CONTEST_URL` |
| Fix scraping/parsing | `crawler.py` | `LuoguCrawler.fetch_contests()`, `parse_contests()` |
| Fix notification UI | `notifier.py` | `show_notification()`, Tkinter layout, dynamic sizing |
| Change settings schema / advance presets | `settings.py` | `DEFAULT_SETTINGS`, `ADVANCE_CHOICES`, JSON persistence |
| Add/edit reminder rules / scheduling | `monitor_logic.py` | `decide_reminders()`, `seconds_until_next_check()`, `merge_sent_reminders()` |
| Wire reminder rules into monitor | `main.py` | `check_contests()`, `_emit_notification()`, dynamic scheduling loop |
| Modify GUI/tray/theme | `gui.py` | `SettingsWindow`, `TrayIcon`, QSS styling |
| Change data storage | `storage.py` | JSON path, format, serialization |

## CONVENTIONS

- **Python 3.7+**, no type hints used
- **OOP** in main source (`main.py`, `crawler.py`, `storage.py`, `settings.py`)
- **Pure logic isolated** in `monitor_logic.py` (no GUI/network/storage deps) — unit-tested with `unittest`
- **Procedural compatibility layer** at module footers (`storage.py`, `settings.py`)
- **Logging** via `config.logger` (`logging.getLogger('LuoguAlert')`) — file + console
- **Chinese docstrings/comments** throughout
- **Dependencies**: `requests>=2.28.0`, `PySide6>=6.6.0`
- **Signal handling** for graceful exit (SIGINT/SIGTERM in CLI mode)
- **Reminder dedup**: persistent per-contest `sent_reminders` list (survives restarts) + in-process `notifier._shown_contests`
- **Advance reminders** (`advance_start_minutes` / `advance_end_minutes`) follow the popup/message channels and are gated by `notify_on_start` / `notify_on_end`
- **Dynamic scheduling**: monitor sleeps to the next trigger point (start−advance, start, end−advance, end), capped by `CHECK_INTERVAL` fallback polling
- **GUI mode**: `python main.py` — starts PySide6 settings window + system tray (default)
- **No Tkinter in GUI mode**: GUI uses PySide6 for window/tray, Tkinter notifications only in CLI mode

## ANTI-PATTERNS (THIS PROJECT)

- **Do NOT put GUI/network/storage logic into `monitor_logic.py`** — keep it pure and unit-testable.
- **Do NOT remove the backward-compat module-level functions** from `storage.py` or `settings.py`.
- **Do NOT duplicate monitoring logic into `main.pyw`** — it is a gitignored local copy, not part of the repo.
- **Do NOT call QApplication before `run_gui()`** — `gui.py` manages the Qt app lifecycle.
- **Do NOT start monitoring in the Qt main thread** — `main.py`'s `run_with_gui()` starts monitoring in a daemon thread.
- **Do NOT use `time.sleep()` in GUI mode** — use `QTimer` if adding periodic tasks inside Qt.

## COMMANDS

```bash
pip install -r requirements.txt    # Setup
python main.py                     # GUI mode (default, PySide6 + system tray)
python main.py --cli               # CLI mode (foreground Tkinter notifications)
pythonw main.py                    # Silent background (Windows, no console)
python -m unittest discover -s tests -t .   # Run unit tests
```

## NOTES

- `data/` and `logs/` directories auto-created at runtime.
- `data/settings.json` auto-created from `DEFAULT_SETTINGS` on first run.
- Luogu parses from `<script id="lentille-context">` JSON blob — site layout changes may break `crawler.parse_contests()`.
- Reminder types: `start_advance` / `start` / `end_advance` / `end`; each contest persists which were sent in `sent_reminders`.
- GUI mode (`--gui`) requires a display (X11/Wayland on Linux, native on Windows/macOS).
- Settings window is frameless, draggable via title bar, minimizes to tray on close.
