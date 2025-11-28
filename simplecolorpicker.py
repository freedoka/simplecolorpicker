#!/usr/bin/env python3
"""
dokapad with color-aware .gtxt format.

Features:
- New / Open / Save / Save As
- Undo / Redo / Cut / Copy / Paste / Select All
- Word Wrap toggle
- Change font family and size (Format → Font…)
- Per-selection text color via right-click → Text Color…
- Clear per-selection text colors
- Change editor background color (Format → Background Color… or right-click)
- Search + Replace panel (Edit → Find / Replace…, Ctrl+F / Ctrl+H)
- Status bar with line/column
- Keyboard shortcuts (Ctrl+N/O/S/Z/Y/X/C/V/A, F5)
- .txt  -> saved as plain text
- .gtxt -> saved as JSON with text + color ranges + background color
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from tkinter import font as tkfont
from tkinter import colorchooser
from datetime import datetime
import os
import json

APP_NAME = "dokapad"
DEFAULT_BG_COLOR = "#fbf4e6"  # RGB(251, 244, 230)
DEFAULT_TITLE = f"Untitled - {APP_NAME}"


class NotepadApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # --- set window icon safely ---
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, "dokapad.png")  # exact file name

            self.icon_image = tk.PhotoImage(file=icon_path)   # keep a reference!
            self.iconphoto(False, self.icon_image)
        except Exception as e:
            print("Icon load failed:", e)

        # --- window setup ---
        self.title(DEFAULT_TITLE)
        self.geometry("800x600")

        # current file path (None = new/unsaved)
        self.file_path = None
        self.word_wrap_enabled = True

        # current text font
        self.current_font = tkfont.Font(family="Consolas", size=12)

        # search panel state
        self.search_window = None
        self.search_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.match_case_var = tk.BooleanVar(value=False)

        # --- create UI ---
        self._create_widgets()
        self._create_menu()
        self._create_bindings()
        self._create_context_menu()

    # -------------------------------------------------------------------------
    # UI CREATION
    # -------------------------------------------------------------------------
    def _create_widgets(self):
        # main vertical layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # text area with scrollbar
        self.text_frame = ttk.Frame(self)
        self.text_frame.grid(row=0, column=0, sticky="nsew")

        self.text_scrollbar = ttk.Scrollbar(self.text_frame, orient="vertical")
        self.text_scrollbar.pack(side="right", fill="y")

        self.text = tk.Text(
            self.text_frame,
            wrap="word",
            undo=True,
            maxundo=-1,  # unlimited
            font=self.current_font,
            background=DEFAULT_BG_COLOR,
        )
        self.text.pack(side="left", fill="both", expand=True)

        # remember initial background color
        self.bg_color = DEFAULT_BG_COLOR

        self.text.config(yscrollcommand=self.text_scrollbar.set)
        self.text_scrollbar.config(command=self.text.yview)

        # status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ln 1, Col 1")

        self.status_bar = ttk.Label(
            self,
            textvariable=self.status_var,
            anchor="e",
            relief="sunken"
        )
        self.status_bar.grid(row=1, column=0, sticky="ew")

    def _create_menu(self):
        menubar = tk.Menu(self)

        # --- File menu ---
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)
        menubar.add_cascade(label="File", menu=file_menu)

        # --- Edit menu ---
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.edit_undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.edit_redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=self.edit_cut)
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=self.edit_copy)
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=self.edit_paste)
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self.select_all)
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Find / Replace...",
            accelerator="Ctrl+F",
            command=self.open_search_panel
        )
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # --- Format menu ---
        format_menu = tk.Menu(menubar, tearoff=0)

        # Word Wrap toggle
        format_menu.add_checkbutton(
            label="Word Wrap",
            onvalue=True,
            offvalue=False,
            command=self.toggle_word_wrap
        )

        # Font chooser
        format_menu.add_command(label="Font...", command=self.choose_font)

        # Background color
        format_menu.add_command(label="Background Color...", command=self.choose_background_color)

        menubar.add_cascade(label="Format", menu=format_menu)

        # --- Help menu ---
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About " + APP_NAME, command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)
        self._format_menu = format_menu  # keep ref if needed later

    def _create_bindings(self):
        # window close button
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        # update status bar on cursor move / key / mouse
        self.text.bind("<<Modified>>", self._on_text_modified)
        self.text.bind("<KeyRelease>", self._update_status_bar)
        self.text.bind("<ButtonRelease-1>", self._update_status_bar)

        # keyboard shortcuts
        self.bind_all("<Control-n>", self._shortcut_new)
        self.bind_all("<Control-o>", self._shortcut_open)
        self.bind_all("<Control-s>", self._shortcut_save)
        self.bind_all("<Control-z>", self._shortcut_undo)
        self.bind_all("<Control-y>", self._shortcut_redo)
        self.bind_all("<Control-x>", self._shortcut_cut)
        self.bind_all("<Control-c>", self._shortcut_copy)
        self.bind_all("<Control-v>", self._shortcut_paste)
        self.bind_all("<Control-a>", self._shortcut_select_all)
        self.bind_all("<F5>", self._shortcut_datetime)

        # search / replace shortcuts
        self.bind_all("<Control-f>", self._shortcut_find_replace)
        self.bind_all("<Control-h>", self._shortcut_find_replace)

    def _create_context_menu(self):
        """Right-click context menu on the text area."""
        self.context_menu = tk.Menu(self.text, tearoff=0)
        self.context_menu.add_command(label="Cut", command=self.edit_cut)
        self.context_menu.add_command(label="Copy", command=self.edit_copy)
        self.context_menu.add_command(label="Paste", command=self.edit_paste)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Text Color...", command=self.pick_text_color)
        self.context_menu.add_command(label="Clear Text Color", command=self.clear_text_color)
        self.context_menu.add_separator()
        # background color from right-click
        self.context_menu.add_command(label="Background Color...", command=self.choose_background_color)

        # Right-click binding (Windows/Linux)
        self.text.bind("<Button-3>", self._show_context_menu)
        # Optional: Mac-style right-click (Ctrl + Click)
        self.text.bind("<Control-Button-1>", self._show_context_menu)

    def _show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # -------------------------------------------------------------------------
    # INTERNAL HELPERS
    # -------------------------------------------------------------------------
    def _set_title(self, modified=False):
        if self.file_path:
            filename = os.path.basename(self.file_path)
        else:
            filename = "Untitled"

        star = "*" if modified else ""
        self.title(f"{star}{filename} - {APP_NAME}")

    def _confirm_discard_changes(self):
        if not self.text.edit_modified():
            return True  # nothing to save

        result = messagebox.askyesnocancel(
            "Unsaved changes",
            "Do you want to save changes before continuing?"
        )
        if result is None:
            # Cancel
            return False
        if result:
            # Yes -> Save
            return self.save_file()
        # No -> discard without saving
        return True

    def _update_status_bar(self, event=None):
        # get current insertion index "line.col"
        index = self.text.index("insert")
        line, col = index.split(".")
        # col is zero-based; Notepad shows 1-based
        col = str(int(col) + 1)
        self.status_var.set(f"Ln {line}, Col {col}")

    def _on_text_modified(self, event=None):
        # Called when Text widget's modified flag changes
        if self.text.edit_modified():
            self._set_title(modified=True)
        else:
            self._set_title(modified=False)
        self._update_status_bar()
        # reset the modified flag so we can detect further edits
        self.text.edit_modified(False)

    # -------------------------------------------------------------------------
    # FILE OPERATIONS
    # -------------------------------------------------------------------------
    def new_file(self):
        if not self._confirm_discard_changes():
            return
        self.text.delete("1.0", "end")
        self._clear_all_color_tags()
        self._clear_search_highlight()
        self.file_path = None
        self.text.edit_modified(False)
        self._set_title(modified=False)

    def open_file(self):
        if not self._confirm_discard_changes():
            return

        filetypes = [
            ("Colored text files", "*.gtxt"),
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        ]
        path = filedialog.askopenfilename(
            title="Open",
            filetypes=filetypes
        )
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()

        try:
            if ext == ".gtxt":
                self._open_gtxt(path)
            else:
                self._open_plain_text(path)
        except Exception as e:
            messagebox.showerror("Error opening file", str(e))
            return

        self.file_path = path
        self.text.edit_modified(False)
        self._set_title(modified=False)
        self._update_status_bar()

    def _open_plain_text(self, path):
        with open(path, "r", encoding="utf-8") as f:
            contents = f.read()

        self.text.delete("1.0", "end")
        self._clear_all_color_tags()
        self._clear_search_highlight()
        self.text.insert("1.0", contents)
        # keep current background color; plain text doesn't change it

    def _open_gtxt(self, path):
        """Open our custom JSON-based .gtxt format (text + color spans + bg)."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        text = data.get("text", "")
        colors = data.get("colors", [])
        bg = data.get("background")

        self.text.delete("1.0", "end")
        self._clear_all_color_tags()
        self._clear_search_highlight()
        self.text.insert("1.0", text)

        # Restore background if present
        if bg:
            self.bg_color = bg
            self.text.config(background=self.bg_color)

        # Restore color spans
        for span in colors:
            start = span.get("start")
            end = span.get("end")
            color = span.get("color")
            if not (start and end and color):
                continue
            tag_name = f"fg_{color.lstrip('#')}"
            self.text.tag_configure(tag_name, foreground=color)
            self.text.tag_add(tag_name, start, end)

    def save_file(self):
        if self.file_path is None:
            return self.save_file_as()
        return self._save_to_path(self.file_path)

    def save_file_as(self):
        filetypes = [
            ("Colored text files", "*.gtxt"),
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        ]
        path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".gtxt",  # default to color-aware format
            filetypes=filetypes
        )
        if not path:
            return False
        return self._save_to_path(path)

    def _save_to_path(self, path):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".gtxt":
                self._save_as_gtxt(path)
            else:
                self._save_as_plain_text(path)
        except Exception as e:
            messagebox.showerror("Error saving file", str(e))
            return False

        self.file_path = path
        self.text.edit_modified(False)
        self._set_title(modified=False)
        return True

    def _save_as_plain_text(self, path):
        text = self.text.get("1.0", "end-1c")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def _save_as_gtxt(self, path):
        """
        Save text + all color spans + background color into JSON.

        Format:
        {
          "text": "full text...",
          "background": "#ffffff",
          "colors": [
            {"start": "1.0", "end": "1.4", "color": "#ff0000"},
            ...
          ]
        }
        """
        text = self.text.get("1.0", "end-1c")
        color_spans = []

        # Collect ranges for all fg_ tags
        for tag in self.text.tag_names():
            if not tag.startswith("fg_"):
                continue
            color = "#" + tag[3:]
            ranges = self.text.tag_ranges(tag)
            # ranges is a list: [start1, end1, start2, end2, ...]
            for i in range(0, len(ranges), 2):
                start = str(ranges[i])
                end = str(ranges[i + 1])
                color_spans.append({
                    "start": start,
                    "end": end,
                    "color": color
                })

        data = {
            "text": text,
            "background": self.bg_color,
            "colors": color_spans
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------------------
    # EDIT OPERATIONS
    # -------------------------------------------------------------------------
    def edit_undo(self):
        try:
            self.text.edit_undo()
        except tk.TclError:
            # nothing to undo
            pass

    def edit_redo(self):
        try:
            self.text.edit_redo()
        except tk.TclError:
            # nothing to redo
            pass

    def edit_cut(self):
        self.edit_copy()
        try:
            self.text.delete("sel.first", "sel.last")
        except tk.TclError:
            # no selection
            pass

    def edit_copy(self):
        try:
            selection = self.text.get("sel.first", "sel.last")
        except tk.TclError:
            return
        self.clipboard_clear()
        self.clipboard_append(selection)

    def edit_paste(self):
        try:
            content = self.clipboard_get()
        except tk.TclError:
            return
        self.text.insert("insert", content)

    def select_all(self):
        self.text.tag_add("sel", "1.0", "end-1c")
        return "break"

    # -------------------------------------------------------------------------
    # FORMAT / VIEW
    # -------------------------------------------------------------------------
    def toggle_word_wrap(self):
        self.word_wrap_enabled = not self.word_wrap_enabled
        if self.word_wrap_enabled:
            self.text.config(wrap="word")
        else:
            self.text.config(wrap="none")

    def choose_font(self):
        """Open a simple dialog to choose font family and size."""
        dialog = tk.Toplevel(self)
        dialog.title("Font")
        dialog.transient(self)
        dialog.grab_set()

        # current settings
        current_family = self.current_font.actual("family")
        current_size = self.current_font.actual("size")

        # font families list
        families = sorted(set(tkfont.families()))

        tk.Label(dialog, text="Font:").grid(row=0, column=0, padx=8, pady=(8, 2), sticky="w")
        font_list = tk.Listbox(dialog, height=12, exportselection=False)
        font_list.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")

        # populate families
        for fam in families:
            font_list.insert("end", fam)

        # select current family
        try:
            idx = families.index(current_family)
            font_list.selection_set(idx)
            font_list.see(idx)
        except ValueError:
            pass

        # size selector
        tk.Label(dialog, text="Size:").grid(row=0, column=1, padx=8, pady=(8, 2), sticky="w")
        size_var = tk.StringVar(value=str(current_size))
        size_spin = tk.Spinbox(
            dialog,
            from_=6,
            to=72,
            textvariable=size_var,
            width=5
        )
        size_spin.grid(row=1, column=1, padx=8, pady=(0, 8), sticky="n")

        # make dialog resizable list area
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        # buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=8)

        def on_ok():
            sel = font_list.curselection()
            if not sel:
                # no selection -> keep current family
                new_family = current_family
            else:
                new_family = families[sel[0]]

            try:
                new_size = int(size_var.get())
            except ValueError:
                new_size = current_size

            # apply to current_font (Text widget uses this font object)
            self.current_font.configure(family=new_family, size=new_size)
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(button_frame, text="OK", width=10, command=on_ok).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Cancel", width=10, command=on_cancel).pack(
            side="left", padx=5
        )

        # center dialog over main window
        self._center_window(dialog)

    def _center_window(self, win):
        """Center a toplevel window over the main app window."""
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    # -------------------------------------------------------------------------
    # TEXT COLOR (PER-SELECTION)
    # -------------------------------------------------------------------------
    def pick_text_color(self):
        """Pick a color and apply it only to the selected text."""
        try:
            start = self.text.index("sel.first")
            end = self.text.index("sel.last")
        except tk.TclError:
            # no selection
            return

        color = colorchooser.askcolor(title="Choose text color")
        # color is ( (r,g,b), "#rrggbb" ) or (None, None) if cancelled
        if not color or not color[1]:
            return

        hex_color = color[1]  # "#rrggbb"
        tag_name = f"fg_{hex_color.lstrip('#')}"

        # configure tag (if called again with same color, it's fine)
        self.text.tag_configure(tag_name, foreground=hex_color)

        # apply tag to selection
        self.text.tag_add(tag_name, start, end)

    def clear_text_color(self):
        """Remove all foreground-color tags from the selected text."""
        try:
            start = self.text.index("sel.first")
            end = self.text.index("sel.last")
        except tk.TclError:
            # no selection
            return

        # remove all tags that start with "fg_"
        for tag in self.text.tag_names():
            if tag.startswith("fg_"):
                self.text.tag_remove(tag, start, end)

    def _clear_all_color_tags(self):
        """Remove all foreground-color tags from the entire document."""
        for tag in self.text.tag_names():
            if tag.startswith("fg_"):
                self.text.tag_remove(tag, "1.0", "end")

    # -------------------------------------------------------------------------
    # BACKGROUND COLOR
    # -------------------------------------------------------------------------
    def choose_background_color(self):
        """Pick a background color for the whole editor."""
        color = colorchooser.askcolor(
            title="Choose background color",
            initialcolor=self.bg_color
        )
        if not color or not color[1]:
            return
        self.bg_color = color[1]
        self.text.config(background=self.bg_color)

    # -------------------------------------------------------------------------
    # SEARCH / REPLACE
    # -------------------------------------------------------------------------
    def open_search_panel(self):
        """Open (or focus) the Search + Replace panel."""
        if self.search_window and tk.Toplevel.winfo_exists(self.search_window):
            self.search_window.deiconify()
            self.search_window.lift()
            self.search_window.focus_force()
            return

        self.search_window = tk.Toplevel(self)
        self.search_window.title("Find / Replace")
        self.search_window.transient(self)
        self.search_window.resizable(False, False)

        # close handler
        def on_close():
            self._clear_search_highlight()
            self.search_window.destroy()
            self.search_window = None

        self.search_window.protocol("WM_DELETE_WINDOW", on_close)

        # layout
        tk.Label(self.search_window, text="Find:").grid(row=0, column=0, padx=8, pady=(8, 2), sticky="e")
        find_entry = tk.Entry(self.search_window, textvariable=self.search_var, width=30)
        find_entry.grid(row=0, column=1, padx=8, pady=(8, 2), sticky="w")

        tk.Label(self.search_window, text="Replace:").grid(row=1, column=0, padx=8, pady=2, sticky="e")
        replace_entry = tk.Entry(self.search_window, textvariable=self.replace_var, width=30)
        replace_entry.grid(row=1, column=1, padx=8, pady=2, sticky="w")

        match_case_cb = tk.Checkbutton(
            self.search_window,
            text="Match case",
            variable=self.match_case_var
        )
        match_case_cb.grid(row=2, column=1, padx=8, pady=(2, 8), sticky="w")

        # buttons
        btn_frame = ttk.Frame(self.search_window)
        btn_frame.grid(row=0, column=2, rowspan=3, padx=8, pady=8, sticky="ns")

        ttk.Button(btn_frame, text="Find Next", width=12, command=self.find_next).pack(pady=2)
        ttk.Button(btn_frame, text="Replace", width=12, command=self.replace_one).pack(pady=2)
        ttk.Button(btn_frame, text="Replace All", width=12, command=self.replace_all).pack(pady=2)
        ttk.Button(btn_frame, text="Close", width=12, command=on_close).pack(pady=(8, 2))

        # focus on find box
        find_entry.focus_set()

        # center over main window
        self._center_window(self.search_window)

    def _clear_search_highlight(self):
        self.text.tag_remove("search_highlight", "1.0", "end")

    def find_next(self):
        """Find next occurrence of the search text."""
        pattern = self.search_var.get()
        if not pattern:
            return

        # starting position: just after current insertion
        start_pos = self.text.index("insert")
        # search options
        nocase = not self.match_case_var.get()

        idx = self.text.search(
            pattern,
            start_pos,
            stopindex="end",
            nocase=nocase
        )

        # if not found from cursor to end, wrap from start
        if not idx:
            idx = self.text.search(pattern, "1.0", stopindex="end", nocase=nocase)
            if not idx:
                # not found at all
                self._clear_search_highlight()
                return

        # highlight match
        end_idx = f"{idx}+{len(pattern)}c"
        self._clear_search_highlight()
        self.text.tag_add("search_highlight", idx, end_idx)
        self.text.tag_configure("search_highlight", background="#ffff66")
        self.text.mark_set("insert", end_idx)
        self.text.see(idx)

    def replace_one(self):
        """Replace the current match and find the next."""
        pattern = self.search_var.get()
        replace_text = self.replace_var.get()
        if not pattern:
            return

        # see if something is highlighted with search_highlight
        ranges = self.text.tag_ranges("search_highlight")
        if ranges:
            start = ranges[0]
            end = ranges[1]
            self.text.delete(start, end)
            self.text.insert(start, replace_text)
            # move cursor after replacement
            self.text.mark_set("insert", f"{start}+{len(replace_text)}c")
        # then search next
        self.find_next()

    def replace_all(self):
        """Replace all occurrences of the search text."""
        pattern = self.search_var.get()
        replace_text = self.replace_var.get()
        if not pattern:
            return

        nocase = not self.match_case_var.get()
        start_pos = "1.0"
        self._clear_search_highlight()

        while True:
            idx = self.text.search(pattern, start_pos, stopindex="end", nocase=nocase)
            if not idx:
                break
            end_idx = f"{idx}+{len(pattern)}c"
            self.text.delete(idx, end_idx)
            self.text.insert(idx, replace_text)
            # continue searching after the inserted text
            start_pos = f"{idx}+{len(replace_text)}c"

    # -------------------------------------------------------------------------
    # HELP
    # -------------------------------------------------------------------------
    def show_about(self):
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME}\n\nA simple open-source Notepad-style editor\n"
            "Written in Python with Tkinter.\n\n"
            "Use .gtxt if you want to preserve colors & background."
        )

    # -------------------------------------------------------------------------
    # EXIT
    # -------------------------------------------------------------------------
    def on_exit(self):
        if not self._confirm_discard_changes():
            return
        self.destroy()

    # -------------------------------------------------------------------------
    # KEYBOARD SHORTCUT HANDLERS (events)
    # -------------------------------------------------------------------------
    def _shortcut_new(self, event):
        self.new_file()
        return "break"

    def _shortcut_open(self, event):
        self.open_file()
        return "break"

    def _shortcut_save(self, event):
        self.save_file()
        return "break"

    def _shortcut_undo(self, event):
        self.edit_undo()
        return "break"

    def _shortcut_redo(self, event):
        self.edit_redo()
        return "break"

    def _shortcut_cut(self, event):
        self.edit_cut()
        return "break"

    def _shortcut_copy(self, event):
        self.edit_copy()
        return "break"

    def _shortcut_paste(self, event):
        self.edit_paste()
        return "break"

    def _shortcut_select_all(self, event):
        self.select_all()
        return "break"

    def _shortcut_datetime(self, event):
        now = datetime.now().strftime("%H:%M %d.%m.%Y")
        self.text.insert("insert", now)
        return "break"

    def _shortcut_find_replace(self, event):
        self.open_search_panel()
        return "break"


def main():
    app = NotepadApp()
    app.mainloop()


if __name__ == "__main__":
    main()
