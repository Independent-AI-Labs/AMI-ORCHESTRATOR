"""
File utilities for the LocalFiles server.
"""

import base64
import difflib
import re
import shutil
from enum import Enum
from pathlib import Path


class OffsetType(Enum):
    BYTE = "byte"
    CHAR = "char"
    LINE = "line"


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
    def list_directory_contents(directory_path: str, root_dir: str, limit: int = 100, recursive: bool = False) -> str:
        """Lists the names of files and subdirectories directly within a specified directory path."""
        validated_path = FileUtils.validate_file_path(directory_path, root_dir)
        path_obj = Path(validated_path)

        if not path_obj.is_dir():
            raise ValueError(f"Path is not a directory: '{directory_path}'")

        if recursive:
            return FileUtils._list_directory_recursive(path_obj, limit)
        return FileUtils._list_directory_non_recursive(path_obj, limit)

    @staticmethod
    def _list_directory_non_recursive(path_obj: Path, limit: int) -> str:
        """Helper for non-recursive listing."""
        contents = []
        for item in path_obj.iterdir():
            contents.append(item.name)
            if len(contents) >= limit:
                break
        return "\n".join(contents)

    @staticmethod
    def _list_directory_recursive(path_obj: Path, limit: int) -> str:
        """Helper for recursive listing with ASCII tree."""
        lines: list[str] = []

        def get_tree_lines(directory: Path, prefix: str = ""):
            if len(lines) >= limit:
                return

            items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            for i, item in enumerate(items):
                if len(lines) >= limit:
                    return

                is_last = i == (len(items) - 1)
                connector = "└───" if is_last else "├───"

                lines.append(f"{prefix}{connector}{item.name}")

                if item.is_dir():
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    get_tree_lines(item, new_prefix)

        lines.append(f"{path_obj.name}/")
        get_tree_lines(path_obj)

        if len(lines) > limit:
            lines = lines[:limit]
            lines.append("... (list truncated)")

        return "\n".join(lines)

    @staticmethod
    def create_dirs(directory_path: str, root_dir: str) -> dict:
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
    def _match_path_name(item: Path, keywords: list[str], regex_keywords: bool) -> bool:
        if not keywords:
            return True
        for keyword in keywords:
            if regex_keywords:
                if re.search(keyword, item.name) or any(re.search(keyword, Path(p).name) for p in item.parts if p):
                    return True
            elif keyword in item.name or any(keyword in str(p) for p in item.parts if p):
                return True
        return False

    @staticmethod
    def _match_file_content(item: Path, keywords: list[str], regex_keywords: bool) -> bool:
        if not keywords:
            return True
        try:
            FileUtils.check_file_size(str(item))
            content = item.read_text(encoding="utf-8")
            for keyword in keywords:
                if regex_keywords:
                    if re.search(keyword, content):
                        return True
                elif keyword in content:
                    return True
        except UnicodeDecodeError:
            # Skip content search for binary files
            pass
        except Exception as e:
            # Log other errors but don't stop the search
            print(f"Error reading file {item} for content search: {e}")
        return False

    @staticmethod
    def find_files(path: str, root_dir: str, keywords_path_name: list[str], keywords_file_content: list[str], regex_keywords: bool = False) -> list[str]:
        """Searches for files based on keywords in path/name or content."""
        validated_path = FileUtils.validate_file_path(path, root_dir)
        path_obj = Path(validated_path)

        if not path_obj.is_dir():
            raise ValueError(f"Path is not a directory: '{path}'")

        matching_files = []

        for item in path_obj.rglob("*"):
            if item.is_file():
                path_name_match = FileUtils._match_path_name(item, keywords_path_name, regex_keywords)
                content_match = FileUtils._match_file_content(item, keywords_file_content, regex_keywords)

                if path_name_match and content_match:
                    matching_files.append(str(item))
        return matching_files

    @staticmethod
    def normalize_line_endings(content: str, target_format: str = "\n") -> str:
        """Normalize line endings in text content."""
        return re.sub(r"\r\n|\r|\n", target_format, content)

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
    def _read_text_content(path_obj: Path, start_offset_inclusive: int, end_offset_inclusive: int, offset_type: OffsetType, encoding: str) -> str:
        full_content = path_obj.read_text(encoding=encoding)
        normalized_full_content = FileUtils.normalize_line_endings(full_content, "\n")
        if full_content.endswith(("\r\n", "\n", "\r")) and not normalized_full_content.endswith("\n"):
            normalized_full_content += "\n"

        processed_content_lines = []
        start_line_for_display = 0  # This will be the actual line number in the file for the first line of processed_content

        if offset_type == OffsetType.LINE:
            all_lines = normalized_full_content.splitlines(keepends=True)
            # Adjust for 1-based indexing from user
            start_line_index = start_offset_inclusive - 1 if start_offset_inclusive > 0 else 0
            end_line_index = len(all_lines) if end_offset_inclusive == -1 else end_offset_inclusive

            processed_content_lines = all_lines[start_line_index:end_line_index]
            start_line_for_display = start_line_index + 1  # Line numbers are 1-indexed

        if offset_type == OffsetType.CHAR:
            end_char = len(normalized_full_content) if end_offset_inclusive == -1 else end_offset_inclusive + 1
            processed_content_segment = normalized_full_content[start_offset_inclusive:end_char]
            processed_content_lines = processed_content_segment.splitlines(keepends=True)

            # Calculate the starting line number for CHAR offset
            start_line_for_display = normalized_full_content[:start_offset_inclusive].count("\n") + 1

        if offset_type == OffsetType.BYTE:
            full_content_bytes = path_obj.read_bytes()
            end_byte = len(full_content_bytes) if end_offset_inclusive == -1 else end_offset_inclusive + 1
            processed_content_bytes_segment = full_content_bytes[start_offset_inclusive:end_byte]
            processed_content_segment = processed_content_bytes_segment.decode(encoding, errors="ignore")
            processed_content_lines = FileUtils.normalize_line_endings(processed_content_segment, "\n").splitlines(keepends=True)

            # Calculate the starting line number for BYTE offset
            char_offset_at_start_byte = len(full_content_bytes[:start_offset_inclusive].decode(encoding, errors="ignore"))
            start_line_for_display = normalized_full_content[:char_offset_at_start_byte].count("\n") + 1

        # Now, unify the numbering logic
        numbered_lines = [f"{i + start_line_for_display: >4} | {line.rstrip('\n')}" for i, line in enumerate(processed_content_lines)]
        return "\n".join(numbered_lines)

    @staticmethod
    def _read_binary_content(path_obj: Path, start_offset_inclusive: int, end_offset_inclusive: int, offset_type: OffsetType) -> bytes:
        content_bytes = path_obj.read_bytes()
        if offset_type == OffsetType.BYTE:
            end_offset = len(content_bytes) if end_offset_inclusive == -1 else end_offset_inclusive + 1
            return content_bytes[start_offset_inclusive:end_offset]
        raise ValueError(f"Offset type {offset_type.name} not supported for binary files.")

    @staticmethod
    def read_file_content(
        file_path: str,
        root_dir: str,
        start_offset_inclusive: int = 0,
        end_offset_inclusive: int = -1,
        offset_type: OffsetType = OffsetType.BYTE,
        encoding: str = "utf-8",
    ):
        """Read file content with proper error handling and normalization, with offset support."""
        validated_path = FileUtils.validate_file_path(file_path, root_dir)
        path_obj = Path(validated_path)

        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'. Please check the path and ensure the file exists.")

        if not path_obj.is_file():
            raise ValueError(f"Path exists but is not a file: '{validated_path}'")

        FileUtils.check_file_size(validated_path)

        file_extension = path_obj.suffix.lower()
        is_image = file_extension in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"]
        is_text = file_extension not in [".bin", ".exe", ".dll", ".zip", ".tar", ".gz", ".7z", ".rar", ".pdf"] and not is_image

        try:
            if is_image:
                return path_obj.read_bytes()
            if not is_text:
                return FileUtils._read_binary_content(path_obj, start_offset_inclusive, end_offset_inclusive, offset_type)
            return FileUtils._read_text_content(path_obj, start_offset_inclusive, end_offset_inclusive, offset_type, encoding)

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
    def is_text_file(file_path: Path, encoding: str = "utf-8") -> bool:
        """Heuristically determines if a file is a text file."""
        text_extensions = {
            ".txt",
            ".log",
            ".csv",
            ".json",
            ".xml",
            ".html",
            ".css",
            ".js",
            ".py",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".md",
            ".yml",
            ".yaml",
            ".ini",
            ".cfg",
            ".conf",
            ".sh",
            ".bat",
            ".ps1",
            ".jsonl",
        }

        if file_path.suffix.lower() in text_extensions:
            return True

        # Read a small chunk to check for non-text characters
        try:
            with file_path.open("rb") as f:
                chunk = f.read(1024)  # Read first 1KB
            # Check for common binary indicators (null bytes, non-printable ASCII)
            if b"\0" in chunk:
                return False
            try:
                chunk.decode(encoding)
                return True
            except UnicodeDecodeError:
                return False
        except Exception:
            return False  # Assume not text if we can't read it

    @staticmethod
    def write_file_content(file_path: str, new_content, root_dir: str, mode: str = "text", encoding: str = "utf-8"):
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
                path_obj.write_bytes(new_content)
            else:
                path_obj.write_text(new_content, encoding=encoding)

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
    def modify_file(
        file_path: str, root_dir: str, start_offset_inclusive: int, end_offset_inclusive: int, offset_type: OffsetType, new_content: str | bytes
    ) -> str:
        """Modifies a file by replacing a range of content with new content."""
        validated_path = FileUtils.validate_file_path(file_path, root_dir)
        path_obj = Path(validated_path)

        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'. Please check the path and ensure the file exists.")

        if not path_obj.is_file():
            raise ValueError(f"Path exists but is not a file: '{validated_path}'")

        is_text = FileUtils.is_text_file(path_obj)

        if is_text:
            original_content = path_obj.read_text(encoding="utf-8")
            if not isinstance(new_content, str):
                raise ValueError("new_content must be a string for text files.")

            if offset_type == OffsetType.LINE:
                lines = original_content.splitlines(keepends=True)
                end_line = len(lines) if end_offset_inclusive == -1 else end_offset_inclusive + 1
                modified_lines = lines[:start_offset_inclusive] + new_content.splitlines(keepends=True) + lines[end_line:]
                modified_content = "".join(modified_lines)
            elif offset_type == OffsetType.CHAR:
                end_char = len(original_content) if end_offset_inclusive == -1 else end_offset_inclusive + 1
                modified_content = original_content[:start_offset_inclusive] + new_content + original_content[end_char:]
            else:  # BYTE for text file
                content_bytes = original_content.encode("utf-8")
                end_byte = len(content_bytes) if end_offset_inclusive == -1 else end_offset_inclusive + 1
                modified_bytes = content_bytes[:start_offset_inclusive] + new_content.encode("utf-8") + content_bytes[end_byte:]
                modified_content = modified_bytes.decode("utf-8")

            path_obj.write_text(modified_content, encoding="utf-8")
            diff_output = FileUtils.generate_diff(original_content, modified_content, file_path)
            return f"Successfully modified text file '{file_path}'.\n\nDiff:\n{diff_output}"
        # Binary file
        original_content_bytes = path_obj.read_bytes()
        if isinstance(new_content, str):
            new_content_bytes = base64.b64decode(new_content.encode("utf-8"))
        elif isinstance(new_content, bytes):
            new_content_bytes = new_content
        else:
            raise ValueError("new_content must be bytes or base64-encoded string for binary files.")

        if offset_type == OffsetType.BYTE:
            end_byte = len(original_content_bytes) if end_offset_inclusive == -1 else end_offset_inclusive
            modified_content_bytes = original_content_bytes[:start_offset_inclusive] + new_content_bytes + original_content_bytes[end_byte:]
            path_obj.write_bytes(modified_content_bytes)
            return f"Successfully modified binary file '{file_path}'. Replaced bytes from {start_offset_inclusive} to {end_offset_inclusive}."
        raise ValueError(f"Offset type {offset_type.name} not supported for binary files.")

    @staticmethod
    def _replace_content_in_binary_file(path_obj: Path, old_content: bytes, new_content: bytes, number_of_occurrences: int) -> tuple[bytes, int]:
        original_content_bytes = path_obj.read_bytes()
        if number_of_occurrences == -1:
            modified_content_bytes = original_content_bytes.replace(old_content, new_content)
            replacements_made = original_content_bytes.count(old_content)
        else:
            modified_content_bytes = original_content_bytes.replace(old_content, new_content, number_of_occurrences)
            replacements_made = original_content_bytes.count(old_content)
            replacements_made = min(replacements_made, number_of_occurrences)
        return modified_content_bytes, replacements_made

    @staticmethod
    def replace_content_in_file(file_path: str, root_dir: str, old_content: str | bytes, new_content: str | bytes, number_of_occurrences: int = -1) -> str:
        """Replaces occurrences of old_content with new_content within a file."""
        validated_path = FileUtils.validate_file_path(file_path, root_dir)
        path_obj = Path(validated_path)

        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'. Please check the path and ensure the file exists.")

        if not path_obj.is_file():
            raise ValueError(f"Path exists but is not a file: '{validated_path}'")

        is_text = FileUtils.is_text_file(path_obj)

        if is_text:
            original_content_text = path_obj.read_text(encoding="utf-8")
            if not isinstance(old_content, str) or not isinstance(new_content, str):
                raise ValueError("old_content and new_content must be strings for text files.")

            original_content_normalized = FileUtils.normalize_line_endings(original_content_text, "\n")
            old_content_normalized = FileUtils.normalize_line_endings(old_content, "\n")
            new_content_normalized = FileUtils.normalize_line_endings(new_content, "\n")

            if number_of_occurrences == -1:
                modified_content = original_content_normalized.replace(old_content_normalized, new_content_normalized)
                replacements_made = original_content_normalized.count(old_content_normalized)
            else:
                modified_content = original_content_normalized.replace(old_content_normalized, new_content_normalized, number_of_occurrences)
                replacements_made = len(re.findall(re.escape(old_content_normalized), original_content_normalized))
                replacements_made = min(replacements_made, number_of_occurrences)

            path_obj.write_text(modified_content, encoding="utf-8")

            diff_output = FileUtils.generate_diff(original_content_text, modified_content, file_path)
            return f"Successfully replaced {replacements_made} occurrence(s) in text file '{file_path}'.\n\nDiff:\n{diff_output}"

        # Binary file handling
        if isinstance(old_content, str):
            old_content_bytes = base64.b64decode(old_content.encode("utf-8"))
        elif isinstance(old_content, bytes):
            old_content_bytes = old_content
        else:
            raise ValueError("old_content must be bytes or base64-encoded string for binary files.")

        if isinstance(new_content, str):
            new_content_bytes = base64.b64decode(new_content.encode("utf-8"))
        elif isinstance(new_content, bytes):
            new_content_bytes = new_content
        else:
            raise ValueError("new_content must be bytes or base64-encoded string for binary files.")

        modified_content_bytes, replacements_made = FileUtils._replace_content_in_binary_file(
            path_obj, old_content_bytes, new_content_bytes, number_of_occurrences
        )
        path_obj.write_bytes(modified_content_bytes)
        return f"Successfully replaced {replacements_made} occurrence(s) in binary file '{file_path}'."

    @staticmethod
    def _delete_single_path(item_path: str, root_dir: str) -> tuple[bool, str]:
        try:
            validated_path = FileUtils.validate_file_path(item_path, root_dir)
            path_obj = Path(validated_path)

            if not path_obj.exists():
                return False, f"Path not found: '{item_path}'"

            if path_obj.is_file():
                path_obj.unlink()
                return True, item_path
            if path_obj.is_dir():
                shutil.rmtree(validated_path)
                return True, item_path
            return False, f"Path is neither a file nor a directory: '{item_path}'"

        except PermissionError as e:
            return False, f"Permission denied deleting '{item_path}': {e}"
        except Exception as e:  # pylint: disable=broad-exception-caught
            return False, f"Error deleting '{item_path}': {e}"

    @staticmethod
    def delete_paths(paths: list[str], root_dir: str) -> dict:
        """Delete multiple files or directories."""
        if not isinstance(paths, list):
            raise ValueError("paths must be a list")

        if not paths:
            raise ValueError("paths list cannot be empty")

        deleted_items = []
        errors = []

        for item_path in paths:
            success, message = FileUtils._delete_single_path(item_path, root_dir)
            if success:
                deleted_items.append(message)
            else:
                errors.append(message)

        if errors:
            error_msg = f"Some items could not be deleted: {'; '.join(errors)}"
            if deleted_items:
                error_msg += f". Successfully deleted: {', '.join(deleted_items)}"

            raise Exception(error_msg) from None

        return {"status": "success", "message": f"Successfully deleted {len(deleted_items)} item(s): {', '.join(deleted_items)}"}
