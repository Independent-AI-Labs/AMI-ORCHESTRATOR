

import sys

def replace_line(file_path: str, line_number: int, new_content: str):
    """
    Replaces a specific line in a file with new content.

    Args:
        file_path (str): The absolute path to the file.
        line_number (int): The 1-based line number to replace.
        new_content (str): The content to write to the specified line.
    """
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

        if not (1 <= line_number <= len(lines)):
            print(f"Error: Line number {line_number} is out of range for file {file_path} (total lines: {len(lines)}).")
            return

        lines[line_number - 1] = new_content + '\n' # Add newline back

        with open(file_path, 'w') as f:
            f.writelines(lines)
        print(f"Successfully replaced line {line_number} in {file_path}.")

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python replace_line_tool.py <file_path> <line_number> <new_content>")
        sys.exit(1)

    file_path = sys.argv[1]
    line_number = int(sys.argv[2])
    new_content = sys.argv[3]

    replace_line(file_path, line_number, new_content)

