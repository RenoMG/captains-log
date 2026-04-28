from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl, Dimension
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.filters import Condition
import random, textwrap, shutil
from functions import convert_date_to_julian
from pathlib import Path
from database.db import list_log_names, list_all_log_data, edit_log, edit_log_title, create_log, delete_log, l, LOGS_DB, create_new_db
from config.config import load_data, motd
from settings_ui import run_settings as settings_app
from styles.lcars import LCARS_STYLE

def run_main():
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
        
    if Path(l / LOGS_DB).exists() is False:
        create_new_db(2439374.5000000, "Uh oh, no database found on boot... did you delete it?")

    #TUI Variables
    LOG_ENTRIES = list_all_log_data()

    current_selection = [0]

    scroll_offset = [0]

    editing = [False]
    editing_title = [False]
    creating_log = [False]
    deleting_log = [False]

    status_message = "Boot Success!"

    # Dynamic border helpers
    def _border_top(title=""):
        inner = f"─── {title} " if title else ""
        padding = max(content_width() - len(inner) - 2, 0)
        return f"╭{inner}{'─' * padding}╮"

    def _border_bottom():
        return f"╰{'─' * max(content_width() - 2, 0)}╯"

    def get_header():
        jd = convert_date_to_julian()
        title_text = "  FILE = CAPTAIN'S LOG  "
        date_text = f"JULIANDATE {jd}"
        # Calculate how many █ needed to fill the first gold block
        # Fixed visible parts: space + title(24) + space + ███(3) + space + ██(2) + space + date + space + █(1)
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

    def get_log_list():
        name_width = max(content_width() - 35, 4)
        lines = [('class:title', _border_top("ACCESS FILE = CAPTAIN'S LOG") + '\n')]

        visible_entries = LOG_ENTRIES[scroll_offset[0]:scroll_offset[0] + max_visible()]
        
        for i, (title, jd, _) in enumerate(visible_entries):
            actual_index = i + scroll_offset[0]
            if actual_index == current_selection[0]:
                marker = ('class:status-on', ' ● ')
                style = 'class:text bold'
            else:
                marker = ('class:status-off', ' ○ ')
                style = 'class:data'
            
            lines.append(marker)
            lines.append((style, f'Enterprise NX-01 DATE {jd}  {textwrap.shorten(config_data["name"], width=name_width, placeholder="...")}\n'))
        
        total = len(LOG_ENTRIES)
        lines.append(('class:title', f' ○ Showing {scroll_offset[0]+1}-{min(scroll_offset[0] + max_visible(), total)} of {total} LOGS\n'))
        lines.append(('class:title', f'{_border_bottom()}'))
        return FormattedText(lines)

    def get_log_content():
        body_width = max(content_width() - 4, 10)
        title_max = max(content_width() - 12, 10)
        blue_bar_len = max(content_width() - 35, 1)
        try: 
            title, jd, body = LOG_ENTRIES[current_selection[0]]
            return FormattedText([
                ('class:gold', '████'),
                ('', ' '),
                ('class:header', f' {textwrap.shorten(config_data["name"], width=25, placeholder="...")} '),
                ('', ' '),
                ('class:blue', '█' * blue_bar_len),
                ('', '\n\n'),
                ('class:title', f'  Title: {textwrap.shorten(title, width=title_max, placeholder="...")}\n'),
                ('class:title', f'  Juliandate: {jd}\n'),
                ('class:title', f'  Ship: Enterprise NX-01\n\n'),
                ('class:title', f'  Log Excerpt:\n\n'),
                ('class:title', f'{_border_top()}\n'),
                ('class:data', f'{textwrap.indent(textwrap.fill(body, width=body_width, placeholder=" ...", replace_whitespace=False), "  ")}\n')
            ])
        except IndexError:
            empty_body = (
                "Well, seems like you either just deleted your last log or have no logs at all? "
                "Hmm, better get to typing! You dont want me calling the Romulans, right?\n"
                "Does this count as an Easter Egg, or just bad programming?"
            )
            wrapped_body = textwrap.indent(
                textwrap.fill(
                    empty_body,
                    width=body_width,
                    placeholder=" ...",
                    replace_whitespace=False,
                ),
                "  ",
            )
            return FormattedText([
                ('class:gold', '████'),
                ('', ' '),
                ('class:header', f' {textwrap.shorten(config_data["name"], width=25, placeholder="...")} '),
                ('', ' '),
                ('class:blue', '█' * blue_bar_len),
                ('', '\n\n'),
                ('class:title', f'  Title: A log in the void\n'),
                ('class:title', f'  Juliandate: {convert_date_to_julian()}\n'),
                ('class:title', f'  Ship: Enterprise NX-01\n\n'),
                ('class:title', f'  Log Excerpt:\n\n'),
                ('class:title', f'{_border_top()}\n'),
                ('class:data', f'{wrapped_body}\n')
            ])

    def get_footer():
        # Build dynamic bottom LCARS bar
        footer_parts = [
            ('class:gold', '█'),
            ('', ' '),
            ('class:header', ' ↑↓ '),
            ('', ' SELECT  '),
            ('class:header', ' E / R '),
            ('', ' EDIT  '),
            ('class:header', ' C '),
            ('', ' NEW  '),
            ('class:orange', ' D '),
            ('', ' DEL '),
            ('class:orange', ' S '),
            ('', ' SETTINGS  '),
            ('class:orange', ' Q '),
            ('', ' QUIT  '),
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
    list_control = FormattedTextControl(get_log_list)
    content_control = FormattedTextControl(get_log_content)
    header_control = FormattedTextControl(get_header)
    footer_control = FormattedTextControl(get_footer)

    # Editor (hidden initially)
    editor_title = TextArea(
        text="",
        multiline=False,
        height=1,
    )

    editor = TextArea(
        text="",
        multiline=True,
        wrap_lines=True,
        height=16,
    )

    def refresh_logs(main_app):
        nonlocal LOG_ENTRIES
        LOG_ENTRIES = list_all_log_data()
        main_app.invalidate()  # Forces a redraw

    # Dynamic content panel height

    def get_layout():
        if editing[0]:
            content_panel = HSplit([
                Window(content_control, height=flexible_height(9, minimum=5)),
                Frame(editor, title="EDIT LOG ENTRY [Ctrl+S save, Esc cancel]"),
            ], height=flexible_height(content_panel_height(), weight=2))
        elif editing_title[0]:
            content_panel = HSplit([
                Window(content_control, height=flexible_height(8, minimum=5)),
                Frame(editor_title, title="EDIT TITLE [Ctrl+S save, Esc cancel]"),
            ], height=flexible_height(content_panel_height(), weight=2))
        elif creating_log[0]:
            content_panel = HSplit([
                Window(content_control, height=flexible_height(8, minimum=5)),
                Frame(editor_title, title="CREATE LOG - TITLE [Ctrl+S save, Esc cancel]"),
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
        if editing[0] or editing_title[0] or creating_log[0]:
            return False
        else:
            return True
        
    @Condition
    def delete_confirm():
        if deleting_log[0] is False:
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
        current_selection[0] = min(len(LOG_ENTRIES) - 1, current_selection[0] + 1)
        if current_selection[0] >= scroll_offset[0] + max_visible():
            scroll_offset[0] = current_selection[0] - max_visible() + 1

    @kb.add('e', filter=editing_active)
    def edit_log_content(event):
        if not editing[0] and not editing_title[0] and not creating_log[0] and not deleting_log[0]:
            if len(LOG_ENTRIES) == 0:
                nonlocal status_message
                status_message = "You have no logs to edit!"
            else:
                editing[0] = True
                editor.text = LOG_ENTRIES[current_selection[0]][2]
                event.app.layout = get_layout()
                event.app.layout.focus(editor)

    @kb.add('r', filter=editing_active)
    def rename_log(event):
        if not editing[0] and not editing_title[0] and not creating_log[0] and not deleting_log[0]:
            if len(LOG_ENTRIES) == 0:
                nonlocal status_message
                status_message = "You have no logs to rename!"
            else:
                editing_title[0] = True
                editor_title.text = LOG_ENTRIES[current_selection[0]][0]
                editor.text = LOG_ENTRIES[current_selection[0]][2]
                event.app.layout = get_layout()
                event.app.layout.focus(editor_title)

    @kb.add('d', filter=editing_active)
    def default_value(event):
        if not editing[0] and not editing_title[0] and not creating_log[0] and not deleting_log[0]:
            if len(LOG_ENTRIES) == 0:
                nonlocal status_message
                status_message = "You have no logs to delete!"
            else:
                deleting_log[0] = True
                status_message = f"Delete Log: {textwrap.shorten(LOG_ENTRIES[current_selection[0]][0], width=23, placeholder='...')}?"
                event.app.layout = get_layout()

    @kb.add('y', filter=delete_confirm)
    def confirm_yes(event):
        if not editing[0] and not editing_title[0] and not creating_log[0]:
            nonlocal status_message
            status_message = f"Deleted Log: {textwrap.shorten(LOG_ENTRIES[current_selection[0]][0], width=23, placeholder='...')}"
            delete_log(LOG_ENTRIES[current_selection[0]][0])
            current_selection[0] = max(0, current_selection[0] - 1)
            if current_selection[0] < scroll_offset[0]:
                scroll_offset[0] = current_selection[0]
            refresh_logs(event.app)
            deleting_log[0] = False

    @kb.add('n', filter=delete_confirm)
    def confirm_no(event):
        if not editing[0] and not editing_title[0] and not creating_log[0]:
            nonlocal status_message
            deleting_log[0] = False
            status_message = "Log Deletion Aborted!"

    @kb.add('c-s')
    def save_entry(event):
        nonlocal status_message
        if editing[0]:
            editor.title = LOG_ENTRIES[current_selection[0]][0]
            edit_log(editor.title, editor.text)
            refresh_logs(event.app)
            editing[0] = False
            status_message = f"Edited Log: {textwrap.shorten(editor.title, width=23, placeholder='...')}"
            event.app.layout = get_layout()

        if editing_title[0]:
            editor.title = LOG_ENTRIES[current_selection[0]][0]
            if editor_title.text in list_log_names():
                status_message = f"Error: Title already exists!"
            else:
                edit_log_title(editor.title, editor_title.text)
                refresh_logs(event.app)
                editing_title[0] = False
                status_message = f"Edited Title: Old: {textwrap.shorten(editor.title, width=14, placeholder='...')} / New: {textwrap.shorten(editor_title.text, width=14, placeholder='...')}"
                event.app.layout = get_layout()

        if creating_log[0]:
            create_log(editor_title.text, convert_date_to_julian())
            refresh_logs(event.app)
            creating_log[0] = False
            status_message = f"Created Log: {textwrap.shorten(editor_title.text, width=23, placeholder='...')}"
            event.app.layout = get_layout()

    @kb.add('escape')
    def cancel_edit(event):
        if editing[0]:
            editing[0] = False
            event.app.layout = get_layout()

        if editing_title[0]:
            editing_title[0] = False
            event.app.layout = get_layout()

        if creating_log[0]:
            creating_log[0] = False
            event.app.layout = get_layout()

    @kb.add('c', filter=editing_active)
    def new_entry(event):
        if not editing[0] and not editing_title[0] and not creating_log[0] and not deleting_log[0]:
            creating_log[0] = True
            editor_title.text = "Set a Title"
            event.app.layout = get_layout()
            refresh_logs(event.app)
            event.app.layout.focus(editor_title)

    @kb.add('s', filter=editing_active)
    async def open_settings(event):
        event.app.exit(result="settings")


    @kb.add('q', filter=editing_active)
    def quit_app(event):
        event.app.exit()

    @kb.add('Q', filter=editing_active)
    def quit_app_uppercase(event):
        event.app.exit()

    main_app = Application(
        layout=get_layout(),
        key_bindings=kb,
        style=LCARS_STYLE,
        full_screen=True,
        mouse_support=True,
        terminal_size_polling_interval=0.5,
    )

    # Navigation loop
    current = "main"
    while True:
        if current == "main":
            result = main_app.run()
            current = result if result else "quit"
        elif current == "settings":
            settings = settings_app()  # calls run_settings(), returns Application
            result = settings.run()
            current = result if result else "main"  # default back to main
            refresh_config_data()
            scroll_offset = [0]
            current_selection = [0]
            refresh_logs(main_app)
        elif current == "quit":
            break