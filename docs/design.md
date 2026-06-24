# Design

## Files
`
converter.py        # entire app — one file
requirements.txt    # one line: markitdown
`

## Window layout
`
+---------------------------------------------------+
| Title: MarkItDown Converter  (resizable)          |
+---------------------------------------------------+
| [Open File...]   <selected file path label>       |
|                                                   |
| [Convert]                                         |
|---------------------------------------------------|
| Markdown Output:                                  |
| +-----------------------------------------------+ |
| |  scrolledtext.ScrolledText  (DISABLED/readonly)| |
| |  full-width, fills remaining height            | |
| +-----------------------------------------------+ |
|                                                   |
| [Save as .md...]                                  |
+---------------------------------------------------+
`

## Class: App(tk.Tk)

### State
- _file_path: tk.StringVar  — bound to the path label; starts "No file selected"
- _md: MarkItDown()         — single shared instance
- _output: scrolledtext.ScrolledText — the output widget

### Methods
- __init__: set title, min size 600x400, create _md, call _build_ui
- _build_ui: lay out all widgets with grid (row weight so output expands)
- _open(): filedialog.askopenfilename(); if path: _file_path.set(path)
- _convert(): guard no-file; try MarkItDown().convert(); fill _output; except -> showerror
- _save(): get _output text; guard empty; asksaveasfilename(.md/.txt); write utf-8

## Import guard
Wrap rom markitdown import MarkItDown in try/except ImportError:
  show messagebox.showerror("MarkItDown not found",
    "Run: pip install markitdown") then sys.exit(1).

## Grid layout (column 0 stretches)
- row 0: Open button (sticky W) + path label (sticky EW, col 1)
- row 1: Convert button (sticky W)
- row 2: "Markdown Output:" label (sticky W)
- row 3: ScrolledText (sticky NSEW, columnspan 2) — row weight=1
- row 4: Save button (sticky W)

## requirements.txt
`
markitdown
`

## Acceptance check (for test phase)
- python converter.py launches without error
- Open File dialog opens on click
- Convert on a .docx/.pdf/.txt fills the text area
- Save writes a .md file containing the text
- Bad file shows showerror, does not crash