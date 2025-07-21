import sys
import os
import base64

def read_file(file_path: str, mode: str = 'text', encoding: str = 'utf-8'):
    try:
        if mode == 'text':
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        elif mode == 'binary':
            with open(file_path, 'rb') as f:
                return f.read()
        else:
            raise ValueError("Invalid mode. Use 'text' or 'binary'.")
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        sys.exit(1)

def write_file(file_path: str, content, mode: str = 'text', encoding: str = 'utf-8'):
    try:
        if mode == 'text':
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
        elif mode == 'binary':
            with open(file_path, 'wb') as f:
                f.write(content)
        else:
            raise ValueError("Invalid mode. Use 'text' or 'binary'.")
        print(f"Successfully wrote to file: {file_path}")
    except Exception as e:
        print(f"Error writing to file {file_path}: {e}")
        sys.exit(1)

def replace_content(file_path: str, old_content_b64, new_content_b64, mode: str = 'text', encoding: str = 'utf-8', count: int = 0):
    try:
        old_content = base64.b64decode(old_content_b64)
        new_content = base64.b64decode(new_content_b64)

        current_content = read_file(file_path, mode, encoding)

        if mode == 'text':
            old_content = old_content.decode(encoding)
            new_content = new_content.decode(encoding)
            if not isinstance(old_content, str) or not isinstance(new_content, str):
                raise ValueError("old_content and new_content must be strings in text mode.")
            if count == 0:
                new_file_content = current_content.replace(old_content, new_content)
            else:
                new_file_content = current_content.replace(old_content, new_content, count)
        elif mode == 'binary':
            if not isinstance(old_content, bytes) or not isinstance(new_content, bytes):
                raise ValueError("old_content and new_content must be bytes in binary mode.")
            if count == 0:
                new_file_content = current_content.replace(old_content, new_content)
            else:
                new_file_content = current_content.replace(old_content, new_content, count)
        else:
            raise ValueError("Invalid mode. Use 'text' or 'binary'.")

        if new_file_content == current_content:
            print(f"No occurrences of the specified content found in {file_path}. No changes made.")
            sys.exit(1)

        write_file(file_path, new_file_content, mode, encoding)
        print(f"Successfully replaced content in {file_path}.")

    except Exception as e:
        print(f"Error replacing content in {file_path}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python file_manager.py <command> <args...>")
        print("Commands:")
        print("  read <file_path> [mode] [encoding]")
        print("  write <file_path> <content> [mode] [encoding]")
        print("  replace <file_path> <old_content_b64> <new_content_b64> [mode] [encoding] [count]")
        sys.exit(1)

    command = sys.argv[1]
    file_path = sys.argv[2]

    if command == 'read':
        mode = sys.argv[3] if len(sys.argv) > 3 else 'text'
        encoding = sys.argv[4] if len(sys.argv) > 4 else 'utf-8'
        content = read_file(file_path, mode, encoding)
        if mode == 'binary':
            sys.stdout.buffer.write(content) # Write bytes directly to stdout
        else:
            print(content)
    elif command == 'write':
        content = sys.argv[3]
        mode = sys.argv[4] if len(sys.argv) > 4 else 'text'
        encoding = sys.argv[5] if len(sys.argv) > 5 else 'utf-8'
        if mode == 'binary':
            content = base64.b64decode(content) # Decode base64 for binary write
        write_file(file_path, content, mode, encoding)
    elif command == 'replace':
        old_content_b64 = sys.argv[3]
        new_content_b64 = sys.argv[4]
        mode = sys.argv[5] if len(sys.argv) > 5 else 'text'
        encoding = sys.argv[6] if len(sys.argv) > 6 else 'utf-8'
        count = int(sys.argv[7]) if len(sys.argv) > 7 else 0

        replace_content(file_path, old_content_b64, new_content_b64, mode, encoding, count)
    else:
        print(f"Error: Unknown command {command}")
        sys.exit(1)