"""
File utilities for the LocalFiles server.
"""

import difflib
import re
from pathlib import Path


class FileUtils:
    """Provides file manipulation utilities."""

    max_file_size = 100 * 1024 * 1024  # 100MB limit

    @staticmethod
    def validate_file_path(file_path: str, root_dir: str) -> str:
        """Validate and normalize file path for security, confining it to root_dir."""
        try:
            # Convert to Path object and resolve to absolute path
            path_obj = Path(file_path).resolve()
            root_path_obj = Path(root_dir).resolve()

            # Ensure the resolved path is a child of the root directory
            if not path_obj.is_relative_to(root_path_obj):
                raise ValueError(f"Path '{file_path}' is outside the allowed root directory '{root_dir}'")

            return str(path_obj)
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise ValueError(f"Invalid file path '{file_path}': {e}") from e

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
            before_lines = before_content.splitlines(keepends=True)
            after_lines = after_content.splitlines(keepends=True)

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
