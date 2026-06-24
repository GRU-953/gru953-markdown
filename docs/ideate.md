# Ideate

## Acceptance items to cover (from brainstorm)
1. User can open a file via a dialog
2. Clicking Convert calls MarkItDown and shows Markdown in a scrollable area
3. User can save the output as a .md file
4. Errors are shown as a plain message

## Candidate A — single-file tkinter app
- One file: converter.py
- GUI: tkinter (Python stdlib, zero extra install)
- File open: tkinter.filedialog.askopenfilename()
- Conversion: MarkItDown().convert(path).text_content
- Output display: tkinter.scrolledtext.ScrolledText
- Save: tkinter.filedialog.asksaveasfilename() + open/write
- Errors: tkinter.messagebox.showerror()
- Run: python converter.py
- Dependencies: pip install markitdown
- Covers all 4 items. Assumptions: Python 3.x installed.

## Candidate B — single-file CustomTkinter app
- One file: converter.py
- GUI: customtkinter (modern rounded look, auto dark/light mode)
- Same logic as A but with CTk widgets
- Dependencies: pip install markitdown customtkinter
- Covers all 4 items. Assumptions: Python 3.x installed + customtkinter.

## Score (text-phase rule: coverage first, then fewest assumptions)
| Candidate | Covers all 4 items | Assumptions         | Lines (est) |
|-----------|-------------------|---------------------|-------------|
| A tkinter | yes               | 1 (Python)          | ~60         |
| B CTk     | yes               | 2 (Python + ctk)    | ~70         |

## Winner: Candidate A
Same coverage, one fewer dependency, smaller. B is a cosmetic upgrade with no
functional gain — YAGNI rules it out.

## Shape chosen
Single file converter.py + requirements.txt (one line: markitdown).
No package structure, no setup.py, no bundling.
