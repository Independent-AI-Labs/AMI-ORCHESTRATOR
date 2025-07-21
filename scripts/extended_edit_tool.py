import sys

def extended_replace(file_path: str, old_string: str, new_string: str, expected_replacements: int = 1):
    """
    Replaces occurrences of old_string with new_string in a file.

    Args:
        file_path (str): The absolute path to the file.
        old_string (str): The exact literal text to replace.
        new_string (str): The exact literal text to replace old_string with.
        expected_replacements (int): The number of replacements expected. Set to 0 to replace all occurrences.
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        count = content.count(old_string)

        if count == 0:
            print(f"Error: No occurrences of the specified old_string found in {file_path}.")
            sys.exit(1)

        if expected_replacements != 0 and count != expected_replacements:
            print(f"Error: Expected {expected_replacements} replacement(s) but found {count} in {file_path}.")
            sys.exit(1)

        if expected_replacements == 0:
            new_content = content.replace(old_string, new_string)
            actual_replacements = count
        else:
            new_content = content.replace(old_string, new_string, expected_replacements)
            actual_replacements = expected_replacements

        with open(file_path, 'w') as f:
            f.write(new_content)

        print(f"Successfully replaced {actual_replacements} occurrence(s) in {file_path}.")

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if not (4 <= len(sys.argv) <= 5):
        print("Usage: python extended_edit_tool.py <file_path> <old_string> <new_string> [expected_replacements]")
        sys.exit(1)

    file_path = sys.argv[1]
    old_string = sys.argv[2]
    new_string = sys.argv[3]
    expected_replacements = int(sys.argv[4]) if len(sys.argv) == 5 else 1

    extended_replace(file_path, old_string, new_string, expected_replacements)
