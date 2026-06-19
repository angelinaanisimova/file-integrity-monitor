🛡 File Integrity Monitor

A simple Windows desktop tool that detects file changes, additions, and deletions.  
Built for non-technical users — no configuration, no installs beyond Python.

---

## What it does

1. **Take a Snapshot** — scans a folder and records a SHA-256 fingerprint of every file.
2. **Check for Changes** — re-scans and compares the current state to the snapshot.
3. **See exactly what changed** — new files appear in green, deleted in red, modified in yellow.
4. **Export a report** — save the results to a plain `.txt` file.

---

## Who it's for

Anyone who needs to know whether files in a folder have been tampered with, accidentally modified, or deleted — without running enterprise software.

Typical uses:
- Monitoring a folder of important documents
- Verifying that a USB drive's contents haven't changed
- Checking that a software installation didn't touch files it shouldn't have

---

## Requirements

- **Windows 10 or 11**
- **Python 3.10 or newer** (download from [python.org](https://www.python.org/downloads/))
- No extra packages — uses only Python's standard library

---

## How to run

```bash
python monitor.py
```

That's it. No `pip install`, no virtual environment.

### Step-by-step for first-time Python users

1. Download and install Python from [python.org](https://www.python.org/downloads/)  
   ✅ Check **"Add Python to PATH"** during install
2. Download or clone this repository
3. Open the folder in File Explorer, click the address bar, type `cmd`, press Enter
4. In the black window that opens, type `python monitor.py` and press Enter

---

## How to use

| Step | Action |
|------|--------|
| 1 | Click **Browse** and select the folder you want to monitor |
| 2 | Click **📸 Take Snapshot** — this records all file fingerprints |
| 3 | Come back later (or make a test change to a file) |
| 4 | Click **🔍 Check for Changes** to see what's different |
| 5 | Optionally click **💾 Save Report** to export results as `.txt` |

### Reading the results

| Colour | Meaning |
|--------|---------|
| 🟢 Green | File was **added** (new file found) |
| 🔴 Red | File was **deleted** (no longer present) |
| 🟡 Yellow | File was **modified** (contents changed) |

---

## Does it send my files anywhere?

**No.** This tool runs entirely on your computer.  
No internet connection is used. No data leaves your machine.  
The snapshot is saved as `fim_snapshot.json` in the same folder as `monitor.py`.

---

## Project structure

```
file_integrity_monitor/
├── monitor.py           ← the entire application (one file)
├── README.md            ← this file
└── fim_snapshot.json    ← created automatically; do NOT commit to Git
```

---

## Packaging as a standalone .exe (no Python required)

Once you've tested the app, you can build a single `.exe` so users don't need Python installed:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed monitor.py
```

The executable appears at `dist/monitor.exe`. Users just double-click it.

---

## Planned improvements

- [ ] Exclude file types from scan (e.g. ignore `.tmp` files)
- [ ] Email alert when changes are detected
- [ ] Windows Task Scheduler integration for automatic checks
- [ ] Multiple folder profiles

---

## License

MIT — free to use, modify, and distribute.
onitor
A simple desktop tool that detects file changes, additions, and deletions. Built for non-technical Windows users.
