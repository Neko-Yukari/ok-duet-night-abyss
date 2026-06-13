import ok
from src.config import config, disguise_config_option
from src.disguise import apply_disguise_from_config, load_disguise_config

if __name__ == '__main__':
    # Apply disguise as early as possible so PEB / console settings take effect
    # before ok-script creates the GUI. The actual GUI window title is applied
    # later via Globals.on_show_main_window so the internal app name (StartCard,
    # About page, etc.) remains "ok-dna" while only the window title is disguised.
    disguise_cfg = load_disguise_config(disguise_config_option.default_config)
    apply_disguise_from_config(disguise_cfg)

    ok = ok.OK(config)
    ok.start()
