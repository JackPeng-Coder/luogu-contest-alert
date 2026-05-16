# Luogu Contest Alert

**Generated:** 2026-05-16
**Commit:** `8a1725c`
**Branch:** `main`

## OVERVIEW

Lightweight Python desktop daemon that monitors Luogu (洛谷) competitive programming platform for contest status changes and fires desktop notifications (Tkinter or PySide6 GUI mode).

## STRUCTURE

```
luogu-contest-alert/
├── config.py       # Settings (URL, headers, intervals), logging setup
├── crawler.py      # HTTP scraper + HTML/JSON parser for Luogu contest list
├── storage.py      # JSON persistence layer (contest state tracking)
├── settings.py     # App settings persistence (data/settings.json)
├── notifier.py     # Tkinter desktop notification window (+ dedup)
├── gui.py          # PySide6 modern GUI (main window + tray icon + toggles)
├── main.py         # OOP entry: ContestMonitor orchestrator
├── main.pyw        # Procedural variant (silent background via pythonw)
├── luogu.ico       # System tray icon
├── requirements.txt
└── README.md
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Change check interval/URL | `config.py` | `CHECK_INTERVAL`, `LUOGU_CONTEST_URL` |
| Fix scraping/parsing | `crawler.py` | `LuoguCrawler.fetch_contests()`, `parse_contests()` |
| Fix notification UI | `notifier.py` | `show_notification()`, Tkinter layout |
| Change settings schema | `settings.py` | `DEFAULT_SETTINGS`, JSON persistence |
| Modify GUI/tray/theme | `gui.py` | `SettingsWindow`, `TrayIcon`, QSS styling |
| Add contest-end detection | `main.py` | `check_contests()` detects both start & end |
| Silent background mode | `main.pyw` | Standalone procedural copy of main logic |
| Change data storage | `storage.py` | JSON path, format, serialization |

## CONVENTIONS

- **Python 3.7+**, no type hints used
- **OOP** in main source (`main.py`, `crawler.py`, `storage.py`, `settings.py`)
- **Procedural compatibility layer** at module footers (`storage.py`, `settings.py`)
- **Logging** via `config.logger` (`logging.getLogger('LuoguAlert')`) — file + console
- **Chinese docstrings/comments** throughout
- **Dependencies**: `requests>=2.28.0`, `PySide6>=6.6.0`
- **Signal handling** for graceful exit (SIGINT/SIGTERM in CLI mode)
- **Deduplication**: notified contests tracked in `notifier._shown_contests` (set)
- **GUI mode**: `python main.py` — starts PySide6 settings window + system tray (default)
- **No Tkinter in GUI mode**: GUI uses PySide6 for window/tray, Tkinter notifications only in CLI mode

## ANTI-PATTERNS (THIS PROJECT)

- **Do NOT duplicate code between `main.py` and `main.pyw`** — they share identical logic but are maintained separately.
- **Do NOT remove the backward-compat module-level functions** from `storage.py` or `settings.py` without updating `main.pyw` imports.
- **Do NOT call QApplication before `run_gui()`** — `gui.py` manages the Qt app lifecycle.
- **Do NOT start monitoring in the Qt main thread** — `main.py`'s `run_with_gui()` starts monitoring in a daemon thread.
- **Do NOT use `time.sleep()` in GUI mode** — use `QTimer` if adding periodic tasks inside Qt.

## COMMANDS

```bash
pip install -r requirements.txt    # Setup
python main.py                     # GUI mode (default, PySide6 + system tray)
python main.py --cli               # CLI mode (foreground Tkinter notifications)
python main.pyw                    # Silent background (Windows, no GUI)
```

## NOTES

- `data/` and `logs/` directories auto-created at runtime.
- `data/settings.json` auto-created from `DEFAULT_SETTINGS` on first run.
- Luogu parses from `<script id="lentille-context">` JSON blob — site layout changes may break `crawler.parse_contests()`.
- `main.pyw` is a procedural fork with no signal handling and blocking `time.sleep()` — less robust than `main.py`.
- GUI mode (`--gui`) requires a display (X11/Wayland on Linux, native on Windows/macOS).
- Settings window is frameless, draggable via title bar, minimizes to tray on close.
