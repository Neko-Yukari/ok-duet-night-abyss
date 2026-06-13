from PySide6.QtCore import QObject, Signal
from pynput import mouse, keyboard
import concurrent.futures
from qfluentwidgets import DoubleSpinBox
from PySide6.QtWidgets import QApplication
from ok import Logger, og
from ok.util.config import Config
from threading import Event

from src.disguise import apply_disguise_from_config

logger = Logger.get_logger(__name__)

# --- 猴子补丁 ---
# 修改 DoubleSpinBox，使其默认拥有一个更大的最大值
_original_init = DoubleSpinBox.__init__


def _new_init(self, *args, **kwargs):
    _original_init(self, *args, **kwargs)
    self.setMaximum(99999.0)


DoubleSpinBox.__init__ = _new_init


# --- 伪装配置实时生效钩子 ---
# ok-script 的 Config 在 __setitem__ 时持久化到文件，但没有发布变化事件。
# 这里补丁 __setitem__，当“伪装进程”配置的任意字段被修改时立即重新应用 disguise。
_config_setitem_patched = False


def _patch_config_setitem_for_disguise():
    global _config_setitem_patched
    if _config_setitem_patched:
        return
    _config_setitem_patched = True

    _original_config_setitem = Config.__setitem__

    def _patched_config_setitem(self, key, value):
        _original_config_setitem(self, key, value)
        try:
            if getattr(self, 'config_file', '').endswith('伪装进程.json'):
                apply_disguise_from_config(self)
        except Exception as e:
            logger.warning(f"Failed to apply disguise config change: {e}")

    Config.__setitem__ = _patched_config_setitem


def _apply_current_disguise_config():
    try:
        disguise_cfg = og.global_config.get_config('伪装进程')
        apply_disguise_from_config(disguise_cfg)
    except Exception as e:
        logger.warning(f"Failed to apply current disguise config: {e}")


# --- 猴子补丁 ---


class Globals(QObject):
    clicked = Signal(int, int, object, bool)
    pressed = Signal(object)

    def __init__(self, exit_event):
        super().__init__()
        self.pynput_mouse = None
        self.pynput_keyboard = None
        self._thread_pool_executor_max_workers = 0
        self.thread_pool_executor = None
        self.thread_pool_exit_event = Event()
        self.shared_frame = None
        exit_event.bind_stop(self)
        self.init_pynput()
        _patch_config_setitem_for_disguise()
        _apply_current_disguise_config()

    def on_show_main_window(self, main_window):
        """Called by ok-script after the main window is created but before it is shown.

        This is where we apply the GUI window title disguise. We do it here instead
        of at startup because the main window does not exist while Globals is being
        initialised, and we keep config['gui_title'] as "ok-dna" so internal widgets
        (StartCard, About, etc.) show the original name.
        """
        try:
            disguise_cfg = og.global_config.get_config('伪装进程')
            if disguise_cfg.get('启用伪装', False):
                gui_title = disguise_cfg.get('GUI窗口标题', '')
                if gui_title:
                    from src.disguise import set_main_window_title
                    set_main_window_title(gui_title)
        except Exception as e:
            logger.warning(f"Failed to apply disguise on main window show: {e}")

    def stop(self):
        logger.info("pynput stop")
        self.reset_pynput()
        self.shutdown_thread_pool_executor()

    def init_pynput(self):
        logger.info("pynput start")
        if self.pynput_mouse is None:
            self.pynput_mouse = mouse.Listener(on_click=self.on_click)
            self.pynput_mouse.start()
        if self.pynput_keyboard is None:
            self.pynput_keyboard = keyboard.Listener(on_press=self.on_press)
            self.pynput_keyboard.start()

    def reset_pynput(self):
        if self.pynput_mouse:
            self.pynput_mouse.stop()
            self.pynput_mouse = None
        if self.pynput_keyboard:
            self.pynput_keyboard.stop()
            self.pynput_keyboard = None

    def on_click(self, x, y, button, pressed):
        self.clicked.emit(x, y, button, pressed)

    def on_press(self, key):
        self.pressed.emit(key)

    def get_thread_pool_executor(self, max_workers=6):
        """
        获取全局执行器。
        如果请求的 max_workers 大于当前值，将安全地重建线程池。
        """
        if self.thread_pool_executor is not None and max_workers > self._thread_pool_executor_max_workers:
            logger.info(
                f"thread pool max_workers not enough, reset max_workers {self._thread_pool_executor_max_workers} -> {max_workers}")
            self.shutdown_thread_pool_executor()

        if self.thread_pool_executor is None:
            logger.info(f"create thread pool executor, max_workers: {max_workers}")
            self.thread_pool_exit_event.clear() 
            self.thread_pool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
            self._thread_pool_executor_max_workers = max_workers

        return self.thread_pool_executor

    def shutdown_thread_pool_executor(self):
        if self.thread_pool_executor is not None:
            logger.info("Shutting down thread pool executor...")
            self.thread_pool_exit_event.set()
            self.thread_pool_executor.shutdown(wait=False, cancel_futures=True)
            self.thread_pool_executor = None
            self._thread_pool_executor_max_workers = 0

    def submit_periodic_task(self, delay, task, *args, **kwargs):
        """
        提交一个循环任务到线程池。
        如果要停止循环，任务函数应返回 False。
        
        :param task: 要执行的函数
        :param delay: 每次执行后的间隔时间（秒）
        :param args: 位置参数
        :param kwargs: 关键字参数
        """
        executor = self.get_thread_pool_executor()

        def loop_wrapper():
            logger.debug(f"Periodic task {task.__name__} started.")
            
            while not self.thread_pool_exit_event.is_set():
                should_stop = False
                try:
                    if task(*args, **kwargs) is False:
                        should_stop = True
                except Exception as e:
                    logger.error(f"Error in periodic task {task.__name__}: {e}")

                if should_stop:
                    logger.debug(f"Periodic task {task.__name__} decided to stop.")
                    break
        
                if self.thread_pool_exit_event.wait(timeout=delay):
                    logger.debug(f"Periodic task {task.__name__} received stop signal.")
                    break
            
            logger.debug(f"Periodic task {task.__name__} stopped.")

        executor.submit(loop_wrapper)

if __name__ == "__main__":
    glbs = Globals(exit_event=None)
