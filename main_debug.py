import ok
from src.config import config, disguise_config_option
from src.disguise import apply_disguise_from_config, load_disguise_config

if __name__ == '__main__':
    config['debug'] = True

    # In debug mode we still allow title disguise but keep the console visible
    # so that debug output remains accessible. The GUI window title is applied
    # via Globals.on_show_main_window so internal widgets keep the "ok-dna" name.
    disguise_cfg = dict(load_disguise_config(disguise_config_option.default_config))
    disguise_cfg['隐藏控制台窗口'] = False
    apply_disguise_from_config(disguise_cfg)

    ok = ok.OK(config)
    ok.start()
