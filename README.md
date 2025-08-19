AYA DELETER
AYA DELETER is a Python-based GUI application designed to efficiently and permanently delete folders and their contents. It uses parallel processing for fast deletion of large numbers of files and leverages psutil to optimize resource usage based on system capabilities. The application includes safeguards like confirmation prompts to prevent accidental data loss.
Features

## Download
Get the latest release: [Download AyaDeleter](https://www.mediafire.com/file/db157oulpb0v3ku/AyaDeleter_Setup.exe/file)

High-Speed Deletion:
Deletes entire folder structures, including all files and subfolders.
Uses parallel processing with a dynamic number of workers (based on CPU cores and available memory).


Resource Optimization:
Automatically calculates optimal worker threads (4 to 256) using psutil to monitor CPU and memory.
Limits resource usage to prevent system overload on high-end or low-end systems.


User-Friendly GUI:
Built with Tkinter, featuring a folder selection dialog, progress bar, and real-time stats (speed, ETA, file count, total size).
Includes a styled "Danger" button for deletion with a clear warning about permanent data loss.
Supports cancellation of ongoing deletion operations.


Custom Icon: Uses AYA.ico for the application window and executable (Windows).
Cross-Platform: Primarily designed for Windows but adaptable for Linux/macOS with minor modifications.
Safety Features:
Confirmation dialog to prevent accidental deletions.
Displays folder path and worker count before deletion.
Gracefully handles errors (e.g., permission issues) with user feedback via message boxes.



Requirements

Python 3.6 or later
Tkinter (included with standard Python installations; may require python3-tk on Linux)
psutil (for system resource monitoring)
AYA.ico icon file (included in the project directory for the application icon)
PyInstaller (optional, for building the executable)

Setup Instructions
1. Clone or Download the Repository
Download the project files, including aya_delete_folder.py, AYA.ico, and aya_delete_folder.spec,
