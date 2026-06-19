"""
File Integrity Monitor
======================
A Windows desktop tool that detects file changes, additions, and deletions.
Built for non-technical users — no dependencies beyond Python's standard library.

Usage:  python monitor.py
"""

import hashlib
import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from datetime import datetime

# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────
SNAPSHOT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fim_snapshot.json")

COLORS = {
    "bg":        "#1E1E2E",   # dark navy background
    "panel":     "#2A2A3E",   # slightly lighter panels
    "accent":    "#7C6AF7",   # purple accent
    "accent2":   "#5A4FD4",   # darker purple for hover
    "text":      "#E0E0F0",   # light text
    "subtext":   "#9090A8",   # muted text
    "added":     "#6BCB77",   # green  — new files
    "deleted":   "#FF6B6B",   # red    — removed files
    "modified":  "#FFD166",   # yellow — changed files
    "info":      "#9090A8",   # grey   — status messages
    "border":    "#3A3A54",   # subtle border
    "badge_ok":  "#27AE60",   # green badge
    "badge_warn":"#E74C3C",   # red badge
    "badge_idle":"#5A4FD4",   # purple badge (idle)
}

FONT_MONO  = ("Consolas", 10)
FONT_UI    = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI Semibold", 13)
FONT_SMALL = ("Segoe UI", 9)


# ─────────────────────────────────────────────
#  Core logic (no GUI dependencies)
# ─────────────────────────────────────────────

def hash_file(filepath: str) -> str | None:
    """Return the SHA-256 hex digest of a file, or None on error."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (PermissionError, OSError):
        return None


def scan_folder(folder: str, progress_cb=None) -> dict[str, str]:
    """
    Walk *folder* recursively and hash every readable file.
    Returns {relative_path: sha256_hex}.
    Files that cannot be read are silently skipped.
    progress_cb(filename) is called for each file (optional).
    """
    snapshot: dict[str, str] = {}
    for root, _, files in os.walk(folder):
        for name in files:
            full_path = os.path.join(root, name)
            relative  = os.path.relpath(full_path, folder)
            if progress_cb:
                progress_cb(relative)
            digest = hash_file(full_path)
            if digest is not None:
                snapshot[relative] = digest
    return snapshot


def compare_snapshots(old: dict, new: dict) -> dict[str, list]:
    """Return a dict with keys 'added', 'deleted', 'modified'."""
    added    = sorted(f for f in new if f not in old)
    deleted  = sorted(f for f in old if f not in new)
    modified = sorted(f for f in new if f in old and new[f] != old[f])
    return {"added": added, "deleted": deleted, "modified": modified}


def save_snapshot(folder: str, files: dict) -> None:
    data = {
        "folder":   folder,
        "taken_at": datetime.now().isoformat(timespec="seconds"),
        "files":    files,
    }
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_snapshot() -> dict | None:
    """Load the saved snapshot JSON, or return None if it doesn't exist."""
    if not os.path.exists(SNAPSHOT_FILE):
        return None
    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


# ─────────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────────

class FIMApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("File Integrity Monitor")
        self.resizable(True, True)
        self.minsize(680, 520)
        self.configure(bg=COLORS["bg"])

        # Set window icon (works silently if no .ico is present)
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self._last_report: str = ""          # text of the last check report
        self._busy: bool = False             # True while a scan is running

        self._build_ui()
        self._refresh_snapshot_info()

        # Centre window on screen
        self.update_idletasks()
        w, h = 780, 600
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── UI construction ─────────────────────────────────────────────

    def _build_ui(self):
        # ── outer padding frame
        outer = tk.Frame(self, bg=COLORS["bg"], padx=18, pady=14)
        outer.pack(fill="both", expand=True)

        # ── title row
        title_row = tk.Frame(outer, bg=COLORS["bg"])
        title_row.pack(fill="x", pady=(0, 12))

        tk.Label(
            title_row,
            text="🛡  File Integrity Monitor",
            font=FONT_TITLE,
            bg=COLORS["bg"],
            fg=COLORS["text"],
        ).pack(side="left")

        # Status badge
        self._badge_var = tk.StringVar(value="  IDLE  ")
        self._badge = tk.Label(
            title_row,
            textvariable=self._badge_var,
            font=FONT_SMALL,
            bg=COLORS["badge_idle"],
            fg="white",
            padx=8,
            pady=3,
            relief="flat",
        )
        self._badge.pack(side="right", padx=(0, 2))

        # ── snapshot info bar
        self._info_var = tk.StringVar(value="No snapshot on file.")
        info_bar = tk.Frame(outer, bg=COLORS["panel"], pady=6, padx=10)
        info_bar.pack(fill="x", pady=(0, 10))
        info_bar.configure(highlightbackground=COLORS["border"], highlightthickness=1)

        tk.Label(
            info_bar,
            textvariable=self._info_var,
            font=FONT_SMALL,
            bg=COLORS["panel"],
            fg=COLORS["subtext"],
            anchor="w",
        ).pack(fill="x")

        # ── folder picker row
        folder_row = tk.Frame(outer, bg=COLORS["bg"])
        folder_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            folder_row,
            text="Folder to monitor:",
            font=FONT_UI,
            bg=COLORS["bg"],
            fg=COLORS["text"],
        ).pack(side="left", padx=(0, 8))

        self._folder_var = tk.StringVar()
        folder_entry = tk.Entry(
            folder_row,
            textvariable=self._folder_var,
            font=FONT_UI,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        folder_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

        self._make_button(folder_row, "📂  Browse", self._browse).pack(side="left")

        # ── action buttons
        btn_row = tk.Frame(outer, bg=COLORS["bg"])
        btn_row.pack(fill="x", pady=(0, 12))

        self._btn_snapshot = self._make_button(
            btn_row, "📸  Take Snapshot", self._take_snapshot, width=20
        )
        self._btn_snapshot.pack(side="left", padx=(0, 8))

        self._btn_check = self._make_button(
            btn_row, "🔍  Check for Changes", self._check_changes, width=22
        )
        self._btn_check.pack(side="left", padx=(0, 8))

        self._btn_report = self._make_button(
            btn_row, "💾  Save Report", self._save_report, width=16
        )
        self._btn_report.pack(side="left", padx=(0, 8))

        self._make_button(
            btn_row, "🗑  Clear Log", self._clear_log, width=14, secondary=True
        ).pack(side="right")

        # ── log area
        log_frame = tk.Frame(outer, bg=COLORS["panel"], padx=1, pady=1)
        log_frame.pack(fill="both", expand=True)

        self.log = scrolledtext.ScrolledText(
            log_frame,
            font=FONT_MONO,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["accent"],
            relief="flat",
            state="disabled",
            wrap="none",
            padx=10,
            pady=8,
        )
        self.log.pack(fill="both", expand=True)

        # colour tags
        self.log.tag_config("added",    foreground=COLORS["added"])
        self.log.tag_config("deleted",  foreground=COLORS["deleted"])
        self.log.tag_config("modified", foreground=COLORS["modified"])
        self.log.tag_config("info",     foreground=COLORS["info"])
        self.log.tag_config("header",   foreground=COLORS["accent"])
        self.log.tag_config("ok",       foreground=COLORS["added"])
        self.log.tag_config("error",    foreground=COLORS["deleted"])

        # ── status bar at bottom
        self._status_var = tk.StringVar(value="Ready.")
        status_bar = tk.Label(
            self,
            textvariable=self._status_var,
            font=FONT_SMALL,
            bg=COLORS["border"],
            fg=COLORS["subtext"],
            anchor="w",
            padx=12,
            pady=4,
        )
        status_bar.pack(fill="x", side="bottom")

    def _make_button(self, parent, text, command, width=None, secondary=False):
        bg     = COLORS["panel"]     if secondary else COLORS["accent"]
        fg     = COLORS["subtext"]   if secondary else "white"
        active = COLORS["border"]    if secondary else COLORS["accent2"]

        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=FONT_UI,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
        )
        if width:
            btn.config(width=width)
        return btn

    # ── helpers ─────────────────────────────────────────────────────

    def _log(self, text: str, tag: str = "info") -> None:
        """Append *text* to the log box (must be called from the main thread)."""
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _log_separator(self) -> None:
        self._log("─" * 60, "info")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)

    def _set_badge(self, text: str, color: str) -> None:
        self._badge_var.set(f"  {text}  ")
        self._badge.configure(bg=color)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        for btn in (self._btn_snapshot, self._btn_check, self._btn_report):
            btn.configure(state=state)

    def _get_folder(self) -> str | None:
        """Return the folder path from the entry field, or show an error."""
        folder = self._folder_var.get().strip()
        if not folder:
            messagebox.showwarning("No folder", "Please select a folder first.")
            return None
        if not os.path.isdir(folder):
            messagebox.showerror("Folder not found", f"'{folder}' is not a valid directory.")
            return None
        return folder

    def _refresh_snapshot_info(self) -> None:
        snap = load_snapshot()
        if snap:
            taken  = snap.get("taken_at", "unknown time")
            folder = snap.get("folder",   "unknown folder")
            count  = len(snap.get("files", {}))
            self._info_var.set(
                f"Snapshot on file — {count} file(s)  •  taken {taken}  •  {folder}"
            )
        else:
            self._info_var.set("No snapshot on file.  Take a snapshot to get started.")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ── actions ─────────────────────────────────────────────────────

    def _browse(self) -> None:
        folder = filedialog.askdirectory(title="Select folder to monitor")
        if folder:
            self._folder_var.set(folder)

    def _take_snapshot(self) -> None:
        folder = self._get_folder()
        if not folder or self._busy:
            return

        self._set_busy(True)
        self._set_badge("SCANNING", COLORS["badge_warn"])
        self._log_separator()
        self._log(f"📸  Taking snapshot of:  {folder}", "header")
        self._log(f"    Started at {datetime.now().strftime('%H:%M:%S')}", "info")

        def run():
            def progress(rel):
                self.after(0, lambda r=rel: self._set_status(f"Hashing: {r}"))

            try:
                files = scan_folder(folder, progress_cb=progress)
                save_snapshot(folder, files)

                def done():
                    self._log(f"✔  Snapshot saved — {len(files)} file(s) recorded.", "ok")
                    self._log(f"   Saved to: {SNAPSHOT_FILE}", "info")
                    self._set_status("Snapshot complete.")
                    self._set_badge("SNAPSHOT TAKEN", COLORS["badge_ok"])
                    self._refresh_snapshot_info()
                    self._set_busy(False)

                self.after(0, done)

            except Exception as exc:
                def err(e=exc):
                    self._log(f"✖  Error: {e}", "error")
                    self._set_status("Snapshot failed.")
                    self._set_badge("ERROR", COLORS["badge_warn"])
                    self._set_busy(False)
                self.after(0, err)

        threading.Thread(target=run, daemon=True).start()

    def _check_changes(self) -> None:
        if self._busy:
            return

        snap = load_snapshot()
        if snap is None:
            messagebox.showinfo(
                "No snapshot",
                "No snapshot found.\nPlease take a snapshot first, then run a check.",
            )
            return

        snap_folder = snap.get("folder", "")

        # Allow the user to override the folder (e.g. after moving files)
        current_folder = self._folder_var.get().strip()
        folder = current_folder if current_folder and os.path.isdir(current_folder) else snap_folder

        if not os.path.isdir(folder):
            messagebox.showerror(
                "Folder not found",
                f"The snapshot folder no longer exists:\n{folder}\n\n"
                "Select a valid folder in the path bar and try again.",
            )
            return

        self._set_busy(True)
        self._set_badge("CHECKING", COLORS["badge_warn"])
        self._log_separator()
        self._log(f"🔍  Checking for changes in:  {folder}", "header")
        self._log(
            f"    Comparing against snapshot from {snap.get('taken_at', '?')}",
            "info",
        )

        def run():
            def progress(rel):
                self.after(0, lambda r=rel: self._set_status(f"Scanning: {r}"))

            try:
                current_files = scan_folder(folder, progress_cb=progress)
                diff = compare_snapshots(snap["files"], current_files)

                added    = diff["added"]
                deleted  = diff["deleted"]
                modified = diff["modified"]
                total    = len(added) + len(deleted) + len(modified)

                # Build the report text (also used by Save Report)
                lines = []
                lines.append(
                    f"File Integrity Check — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                lines.append(f"Folder   : {folder}")
                lines.append(
                    f"Snapshot : {snap.get('taken_at','?')}  ({len(snap['files'])} files)"
                )
                lines.append(f"Current  : {len(current_files)} files")
                lines.append("")

                if total == 0:
                    lines.append("✔  No changes detected.")
                else:
                    if added:
                        lines.append(f"ADDED ({len(added)}):")
                        lines += [f"  + {f}" for f in added]
                        lines.append("")
                    if deleted:
                        lines.append(f"DELETED ({len(deleted)}):")
                        lines += [f"  - {f}" for f in deleted]
                        lines.append("")
                    if modified:
                        lines.append(f"MODIFIED ({len(modified)}):")
                        lines += [f"  ~ {f}" for f in modified]
                        lines.append("")

                report_text = "\n".join(lines)

                def done():
                    self._last_report = report_text

                    if total == 0:
                        self._log("✔  No changes detected — everything looks clean.", "ok")
                        self._set_badge("CLEAN", COLORS["badge_ok"])
                    else:
                        if added:
                            self._log(f"\n  ┌─ ADDED ({len(added)}) ─────────────────────", "added")
                            for f in added:
                                self._log(f"  │  + {f}", "added")

                        if deleted:
                            self._log(f"\n  ┌─ DELETED ({len(deleted)}) ──────────────────", "deleted")
                            for f in deleted:
                                self._log(f"  │  - {f}", "deleted")

                        if modified:
                            self._log(f"\n  ┌─ MODIFIED ({len(modified)}) ────────────────", "modified")
                            for f in modified:
                                self._log(f"  │  ~ {f}", "modified")

                        self._log(
                            f"\n  {total} change(s) found  "
                            f"({len(added)} added, {len(deleted)} deleted, {len(modified)} modified)",
                            "error",
                        )
                        self._set_badge("CHANGES FOUND", COLORS["badge_warn"])

                    self._set_status(
                        f"Check complete — {total} change(s) found."
                        if total else "Check complete — no changes."
                    )
                    self._set_busy(False)

                self.after(0, done)

            except Exception as exc:
                def err(e=exc):
                    self._log(f"✖  Error during check: {e}", "error")
                    self._set_status("Check failed.")
                    self._set_badge("ERROR", COLORS["badge_warn"])
                    self._set_busy(False)
                self.after(0, err)

        threading.Thread(target=run, daemon=True).start()

    def _save_report(self) -> None:
        if not self._last_report:
            messagebox.showinfo(
                "Nothing to save",
                "Run a check first — the report will appear here once changes are detected.",
            )
            return

        path = filedialog.asksaveasfilename(
            title="Save report",
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
            initialfile=f"fim_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._last_report)
            self._log(f"💾  Report saved to: {path}", "ok")
            self._set_status(f"Report saved: {path}")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = FIMApp()
    app.mainloop()
