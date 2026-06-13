import ok
from src.config import config, disguise_config_option
from src.disguise import apply_disguise_from_config, load_disguise_config

if __name__ == '__main__':
    # Apply disguise as early as possible so the console / window titles are
    # camouflaged before ok-script creates the GUI. Load the user's saved
    # disguise config so the title persists across restarts.
    disguise_cfg = load_disguise_config(disguise_config_option.default_config)
    apply_disguise_from_config(disguise_cfg)

    # Use the saved/custom GUI title as the framework window title so the window
    # is created with the correct name instead of being renamed after the fact.
    custom_gui_title = disguise_cfg.get('GUI窗口标题', '')
    if disguise_cfg.get('启用伪装', False) and custom_gui_title:
        config['gui_title'] = custom_gui_title

    ok = ok.OK(config)
    ok.start()
