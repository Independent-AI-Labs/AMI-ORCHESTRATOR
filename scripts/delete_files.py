import os
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_files.py <file_path1> [file_path2 ...]")
        sys.exit(1)

    files_to_delete = sys.argv[1:]

    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            print(f"Successfully deleted: {file_path}")
        except OSError as e:
            print(f"Error deleting {file_path}: {e}")