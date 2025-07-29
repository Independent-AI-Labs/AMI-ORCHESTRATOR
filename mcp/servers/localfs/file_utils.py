"""
File utilities for the LocalFiles server.
"""

import base64
import difflib
import re
import shutil
from pathlib import Path
from typing import cast


class FileUtils:
    """Provides file manipulation utilities."""

    max_file_size = 100 * 1024 * 1024  # 100MB limit

    @staticmethod
    def validate_file_path(file_path: str, root_dir: str) -> str:
        try:
            # Resolve the root directory to an absolute path
            root_path = Path(root_dir).resolve()

            # Resolve the provided file path
            # If the path is absolute, resolve it directly.
            # If it's relative, resolve it relative to the root_dir.
            resolved_path = Path(file_path).resolve() if Path(file_path).is_absolute() else (root_path / file_path).resolve()

            # Check if the resolved path is within the root directory
            if not resolved_path.is_relative_to(root_path):
                raise ValueError(f"Path '{file_path}' is outside the allowed root directory '{root_dir}'")

            return str(resolved_path)
        except (ValueError, TypeError) as e:
            # Catch specific, expected errors for better diagnostics
            raise ValueError(f"Invalid file path '{file_path}': {e}") from e
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Catch any other unexpected errors during path resolution
            raise ValueError(f"An unexpected error occurred while resolving path '{file_path}': {e}") from e

    @staticmethod
    def check_file_size(file_path: str):
        """Check if file size is within limits."""
        path_obj = Path(file_path)
        if path_obj.exists():
            size = path_obj.stat().st_size
            if size > FileUtils.max_file_size:
                raise ValueError(f"File too large: {size} bytes (max: {FileUtils.max_file_size} bytes)")

    @staticmethod
    def normalize_line_endings(content: str, target_format: str = "\n") -> str:
        """Normalize line endings in text content and ensure a trailing newline."""
        normalized_content = re.sub(r"\r\n|\r|\n", target_format, content)
        # Only add trailing newline if content is not empty and doesn't already end with one
        if normalized_content and not normalized_content.endswith(target_format):
            normalized_content += target_format
        return normalized_content

    @staticmethod
    def generate_diff(before_content: str, after_content: str, file_path: str) -> str:
        """Generate a unified diff between before and after content."""
        try:
            before_lines = before_content.splitlines(keepends=False)
            after_lines = after_content.splitlines(keepends=False)

            diff = difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=f"{Path(file_path).name} (before)",
                tofile=f"{Path(file_path).name} (after)",
                lineterm="",
            )

            diff_lines = list(diff)
            if not diff_lines:
                return "No changes detected in diff"

            # Limit diff output to prevent extremely long responses
            max_diff_lines = 100
            if len(diff_lines) > max_diff_lines:
                diff_text = "\n".join(diff_lines[:max_diff_lines])
                diff_text += f"\n... (diff truncated after {max_diff_lines} lines)"
            else:
                diff_text = "\n".join(diff_lines)

            return diff_text
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Failed to generate diff: {e}"

    @staticmethod
    def read_file_content(file_path: str, root_dir: str, mode: str = "text", encoding: str = "utf-8"):
        """Read file content with proper error handling and normalization."""
        validated_path = FileUtils.validate_file_path(file_path, root_dir)
        path_obj = Path(validated_path)

        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'. Please check the path and ensure the file exists.")

        if not path_obj.is_file():
            raise ValueError(f"Path exists but is not a file: '{validated_path}'")

        FileUtils.check_file_size(validated_path)

        try:
            if mode == "binary":
                return path_obj.read_bytes()
            content = path_obj.read_text(encoding=encoding)
            # Normalize line endings to \n for consistent processing
            return FileUtils.normalize_line_endings(content, "\n")

        except UnicodeDecodeError as e:
            raise ValueError(
                f"Cannot decode file '{validated_path}' with encoding '{encoding}'. Error: {e}. Try using a different encoding or 'binary' mode."
            ) from e
        except PermissionError as e:
            raise PermissionError(f"Permission denied: cannot read file '{validated_path}'") from e
        except ValueError as e:
            raise e
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise OSError(f"Unexpected error reading file '{validated_path}': {e}") from e

    @staticmethod
    def write_file_content(file_path: str, content, root_dir: str, mode: str = "text", encoding: str = "utf-8"):
        """Write file content with proper error handling."""
        validated_path = FileUtils.validate_file_path(file_path, root_dir)
        path_obj = Path(validated_path)

        # Create directory if it doesn't exist
        parent_dir = path_obj.parent
        if parent_dir and not parent_dir.exists():
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:  # pylint: disable=broad-exception-caught
                raise OSError(f"Failed to create parent directory '{parent_dir}': {e}") from e

        try:
            if mode == "binary":
                path_obj.write_bytes(content)
            else:
                path_obj.write_text(content, encoding=encoding)

        except PermissionError as e:
            raise PermissionError(f"Permission denied: cannot write to file '{validated_path}'") from e
        except OSError as e:
            no_space_left_on_device = 28
            if e.errno == no_space_left_on_device:  # No space left on device
                raise OSError(f"No space left on device when writing to '{validated_path}': {e}") from e
            raise OSError(f"OS error writing to file '{validated_path}': {e}") from e
        except ValueError as e:
            raise e
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise OSError(f"Unexpected error writing to file '{validated_path}': {e}") from e

    @staticmethod
    def validate_and_decode_content(content: str | bytes, mode: str) -> str | bytes:
        """Validates and decodes content based on mode."""
        if content is None:
            raise ValueError("content cannot be None")

        if mode == "binary":
            if isinstance(content, str):
                try:
                    return base64.b64decode(content.encode("utf-8"))
                except (TypeError, ValueError) as e:
                    raise ValueError(f"Invalid base64 content for binary mode: {e}") from e
            elif isinstance(content, bytes):
                return content
            else:
                raise ValueError("Binary mode requires base64-encoded string or bytes content")
        elif mode == "text":
            if isinstance(content, bytes):
                try:
                    return content.decode("utf-8")
                except UnicodeDecodeError as e:
                    raise ValueError(f"Cannot decode bytes to string in text mode: {e}") from e
            elif isinstance(content, str):
                return content
            else:
                raise ValueError("Text mode requires string or bytes content")
        else:
            raise ValueError("Mode must be 'text' or 'binary'")

    @staticmethod
    def get_write_success_message_binary(file_path: str, content: bytes) -> str:
        """Generates the success message for binary file writes."""
        content_bytes: bytes = content
        content_size = len(content_bytes)
        return f"Successfully wrote binary content to '{file_path}' ({content_size} bytes)."

    @staticmethod
    def get_write_success_message_text(file_path: str, content: str, original_content: str | None) -> tuple[str, str | None]:
        """Generates the success message and diff for text file writes."""
        diff_output: str | None = None
        if original_content is not None:
            diff_output = FileUtils.generate_diff(original_content, content, file_path)

        line_count = content.count("\n") + 1
        char_count = len(content)

        message = f"Successfully wrote text content to '{file_path}' ({char_count} characters, {line_count} lines)."
        return message, diff_output

    @staticmethod
    def process_text_replacement(current_content: str, old_string: str, new_string: str, count: int) -> tuple[str, int]:
        """Handles text mode string replacement logic."""
        if not isinstance(old_string, str) or not isinstance(new_string, str):
            raise ValueError("old_string and new_string must be strings in text mode")

        if not old_string:
            raise ValueError("old_string cannot be empty - this would insert new_string between every character")

        old_string_normalized = FileUtils.normalize_line_endings(old_string, "\n")
        new_string_normalized = FileUtils.normalize_line_endings(new_string, "\n")

        occurrence_count = current_content.count(old_string_normalized)
        if occurrence_count == 0:
            return "No changes made: search string not found.", 0

        if count == 0:
            new_content = current_content.replace(old_string_normalized, new_string_normalized)
            actual_replacements = current_content.count(old_string_normalized)
        else:
            new_content = current_content.replace(old_string_normalized, new_string_normalized, count)
            actual_replacements = count

        return new_content, actual_replacements

    @staticmethod
    def process_binary_replacement(current_content: bytes, old_string: bytes, new_string: bytes, count: int) -> tuple[bytes, int]:
        """Handles binary mode string replacement logic."""
        if not isinstance(old_string, bytes) or not isinstance(new_string, bytes):
            raise ValueError("old_string and new_string must be bytes in binary mode")

        if not old_string:
            raise ValueError("old_string cannot be empty - this would insert new_string between every byte")

        occurrence_count = current_content.count(old_string)
        if occurrence_count == 0:
            return b"No changes made: search bytes not found.", 0

        if count == 0:
            new_content = current_content.replace(old_string, new_string)
            actual_replacements = current_content.count(old_string)
        else:
            new_content = current_content.replace(old_string, new_string, count)
            actual_replacements = count

        return new_content, actual_replacements

    @staticmethod
    def handle_no_replacements(file_path: str) -> dict:
        return {"status": "success", "message": f"No changes made to '{file_path}': search string not found or no replacements occurred."}

    @staticmethod
    def handle_identical_content(file_path: str) -> dict:
        return {"status": "success", "message": f"No changes made to '{file_path}': replacement resulted in identical content."}

    @staticmethod
    def perform_replacement(original_content: str | bytes, old_string: str | bytes, new_string: str | bytes, mode: str, count: int) -> tuple[str | bytes, int]:
        if mode == "binary":
            if not isinstance(original_content, bytes):
                raise TypeError("Original content must be bytes in binary mode")
            try:
                old_bytes = base64.b64decode(cast(str, old_string).encode("utf-8"))
                new_bytes = base64.b64decode(cast(str, new_string).encode("utf-8"))
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid base64 content for binary mode: {e}") from e
            return FileUtils.process_binary_replacement(original_content, old_bytes, new_bytes, count)
        if mode == "text":
            if not isinstance(original_content, str):
                raise TypeError("Original content must be string in text mode")
            return FileUtils.process_text_replacement(original_content, cast(str, old_string), cast(str, new_string), count)
        raise ValueError("Mode must be 'text' or 'binary'")

    @staticmethod
    def replace_lines(
        original_content: str,
        start_line: int,
        end_line: int,
        new_string: str,
    ) -> str:
        """Replaces content within a specified range of lines."""
        lines = original_content.splitlines(keepends=True)
        total_lines = len(lines)

        if start_line <= 0 or end_line <= 0:
            raise ValueError("Line numbers must be positive (1-based indexing)")

        if start_line > end_line:
            raise ValueError(f"Start line ({start_line}) must be less than or equal to end line ({end_line})")

        if start_line > total_lines + 1:  # Allow replacing at end of file
            raise ValueError(f"Start line {start_line} exceeds file length ({total_lines} lines)")

        if end_line > total_lines + 1:  # Allow replacing at end of file
            raise ValueError(f"End line {end_line} exceeds file length ({total_lines} lines)")

        # Convert to 0-based indexing
        start_idx = start_line - 1
        end_idx = end_line

        # Normalize the new string's line endings and split
        new_string_normalized = FileUtils.normalize_line_endings(new_string, "\n")
        new_lines = new_string_normalized.splitlines(keepends=True)

        # Perform replacement
        modified_lines = lines[:start_idx] + new_lines + lines[end_idx:]
        return "".join(modified_lines)

    @staticmethod
    def delete_lines(original_content: str, start_line: int, end_line: int) -> str:
        """Deletes lines within a specified range."""
        lines = original_content.splitlines(keepends=True)
        total_lines = len(lines)

        if start_line <= 0 or end_line <= 0:
            raise ValueError("Line numbers must be positive (1-based indexing)")

        if start_line > end_line:
            raise ValueError(f"Start line ({start_line}) must be less than or equal to end line ({end_line})")

        if start_line > total_lines + 1:  # Allow deleting from end of file
            raise ValueError(f"Start line {start_line} exceeds file length ({total_lines} lines)")

        if end_line > total_lines + 1:  # Allow deleting from end of file
            raise ValueError(f"End line {end_line} exceeds file length ({total_lines} lines)")

        # Convert to 0-based indexing
        start_idx = start_line - 1
        end_idx = end_line

        # Delete the specified lines by keeping everything before and after
        modified_lines = lines[:start_idx] + lines[end_idx:]
        return "".join(modified_lines)

    @staticmethod
    def insert_lines(original_content: str, line_number: int, content: str) -> str:
        """Inserts content at a specified line number."""
        lines = original_content.splitlines(keepends=True)
        total_lines = len(lines)

        if line_number <= 0:
            raise ValueError("Line number must be positive (1-based indexing)")

        if line_number > total_lines + 1:  # Allow inserting at line_number = total_lines + 1 (append to end)
            raise ValueError(f"Line number {line_number} exceeds file length + 1 ({total_lines + 1})")

        # Normalize the content's line endings and split
        content_normalized = FileUtils.normalize_line_endings(content, "\n")
        insert_lines = content_normalized.splitlines(keepends=False)

        # Re-add newlines for joining
        insert_lines_with_ends = [line + "\n" for line in insert_lines]

        # Convert to 0-based indexing for insertion
        insert_idx = line_number - 1

        # Insert the new lines
        modified_lines = lines[:insert_idx] + insert_lines_with_ends + lines[insert_idx:]
        return "".join(modified_lines)

    @staticmethod
    def delete_files(file_paths: list, root_dir: str) -> dict:
        """Delete multiple files."""
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        if not file_paths:
            raise ValueError("file_paths list cannot be empty")

        deleted_files = []
        errors = []

        for file_path in file_paths:
            try:
                validated_path = FileUtils.validate_file_path(file_path, root_dir)
                path_obj = Path(validated_path)

                if not path_obj.exists():
                    errors.append(f"File not found: '{file_path}'")
                    continue

                if not path_obj.is_file():
                    errors.append(f"Path is not a file: '{file_path}'")
                    continue

                path_obj.unlink()
                deleted_files.append(file_path)

            except PermissionError as e:
                errors.append(f"Permission denied deleting file: '{file_path}': {e}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                errors.append(f"Error deleting file '{file_path}': {e}")

        if errors:
            error_msg = f"Some files could not be deleted: {'; '.join(errors)}"
            if deleted_files:
                error_msg += f". Successfully deleted: {', '.join(deleted_files)}"

            raise Exception(error_msg) from None  # pylint: disable=raise-missing-from

        return {"status": "success", "message": f"Successfully deleted {len(deleted_files)} file(s): {', '.join(deleted_files)}"}

    @staticmethod
    def validate_move_paths(source_paths: list, destination_paths: list):
        if not isinstance(source_paths, list) or not isinstance(destination_paths, list):
            raise ValueError("source_paths and destination_paths must be lists")
        if not source_paths or not destination_paths:
            raise ValueError("source_paths and destination_paths lists cannot be empty")
        if len(source_paths) != len(destination_paths):
            raise ValueError(f"Number of source paths ({len(source_paths)}) must match destination paths ({len(destination_paths)})")

    @staticmethod
    def handle_destination_directory(dest_path_obj: Path, create_dirs: bool, source_path: str) -> str | None:
        dest_dir = dest_path_obj.parent
        if dest_dir and not dest_dir.exists():
            if create_dirs:
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    return f"Failed to create destination directory '{dest_dir}' for '{source_path}': {e}"
            else:
                return f"Destination directory does not exist: '{dest_dir}' for '{source_path}'"
        return None

    @staticmethod
    def perform_single_file_move(source_path: str, dest_path: str, create_dirs: bool, root_dir: str) -> tuple[bool, str | None]:
        result: tuple[bool, str | None] = (False, None)
        try:
            validated_source = FileUtils.validate_file_path(source_path, root_dir)
            validated_dest = FileUtils.validate_file_path(dest_path, root_dir)

            source_path_obj = Path(validated_source)
            if not source_path_obj.exists():
                result = False, f"Source file not found: '{source_path}'"
            elif not source_path_obj.is_file():
                result = False, f"Source path is not a file: '{source_path}'"
            else:
                dest_path_obj = Path(validated_dest)
                dir_error = FileUtils.handle_destination_directory(dest_path_obj, create_dirs, source_path)
                if dir_error:
                    result = False, dir_error
                elif dest_path_obj.exists():
                    result = False, f"Destination already exists: '{dest_path}' for source '{source_path}'"
                else:
                    shutil.move(validated_source, validated_dest)
                    result = True, None
        except PermissionError as e:
            result = False, f"Permission denied moving file: '{source_path}' -> '{dest_path}': {e}"
        except Exception as e:  # pylint: disable=broad-exception-caught
            result = False, f"Error moving file '{source_path}' -> '{dest_path}': {e}"
        return result

    @staticmethod
    def move_files(source_paths: list, destination_paths: list, create_dirs: bool, root_dir: str) -> dict:
        """Move/rename files from source paths to destination paths."""
        FileUtils.validate_move_paths(source_paths, destination_paths)

        moved_files = []
        errors = []

        for i, source_path in enumerate(source_paths):
            dest_path = destination_paths[i]
            success, error_message = FileUtils.perform_single_file_move(source_path, dest_path, create_dirs, root_dir)
            if success:
                moved_files.append(f"'{source_path}' to '{dest_path}'")
            else:
                errors.append(f"Failed to move '{source_path}' to '{dest_path}': {error_message}")

        if errors:
            error_msg = f"Some files could not be moved: {'; '.join(errors)}"
            if moved_files:
                error_msg += f". Successfully moved: {', '.join(moved_files)}"
            raise Exception(error_msg) from None

        return {"status": "success", "message": f"Successfully moved {len(moved_files)} file(s): {', '.join(moved_files)}"}

    @staticmethod
    def create_directory(directory_path: str, root_dir: str) -> dict:
        """Create a directory and any necessary parent directories."""
        validated_path = FileUtils.validate_file_path(directory_path, root_dir)
        path_obj = Path(validated_path)

        if path_obj.exists():
            if path_obj.is_dir():
                return {"status": "success", "message": f"Directory already exists: '{directory_path}'"}
            raise ValueError(f"Path exists but is not a directory: '{directory_path}'")

        path_obj.mkdir(parents=True, exist_ok=True)
        return {"status": "success", "message": f"Successfully created directory: '{directory_path}'"}

    @staticmethod
    def delete_directory(directory_path: str, root_dir: str) -> dict:
        """Delete a directory and all its contents."""
        validated_path = FileUtils.validate_file_path(directory_path, root_dir)
        path_obj = Path(validated_path)

        if not path_obj.exists():
            raise FileNotFoundError(f"Directory not found: '{directory_path}'")

        if not path_obj.is_dir():
            raise ValueError(f"Path is not a directory: '{directory_path}'")

        # Count items before deletion for informative message
        item_count = sum(1 for _ in path_obj.rglob("*")) + 1  # +1 for the directory itself

        shutil.rmtree(validated_path)
        return {"status": "success", "message": f"Successfully deleted directory '{directory_path}' and all its contents ({item_count} items)"}
