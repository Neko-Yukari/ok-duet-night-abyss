"""
Process/window disguise utilities.

Provides optional camouflage for the ok-dna automation tool on Windows:
- Hide the console window when running from a terminal.
- Rename the console window title.
- Provide a configurable GUI window title.

Notes
-----
The "process name" seen in Task Manager is determined by the executable file
name. When running from source it will be ``python.exe`` / ``pythonw.exe``.
When packaged with pyappify, the name comes from ``pyappify.yml``.
Renaming a live process image from user-mode is unreliable and fragile,
so this module focuses on the parts that can be safely disguised at runtime.
"""

from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import dataclass
from typing import Callable

from ok import Logger

logger = Logger.get_logger(__name__)

# Windows constants
_SW_HIDE = 0
_SW_SHOW = 1

_kernel32 = ctypes.windll.kernel32
_user32 = ctypes.windll.user32

# Configure ctypes signatures for robustness
_kernel32.GetConsoleWindow.argtypes = []
_kernel32.GetConsoleWindow.restype = ctypes.c_void_p

_kernel32.SetConsoleTitleW.argtypes = [ctypes.c_wchar_p]
_kernel32.SetConsoleTitleW.restype = ctypes.c_bool

_user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
_user32.ShowWindow.restype = ctypes.c_bool

_user32.SetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
_user32.SetWindowTextW.restype = ctypes.c_bool

_user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
_user32.GetWindowTextLengthW.restype = ctypes.c_int

_user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int

_user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
_user32.GetWindowThreadProcessId.restype = ctypes.c_uint

_ENUM_WINDOWS_PROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    ctypes.c_void_p,
    ctypes.c_void_p,
)
_user32.EnumWindows.argtypes = [_ENUM_WINDOWS_PROC, ctypes.c_void_p]
_user32.EnumWindows.restype = ctypes.c_bool


def _get_console_window() -> int | None:
    """Return the native HWND of the console window, if any."""
    try:
        hwnd = _kernel32.GetConsoleWindow()
        return hwnd if hwnd else None
    except Exception as e:  # pragma: no cover - best effort
        logger.debug(f"GetConsoleWindow failed: {e}")
        return None


def hide_console_window() -> bool:
    """Hide the console window so the tool does not appear as a terminal process."""
    hwnd = _get_console_window()
    if not hwnd:
        logger.debug("No console window found to hide")
        return False
    try:
        _user32.ShowWindow(hwnd, _SW_HIDE)
        logger.info("Console window hidden")
        return True
    except Exception as e:
        logger.warning(f"Failed to hide console window: {e}")
        return False


def set_console_title(title: str) -> bool:
    """Set the console window title."""
    if not title:
        return False
    try:
        _kernel32.SetConsoleTitleW(title)
        logger.info(f"Console title set to: {title}")
        return True
    except Exception as e:
        logger.warning(f"Failed to set console title: {e}")
        return False


def set_window_text(hwnd: int, title: str) -> bool:
    """Set the text/title of an arbitrary window."""
    if not hwnd or not title:
        return False
    try:
        _user32.SetWindowTextW(hwnd, title)
        return True
    except Exception as e:
        logger.warning(f"Failed to set window text: {e}")
        return False


def enum_windows(callback: Callable[[int], None]) -> None:
    """Enumerate top-level windows and call ``callback(hwnd)`` for each."""
    @_ENUM_WINDOWS_PROC
    def _enum_proc(hwnd, _lparam):
        callback(int(hwnd))
        return True

    try:
        _user32.EnumWindows(_enum_proc, None)
    except Exception as e:
        logger.warning(f"EnumWindows failed: {e}")


def get_window_text(hwnd: int) -> str:
    """Return the window title of ``hwnd`` or an empty string."""
    try:
        length = _user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        _user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception as e:
        logger.debug(f"GetWindowText failed: {e}")
        return ""


def get_window_thread_process_id(hwnd: int) -> tuple[int, int]:
    """Return ``(thread_id, process_id)`` for the window."""
    pid = ctypes.c_ulong(0)
    try:
        tid = _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return tid, pid.value
    except Exception as e:
        logger.debug(f"GetWindowThreadProcessId failed: {e}")
        return 0, 0


def find_windows_by_title(title: str) -> list[int]:
    """Return all top-level HWNDs whose titles contain ``title``."""
    matches: list[int] = []

    def _check(hwnd: int) -> None:
        if title in get_window_text(hwnd):
            matches.append(hwnd)

    enum_windows(_check)
    return matches


def find_own_windows() -> list[int]:
    """Return top-level HWNDs that belong to the current process."""
    current_pid = os.getpid()
    matches: list[int] = []

    def _check(hwnd: int) -> None:
        _, pid = get_window_thread_process_id(hwnd)
        if pid == current_pid:
            matches.append(hwnd)

    enum_windows(_check)
    return matches


_original_main_window_title: str | None = None
_original_application_name: str | None = None


def set_main_window_title(title: str) -> bool:
    """Set the Qt main window title if the main window exists.

    This is the preferred way to disguise the window title because
    qfluentwidgets' FluentWindow uses a custom title bar that only updates
    when Qt's own setWindowTitle() is called. Win32 SetWindowTextW changes the
    taskbar text but not the in-window title bar.

    In addition to the window title, QApplication's application name and
    display name are updated so Windows does not render the title as
    ``<window title> - <app name>`` in the taskbar or Alt-Tab.
    """
    global _original_main_window_title, _original_application_name
    if not title:
        return False
    try:
        from ok import og
        from PySide6.QtWidgets import QApplication
        main_window = getattr(og, 'main_window', None)
        if main_window is None:
            logger.debug("No Qt main window available yet")
            return False
        if _original_main_window_title is None:
            _original_main_window_title = main_window.windowTitle()
        main_window.setWindowTitle(title)

        app = QApplication.instance()
        if app is not None:
            if _original_application_name is None:
                _original_application_name = app.applicationDisplayName()
            app.setApplicationName(title)
            app.setApplicationDisplayName(title)

        logger.info(f"Set Qt main window title to: {title}")
        return True
    except Exception as e:
        logger.warning(f"Failed to set Qt main window title: {e}")
        return False


