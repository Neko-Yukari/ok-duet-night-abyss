import ok
from src.config import config, disguise_config_option
from src.disguise import apply_disguise_from_config

if __name__ == '__main__':
    # Apply disguise as early as possible so the console / window titles are
    # camouflaged before ok-script creates the GUI. The same helper is reused
    # later by src.globals when the user changes a disguise option at runtime.
    disguise_defaults = disguise_config_option.default_config
    apply_disguise_from_config(disguise_defaults)

    # Use the saved/custom GUI title as the framework window title so the window
    # is created with the correct name instead of being renamed after the fact.
    custom_gui_title = disguise_defaults.get('GUI窗口标题', '')
    if disguise_defaults.get('启用伪装', False) and custom_gui_title:
        config['gui_title'] = custom_gui_title

    ok = ok.OK(config)
    ok.start()
