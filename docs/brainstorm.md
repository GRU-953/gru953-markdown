# Brainstorm

## Idea (verbatim)
Develop a Windows application to convert files to markdown formats using
https://github.com/microsoft/markitdown

## One-line restatement
A Windows GUI app where you pick a file, click Convert, and get clean Markdown out -
powered by Microsoft's MarkItDown library.

## Core need
Users have files in office formats (Word, Excel, PowerPoint, PDF, HTML, etc.)
and need their content as plain Markdown text - for notes, wikis, AI pipelines,
or static sites.

## What MarkItDown gives us
- Python library (and CLI) by Microsoft
- Converts: PDF, .docx, .xlsx, .pptx, .html, images, audio, CSV, JSON, XML, ZIP
- Output: Markdown string
- Install: pip install markitdown

## Constraints
1. Python required - MarkItDown is a Python package; the app runs in Python.
2. Windows target - GUI must work on Windows 10/11.
3. Smallest-correct GUI - tkinter is bundled with Python (zero extra deps).
4. Distribution - plain Python script + requirements.txt; no bundling needed for now.

## Acceptance items (minimum)
- [ ] User can open a file via a dialog
- [ ] Clicking Convert calls MarkItDown and shows Markdown in a scrollable area
- [ ] User can save the output as a .md file
- [ ] Errors (unsupported file, MarkItDown exception) are shown as a plain message

## YAGNI - deliberately left out
- Drag and drop (not required)
- Batch/folder conversion (not required)
- Markdown preview/render (not required)
- Dark mode toggle (not required)
- PyInstaller / .exe packaging (not required yet)
- Settings panel (not required)
