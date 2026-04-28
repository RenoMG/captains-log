from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl, Dimension
from prompt_toolkit.widgets import TextArea, Frame, RadioList
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.filters import Condition
import random, textwrap, shutil
from functions import change_logs_location_question, convert_date_to_julian
from database.db import create_new_db
from config.config import load_data, motd, config_json_write
from styles.lcars import LCARS_STYLE


def run_settings():
    # Responsive terminal helpers.
    # These are functions instead of fixed values so resizing the terminal
    # updates the rendered text and prompt_toolkit layout dimensions.
    def terminal_size():
        size = shutil.get_terminal_size((80, 24))
        return size.columns, size.lines

    def content_width():
        columns, _ = terminal_size()
        return max(20, min(columns - 1, 120))

    def max_visible():
        _, rows = terminal_size()
        return max(min((rows - 9) // 3, 20), 1)

    def flexible_height(preferred, minimum=1, weight=1):
        return Dimension(preferred=max(preferred, minimum), min=minimum, weight=weight)

    def content_panel_height():
        _, rows = terminal_size()
        return max(rows - max_visible() - 9, 3)

    config_data = None
    get_motd = None

    def refresh_config_data():
        nonlocal config_data, get_motd
        config_data = load_data()

        if config_data["custom_MOTD_enabled"] is False:
            get_motd = motd[random.randrange(len(motd))]
        else: 
            get_motd = config_data["custom_motd"]

    refresh_config_data()

    def check_motd_captain_name():
        if "{captain_name}" in get_motd:
            return get_motd.format(captain_name=config_data["name"])
        else:
            return get_motd

    # Dynamic border helpers
    def _border_top(title=""):
        inner = f"─── {title} " if title else ""
        padding = max(content_width() - len(inner) - 2, 0)
        return f"╭{inner}{'─' * padding}╮"

    def _border_bottom():
        return f"╰{'─' * max(content_width() - 2, 0)}╯"

    #TUI Variables
    SETTINGS_ITEMS = [("Set Name", "The Captain's Name! Captain for default,\n  or your own name!", "name"), 
                    ("Set MOTD", "The MOTD! Use a default set or set your own MOTD!\n  Use {captain_name} to use your name!", "custom_motd"), 
                    ("Set Logs Location", "Location to store Captain's Logs! Use the default or\n  your own location!", "logs_location")]

    current_selection = [0]

    scroll_offset = [0]

    editing = [False]
    editing_location = [False]

    status_message = "Settings Loaded!"

    NEW_DB_BODY = "This is a new database, did you move location?\n\nOld database should be at captains_log/storage/logs!"

    def get_header():
        jd = convert_date_to_julian()
        title_text = "  FILE = SETTINGS  "
        date_text = f"JULIANDATE {jd}"
        fixed_visible = 1 + len(title_text) + 1 + 3 + 1 + 2 + 1 + len(date_text) + 1 + 1
        bar_len = max(content_width() - fixed_visible, 4)

        return FormattedText([
            ('class:gold', '█' * bar_len),
            ('', ' '),
            ('class:header', title_text),
            ('', ' '),
            ('class:gold', '███'),
            ('', ' '),
            ('class:orange', '██'),
            ('', ' '),
            ('class:stardate', date_text),
            ('', ' '),
            ('class:orange', '█'),
            ('', '\n'),
            ('class:title', f'MOTD: {textwrap.shorten(check_motd_captain_name(), width=max(content_width() - 7, 10), placeholder="...")}\n\n'),
            ('', '\n'),
        ])

    def get_settings_list():
        lines = [('class:title', f'{_border_top("ACCESS FILE = SETTINGS")}\n')]

        visible_entries = SETTINGS_ITEMS[scroll_offset[0]:scroll_offset[0] + max_visible()]
        
        for i, (setting, _, _) in enumerate(visible_entries):
            actual_index = i + scroll_offset[0]
            if actual_index == current_selection[0]:
                marker = ('class:status-on', ' ● ')
                style = 'class:text bold'
            else:
                marker = ('class:status-off', ' ○ ')
                style = 'class:data'
            
            lines.append(marker)
            lines.append((style, f'{setting}\n'))
        
        total = len(SETTINGS_ITEMS)
        lines.append(('class:title', f' ○ Showing {scroll_offset[0]+1}-{min(scroll_offset[0] + max_visible(), total)} of {total} SETTINGS\n'))
        lines.append(('class:title', f'{_border_bottom()}\n'))
        lines.append(('class:data', 'Some helpful information:\n\n'))
        lines.append(('class:data', 'Use {captain_name} to insert your name into a\ncustom MOTD!\n\n'))
        lines.append(('class:data', 'If you change the Logs location, you will have to\nmanually move your database file from the\ndefault location at /captains_log/storage/logs.\nA new database will be created if none exist!\n\n'))
        lines.append(('class:data', 'Stay safe among the stars!'))
        return FormattedText(lines)

    def get_setting_details():
        setting = SETTINGS_ITEMS[current_selection[0]]
        blue_bar_len = max(content_width() - 35, 1)

        lines = [('class:gold', '████')]
        lines.append(('class:gold', '████'))
        lines.append(('', ' '))
        lines.append(('class:header', ' CURRENT VALUES '))
        lines.append(('', ' '))
        lines.append(('class:blue', '█' * blue_bar_len))
        lines.append(('', '\n\n'))
        lines.append(('class:title', f'  Setting: {setting[0]}\n'))
        lines.append(('class:title', f'  Details:\n  {setting[1]}\n\n'))
        lines.append(('class:title', f'{_border_top()}\n'))
        lines.append(('class:data', f' Current Value:\n\n'))
        lines.append(('class:data', f' "{config_data[setting[2]]}"\n\n'))
        if setting[0] == "Set MOTD":
            lines.append(('class:data', f' "Enabled: {config_data["custom_MOTD_enabled"]}"'))
        return FormattedText(lines)

    def get_footer():
        footer_parts = [
            ('class:gold', '███████'),
            ('', ' '),
            ('class:header', ' ↑↓ '),
            ('', ' SELECT  '),
            ('class:header', ' E '),
            ('', ' EDIT  '),
            ('class:orange', ' D '),
            ('', ' DEFAULT '),
            ('class:orange', ' H '),
            ('', ' HOME '),
        ]
        text_len = sum(len(text) for _, text in footer_parts)
        fill = max(content_width() - text_len, 1)
        footer_parts.append(('class:gold', '█' * fill))

        return FormattedText([
            ('class:title', f'{_border_bottom()}\n'),
            ('class:title', f'  {status_message}\n'),
            ('', '\n'),
        ] + footer_parts)

    # Controls
    list_control = FormattedTextControl(get_settings_list)
    content_control = FormattedTextControl(get_setting_details)
    header_control = FormattedTextControl(get_header)
    footer_control = FormattedTextControl(get_footer)

    # Editor (hidden initially)
    editor = TextArea(
        text="",
        multiline=False,
        height=1,
    )

    location_editor = TextArea(
        text="",
        multiline=False,
        height=1,
        validator=change_logs_location_question()
    )

    enable_disable = RadioList(
        values=[(True, "Enable"), (False, "Disable")])


    def get_layout():
        if editing[0]:
            if SETTINGS_ITEMS[current_selection[0]][2] == "custom_motd":
                content_panel = HSplit([
                    Window(content_control, height=flexible_height(12, minimum=5)),
                    Frame(editor, title="EDIT SETTING [Ctrl+S save, Esc cancel]"),
                    Frame(enable_disable, title="ENABLE CUSTOM MOTD [Mouse Input]"),
                ], height=flexible_height(content_panel_height(), weight=2))
            else:
                content_panel = HSplit([
                    Window(content_control, height=flexible_height(12, minimum=5)),
                    Frame(editor, title="EDIT SETTING [Ctrl+S save, Esc cancel]"),
                ], height=flexible_height(content_panel_height(), weight=2))
        elif editing_location[0]:
            content_panel = HSplit([
                Window(content_control, height=flexible_height(12, minimum=5)),
                Frame(location_editor, title="EDIT LOG LOCATION [Ctrl+S save, Esc cancel]"),
            ], height=flexible_height(content_panel_height(), weight=2))
        else:
            content_panel = Window(content_control, height=flexible_height(content_panel_height(), weight=2))

        return Layout(HSplit([
            Window(header_control, height=flexible_height(2)),
            Window(list_control, height=flexible_height(max_visible() + 3)),
            content_panel,
            Window(footer_control, height=flexible_height(4)),
        ]))

    kb = KeyBindings()

    @Condition
    def editing_active():
        if editing[0] or editing_location[0]:
            return False
        else:
            return True

    @kb.add('up', filter=editing_active)
    def nav_up(event):
        current_selection[0] = max(0, current_selection[0] - 1)
        if current_selection[0] < scroll_offset[0]:
            scroll_offset[0] = current_selection[0]

    @kb.add('down', filter=editing_active)
    def nav_down(event):
        current_selection[0] = min(len(SETTINGS_ITEMS) - 1, current_selection[0] + 1)
        if current_selection[0] >= scroll_offset[0] + max_visible():
            scroll_offset[0] = current_selection[0] - max_visible() + 1

    @kb.add('e', filter=editing_active)
    def edit_log_content(event):
        if not editing[0] and not editing_location[0]:
            if SETTINGS_ITEMS[current_selection[0]][2] == "logs_location":
                editing_location[0] = True
                location_editor.text = config_data[SETTINGS_ITEMS[current_selection[0]][2]]
                event.app.layout = get_layout()
                event.app.layout.focus(location_editor)
            else:
                editing[0] = True
                editor.text = config_data[SETTINGS_ITEMS[current_selection[0]][2]]
                event.app.layout = get_layout()
                event.app.layout.focus(editor)

    @kb.add('d', filter=editing_active)
    def default_value(event):
        nonlocal status_message
        if SETTINGS_ITEMS[current_selection[0]][2] == "name":
            config_data["name"] = "Captain"
            config_json_write(config_data)
            refresh_config_data()
            status_message = f"Name Updated: Captain"
            event.app.layout = get_layout()
        if SETTINGS_ITEMS[current_selection[0]][2] == "custom_motd":
            config_data["custom_motd"] = "None"
            config_data["custom_MOTD_enabled"] = False
            config_json_write(config_data)
            refresh_config_data()
            status_message = f"MOTD Updated: Default MOTD"
            event.app.layout = get_layout()

        if SETTINGS_ITEMS[current_selection[0]][2] == "logs_location":
            config_data["logs_location"] = "storage/logs/"
            config_json_write(config_data)
            refresh_config_data()
            status_message = f"Log Location Updated: storage/logs/"
            try:
                create_new_db(convert_date_to_julian(), NEW_DB_BODY)
            except FileExistsError:
                status_message = "Database exists, skipping creation! Log Location Updated: storage/logs/"
            event.app.layout = get_layout()

    @kb.add('c-s')
    def save_entry(event):
        nonlocal status_message
        if editing[0]:
            if SETTINGS_ITEMS[current_selection[0]][2] == "name":
                config_data["name"] = editor.text
                config_json_write(config_data)
                refresh_config_data()
                editing[0] = False
                status_message = f"Name Updated: {textwrap.shorten(editor.text, width=30, placeholder='...')}"
                event.app.layout = get_layout()
            if SETTINGS_ITEMS[current_selection[0]][2] == "custom_motd":
                config_data["custom_motd"] = editor.text
                config_data["custom_MOTD_enabled"] = enable_disable.current_value
                config_json_write(config_data)
                refresh_config_data()
                editing[0] = False
                status_message = f"MOTD Updated: {textwrap.shorten(editor.text, width=30, placeholder='...')}"
                event.app.layout = get_layout()
        if editing_location[0]:
            buffer = location_editor.buffer
            if buffer.validate():
                config_data["logs_location"] = location_editor.text
                config_json_write(config_data)
                refresh_config_data()
                editing_location[0] = False
                status_message = f"Log Location Updated: {textwrap.shorten(location_editor.text, width=30, placeholder='...')}"
                try:
                    create_new_db(convert_date_to_julian(), NEW_DB_BODY)
                except FileExistsError:
                    status_message = "Database exists, skipping creation! Log location updated."
                event.app.layout = get_layout()
            else:
                status_message = buffer.validation_error

    @kb.add('escape')
    def cancel_edit(event):
        if editing[0]:
            editing[0] = False
            event.app.layout = get_layout()
        if editing_location[0]:
            editing_location[0] = False
            event.app.layout = get_layout()

    @kb.add('h', filter=editing_active)
    def go_home(event):
        event.app.exit()

    @kb.add('H', filter=editing_active)
    def go_home_uppercase(event):
        event.app.exit()

    settings_menu = Application(
        layout=get_layout(),
        key_bindings=kb,
        style=LCARS_STYLE,
        full_screen=True,
        mouse_support=True,
        terminal_size_polling_interval=0.5,
    )

    return settings_menu