def restore_main_window_title() -> bool:
    """Restore the Qt main window title to its original value."""
    global _original_main_window_title, _original_application_name
    if _original_main_window_title is None and _original_application_name is None:
        return False
    try:
        from ok import og
        from PySide6.QtWidgets import QApplication
        main_window = getattr(og, 'main_window', None)
        if main_window is not None and _original_main_window_title is not None:
            main_window.setWindowTitle(_original_main_window_title)
            logger.info(f"Restored Qt main window title to: {_original_main_window_title}")

        app = QApplication.instance()
        if app is not None and _original_application_name is not None:
            app.setApplicationName(_original_application_name)
            app.setApplicationDisplayName(_original_application_name)
            logger.info(f"Restored application name to: {_original_application_name}")
        return True
    except Exception as e:
        logger.warning(f"Failed to restore Qt main window title: {e}")
        return False


def set_own_window_title(title: str) -> bool:
    """Set the title of the current process's first top-level window."""
    if not title:
        return False
    hwnds = find_own_windows()
    if not hwnds:
        logger.debug("No top-level window found for the current process")
        return False
    for hwnd in hwnds:
        set_window_text(hwnd, title)
    logger.info(f"Set current process window title to: {title}")
    return True


def rename_own_gui_window(old_title: str, new_title: str) -> bool:
    """
    Rename a running GUI window belonging to this process from ``old_title`` to
    ``new_title``.

    This is a fallback for when the window has already been created with the
    original title (e.g. when applying disguise after startup). Only windows
    owned by the current process are touched to avoid renaming other
    applications.
    """
    if not old_title or not new_title:
        return False

    hwnds = [hwnd for hwnd in find_own_windows() if old_title in get_window_text(hwnd)]
    if not hwnds:
        logger.debug(f"No own window with title containing '{old_title}' found")
        return False

    for hwnd in hwnds:
        if set_window_text(hwnd, new_title):
            logger.info(f"Renamed own GUI window {hwnd} title to: {new_title}")
    return True


@dataclass
class DisguiseConfig:
    enabled: bool = False
    hide_console: bool = True
    console_title: str = ""
    gui_title: str = ""
    rename_existing_window: bool = False
    old_gui_title: str = "ok-dna"

    def effective_gui_title(self) -> str:
        return self.gui_title or self.old_gui_title


def apply_disguise(cfg: DisguiseConfig) -> DisguiseConfig:
    """
    Apply runtime disguise settings.

    Returns the same config object so callers can read the effective GUI title.
    """
    if not cfg.enabled:
        logger.debug("Disguise is disabled")
        restore_main_window_title()
        return cfg

    if cfg.hide_console:
        hide_console_window()

    if cfg.console_title:
        set_console_title(cfg.console_title)

    if cfg.rename_existing_window and cfg.old_gui_title and cfg.gui_title:
        rename_own_gui_window(cfg.old_gui_title, cfg.gui_title)

    return cfg


def apply_disguise_from_config(cfg: dict, debug: bool = False) -> DisguiseConfig:
    """
    Apply disguise settings directly from a raw configuration mapping.

    This is used both at startup and when the user changes a disguise option
    in the GUI so that the change takes effect immediately.

    When ``debug`` is True the console window is never hidden so that logs
    remain visible during development.
    """
    enabled = cfg.get("启用伪装", False)
    gui_title = cfg.get("GUI窗口标题", "") if enabled else ""
    console_title = cfg.get("控制台窗口标题", "") if enabled else ""
    hide_console = cfg.get("隐藏控制台窗口", True) if enabled else False
    if debug:
        hide_console = False

    result = apply_disguise(DisguiseConfig(
        enabled=enabled,
        hide_console=hide_console,
        console_title=console_title,
        gui_title=gui_title,
        rename_existing_window=False,
        old_gui_title="",
    ))

    if enabled and gui_title:
        set_main_window_title(gui_title)
    else:
        restore_main_window_title()

    if enabled and cfg.get("修改PEB映像路径", False):
        from src.disguise_peb import apply_peb_disguise, PebDisguiseConfig
        fake_path = cfg.get("PEB伪装的映像路径", r"C:\Windows\System32\svchost.exe")
        fake_cmd = cfg.get("PEB伪装的命令行", "") or fake_path
        apply_peb_disguise(PebDisguiseConfig(
            enabled=True,
            fake_image_path=fake_path,
            fake_command_line=fake_cmd,
        ))

    return result


def load_disguise_config(defaults: dict | None = None) -> dict:
    """Load the saved '伪装进程' config, falling back to ``defaults``."""
    from ok.util.config import Config
    defaults = defaults or {}
    try:
        cfg = Config('伪装进程', defaults)
        return dict(cfg)
    except Exception as e:
        logger.warning(f"Failed to load saved disguise config: {e}")
        return dict(defaults)


def main() -> int:
    """Small CLI smoke-test for the disguise helpers."""
    cfg = DisguiseConfig(
        enabled=True,
        hide_console=False,
        console_title="Disguised Console",
        gui_title="Disguised GUI",
    )
    apply_disguise(cfg)
    print(f"Console title set (if visible). Effective GUI title: {cfg.effective_gui_title()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
