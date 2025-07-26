"""
File utilities for the LocalFiles server.
"""

import difflib
import os
import re
from pathlib import Path


class FileUtils:
    """Provides file manipulation utilities."""

    max_file_size = 100 * 1024 * 1024  # 100MB limit

    @staticmethod
    def validate_file_path(file_path: str) -> str:
        """Validate and normalize file path for security."""
        try:
            # Convert to Path object and resolve to absolute path
            path_obj = Path(file_path).resolve()

            # Basic security check - prevent directory traversal attacks
            if ".." in str(path_obj) and not str(path_obj).startswith(os.path.abspath(os.getcwd())):
                raise ValueError("Invalid file path: directory traversal not allowed")

            return str(path_obj)
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise ValueError(f"Invalid file path '{file_path}': {e}") from e

    @staticmethod
    def check_file_size(file_path: str):
        """Check if file size is within limits."""
        try:
            size = os.path.getsize(file_path)
            if size > FileUtils.max_file_size:
                raise ValueError(f"File too large: {size} bytes (max: {FileUtils.max_file_size} bytes)")
        except OSError:
            pass  # File doesn't exist yet, which is fine for write operations

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
                fromfile=f"{os.path.basename(file_path)} (before)",
                tofile=f"{os.path.basename(file_path)} (after)",
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
    def read_file_content(file_path: str, mode: str = "text", encoding: str = "utf-8"):
        """Read file content with proper error handling and normalization."""
        validated_path = FileUtils.validate_file_path(file_path)

        if not os.path.exists(validated_path):
            raise FileNotFoundError(f"File not found: '{file_path}'. Please check the path and ensure the file exists.")

        if not os.path.isfile(validated_path):
            raise ValueError(f"Path exists but is not a file: '{validated_path}'")

        FileUtils.check_file_size(validated_path)

        try:
            if mode == "binary":
                with open(validated_path, "rb") as f:
                    return f.read()
            else:
                with open(validated_path, "r", encoding=encoding) as f:
                    content = f.read()
                # Normalize line endings to \n for consistent processing
                return FileUtils.normalize_line_endings(content, "\n")

        except UnicodeDecodeError as e:
            raise ValueError(
                f"Cannot decode file '{validated_path}' with encoding '{encoding}'. " f"Error: {e}. Try using a different encoding or 'binary' mode."
            ) from e
        except PermissionError as e:
            raise PermissionError(f"Permission denied: cannot read file '{validated_path}'") from e
        except ValueError as e:
            raise e
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise IOError(f"Unexpected error reading file '{validated_path}': {e}") from e

    @staticmethod
    def write_file_content(file_path: str, content, mode: str = "text", encoding: str = "utf-8"):
        """Write file content with proper error handling."""
        validated_path = FileUtils.validate_file_path(file_path)

        # Create directory if it doesn't exist
        parent_dir = os.path.dirname(validated_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:  # pylint: disable=broad-exception-caught
                raise OSError(f"Failed to create parent directory '{parent_dir}': {e}") from e

        try:
            if mode == "binary":
                with open(validated_path, "wb") as f:
                    f.write(content)
            else:
                with open(validated_path, "w", encoding=encoding) as f:
                    f.write(content)

        except PermissionError as e:
            raise PermissionError(f"Permission denied: cannot write to file '{validated_path}'") from e
        except OSError as e:
            if e.errno == 28:  # No space left on device
                raise OSError(f"No space left on device when writing to '{validated_path}': {e}") from e
            raise OSError(f"OS error writing to file '{validated_path}': {e}") from e
        except ValueError as e:
            raise e
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise IOError(f"Unexpected error writing to file '{validated_path}': {e}") from e
