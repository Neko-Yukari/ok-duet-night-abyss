import ok
from src.config import config, disguise_config_option
from src.disguise import DisguiseConfig, apply_disguise

if __name__ == '__main__':
    # Load default disguise settings so the window/console can be camouflaged
    # before ok-script creates the GUI. User-saved config values will be applied
    # later by the framework; this just gives us an early, best-effort disguise.
    disguise_defaults = disguise_config_option.default_config
    effective_gui_title = config.get('gui_title', 'ok-dna')

    if disguise_defaults.get('启用伪装', False):
        custom_title = disguise_defaults.get('GUI窗口标题', '')
        if custom_title:
            effective_gui_title = custom_title
            config['gui_title'] = custom_title

        apply_disguise(DisguiseConfig(
            enabled=True,
            hide_console=disguise_defaults.get('隐藏控制台窗口', True),
            console_title=disguise_defaults.get('控制台窗口标题', ''),
            gui_title=effective_gui_title,
            rename_existing_window=False,
            old_gui_title='ok-dna',
        ))

    config = config
    ok = ok.OK(config)
    ok.start()
