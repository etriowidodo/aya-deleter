import ctypes
import logging
import os
import sys
import psutil
import tkinter as tk
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import threading



try:
    import winreg
except ImportError:
    winreg = None  # untuk platform non-Windows


class ConsolelessProgressBar:
    def __init__(self, folder, delete_workers):
        self.folder = folder
        self.delete_workers = delete_workers
        self.processed_files = 0
        self.total_files = 0
        self.cancel_flag = threading.Event()

        self.root = tk.Tk()
        self.root.title("Deleting...")
        self.root.geometry("400x120")
        self.root.resizable(False, False)
        myappid = 'artainovasipersada.ayadeletefolder.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        os.environ['PYTHONWINDOWICON'] = os.path.abspath('AYA.ico')
        self._set_app_icon(self.root )
        ttk.Label(self.root, text=f"Deleting folder:\n{folder}").pack(pady=5)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        self.status_label = ttk.Label(self.root, text="Starting...")
        self.status_label.pack()

        # Add cancel button
        self.cancel_button = ttk.Button(self.root, text="Cancel", command=self.cancel)
        self.cancel_button.pack(pady=5)
    def _set_app_icon(self, window=None):
        target = window or self
        try:
            target.iconbitmap(self._get_resource_path('AYA.ico'))
        except Exception as e:
            logging.warning(f"Failed to set icon: {e}")

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
    def cancel(self):
        self.cancel_flag.set()
        self.status_label.config(text="Cancelling...")
        self.cancel_button.config(state="disabled")

    def start(self, delete_function):
        threading.Thread(target=delete_function, args=(self.update_progress, self.cancel_flag), daemon=True).start()
        self.root.mainloop()

    def update_progress(self, processed, total, current_file=""):
        self.processed_files = processed
        self.total_files = total
        percent = (processed / total) * 100 if total else 100
        self.progress_var.set(percent)
        self.status_label.config(text=f"{processed}/{total} files\n{current_file}")
        self.root.update_idletasks()


def add_context_menu(name="Delete With AYA"):
    if winreg is None:
        return
    exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
    try:
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\\" + name)
        winreg.SetValue(key, "", winreg.REG_SZ, name)
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe_path)
        cmd = winreg.CreateKey(key, "command")
        winreg.SetValue(cmd, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
        winreg.CloseKey(key)

        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"Directory\shell\\" + name)
        winreg.SetValue(key, "", winreg.REG_SZ, name)
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe_path)
        cmd = winreg.CreateKey(key, "command")
        winreg.SetValue(cmd, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
        winreg.CloseKey(key)

        print(f"[OK] Context menu '{name}' installed with icon")
    except PermissionError:
        print("[ERROR] Admin required to write registry!")


def remove_context_menu(name="Hapus dengan AYA"):
    if winreg is None:
        return
    try:
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\\" + name + r"\command")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\\" + name)
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"Directory\shell\\" + name + r"\command")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r"Directory\shell\\" + name)
        print(f"[OK] Context menu '{name}' removed")
    except:
        pass


