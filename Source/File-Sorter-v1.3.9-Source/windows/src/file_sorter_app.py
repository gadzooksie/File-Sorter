"""File Sorter v1.3.9 cross-platform single-window GUI."""
from __future__ import annotations

import hashlib
from decimal import Decimal
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser

from sorter_core import (VERSION, ConfigurationError, Rule, SortEngine,
                         config_dir, expand_path, load_directories, load_rules,
                         portable_path, save_directories, save_rules, setup_defaults,
                         load_overwrite_setting, save_overwrite_setting,
                         load_scan_interval, load_destination_mode, save_destination_mode, save_scan_interval, parse_scan_interval,
                         SCAN_INTERVAL_STEP,
                         validate_rule, normalize_positions)

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    BaseTk = TkinterDnD.Tk
    DRAG_DROP_AVAILABLE = True
except ImportError:
    BaseTk = tk.Tk
    DRAG_DROP_AVAILABLE = False

API_URL = 'https://api.github.com/repos/gadzooksie/File-Sorter/releases/latest'
BG = '#101925'
PANEL = '#1d2c3b'
FIELD = '#223347'
BORDER = '#354a5d'
FG = '#edf2f7'
SUBTLE = '#a7b9c9'
ACCENT = '#267f82'
GREEN = '#29a486'
FONT_FAMILY = 'Helvetica Neue' if sys.platform == 'darwin' else 'DejaVu Sans'
MONO_FAMILY = 'Menlo' if sys.platform == 'darwin' else 'DejaVu Sans Mono'
FONT = (FONT_FAMILY, 11)
SMALL = (FONT_FAMILY, 9)


class ColorButton(tk.Label):
    """Aqua-safe dark control with an in-widget focus indication.

    Aqua can draw Tk's native highlight/focus border in the wrong place when
    Label acts as a button, especially on Retina displays. Disable that border
    completely and indicate focus by changing the *background* instead.
    Keep keyboard focus, Return/Space activation, and pointer interactions.
    """
    def __init__(self, parent, text, command, color=FIELD, **kwargs):
        self._action = command
        self._base_color = color
        self._hover_color = ACCENT if color != ACCENT else '#30979b'
        self._pressed = False
        self._hovered = False
        self._focused = False
        kwargs.setdefault('anchor', 'center')
        # Critically, do not use highlightthickness > 0 on Aqua. On some Tk
        # builds the focus rectangle can overlap the label text or misalign.
        super().__init__(parent, text=text, bg=color, fg=FG, font=FONT,
                         cursor='hand2', padx=18, pady=8, takefocus=1,
                         highlightthickness=0, bd=0, relief='flat', **kwargs)
        self.bind('<Enter>', self._enter)
        self.bind('<Leave>', self._leave)
        self.bind('<ButtonPress-1>', self._press)
        self.bind('<ButtonRelease-1>', self._release)
        self.bind('<KeyPress-Return>', self._key)
        self.bind('<KeyPress-space>', self._key)
        self.bind('<FocusIn>', self._focus_in)
        self.bind('<FocusOut>', self._focus_out)

    def _redraw(self):
        self.configure(bg=self._hover_color if self._hovered or self._focused else self._base_color)

    def _enter(self, event):
        self._hovered = True
        self._redraw()

    def _leave(self, event):
        self._hovered = False
        self._pressed = False
        self._redraw()

    def _press(self, event):
        self.focus_set()
        self._pressed = True

    def _release(self, event):
        inside = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        activate = self._pressed and inside
        self._pressed = False
        if activate:
            self._action()

    def _key(self, event):
        self._action()
        return 'break'

    def _focus_in(self, event):
        self._focused = True
        self._redraw()

    def _focus_out(self, event):
        self._focused = False
        self._pressed = False
        self._redraw()


def make_button(parent, text, command, color=FIELD, **kwargs):
    if sys.platform == 'darwin':
        return ColorButton(parent, text, command, color, **kwargs)
    return tk.Button(parent, text=text, command=command, bg=color, fg=FG,
                     activebackground=ACCENT, activeforeground='white',
                     bd=0, relief='flat', cursor='hand2', font=FONT,
                     padx=13, pady=9, **kwargs)


def make_label(parent, text, size=11, color=FG, **kwargs):
    return tk.Label(parent, text=text, bg=BG, fg=color,
                    font=(FONT_FAMILY, size), **kwargs)


def apply_file_sorter_icon(root: tk.Tk) -> bool:
    """Set the approved transparent icon when the GUI backend supports it."""
    roots = [Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)),
             Path(__file__).resolve().parent.parent]
    for base in roots:
        candidate = base / 'assets' / 'file-sorter.png'
        if not candidate.is_file():
            continue
        try:
            icon = tk.PhotoImage(master=root, file=str(candidate))
            root.iconphoto(True, icon)
            root._file_sorter_icon = icon  # keep Tcl image alive
            return True
        except (tk.TclError, OSError):
            # The macOS Finder/Dock icon comes from CFBundleIconFile regardless.
            pass
    return False


def detect_pattern(filename: str) -> str | None:
    name = Path(filename).name
    if not name or '.' not in name or name.startswith('.') and name.count('.') == 1:
        return None
    lowered = name.lower()
    for compound in ('.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst', '.tar.lz4', '.tar.z', '.user.js'):
        if lowered.endswith(compound):
            return '*' + name[-len(compound):]
    ext = Path(name).suffix
    return '*' + ext if ext and len(ext) <= 30 else None


