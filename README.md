# 🔬 Research Logger
## A Minimal Digital Lab Notebook for Researchers

A clean, lightweight daily research logging application for Windows.
Log your experiments, ideas, results, and plans — all in one place.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📓 Daily Log Entries | Auto-filled template with structured sections |
| 🗓 Calendar View | Browse and navigate past entries visually |
| 📎 Attachments | Attach PDFs, images, files with drag-and-drop |
| 🔍 Full-Text Search | Search by keyword, date range, or tag |
| 🏷 Tags | Tag entries and filter your log by topic |
| ⏰ Daily Reminders | Configurable popup reminder (e.g. 8 PM) |
| 🌅 Morning Summary | See yesterday's work when you open the app |
| 📊 Auto Summaries | Weekly & monthly summaries via local TF-IDF NLP |
| 📥 PDF Export | Export any entry or summary to a clean PDF |
| 💾 Auto-Save | Every 10 seconds (configurable) |
| 👁 Markdown Preview | Live rendered preview of your notes |
| 🌙 Dark Mode | Toggle between light and dark themes in Settings |

---

## 🖥 System Requirements

- **OS:** Windows 10 / 11 (also works on macOS and Linux)
- **Python:** 3.10 or newer
- **Disk:** ~50 MB for dependencies

---

## 📦 Installation

### 1. Install Python
Download from [python.org](https://www.python.org/downloads/) — ensure "Add Python to PATH" is checked.

### 2. Clone or download this folder
```
research_logger/
├── main.py
├── requirements.txt
├── styles.qss
├── styles_dark.qss
├── database/
│   └── db_manager.py
├── ui/
│   ├── main_window.py
│   ├── sidebar.py
│   ├── editor_panel.py
│   ├── attachments_panel.py
│   ├── search_dialog.py
│   ├── settings_dialog.py
│   ├── summary_dialog.py
│   └── morning_summary.py
└── utils/
    ├── templates.py
    ├── summarizer.py
    ├── reminder.py
    └── exporter.py
```

### 3. Install dependencies
Open a terminal / Command Prompt in the `research_logger` folder:

```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
python main.py
```

---

## 🚀 Quick Start Guide

### Opening the App
Each time you open Research Logger, if it's morning (6–11 AM) and you have
a yesterday entry, a **Morning Summary** popup will appear showing:
- What you worked on yesterday
- Your "Plan for Tomorrow" from yesterday

### Writing a Log Entry
Today's entry opens automatically with this template:

```markdown
# Research Log — Wednesday, January 15, 2025

## What I Worked On Today

## Experiments / Results

## Problems Encountered

## Ideas / Observations

## Plan for Tomorrow
```

Fill in each section. **Auto-save runs every 10 seconds.**

### Adding Tags
At the bottom of the editor, type tags separated by commas:
```
ml-experiment, paper-review, debugging, neural-network
```
Tags appear in the sidebar for quick filtering.

### Attaching Files
- **Drag and drop** any file onto the right panel
- Or click **+ Add File** to browse
- Attached files are stored in `/attachments/YYYY-MM-DD/`
- A markdown link is automatically inserted into your entry

### Searching Logs
Press **Ctrl+F** or click 🔍 Search to open the search dialog.
- Search by keyword (full-text search)
- Filter by tag
- Double-click a result to open that entry

### Summaries
Click **📊 Summary** in the toolbar:
- **Weekly tab** — highlights from the last 7 days with keyword extraction
- **Monthly tab** — overview of an entire month

### Exporting to PDF
Press **Ctrl+E** or click **📥 Export PDF** to save the current entry as a PDF.
Summaries can also be exported from the Summary dialog.

### Reminders
Go to **⚙️ Settings** to configure:
- Reminder time (default: 20:00)
- Enable/disable morning summary
- Auto-save interval
- Light / Dark theme

---

## 📂 Data Storage

All data is stored locally:

| Data | Location |
|---|---|
| Log database | `research_logger/research_logger.db` (SQLite) |
| Attachments | `research_logger/attachments/YYYY-MM-DD/` |
| Exported PDFs | Wherever you choose to save them |

No data is sent to any server. Everything is offline and private.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+T` | Open today's entry |
| `Ctrl+N` | New entry (pick date) |
| `Ctrl+F` | Search logs |
| `Ctrl+E` | Export current entry to PDF |
| `Ctrl+S` | Force save (via autosave trigger) |

---

## 🔮 Future Upgrade Ideas

1. **AI Summaries** — Plug in a local LLM (Ollama / llama.cpp) for smarter summaries
2. **Research Timeline** — Visual timeline of activity with entry density graphs
3. **Experiment Tracker** — Dedicated experiment management with parameters & results tables
4. **Graph of Activity** — Calendar heatmap (like GitHub contributions)
5. **Notion Export** — Export entries to Notion or Obsidian format
6. **Citation Manager** — Link DOIs and papers to entries
7. **Collaboration** — Shared team log via SQLite over network share
8. **Mobile Companion** — Quick-add entries from phone via local REST API
9. **Voice Notes** — Attach audio recordings to entries
10. **LaTeX Support** — Render equations in the preview pane

---


---

## 🔨 Building a Standalone Windows EXE

You can package the app into a single distributable `.exe` that requires **no Python installation** on the target machine.

### Quick build (recommended)

**Option A — PowerShell (works with both `pip` and `uv`):**
```powershell
.\build_exe.ps1
```

**Option B — Command Prompt:**
```bat
build_exe.bat
```

Both scripts will:
1. Install all dependencies (including PyInstaller)
2. Clean any previous build
3. Run PyInstaller with the included `research_logger.spec`
4. Output the finished app to `dist\ResearchLogger\`

### Manual build

```powershell
pip install pyinstaller
pyinstaller research_logger.spec --noconfirm
```

### Output

```
dist/
└── ResearchLogger/
    ├── ResearchLogger.exe   ← Launch this
    ├── PySide6/
    └── ... (supporting DLLs)
```

Zip the entire `dist\ResearchLogger\` folder to share with others — it runs on any Windows 10/11 PC with no dependencies.

### Adding a custom icon

1. Create or find a 256×256 `.ico` file and name it `icon.ico`
2. Place it in the `research_logger/` folder
3. Uncomment the `icon='icon.ico'` line in `research_logger.spec`
4. Rebuild

### Build time & size

| Metric | Typical value |
|---|---|
| Build time | 2–4 minutes |
| Output folder size | ~150–250 MB |
| Zipped for distribution | ~80–120 MB |

> **Note:** The large size is because PySide6 bundles Qt's full runtime. This is normal for Qt-based Python apps.

## 🐛 Troubleshooting

**App won't start?**
```bash
pip install --upgrade PySide6 PySide6-WebEngine
```

**PDF export fails?**
```bash
pip install reportlab
```

**Markdown preview is blank?**
```bash
pip install markdown2
```

**Preview pane missing?**
`QWebEngineView` requires `PySide6-WebEngine`. Install it with:
```bash
pip install PySide6-WebEngine
```

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built with Python + PySide6. Designed for researchers who value simplicity.*
