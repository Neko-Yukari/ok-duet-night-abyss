import ok
from src.config import config, disguise_config_option
from src.disguise import apply_disguise_from_config, load_disguise_config

if __name__ == '__main__':
    config['debug'] = True

    # In debug mode we still allow title disguise but keep the console visible
    # so that debug output remains accessible. Load the saved disguise config
    # so the custom title persists across restarts.
    disguise_cfg = dict(load_disguise_config(disguise_config_option.default_config))
    disguise_cfg['隐藏控制台窗口'] = False
    apply_disguise_from_config(disguise_cfg)

    custom_gui_title = disguise_cfg.get('GUI窗口标题', '')
    if disguise_cfg.get('启用伪装', False) and custom_gui_title:
        config['gui_title'] = custom_gui_title

    ok = ok.OK(config)
    ok.start()
