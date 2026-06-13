import ok
from src.config import config, disguise_config_option
from src.disguise import DisguiseConfig, apply_disguise

if __name__ == '__main__':
    config = config
    config['debug'] = True

    # In debug mode we still allow title disguise but keep the console visible
    # so that debug output remains accessible.
    disguise_defaults = disguise_config_option.default_config
    effective_gui_title = config.get('gui_title', 'ok-dna')

    if disguise_defaults.get('启用伪装', False):
        custom_title = disguise_defaults.get('GUI窗口标题', '')
        if custom_title:
            effective_gui_title = custom_title
            config['gui_title'] = custom_title

        apply_disguise(DisguiseConfig(
            enabled=True,
            hide_console=False,  # keep console for debug output
            console_title=disguise_defaults.get('控制台窗口标题', ''),
            gui_title=effective_gui_title,
            rename_existing_window=False,
            old_gui_title='ok-dna',
        ))

    ok = ok.OK(config)
    ok.start()