def delete_utama(path, progress_callback=None, cancel_flag=None):
    def _format_size(size_bytes):
        """Convert size to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _scan_files(folder):
        """Scan and count all files in the folder"""
        file_list = []
        total_size = 0

        if progress_callback:
            progress_callback(0, 0, "Scanning files...")

        if os.path.isfile(folder):
            # Handle single file case
            try:
                size = os.path.getsize(folder)
                file_list.append(folder)
                total_size += size
                if progress_callback:
                    progress_callback(1, 1, f"Found 1 file ({_format_size(size)})")
            except OSError:
                pass
            return file_list, total_size

        # Handle directory case
        for root, _, files in os.walk(folder):
            if cancel_flag and cancel_flag.is_set():
                return [], 0

            for name in files:
                file_path = os.path.join(root, name)
                try:
                    size = os.path.getsize(file_path)
                    file_list.append(file_path)
                    total_size += size

                    if len(file_list) % 1000 == 0 and progress_callback:
                        progress_callback(len(file_list), len(file_list), f"Scanned {len(file_list)} files")
                except OSError:
                    continue

        if progress_callback:
            progress_callback(len(file_list), len(file_list),
                              f"Found {len(file_list)} files ({_format_size(total_size)})")
        return file_list, total_size

    def _delete_single_file(file_path, lock, processed_files, total_files):
        """Delete a single file with error handling"""
        if cancel_flag and cancel_flag.is_set():
            return

        try:
            if os.path.getsize(file_path) > 100 * 1024 * 1024:  # >100MB
                if progress_callback:
                    progress_callback(processed_files[0], total_files, os.path.basename(file_path))

            os.unlink(file_path)

            with lock:
                processed_files[0] += 1
                if progress_callback:
                    progress_callback(processed_files[0], total_files, "")
        except OSError as e:
            print(f"Failed to delete {file_path}: {e}")

    def _delete_files_parallel(file_list, total_files):
        """Delete files using thread pool"""
        if not file_list:
            return 0

        if progress_callback:
            progress_callback(0, total_files, f"Deleting {len(file_list)} files with {delete_workers} workers...")

        lock = Lock()
        processed_files = [0]

        def worker(file_path):
            if cancel_flag and cancel_flag.is_set():
                return

            try:
                os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
            finally:
                with lock:
                    processed_files[0] += 1
                    if progress_callback:
                        progress_callback(processed_files[0], total_files, os.path.basename(file_path))

        # For single file, don't use thread pool
        if len(file_list) == 1:
            worker(file_list[0])
        else:
            with ThreadPoolExecutor(max_workers=delete_workers) as executor:
                list(executor.map(worker, file_list))

        return processed_files[0]

    def _remove_empty_dirs(folder):
        """Remove all empty directories recursively"""
        if cancel_flag and cancel_flag.is_set():
            return

        # Skip if it's a file
        if os.path.isfile(folder):
            return

        if progress_callback:
            progress_callback(0, 0, "Removing empty directories...")

        for root, dirs, _ in os.walk(folder, topdown=False):
            if cancel_flag and cancel_flag.is_set():
                return

            for name in dirs:
                dir_path = os.path.join(root, name)
                try:
                    os.rmdir(dir_path)
                except OSError:
                    pass

        try:
            os.rmdir(folder)
            if progress_callback:
                progress_callback(0, 0, "Success! Deleted folder and all contents")
        except OSError as e:
            if progress_callback:
                progress_callback(0, 0, f"Deleted files but could not remove folder: {e}")

    try:
        delete_workers = calculate_workers()
        file_list, total_size = _scan_files(path)
        if cancel_flag and cancel_flag.is_set():
            return

        processed_count = _delete_files_parallel(file_list, len(file_list))
        if cancel_flag and cancel_flag.is_set():
            return

        # Only try to remove directories if it was a directory
        if os.path.isdir(path):
            _remove_empty_dirs(path)

        if not cancel_flag or not cancel_flag.is_set():
            if progress_callback:
                progress_callback(processed_count, len(file_list),
                                  f"Deleted {processed_count} files ({_format_size(total_size)})")
    except Exception as e:
        if progress_callback:
            progress_callback(0, 0, f"Error: {str(e)}")
        print(f"Error: {str(e)}")


def calculate_workers():
    try:
        cpu_count = os.cpu_count() or 4
        mem = psutil.virtual_memory()
        mem_workers = mem.available // (512 * 1024 * 1024)
        workers = min(cpu_count * 2, mem_workers, 128)
        if mem.total >= 32 * 1024 ** 3:
            workers = min(workers * 2, 256)
        return max(4, workers)
    except:
        return 8


if __name__ == "__main__":
    if "--install-context" in sys.argv:
        add_context_menu()
        sys.exit(0)
    if "--remove-context" in sys.argv:
        remove_context_menu()
        sys.exit(0)
    if len(sys.argv) > 1:
        target = sys.argv[1]
        print(f"Hapus cepat untuk: {target}")
        progress_win = ConsolelessProgressBar(target, delete_workers=calculate_workers())
        progress_win.start(lambda cb, cf: delete_utama(target, cb, cf))
        sys.exit(0)