def parse_semver(value: str) -> tuple[int, int, int] | None:
    m = re.search(r'(?<![\d.])v?(\d+)\.(\d+)\.(\d+)(?![\d.])', value)
    return tuple(int(m.group(i)) for i in (1, 2, 3)) if m else None


class FileSorterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f'File Sorter v{VERSION}')
        if sys.platform == 'darwin':
            # Fit a normal Mac laptop screen and reserve room for the Dock/menu bar.
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.root.geometry(f'{min(975, max(720, sw - 80))}x{min(700, max(570, sh - 115))}')
            self.root.minsize(700, 550)
        else:
            self.root.geometry('1100x735')
            self.root.minsize(850, 585)
        self.root.configure(bg=BG)
        apply_file_sorter_icon(self.root)
        self.config = setup_defaults()
        self.queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.engine = SortEngine(self.config, log=lambda msg: self.queue.put(('log', msg)))
        self.dirs = load_directories(self.config / 'directories.txt')
        self.rules = load_rules(self.config / 'rules.tsv')
        self.rule_index: int | None = None
        self.detail_open = False
        self.active_page = 'menu'
        self.update_link: str | None = None
        self.manual_check = False
        self.pattern = tk.StringVar()
        self.destination = tk.StringVar()
        self.position_label = tk.StringVar(value='New rule: last position')
        self.rule_sources = tk.StringVar(value='')  # Empty = main watched folders.
        self.scope = tk.StringVar(value='watch')
        self.mode = tk.StringVar(value='move')
        self.dir_entry = tk.StringVar()
        self.auto_check = tk.BooleanVar(value=self._auto_check_enabled())
        self.overwrite_files = tk.BooleanVar(value=load_overwrite_setting(self.config))
        self.scan_interval = tk.StringVar(value=format(load_scan_interval(self.config), "f"))
        self.destination_mode = tk.StringVar(value=load_destination_mode(self.config))
        self.collision_message = tk.StringVar()
        self._refresh_collision_label()
        self.status = tk.StringVar(value='Ready')
        self.sorting_status = tk.StringVar(value='STOPPED')
        self._make_styles()
        self._make_shell()
        self._make_menu()
        self._make_sorter()
        self._make_config()
        self.show('menu')
        self._setup_shortcuts()
        self._closing = False
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self._poll_job = self.root.after(100, self._poll_messages)
        self._check_job = self.root.after(700, self._scheduled_update_check) if self.auto_check.get() else None

    def _setup_shortcuts(self):
        """Quick navigation without stealing normal text-entry keystrokes."""
        prefix = 'Command' if sys.platform == 'darwin' else 'Control'

        def binding(callback):
            def activate(event):
                if self._closing:
                    return 'break'
                callback()
                return 'break'
            return activate

        for number, page in (('1', 'menu'), ('2', 'sorter'), ('3', 'config')):
            self.root.bind_all(f'<{prefix}-Key-{number}>', binding(lambda dest=page: self.show(dest)))
        self.root.bind_all(f'<{prefix}-Key-l>', binding(self.clear_log))
        self.root.bind_all(f'<{prefix}-Key-r>', binding(lambda: self.refresh_configuration_shortcut()))

    def refresh_configuration_shortcut(self):
        if self.active_page != 'config':
            self.status.set('Open Config to reload folders and rules.')
            return
        self.dirs = load_directories(self.config / 'directories.txt')
        self.rules = load_rules(self.config / 'rules.tsv')
        self.refresh_dirs()
        self.refresh_rules()
        self.status.set('Configuration refreshed from disk.')

    def _make_styles(self):
        s = ttk.Style(self.root)
        try:
            s.theme_use('clam')
        except tk.TclError:
            pass
        s.configure('Dark.TCombobox', fieldbackground=FIELD, background=FIELD,
                    foreground=FG, arrowcolor=FG)
        s.configure('Dark.Vertical.TScrollbar', background=FIELD, arrowcolor=FG)

    def _make_shell(self):
        self.header = tk.Frame(self.root, bg=BG, height=65 if sys.platform == 'darwin' else 80)
        self.header.pack(fill='x', padx=24, pady=(10 if sys.platform == 'darwin' else 15, 5))
        self.page_title = make_label(self.header, 'FILE SORTER', size=15)
        self.page_title.pack(side='left', pady=12)
        self.back = make_button(self.header, 'BACK TO MENU', lambda: self.show('menu'), color='#345b87')
        self.back.pack(side='right')
        tk.Frame(self.root, bg=ACCENT, height=3).pack(fill='x', padx=24)
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill='both', expand=True, padx=24, pady=16)
        self.footer = make_label(self.root, '', size=9, color=SUBTLE,
                                 anchor='w', textvariable=self.status)
        self.footer.pack(fill='x', padx=25, pady=(0, 16))
        self.pages = {}
        for kind in ('menu', 'sorter', 'config'):
            self.pages[kind] = tk.Frame(self.body, bg=BG)

    def _make_menu(self):
        frame = self.pages['menu']
        os_label = 'macOS' if sys.platform == 'darwin' else 'Windows and macOS'
        make_label(frame, f'File Sorter v{VERSION}  |  {os_label}', 10, SUBTLE).pack(anchor='w', pady=(0, 18))
        for name, subtitle, command in (
            ('START SORTER', 'View status, control sorting, and read the activity log.', lambda: self.show('sorter')),
            ('CONFIGURE', 'Edit watched folders, file formats, and destinations.', lambda: self.show('config')),
            ('CHECK FOR UPDATES', 'Check the latest GitHub release for your operating system.', lambda: self.check_updates(True)),
        ):
            outer = tk.Frame(frame, bg=PANEL, height=96 if sys.platform == 'darwin' else 110)
            outer.pack(fill='x', pady=6)
            outer.pack_propagate(False)
            button_color = ACCENT if name == 'START SORTER' else FIELD
            make_button(outer, name + '  >', command, color=button_color).pack(anchor='w', padx=17, pady=(8, 0))
            tk.Label(outer, text=subtitle, bg=PANEL, fg=SUBTLE,
                     font=SMALL, anchor='w').pack(anchor='w', padx=28, pady=7)
        make_label(frame, ('Command' if sys.platform == 'darwin' else 'Ctrl') + '+1/2/3: Menu / Sorter / Config  |  +L: Clear Log  |  +R: Reload',
                   size=9, color=SUBTLE).pack(anchor='w', pady=(7, 0))
        make_label(frame, 'Sorting remains active when you switch pages. Closing this window stops sorting.',
                   size=9, color=SUBTLE).pack(anchor='w', pady=(20, 0))
        options = tk.Frame(frame, bg=BG)
        options.pack(fill='x', pady=14)
        tk.Checkbutton(options, text='Automatically check for new releases (once every six hours)',
                       variable=self.auto_check, command=self._save_auto_check,
                       bg=BG, fg=SUBTLE, activebackground=BG,
                       activeforeground=FG, selectcolor=FIELD, font=SMALL).pack(anchor='w')
        self.update_result = make_label(frame, '', 10, GREEN)
        self.update_result.pack(anchor='w', pady=5)
        self.update_open_button = make_button(frame, 'OPEN RELEASE PAGE', self._open_release)

    def _make_choice_button(self, parent, variable, choices):
        """Avoid Aqua ttk Combobox colors on macOS; retain native option menus."""
        values = dict(choices)
        popup = None

        def show_choices():
            if popup is not None:
                popup.tk_popup(button.winfo_rootx(), button.winfo_rooty() + button.winfo_height())

        button = make_button(parent, '', show_choices)
        popup = tk.Menu(button, tearoff=False)
        for code, label in choices:
            popup.add_radiobutton(label=label, variable=variable, value=code)

        def refresh(*_):
            button.configure(text=f'{values.get(variable.get(), variable.get())}  \u25be')

        variable.trace_add('write', refresh)
        refresh()
        return button

    def _make_sorter(self):
        frame = self.pages['sorter']
        make_label(frame, 'FILE SORTING', 14).pack(anchor='w')
        status_frame = tk.Frame(frame, bg=PANEL, height=115)
        status_frame.pack(fill='x', pady=(12, 13))
        status_frame.pack_propagate(False)
        tk.Label(status_frame, textvariable=self.sorting_status, bg=PANEL,
                 fg=GREEN, font=(FONT_FAMILY, 15, 'bold')).pack(anchor='w', padx=19, pady=(18, 8))
        tk.Label(status_frame, textvariable=self.collision_message,
                 bg=PANEL, fg=SUBTLE, font=SMALL).pack(anchor='w', padx=19)
        controls = tk.Frame(frame, bg=BG)
        controls.pack(fill='x', pady=(0, 13))
        make_button(controls, 'START SORTING', self.start_sorter, GREEN).pack(side='left', padx=(0, 8))
        make_button(controls, 'STOP SORTING', self.stop_sorter, '#64404b').pack(side='left', padx=8)
        make_button(controls, 'CLEAR LOG', self.clear_log).pack(side='left', padx=8)
        make_label(frame, 'RECENT ACTIVITY', 10, SUBTLE).pack(anchor='w', pady=7)
        logframe = tk.Frame(frame, bg=PANEL)
        logframe.pack(fill='both', expand=True)
        self.logbox = tk.Text(logframe, bg=PANEL, fg=FG, insertbackground=FG,
                              bd=0, highlightthickness=0, wrap='word', font=(MONO_FAMILY, 10))
        self.logbox.pack(fill='both', expand=True, padx=14, pady=13)
        self.logbox.insert('end', 'Ready. Use START SORTING to begin.\n')
        self.logbox.config(state='disabled')

    def _make_config(self):
        frame = self.pages['config']
        make_label(frame, 'SORTER CONFIGURATION', 14).pack(anchor='w')
        make_label(frame, 'Changes are saved immediately and loaded on the next sorting scan.', 9, SUBTLE).pack(anchor='w', pady=(2, 11))
        # This is a global setting; putting it above the config tabs makes it
        # visible from both Watched Directories and File Formats pages.
        overwrite_row = tk.Frame(frame, bg=PANEL)
        overwrite_row.pack(fill='x', pady=(0, 8))
        self.overwrite_button = make_button(overwrite_row, '', self.toggle_overwrite,
                                            color='#80523a')
        self.overwrite_button.pack(side='left', padx=8, pady=6)
        self._refresh_overwrite_button()
        tk.Label(overwrite_row, text='ON replaces matching existing files. OFF skips collisions.',
                 bg=PANEL, fg=SUBTLE, font=SMALL).pack(side='left', padx=8)
        interval_row = tk.Frame(frame, bg=PANEL)
        interval_row.pack(fill='x', pady=(0, 8))
        make_label(interval_row, 'CHECK INTERVAL (seconds)', 9, SUBTLE).pack(side='left', padx=(10, 8))
        self.interval_entry = tk.Entry(interval_row, textvariable=self.scan_interval, width=12,
                                       bg=FIELD, fg=FG, insertbackground=FG,
                                       font=FONT, bd=0, highlightthickness=0)
        self.interval_entry.pack(side='left', ipady=7, padx=(0, 7))
        self.interval_entry.bind('<Return>', lambda event: self.save_interval())
        arrows = tk.Frame(interval_row, bg=PANEL)
        arrows.pack(side='left', padx=(0, 7), pady=4)
        for glyph, direction in (('▲', 1), ('▼', -1)):
            control = make_button(arrows, glyph, lambda d=direction: self.step_interval(d))
            control.configure(padx=9, pady=0, font=(FONT_FAMILY, 9))
            control.pack(side='top', fill='x', pady=(0, 1))
        make_button(interval_row, 'APPLY', self.save_interval, color=ACCENT).pack(side='left', pady=5)
        switcher = tk.Frame(frame, bg=BG)
        switcher.pack(fill='x', pady=(0, 12))
        make_button(switcher, 'WATCHED DIRECTORIES', lambda: self.config_page('dirs')).pack(side='left', padx=(0, 7))
        make_button(switcher, 'FILE FORMATS AND DESTINATIONS', lambda: self.config_page('rules')).pack(side='left', padx=7)
        self.config_content = tk.Frame(frame, bg=BG)
        self.config_content.pack(fill='both', expand=True)
        self.dirs_page = tk.Frame(self.config_content, bg=BG)
        self.rules_page = tk.Frame(self.config_content, bg=BG)
        self._make_dirs_page()
        self._make_rules_page()
        self.config_page('dirs')

    def _list_widget(self, parent, height=12):
        wrap = tk.Frame(parent, bg=PANEL)
        widget = tk.Listbox(wrap, bg=PANEL, fg=FG, selectbackground=ACCENT,
                            selectforeground='white', activestyle='none',
                            highlightthickness=0, bd=0, font=FONT, height=height,
                            exportselection=False)
        scroll = tk.Scrollbar(wrap, command=widget.yview)
        widget.config(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        widget.pack(side='left', fill='both', expand=True)
        return wrap, widget

    def _make_dirs_page(self):
        make_label(self.dirs_page, 'Top-level files in these directories are monitored.', 10, SUBTLE).pack(anchor='w', pady=(0, 8))
        mode_row = tk.Frame(self.dirs_page, bg=PANEL)
        mode_row.pack(fill='x', pady=(0, 8))
        make_label(mode_row, 'DESTINATION MODE', 9, SUBTLE).pack(side='left', padx=(9, 8), pady=8)
        self.destination_mode_button = make_button(mode_row, '', self.toggle_destination_mode, ACCENT)
        self.destination_mode_button.pack(side='left', padx=5, pady=5)
        self._refresh_destination_mode_button()
        make_label(self.dirs_page, 'Only destinations inside ~/Sorted are relocated. Custom paths are unchanged.', 9, SUBTLE).pack(anchor='w', pady=(0, 8))
        wrap, self.dir_list = self._list_widget(self.dirs_page, height=11)
        wrap.pack(fill='both', expand=True)
        self.dir_list.bind('<<ListboxSelect>>', self._select_dir)
        entryrow = tk.Frame(self.dirs_page, bg=BG)
        entryrow.pack(fill='x', pady=(13, 6))
        tk.Entry(entryrow, textvariable=self.dir_entry, bg=FIELD, fg=FG, insertbackground=FG, insertwidth=2, insertofftime=450, insertontime=550,
                 bd=0, font=FONT).pack(side='left', fill='x', expand=True, ipady=9)
        make_button(entryrow, 'BROWSE', self.browse_watch).pack(side='left', padx=7)
        buttons = tk.Frame(self.dirs_page, bg=BG)
        buttons.pack(fill='x')
        make_button(buttons, 'ADD DIRECTORY', self.add_directory, GREEN).pack(side='left', padx=(0, 8))
        make_button(buttons, 'REMOVE SELECTED', self.remove_directory, '#64404b').pack(side='left')
        suggestions = tk.Frame(self.dirs_page, bg=BG)
        suggestions.pack(fill='x', pady=(7, 0))
        make_label(suggestions, 'Quick add:', 9, SUBTLE).pack(side='left', padx=(0, 8))
        make_button(suggestions, 'Downloads', lambda: self.add_suggested_directory('Downloads')).pack(side='left', padx=(0, 6))
        make_button(suggestions, 'Documents', lambda: self.add_suggested_directory('Documents')).pack(side='left')
        self.refresh_dirs()

    def _make_rules_page(self):
        top = tk.Frame(self.rules_page, bg=BG)
        top.pack(fill='both', expand=True)
        left = tk.Frame(top, bg=BG)
        left.pack(side='left', fill='both', expand=True, padx=(0, 15))
        right_holder = tk.Frame(top, bg=BG, width=390)
        right_holder.pack(side='right', fill='y')
        right_holder.pack_propagate(False)
        right_scroll = tk.Scrollbar(right_holder, orient='vertical')
        right_scroll.pack(side='right', fill='y')
        self.rule_canvas = tk.Canvas(right_holder, bg=BG, highlightthickness=0,
                                    bd=0, yscrollcommand=right_scroll.set)
        self.rule_canvas.pack(side='left', fill='both', expand=True)
        right_scroll.configure(command=self.rule_canvas.yview)
        right = tk.Frame(self.rule_canvas, bg=BG)
        self.rule_window = self.rule_canvas.create_window((0, 0), window=right, anchor='nw')
        right.bind('<Configure>', lambda event: self.rule_canvas.configure(
            scrollregion=self.rule_canvas.bbox('all')))
        self.rule_canvas.bind('<Configure>', lambda event: self.rule_canvas.itemconfigure(
            self.rule_window, width=event.width))
        make_label(left, 'RULE ORDER (FIRST MATCH WINS)', 10, SUBTLE).pack(anchor='w', pady=(0, 7))
        wrap, self.rule_list = self._list_widget(left, height=12)
        wrap.pack(fill='both', expand=True)
        self.rule_list.bind('<<ListboxSelect>>', self._select_rule)
        bar = tk.Frame(left, bg=BG)
        bar.pack(fill='x', pady=8)
        make_button(bar, 'NEW', self.new_rule).pack(side='left', padx=(0, 6))
        make_button(bar, 'DELETE', self.delete_rule, '#64404b').pack(side='left', padx=6)
        make_button(bar, 'UP', lambda: self.move_rule(-1)).pack(side='left', padx=6)
        make_button(bar, 'DOWN', lambda: self.move_rule(1)).pack(side='left', padx=6)

        make_label(right, 'EDIT FILE FORMAT', 11, SUBTLE).pack(anchor='w', pady=(0, 8))
        make_label(right, 'File extension / pattern (e.g., *.pdf or *.tar.gz)', 9, SUBTLE).pack(anchor='w')
        tk.Entry(right, textvariable=self.pattern, bg=FIELD, fg=FG,
                 insertbackground=FG, insertwidth=2, insertofftime=450, insertontime=550, font=FONT, bd=0).pack(fill='x', ipady=9, pady=(3, 7))
        make_button(right, 'SELECT SAMPLE FILE', self.sample_file).pack(fill='x', pady=(0, 4))
        self.drop_hint = make_label(right, 'Drag a sample file here, or use Select Sample File.', 9, SUBTLE, wraplength=370)
        self.drop_hint.pack(anchor='w', pady=(0, 10))
        if DRAG_DROP_AVAILABLE:
            self._attach_file_drop(right)
        make_button(right, 'DESTINATION & OPTIONS  [+]', self.toggle_details).pack(fill='x', pady=5)
        self.details = tk.Frame(right, bg=BG)
        make_label(self.details, 'Destination directory', 9, SUBTLE).pack(anchor='w', pady=(9, 3))
        tk.Entry(self.details, textvariable=self.destination, bg=FIELD, fg=FG,
                 insertbackground=FG, insertwidth=2, insertofftime=450, insertontime=550, font=FONT, bd=0).pack(fill='x', ipady=8, pady=(0, 8))
        make_button(self.details, 'BROWSE DESTINATION', self.browse_destination).pack(fill='x')
        make_label(self.details, 'Scope', 9, SUBTLE).pack(anchor='w', pady=(10, 3))
        if sys.platform == 'darwin':
            self.scope_picker = self._make_choice_button(self.details, self.scope,
                [('watch', 'Watched folders'), ('home', 'Home folder only'),
                 ('saves', 'Sorted saves only')])
        else:
            self.scope_picker = ttk.Combobox(self.details, textvariable=self.scope, state='readonly',
                                             values=('watch', 'home', 'saves'), style='Dark.TCombobox')
        self.scope_picker.pack(fill='x')
        make_label(self.details, 'Mode', 9, SUBTLE).pack(anchor='w', pady=(10, 3))
        if sys.platform == 'darwin':
            self.mode_picker = self._make_choice_button(self.details, self.mode,
                [('move', 'Normal move'), ('archive', '72-hour archive split')])
        else:
            self.mode_picker = ttk.Combobox(self.details, textvariable=self.mode, state='readonly',
                                           values=('move', 'archive'), style='Dark.TCombobox')
        self.mode_picker.pack(fill='x')
        make_label(self.details, 'Priority: position in list (top rule wins)', 9, SUBTLE).pack(anchor='w', pady=(10, 3))
        tk.Label(self.details, textvariable=self.position_label, bg=FIELD, fg=FG,
                 font=FONT, anchor='w', padx=9, pady=8).pack(fill='x')
        make_label(self.details, 'Use MOVE UP / MOVE DOWN in the rule list to change priority.',
                   9, SUBTLE, wraplength=350).pack(anchor='w')
        make_label(self.details, 'Watch directories for this rule', 9, SUBTLE).pack(anchor='w', pady=(10, 3))
        make_label(self.details, 'Blank = all watched folders from the main menu.', 9, SUBTLE,
                   wraplength=360).pack(anchor='w')
        rule_sources_entry = tk.Entry(self.details, textvariable=self.rule_sources,
                                      bg=FIELD, fg=FG, insertbackground=FG,
                                      insertwidth=2, insertofftime=450, insertontime=550,
                                      font=FONT, bd=0)
        rule_sources_entry.pack(fill='x', ipady=8, pady=(4, 4))
        make_label(self.details, 'Multiple directories: separate paths with |', 9, SUBTLE).pack(anchor='w')
        source_buttons = tk.Frame(self.details, bg=BG)
        source_buttons.pack(fill='x', pady=(4, 0))
        make_button(source_buttons, 'ADD FOLDER', self.browse_rule_source).pack(side='left', padx=(0, 6))
        make_button(source_buttons, 'USE ALL WATCHED', lambda: self.rule_sources.set('')).pack(side='left')
        make_label(self.details, 'Archive mode puts files in New/<type> or Old/<type> after 72 hours.',
                   9, SUBTLE, wraplength=370, justify='left').pack(anchor='w', pady=(10, 0))
        self.save_button = make_button(right, 'SAVE RULE', self.save_rule, GREEN)
        self.save_button.pack(fill='x', pady=12)
        make_button(right, 'RESTORE DEFAULT RULES', self.restore_default_rules).pack(fill='x')
        self.refresh_rules()
        self.new_rule()

    def _attach_file_drop(self, widget):
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind('<<Drop>>', self._drop_rule_sample)

    def _drop_rule_sample(self, event):
        try:
            paths = self.root.tk.splitlist(event.data)
        except tk.TclError:
            return
        for p in paths:
            p = Path(p)
            if p.is_dir():
                self.destination.set(portable_path(p))
                self.open_details()
                self.status.set('Destination selected from dropped folder. Save Rule to apply.')
                return
            if p.is_file():
                self.apply_sample(p)
                return

    def show(self, name: str):
        for widget in self.pages.values():
            widget.pack_forget()
        self.pages[name].pack(fill='both', expand=True)
        self.active_page = name
        self.page_title.configure(text={'menu':'FILE SORTER', 'sorter':'FILE SORTER | SORTING',
                                        'config':'FILE SORTER | CONFIGURATION'}[name])
        if name == 'menu':
            self.back.pack_forget()
        else:
            self.back.pack(side='right')
        if name == 'config':
            self.refresh_dirs()
            self.refresh_rules()
        self.status.set(f'File Sorter v{VERSION}  |  {name.title()}')

    def config_page(self, page: str):
        self.dirs_page.pack_forget()
        self.rules_page.pack_forget()
        (self.dirs_page if page == 'dirs' else self.rules_page).pack(fill='both', expand=True)

    def _select_dir(self, event=None):
        sel = self.dir_list.curselection()
        if sel:
            self.dir_entry.set(self.dirs[sel[0]])

    def refresh_dirs(self):
        self.dir_list.delete(0, 'end')
        for path in self.dirs:
            self.dir_list.insert('end', path)

    def add_suggested_directory(self, name: str):
        path = Path.home() / name
        if not path.is_dir():
            messagebox.showinfo('Folder not found', f'{path} does not exist. Use Browse to choose another folder.', parent=self.root)
            return
        self.dir_entry.set(portable_path(path))
        self.add_directory()

    def add_directory(self):
        try:
            path = portable_path(self.dir_entry.get())
            expanded = expand_path(path)
            if not expanded.is_dir():
                raise ConfigurationError('This directory does not exist.')
            if expanded == Path(expanded.anchor):
                raise ConfigurationError('Watching the filesystem root is not allowed.')
            if path not in self.dirs:
                self.dirs.append(path)
            save_directories(self.config / 'directories.txt', self.dirs)
            self.refresh_dirs()
            self.status.set(f'Watching {path}')
        except (ConfigurationError, OSError) as e:
            messagebox.showerror('Invalid directory', str(e), parent=self.root)

    def remove_directory(self):
        sel = self.dir_list.curselection()
        if not sel:
            return
        self.dirs.pop(sel[0])
        save_directories(self.config / 'directories.txt', self.dirs)
        self.refresh_dirs()
        self.dir_entry.set('')
        self.status.set('Watched directory removed (files untouched).')

    def browse_watch(self):
        value = filedialog.askdirectory(parent=self.root, title='Choose folder to monitor')
        if value:
            self.dir_entry.set(portable_path(value))

    def refresh_rules(self):
        self.rule_list.delete(0, 'end')
        total = len(self.rules)
        for i, r in enumerate(self.rules):
            self.rule_list.insert('end', f'{i+1}/{total}  {r.pattern:18} {r.scope:6} -> {r.destination}')
        self.update_position_label()

    def update_position_label(self):
        if self.rule_index is None:
            self.position_label.set(f'New rule: {len(self.rules)+1}/{len(self.rules)+1} (last)')
        else:
            self.position_label.set(f'{self.rule_index+1}/{len(self.rules)}  -  higher in list = higher priority')

    def _select_rule(self, event=None):
        selection = self.rule_list.curselection()
        if not selection:
            return
        i = selection[0]
        self.rule_index = i
        rule = self.rules[i]
        self.pattern.set(rule.pattern)
        self.destination.set(rule.destination)
        self.scope.set(rule.scope)
        self.mode.set(rule.mode)
        self.update_position_label()
        self.rule_sources.set('' if rule.sources == '-' else rule.sources)

    def new_rule(self):
        self.rule_index = None
        self.rule_list.selection_clear(0, 'end')
        self.pattern.set('')
        self.destination.set('~/Sorted/Other')
        self.scope.set('watch')
        self.mode.set('move')
        self.update_position_label()
        self.rule_sources.set('')
        self.open_details()
        self.status.set('New rule: enter a file pattern and destination, then Save Rule.')

    def open_details(self):
        if not self.detail_open:
            self.details.pack(fill='x', before=self.save_button)
            self.detail_open = True

    def toggle_details(self):
        if self.detail_open:
            self.details.pack_forget()
            self.detail_open = False
        else:
            self.open_details()

    def sample_file(self):
        p = filedialog.askopenfilename(parent=self.root, title='Choose sample file (not moved)')
        if p:
            self.apply_sample(Path(p))

    def apply_sample(self, file: Path):
        pattern = detect_pattern(file.name)
        if not pattern:
            messagebox.showwarning('Unknown extension', 'This file has no detectable extension.', parent=self.root)
            return
        for i, rule in enumerate(self.rules):
            if rule.scope == 'watch' and rule.pattern.lower() == pattern.lower():
                self.rule_list.selection_clear(0, 'end')
                self.rule_list.selection_set(i)
                self.rule_list.see(i)
                self._select_rule()
                self.open_details()
                self.status.set(f'Existing rule selected: {pattern}. Sample file was not moved.')
                return
        self.new_rule()
        self.pattern.set(pattern)
        self.open_details()
        self.status.set(f'Detected {pattern}. Choose a destination and click Save Rule.')

    def browse_destination(self):
        value = filedialog.askdirectory(parent=self.root, title='Select destination folder')
        if value:
            self.destination.set(portable_path(value))

    def browse_rule_source(self):
        folder = filedialog.askdirectory(parent=self.root, title='Add a watched folder for this rule')
        if not folder:
            return
        old = self.rule_sources.get().strip()
        value = portable_path(folder)
        existing = [s.strip() for s in old.split('|') if s.strip()]
        if value not in existing:
            existing.append(value)
        self.rule_sources.set('|'.join(existing))

    def save_rule(self):
        try:
            sources = [portable_path(v.strip()) for v in self.rule_sources.get().split('|') if v.strip()]
            rule = validate_rule(Rule(self.scope.get(), self.pattern.get().strip(),
                                      portable_path(self.destination.get()), self.mode.get(),
                                      0, '|'.join(sources) if sources else '-'))
            if self.rule_index is None:
                if len(self.rules) >= 256:
                    raise ConfigurationError('Maximum of 256 rules.')
                self.rules.append(rule)
                self.rule_index = len(self.rules) - 1
            else:
                self.rules[self.rule_index] = rule
            self.rules = normalize_positions(self.rules)
            save_rules(self.config / 'rules.tsv', self.rules)
            self.refresh_rules()
            self.rule_list.selection_set(self.rule_index)
            self.rule_list.see(self.rule_index)
            self.status.set(f'Rule saved: {rule.pattern} -> {rule.destination}')
        except (ConfigurationError, OSError, ValueError) as e:
            messagebox.showerror('Invalid rule', str(e), parent=self.root)

    def delete_rule(self):
        if self.rule_index is None:
            return
        self.rules.pop(self.rule_index)
        save_rules(self.config / 'rules.tsv', self.rules)
        self.refresh_rules()
        self.new_rule()
        self.status.set('Rule removed.')

    def move_rule(self, offset: int):
        i = self.rule_index
        if i is None:
            return
        j = i + offset
        if 0 <= j < len(self.rules):
            self.rules[i], self.rules[j] = self.rules[j], self.rules[i]
            save_rules(self.config / 'rules.tsv', self.rules)
            self.rule_index = j
            self.refresh_rules()
            self.rule_list.selection_set(j)
            self.rule_list.see(j)

    def restore_default_rules(self):
        if not messagebox.askyesno('Restore defaults', 'Replace all sorting rules with the bundled defaults?\nWatched folders are unchanged.', parent=self.root):
            return
        from sorter_core import defaults_dir
        self.rules = load_rules(defaults_dir() / 'rules.tsv')
        save_rules(self.config / 'rules.tsv', self.rules)
        self.refresh_rules()
        self.new_rule()
        self.status.set('Default rules restored.')

    def start_sorter(self):
        if self.engine.start():
            self.sorting_status.set('RUNNING')
            self.status.set('File sorting started.')
        else:
            self.status.set('Sorting is already running.')

    def stop_sorter(self):
        self.engine.stop()
        self.sorting_status.set('STOPPED')
        self.status.set('Sorting stopped.')

    def clear_log(self):
        self.logbox.config(state='normal')
        self.logbox.delete('1.0', 'end')
        self.logbox.config(state='disabled')

    def _poll_messages(self):
        if self._closing:
            return
        try:
            while True:
                kind, message = self.queue.get_nowait()
                if kind == 'log':
                    self.logbox.config(state='normal')
                    self.logbox.insert('end', message + '\n')
                    if int(self.logbox.index('end-1c').split('.')[0]) > 1000:
                        self.logbox.delete('1.0', '200.0')
                    self.logbox.see('end')
                    self.logbox.config(state='disabled')
                elif kind == 'update':
                    self.update_result.config(text=message)
                    self.status.set(message)
                    if self.update_link:
                        self.update_open_button.pack(anchor='w', pady=7)
        except queue.Empty:
            pass
        if not self._closing:
            self._poll_job = self.root.after(150, self._poll_messages)

    def _refresh_destination_mode_button(self):
        self.destination_mode_button.configure(text=(
            'EACH FOLDER /Sorted' if self.destination_mode.get() == 'per-folder'
            else 'SHARED ~/Sorted'))

    def toggle_destination_mode(self):
        new_mode = 'per-folder' if self.destination_mode.get() == 'shared' else 'shared'
        try:
            save_destination_mode(self.config, new_mode)
        except OSError as exc:
            messagebox.showerror('Cannot save destination mode', str(exc), parent=self.root)
            return
        self.destination_mode.set(new_mode)
        self._refresh_destination_mode_button()
        self.status.set('Each watched folder has its own Sorted/ output.' if new_mode == 'per-folder'
                        else 'All watched folders share ~/Sorted/.')

    def save_interval(self):
        try:
            setting = save_scan_interval(self.config, self.scan_interval.get())
        except (ConfigurationError, OSError, ValueError) as error:
            messagebox.showerror('Invalid check interval', str(error), parent=self.root)
            self.interval_entry.focus_set()
            return
        self.scan_interval.set(format(setting, 'f'))
        self._refresh_collision_label()
        self.status.set(f'Check interval saved: {setting} seconds. Applies on the next scan.')

    def step_interval(self, direction: int):
        try:
            current = parse_scan_interval(self.scan_interval.get())
        except ConfigurationError:
            current = load_scan_interval(self.config)
        new_value = current + SCAN_INTERVAL_STEP * direction
        if new_value <= 0:
            new_value = SCAN_INTERVAL_STEP
        self.scan_interval.set(format(new_value, 'f'))
        self.save_interval()

    def _refresh_collision_label(self):
        state = 'REPLACE matching files' if self.overwrite_files.get() else 'SKIP existing files'
        self.collision_message.set(f'Every {load_scan_interval(self.config)} seconds | First matching rule in the list wins | {state}')

    def _refresh_overwrite_button(self):
        self.overwrite_button.configure(text='OVERWRITE FILES: ON' if self.overwrite_files.get()
                                        else 'OVERWRITE FILES: OFF')

    def toggle_overwrite(self):
        new_state = not self.overwrite_files.get()
        if new_state and not messagebox.askyesno(
                'Enable file overwriting?',
                'This will permanently replace existing destination files with the same name. '
                'Replaced files cannot be recovered through File Sorter.\n\nEnable overwriting?',
                icon='warning', parent=self.root):
            return
        try:
            save_overwrite_setting(self.config, new_state)
        except OSError as exc:
            messagebox.showerror('Could not save setting', str(exc), parent=self.root)
            return
        self.overwrite_files.set(new_state)
        self._refresh_collision_label()
        self._refresh_overwrite_button()
        self.status.set('Overwrite Files enabled. Existing files can be replaced.' if new_state
                        else 'Overwrite Files disabled. Existing files will be skipped.')

    def _auto_check_enabled(self):
        f = self.config / 'auto-update.txt'
        return not f.exists() or f.read_text(encoding='utf-8').strip().lower() != 'off'

    def _save_auto_check(self):
        from sorter_core import atomic_text
        atomic_text(self.config / 'auto-update.txt', 'on\n' if self.auto_check.get() else 'off\n')

    def _scheduled_update_check(self):
        last = self.config / 'last-check.txt'
        try:
            if last.exists() and time.time() - float(last.read_text().strip()) < 6*3600:
                return
        except (ValueError, OSError):
            pass
        self.check_updates(False)

    def check_updates(self, manual: bool = True):
        self.update_result.config(text='Checking GitHub Releases...')
        self.manual_check = manual
        threading.Thread(target=self._fetch_update, daemon=True).start()

    def _fetch_update(self):
        from sorter_core import atomic_text
        try:
            req = urllib.request.Request(API_URL, headers={'Accept':'application/vnd.github+json',
                                                            'User-Agent':'File-Sorter/'+VERSION})
            with urllib.request.urlopen(req, timeout=12) as response:
                data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise ValueError('Release metadata too large')
            release = json.loads(data)
            if release.get('draft') or release.get('prerelease'):
                raise ValueError('Latest release is not stable')
            version = parse_semver(release.get('tag_name', '')) or parse_semver(release.get('name', ''))
            self.update_link = release.get('html_url', 'https://github.com/gadzooksie/File-Sorter/releases/latest')
            if version and version > parse_semver(VERSION):
                message = f'New version {".".join(map(str, version))} available. Open the release to install.'
            else:
                message = f'Installed version v{VERSION} is up to date.'
            atomic_text(self.config / 'last-check.txt', str(time.time()) + '\n')
        except Exception as error:
            self.update_link = None
            message = f'Update check unavailable: {error}'
        self.queue.put(('update', message))

    def _open_release(self):
        if self.update_link:
            webbrowser.open(self.update_link)

    def on_close(self):
        self._closing = True
        for job in (self._poll_job, self._check_job):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        self.engine.stop()
        self.root.destroy()


def main():
    if '--version' in sys.argv:
        print('File Sorter v' + VERSION)
        return
    if '--self-test' in sys.argv:
        setup_defaults()
        load_rules(config_dir() / 'rules.tsv')
        load_directories(config_dir() / 'directories.txt')
        return
    root = BaseTk()
    app = FileSorterApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
