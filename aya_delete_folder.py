import logging
import os
import sys
import time
import threading
import psutil
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class SuperFastDeleteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AYA DELETER")
        self.root.geometry("720x480")
        import ctypes
        myappid = 'artainovasipersada.ayadeletefolder.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        os.environ['PYTHONWINDOWICON'] = os.path.abspath('AYA.ico')
        self._set_app_icon(root)
        # Calculate optimal workers based on system resources
        self.delete_workers = self._calculate_workers()

        # GUI state
        self.folder_path = tk.StringVar()
        self.progress = tk.DoubleVar(value=0.0)
        self.status = tk.StringVar(value=f"Ready (Workers: {self.delete_workers})")
        self.speed = tk.StringVar(value="0 files/sec")
        self.file_count = tk.IntVar(value=0)
        self.total_files = tk.IntVar(value=0)
        self.total_size = tk.StringVar(value="0 GB")
        self.eta = tk.StringVar(value="-")
        self.current_file = tk.StringVar(value="")

        # Runtime state
        self.cancel_flag = threading.Event()
        self.executor = None
        self.processed_files = 0
        self._start_time = None
        self._lock = threading.Lock()
        self._total_size_bytes = 0

        self.create_widgets()
        self.setup_styles()

    def _get_resource_path(self, filename):
        base_path = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(base_path, filename),
            os.path.join(getattr(sys, '_MEIPASS', ''), filename),
            filename
        ]
        for path in possible_paths:
            if path and os.path.exists(path):
                return path
        return None

    def _set_app_icon(self, window=None):
        target = window or self
        try:
            target.iconbitmap(self._get_resource_path('AYA.ico'))
        except Exception as e:
            logging.warning(f"Failed to set icon: {e}")
    def _calculate_workers(self):
        """Calculate optimal number of workers based on system resources"""
        try:
            # Base workers on CPU cores (I/O bound can use more than cores)
            cpu_count = os.cpu_count() or 4
            cpu_workers = cpu_count * 2

            # Limit based on available memory (1 worker per 512MB)
            mem = psutil.virtual_memory()
            mem_workers = mem.available // (512 * 1024 * 1024)

            # Use minimum between CPU and memory suggestion
            workers = min(cpu_workers, mem_workers, 128)  # Max 128 workers

            # Special case for high-end systems
            if mem.total >= 32 * 1024 * 1024 * 1024:  # 32GB+ RAM
                workers = min(workers * 2, 256)  # Up to 256 workers for extreme systems

            return max(4, workers)  # Minimum 4 workers
        except:
            return 8  # Fallback value

    def create_widgets(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # Folder selection
        path_frame = ttk.LabelFrame(main, text="Folder to Delete", padding=10)
        path_frame.pack(fill=tk.X, pady=6)

        ttk.Label(path_frame, text="Folder Path:").grid(row=0, column=0, sticky="w")
        path_entry = ttk.Entry(path_frame, textvariable=self.folder_path)
        path_entry.grid(row=0, column=1, padx=6, sticky="we")
        ttk.Button(path_frame, text="Browse", command=self.browse_folder).grid(row=0, column=2)
        path_frame.columnconfigure(1, weight=1)

        # Progress info
        prog_frame = ttk.LabelFrame(main, text="Deletion Progress", padding=10)
        prog_frame.pack(fill=tk.X, pady=6)

        ttk.Label(prog_frame, textvariable=self.status).pack(anchor="w")
        ttk.Label(prog_frame, textvariable=self.current_file, foreground="gray").pack(anchor="w")
        ttk.Progressbar(prog_frame, variable=self.progress, maximum=100).pack(fill=tk.X, pady=8)

        # Stats frame
        stats_frame = ttk.Frame(prog_frame)
        stats_frame.pack(fill=tk.X)
        ttk.Label(stats_frame, text="Speed:").pack(side=tk.LEFT)
        ttk.Label(stats_frame, textvariable=self.speed).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Label(stats_frame, text="ETA:").pack(side=tk.LEFT)
        ttk.Label(stats_frame, textvariable=self.eta).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Label(stats_frame, text="Files:").pack(side=tk.LEFT)
        ttk.Label(stats_frame, textvariable=self.file_count).pack(side=tk.LEFT, padx=(4, 2))
        ttk.Label(stats_frame, text="/").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(stats_frame, textvariable=self.total_files).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Label(stats_frame, text="Size:").pack(side=tk.LEFT)
        ttk.Label(stats_frame, textvariable=self.total_size).pack(side=tk.LEFT)

        # Action buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Start Delete", command=self.start_delete, style="Danger.TButton").pack(side=tk.LEFT,
                                                                                                           padx=(0, 6))
        ttk.Button(btn_frame, text="Cancel", command=self.cancel_delete).pack(side=tk.LEFT)

        # Warning label
        warn_frame = ttk.LabelFrame(main, text="⚠️ Warning", padding=10)
        warn_frame.pack(fill=tk.X, pady=6)
        ttk.Label(
            warn_frame,
            justify="left",
            text="This will PERMANENTLY delete all files and subfolders!\n"
                 "Deleted files cannot be recovered! Double check the folder path."
        ).pack(anchor="w")

    def setup_styles(self):
        style = ttk.Style()
        # Gunakan theme 'clam' supaya warna bisa muncul
        style.theme_use("clam")

        # Style untuk tombol merah (Danger)
        style.configure("Danger.TButton",
                        foreground="white",  # teks putih
                        background="#dc3545",  # merah
                        font=("TkDefaultFont", 10, "bold"))
        style.map("Danger.TButton",
                  background=[("active", "#c82333"), ("disabled", "#dc3545")],
                  foreground=[("disabled", "white")])

    def browse_folder(self):
        path = filedialog.askdirectory(title="Select Folder to Delete")
        if path:
            self.folder_path.set(path)

    def start_delete(self):
        folder = self.folder_path.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder first")
            return

        if not os.path.isdir(folder):
            messagebox.showerror("Error", "Selected path is not a folder")
            return

        # Final confirmation
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"PERMANENTLY delete ALL contents in:\n{folder}\n\n"
            f"Using {self.delete_workers} parallel workers\n"
            "This action cannot be undone!",
            icon="warning"
        )
        if not confirm:
            return

        self._prepare_for_deletion()
        threading.Thread(target=self._run_delete, daemon=True).start()
        self._start_time = time.time()
        self.root.after(200, self._tick_ui)

    def _prepare_for_deletion(self):
        """Reset all counters and flags"""
        self.cancel_flag.clear()
        self.progress.set(0.0)
        self.file_count.set(0)
        self.total_files.set(0)
        self.total_size.set("0 GB")
        self.processed_files = 0
        self._total_size_bytes = 0
        self.status.set("Scanning folder...")
        self.speed.set("0 files/sec")
        self.eta.set("-")
        self.current_file.set("")

    def _run_delete(self):
        try:
            folder = self.folder_path.get()

            # Phase 1: Scan all files
            file_list, total_size = self._scan_files(folder)
            if self.cancel_flag.is_set():
                return

            # Phase 2: Delete files in parallel
            self._delete_files_parallel(file_list)
            if self.cancel_flag.is_set():
                return

            # Phase 3: Remove empty directories
            self._remove_empty_dirs(folder)

            if not self.cancel_flag.is_set():
                self.status.set(f"Deleted {self.processed_files} files ({self._format_size(total_size)})")

        except Exception as e:
            self.status.set(f"Error: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            if self.executor:
                self.executor.shutdown(wait=False)
                self.executor = None

    def _scan_files(self, folder):
        """Scan and count all files in the folder"""
        file_list = []
        total_size = 0

        self.status.set("Scanning files...")

        for root, _, files in os.walk(folder):
            if self.cancel_flag.is_set():
                return [], 0

            for name in files:
                file_path = os.path.join(root, name)
                try:
                    size = os.path.getsize(file_path)
                    file_list.append(file_path)
                    total_size += size

                    # Update UI periodically during scan
                    if len(file_list) % 1000 == 0:
                        self.total_files.set(len(file_list))
                        self.total_size.set(self._format_size(total_size))
                except OSError:
                    continue

        self.total_files.set(len(file_list))
        self.total_size.set(self._format_size(total_size))
        return file_list, total_size

    def _delete_files_parallel(self, file_list):
        """Delete files using thread pool"""
        self.status.set(f"Deleting {len(file_list)} files with {self.delete_workers} workers...")

        self.executor = ThreadPoolExecutor(max_workers=self.delete_workers)
        futures = []

        for file_path in file_list:
            if self.cancel_flag.is_set():
                break
            futures.append(self.executor.submit(self._delete_single_file, file_path))

        # Wait for completion
        for future in as_completed(futures):
            if self.cancel_flag.is_set():
                break
            try:
                future.result()  # Raise exceptions if any
            except Exception as e:
                print(f"Error deleting file: {e}")

    def _delete_single_file(self, file_path):
        """Delete a single file with error handling"""
        if self.cancel_flag.is_set():
            return

        try:
            # Show current file (for large files)
            if os.path.getsize(file_path) > 100 * 1024 * 1024:  # >100MB
                self.current_file.set(os.path.basename(file_path))

            os.unlink(file_path)

            with self._lock:
                self.processed_files += 1
        except OSError as e:
            print(f"Failed to delete {file_path}: {e}")
        finally:
            self.current_file.set("")

    def _remove_empty_dirs(self, folder):
        """Remove all empty directories recursively"""
        if self.cancel_flag.is_set():
            return

        self.status.set("Removing empty directories...")

        for root, dirs, _ in os.walk(folder, topdown=False):
            if self.cancel_flag.is_set():
                return

            for name in dirs:
                dir_path = os.path.join(root, name)
                try:
                    os.rmdir(dir_path)
                except OSError:
                    pass  # Directory not empty

        # Try to remove the main folder
        try:
            os.rmdir(folder)
            self.status.set(f"Success! Deleted folder and all contents")
        except OSError as e:
            self.status.set(f"Deleted files but could not remove folder: {e}")

    def _format_size(self, size_bytes):
        """Convert size to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _tick_ui(self):
        """Update UI periodically"""
        if self.total_files.get() > 0:
            # Update progress
            progress = (self.processed_files / self.total_files.get()) * 100
            self.progress.set(min(100.0, progress))
            self.file_count.set(self.processed_files)

            # Calculate speed and ETA
            elapsed = max(0.001, time.time() - self._start_time)
            files_sec = self.processed_files / elapsed
            self.speed.set(f"{files_sec:.1f} files/sec")

            remaining = max(0, self.total_files.get() - self.processed_files)
            if files_sec > 0:
                eta_sec = remaining / files_sec
                self.eta.set(self._format_time(eta_sec))

        if not self.cancel_flag.is_set() and self.progress.get() < 100.0:
            self.root.after(200, self._tick_ui)

    def _format_time(self, seconds):
        """Format seconds to human-readable time"""
        if seconds >= 3600:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
        elif seconds >= 60:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        return f"{int(seconds)}s"

    def cancel_delete(self):
        self.cancel_flag.set()
        self.status.set("Cancelling...")
        if self.executor:
            self.executor.shutdown(wait=False)
            self.executor = None

    def on_closing(self):
        self.cancel_delete()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SuperFastDeleteApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()