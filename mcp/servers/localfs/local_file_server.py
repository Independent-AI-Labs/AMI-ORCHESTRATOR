import argparse
import base64
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

import yaml

from orchestrator.mcp.servers.localfs.file_utils import FileUtils
from orchestrator.mcp.servers.localfs.tool_definitions import get_tool_declarations


class LocalFiles:
    """Provides file manipulation tools via the MCP protocol."""

    def __init__(self, root_dir: str):
        self.tools = {tool_decl["name"]: getattr(self, tool_decl["name"]) for tool_decl in get_tool_declarations()}
        self.root_dir = root_dir

        # Create a /logs directory in the project root if it doesn't exist
        logs_dir = Path(self.root_dir) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate a unique log file name with a timestamp
        log_file = logs_dir / f"mcp_server_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="[%(asctime)s] [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s",
        )

    def _send_response(self, response):
        """Send a JSON-RPC response to stdout."""
        try:
            response_str = json.dumps(response) + "\n"
            sys.stdout.buffer.write(response_str.encode("utf-8"))
            sys.stdout.buffer.flush()
            logging.info("Response sent successfully: %s", response.get("id", "unknown"))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to send response: %s", e)

    def _send_error(self, message, request_id=None, code=-32602):
        """Send a JSON-RPC error response."""
        logging.error("Error response: %s (request_id: %s)", message, request_id)
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": str(message)},
        }
        if request_id:
            error_response["id"] = request_id
        self._send_response(error_response)

    def _filter_tool_arguments(self, tool_name: str, tool_args: dict) -> dict:
        """Filter tool arguments to only include expected parameters."""
        tool_declarations = get_tool_declarations()
        expected_params: set[str] = set()
        for tool_decl in tool_declarations:
            if tool_decl["name"] == tool_name:
                expected_params = set(tool_decl["inputSchema"]["properties"].keys())
                break

        if not expected_params:
            return tool_args

        filtered_args = {k: v for k, v in tool_args.items() if k in expected_params}

        # Log if we filtered out any parameters
        filtered_out = set(tool_args.keys()) - expected_params
        if filtered_out:
            logging.warning("Filtered out unexpected parameters for %s: %s", tool_name, filtered_out)

        return filtered_args

    def read_file(self, file_path: str, mode: str = "text", encoding: str = "utf-8") -> str:
        """Read content from a file."""
        try:
            logging.info("Reading file: %s (mode: %s, encoding: %s)", file_path, mode, encoding)
            content = FileUtils.read_file_content(file_path, self.root_dir, mode, encoding)

            if mode == "binary":
                # Return base64 encoded content for binary files
                encoded_content = base64.b64encode(content).decode("utf-8")
                logging.info(
                    "Successfully read binary file: %s (%s bytes)",
                    file_path,
                    len(content),
                )
                return encoded_content
            logging.info(
                "Successfully read text file: %s (%s characters, %s lines)",
                file_path,
                len(content),
                content.count(chr(10)),
            )
            # Prepend line numbers for text files
            lines = content.splitlines(keepends=True)
            numbered_lines = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
            return "".join(numbered_lines)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to read file %s: %s", file_path, e)
            raise e

    def _validate_and_decode_content(self, content: str | bytes, mode: str) -> str | bytes:
        """Validates and decodes content based on mode."""
        if content is None:
            raise ValueError("content cannot be None")

        if mode == "binary":
            if isinstance(content, str):
                try:
                    decoded_content = base64.b64decode(content.encode("utf-8"))
                    logging.info("Decoded base64 content: %s bytes", len(decoded_content))
                    return decoded_content
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

    def _get_write_success_message_binary(self, file_path: str, content: bytes) -> str:
        """Generates the success message for binary file writes."""
        content_bytes: bytes = content
        content_size = len(content_bytes)
        logging.info(
            "Successfully wrote binary file: %s (%s bytes)",
            file_path,
            content_size,
        )
        return f"Successfully wrote binary content to '{file_path}' ({content_size} bytes)."

    def _get_write_success_message_text(self, file_path: str, content: str, original_content: str | None) -> tuple[str, str | None]:
        """Generates the success message and diff for text file writes."""
        diff_output: str | None = None
        if original_content is not None:
            diff_output = FileUtils.generate_diff(original_content, content, file_path)

        line_count = content.count("\n") + 1
        char_count = len(content)

        message = f"Successfully wrote text content to '{file_path}' ({char_count} characters, {line_count} lines)."
        return message, diff_output

    def _get_write_success_message(self, file_path: str, content: str | bytes, mode: str, original_content: str | bytes | None) -> dict:
        """Generates the success message for write_file, dispatching to specific handlers."""
        if mode == "binary":
            # MyPy knows content is bytes here due to the mode check
            message = self._get_write_success_message_binary(file_path, cast(bytes, content))
            return {"message": message, "diff": None}
        # MyPy knows content is str here due to the mode check
        # MyPy knows original_content is str | None here
        message, diff_output = self._get_write_success_message_text(file_path, cast(str, content), cast(str | None, original_content))
        return {"message": message, "diff": diff_output}

    def write_file(self, file_path: str, content: str | bytes, mode: str = "text", encoding: str = "utf-8") -> dict:
        """Write content to a file."""
        try:
            logging.info("Writing file: %s (mode: %s, encoding: %s)", file_path, mode, encoding)

            if not file_path:
                raise ValueError("file_path cannot be empty")

            processed_content_raw = self._validate_and_decode_content(content, mode)
            processed_content: str | bytes

            if mode == "binary":
                assert isinstance(processed_content_raw, bytes)
                processed_content = processed_content_raw
            else:  # mode == "text"
                assert isinstance(processed_content_raw, str)
                processed_content = processed_content_raw

            file_path_obj = Path(file_path)
            file_exists = file_path_obj.exists()
            original_content: str | bytes | None = None

            if file_exists:
                try:
                    read_content = FileUtils.read_file_content(file_path, self.root_dir, mode, encoding)
                    original_content = cast(bytes, read_content) if mode == "binary" else cast(str, read_content)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logging.warning("Could not read existing file for diff: %s", e)

            FileUtils.write_file_content(file_path, processed_content, self.root_dir, mode, encoding)
            result_dict = self._get_write_success_message(file_path, processed_content, mode, original_content)
            response_data = {"status": "success", "message": result_dict["message"]}
            if result_dict["diff"]:
                response_data["diff"] = result_dict["diff"]
            return response_data

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to write file %s: %s", file_path, e)
            raise e

    def _process_text_replacement(self, file_path: str, current_content: str, old_string: str, new_string: str, count: int) -> tuple[str, int]:
        """Handles text mode string replacement logic."""
        if not isinstance(old_string, str) or not isinstance(new_string, str):
            raise ValueError("old_string and new_string must be strings in text mode")

        if not old_string:
            raise ValueError("old_string cannot be empty - this would insert new_string between every character")

        old_string_normalized = FileUtils.normalize_line_endings(old_string, "\n")
        new_string_normalized = FileUtils.normalize_line_endings(new_string, "\n")

        occurrence_count = current_content.count(old_string_normalized)
        if occurrence_count == 0:
            logging.info("No occurrences found of search string in %s", file_path)
            return "No changes made to '{file_path}': search string not found.", 0

        if count == 0:
            new_content = current_content.replace(old_string_normalized, new_string_normalized)
            actual_replacements = current_content.count(old_string_normalized)
        else:
            new_content = current_content.replace(old_string_normalized, new_string_normalized, count)
            actual_replacements = count

        return new_content, actual_replacements

    def _process_binary_replacement(self, file_path: str, current_content: bytes, old_string: bytes, new_string: bytes, count: int) -> tuple[bytes, int]:
        """Handles binary mode string replacement logic."""
        if not isinstance(old_string, bytes) or not isinstance(new_string, bytes):
            raise ValueError("old_string and new_string must be bytes in binary mode")

        if not old_string:
            raise ValueError("old_string cannot be empty - this would insert new_string between every byte")

        occurrence_count = current_content.count(old_string)
        if occurrence_count == 0:
            logging.info("No occurrences found of search bytes in %s", file_path)
            return b"No changes made to '{file_path}': search bytes not found.", 0

        if count == 0:
            new_content = current_content.replace(old_string, new_string)
            actual_replacements = current_content.count(old_string)
        else:
            new_content = current_content.replace(old_string, new_string, count)
            actual_replacements = count

        return new_content, actual_replacements

    def _handle_no_replacements(self, file_path: str) -> dict:
        logging.info(
            "No changes made to %s - search string not found or no replacements occurred",
            file_path,
        )
        return {"status": "success", "message": f"No changes made to '{file_path}': search string not found or no replacements occurred."}

    def _handle_identical_content(self, file_path: str) -> dict:
        logging.info(
            "No changes made to %s - content identical after replacement",
            file_path,
        )
        return {"status": "success", "message": f"No changes made to '{file_path}': replacement resulted in identical content."}

    def _read_file_content(self, file_path: str, mode: str, encoding: str) -> str | bytes:
        return FileUtils.read_file_content(file_path, self.root_dir, mode, encoding)

    def _perform_replacement(
        self, file_path: str, original_content: str | bytes, old_string: str | bytes, new_string: str | bytes, mode: str, count: int
    ) -> tuple[str | bytes, int]:
        if mode == "binary":
            if not isinstance(original_content, bytes):
                raise TypeError("Original content must be bytes in binary mode")
            try:
                old_bytes = base64.b64decode(cast(str, old_string).encode("utf-8"))
                new_bytes = base64.b64decode(cast(str, new_string).encode("utf-8"))
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid base64 content for binary mode: {e}") from e
            return self._process_binary_replacement(file_path, original_content, old_bytes, new_bytes, count)
        if mode == "text":
            if not isinstance(original_content, str):
                raise TypeError("Original content must be string in text mode")
            return self._process_text_replacement(file_path, original_content, cast(str, old_string), cast(str, new_string), count)
        raise ValueError("Mode must be 'text' or 'binary'")

    def edit_file_replace_string(
        self,
        file_path: str,
        old_string: str | bytes,
        new_string: str | bytes,
        mode: str = "text",
        encoding: str = "utf-8",
        count: int = 0,
    ) -> dict:
        """Replace occurrences of old_string with new_string in a file."""
        try:
            logging.info(
                "Replacing string in file: %s (mode: %s, count: %s)",
                file_path,
                mode,
                count,
            )
            original_content = self._read_file_content(file_path, mode, encoding)
            new_content: str | bytes
            actual_replacements: int

            new_content, actual_replacements = self._perform_replacement(file_path, original_content, old_string, new_string, mode, count)

            if actual_replacements == 0:
                logging.info(
                    "No changes made to %s - search string not found or no replacements occurred",
                    file_path,
                )
                return self._handle_no_replacements(file_path)

            if new_content == original_content:
                return self._handle_identical_content(file_path)

            FileUtils.write_file_content(file_path, new_content, self.root_dir, mode, encoding)

            diff_output = ""
            if mode == "binary":
                diff_output = "Binary content changed."
            else:
                diff_output = FileUtils.generate_diff(cast(str, original_content), cast(str, new_content), file_path)

            logging.info(
                "Successfully replaced %s occurrences in %s",
                actual_replacements,
                file_path,
            )

            result_msg = f"Successfully replaced {actual_replacements} occurrence(s) in '{file_path}'."
            if diff_output:
                result_msg += f"\n\nDiff:\n{diff_output}"

            response_data = {"status": "success", "message": result_msg}
            if diff_output:
                response_data["diff"] = diff_output
            return response_data
        except (ValueError, PermissionError) as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to replace string in file %s: %s", file_path, e)
            raise e
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to replace string in file %s: %s", file_path, e)
            raise e

    def edit_file_replace_lines(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        new_string: str,
        encoding: str = "utf-8",
    ) -> dict:
        """Replace content within a specified range of lines."""
        try:
            logging.info("Replacing lines %s-%s in file: %s", start_line, end_line, file_path)

            if start_line <= 0 or end_line <= 0:
                raise ValueError("Line numbers must be positive (1-based indexing)")

            if start_line > end_line:
                raise ValueError(f"Start line ({start_line}) must be less than or equal to end line ({end_line})")

            # Read original content for diff
            original_content = FileUtils.read_file_content(file_path, self.root_dir, "text", encoding)
            lines = original_content.splitlines(keepends=True)  # Keep ends here
            total_lines = len(lines)

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
            new_content = "".join(modified_lines)

            FileUtils.write_file_content(file_path, new_content, self.root_dir, "text", encoding)

            # Generate diff
            diff_output = FileUtils.generate_diff(original_content, new_content, file_path)

            replaced_lines = end_line - start_line + 1
            new_line_count = len(new_lines)

            logging.info(
                "Successfully replaced %s lines with %s lines in %s",
                replaced_lines,
                new_line_count,
                file_path,
            )

            result_msg = f"Successfully replaced lines {start_line}-{end_line} ({replaced_lines} lines) with {new_line_count} line(s) in '{file_path}'."
            if diff_output:
                result_msg += f"\n\nDiff:\n{diff_output}"

            response_data = {"status": "success", "message": result_msg}
            if diff_output:
                response_data["diff"] = diff_output
            return response_data

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to replace lines in file %s: %s", file_path, e)
            raise e

    def edit_file_delete_lines(self, file_path: str, start_line: int, end_line: int, encoding: str = "utf-8") -> dict:
        """Delete lines within a specified range."""
        try:
            logging.info("Deleting lines %s-%s in file: %s", start_line, end_line, file_path)

            if start_line <= 0 or end_line <= 0:
                raise ValueError("Line numbers must be positive (1-based indexing)")

            if start_line > end_line:
                raise ValueError(f"Start line ({start_line}) must be less than or equal to end line ({end_line})")

            # Read original content for diff
            original_content = FileUtils.read_file_content(file_path, self.root_dir, "text", encoding)
            lines = original_content.splitlines(keepends=True)  # Keep ends here
            total_lines = len(lines)

            if start_line > total_lines + 1:  # Allow deleting from end of file
                raise ValueError(f"Start line {start_line} exceeds file length ({total_lines} lines)")

            if end_line > total_lines + 1:  # Allow deleting from end of file
                raise ValueError(f"End line {end_line} exceeds file length ({total_lines} lines)")

            # Convert to 0-based indexing
            start_idx = start_line - 1
            end_idx = end_line

            # Delete the specified lines by keeping everything before and after
            modified_lines = lines[:start_idx] + lines[end_idx:]
            new_content = "".join(modified_lines)

            FileUtils.write_file_content(file_path, new_content, self.root_dir, "text", encoding)

            # Generate diff
            diff_output = FileUtils.generate_diff(original_content, new_content, file_path)

            deleted_lines = end_line - start_line + 1
            remaining_lines = len(modified_lines)

            logging.info("Successfully deleted %s lines from %s", deleted_lines, file_path)

            result_msg = f"Successfully deleted lines {start_line}-{end_line} ({deleted_lines} lines) from '{file_path}'. File now has {remaining_lines} lines."
            if diff_output:
                result_msg += f"\n\nDiff:\n{diff_output}"

            response_data = {"status": "success", "message": result_msg}
            if diff_output:
                response_data["diff"] = diff_output
            return response_data

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to delete lines from file %s: %s", file_path, e)
            raise e

    def edit_file_insert_lines(self, file_path: str, line_number: int, content: str, encoding: str = "utf-8") -> dict:
        """Insert content at a specified line number."""
        try:
            logging.info("Inserting content at line %s in file: %s", line_number, file_path)

            if line_number <= 0:
                raise ValueError("Line number must be positive (1-based indexing)")

            # Read original content for diff
            original_content = FileUtils.read_file_content(file_path, self.root_dir, "text", encoding)
            lines = original_content.splitlines(keepends=True)  # Keep ends here
            total_lines = len(lines)

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
            new_content = "".join(modified_lines)

            FileUtils.write_file_content(file_path, new_content, self.root_dir, "text", encoding)

            # Generate diff
            diff_output = FileUtils.generate_diff(original_content, new_content, file_path)

            inserted_line_count = len(insert_lines)
            new_total_lines = len(modified_lines)

            logging.info(
                "Successfully inserted %s lines at line %s in %s",
                inserted_line_count,
                line_number,
                file_path,
            )

            result_msg = f"Successfully inserted {inserted_line_count} line(s) at line {line_number} in '{file_path}'. File now has {new_total_lines} lines."
            if diff_output:
                result_msg += f"\n\nDiff:\n{diff_output}"

            response_data = {"status": "success", "message": result_msg}
            if diff_output:
                response_data["diff"] = diff_output
            return response_data

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to insert lines in file %s: %s", file_path, e)
            raise e

    def delete_files(self, file_paths: list) -> dict:
        """Delete multiple files."""
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        if not file_paths:
            raise ValueError("file_paths list cannot be empty")

        deleted_files = []
        errors = []

        logging.info("Attempting to delete %s file(s)", len(file_paths))

        for file_path in file_paths:
            try:
                validated_path = FileUtils.validate_file_path(file_path, self.root_dir)
                path_obj = Path(validated_path)

                if not path_obj.exists():
                    errors.append(f"File not found: '{file_path}'")
                    continue

                if not path_obj.is_file():
                    errors.append(f"Path is not a file: '{file_path}'")
                    continue

                path_obj.unlink()
                deleted_files.append(file_path)
                logging.info("Successfully deleted file: %s", file_path)

            except PermissionError as e:
                errors.append(f"Permission denied deleting file: '{file_path}': {e}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                errors.append(f"Error deleting file '{file_path}': {e}")

        if errors:
            error_msg = f"Some files could not be deleted: {'; '.join(errors)}"
            if deleted_files:
                error_msg += f". Successfully deleted: {', '.join(deleted_files)}"

            logging.error(error_msg)
            raise Exception(error_msg) from None  # pylint: disable=raise-missing-from

        logging.info("Successfully deleted all %s file(s)", len(deleted_files))

        return {"status": "success", "message": f"Successfully deleted {len(deleted_files)} file(s): {', '.join(deleted_files)}"}

    def _validate_move_paths(self, source_paths: list, destination_paths: list):
        if not isinstance(source_paths, list) or not isinstance(destination_paths, list):
            raise ValueError("source_paths and destination_paths must be lists")
        if not source_paths or not destination_paths:
            raise ValueError("source_paths and destination_paths lists cannot be empty")
        if len(source_paths) != len(destination_paths):
            raise ValueError(f"Number of source paths ({len(source_paths)}) must match destination paths ({len(destination_paths)})")

    def _handle_destination_directory(self, dest_path_obj: Path, create_dirs: bool, source_path: str) -> str | None:
        dest_dir = dest_path_obj.parent
        if dest_dir and not dest_dir.exists():
            if create_dirs:
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    logging.info("Created destination directory: %s", dest_dir)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    return f"Failed to create destination directory '{dest_dir}' for '{source_path}': {e}"
            else:
                return f"Destination directory does not exist: '{dest_dir}' for '{source_path}'"
        return None

    def _perform_single_file_move(self, source_path: str, dest_path: str, create_dirs: bool) -> tuple[bool, str | None]:
        result: tuple[bool, str | None] = (False, None)
        try:
            validated_source = FileUtils.validate_file_path(source_path, self.root_dir)
            validated_dest = FileUtils.validate_file_path(dest_path, self.root_dir)

            source_path_obj = Path(validated_source)
            if not source_path_obj.exists():
                result = False, f"Source file not found: '{source_path}'"
            elif not source_path_obj.is_file():
                result = False, f"Source path is not a file: '{source_path}'"
            else:
                dest_path_obj = Path(validated_dest)
                dir_error = self._handle_destination_directory(dest_path_obj, create_dirs, source_path)
                if dir_error:
                    result = False, dir_error
                elif dest_path_obj.exists():
                    result = False, f"Destination already exists: '{dest_path}' for source '{source_path}'"
                else:
                    file_size = source_path_obj.stat().st_size if source_path_obj.exists() else 0
                    shutil.move(validated_source, validated_dest)
                    logging.info("Successfully moved file: %s -> %s (%s bytes)", source_path, dest_path, file_size)
                    result = True, None
        except PermissionError as e:
            result = False, f"Permission denied moving file: '{source_path}' -> '{dest_path}': {e}"
        except Exception as e:  # pylint: disable=broad-exception-caught
            result = False, f"Error moving file '{source_path}' -> '{dest_path}': {e}"
        return result

    def move_files(self, source_paths: list, destination_paths: list, create_dirs: bool = True) -> dict:
        """Move/rename files from source paths to destination paths."""
        self._validate_move_paths(source_paths, destination_paths)

        moved_files = []
        errors = []

        logging.info("Attempting to move %s file(s)", len(source_paths))

        for source_path, dest_path in zip(source_paths, destination_paths, strict=False):
            success, error_msg = self._perform_single_file_move(source_path, dest_path, create_dirs)
            if success:
                moved_files.append((source_path, dest_path))
            else:
                errors.append(error_msg)

        if errors:
            # Filter out None values before joining
            filtered_errors = [err for err in errors if err is not None]
            error_msg = f"Some files could not be moved: {'; '.join(filtered_errors)}"
            if moved_files:
                moved_list = [f"{src} -> {dst}" for src, dst in moved_files]
                error_msg += f". Successfully moved: {', '.join(moved_list)}"
            logging.error(error_msg)
            raise Exception(error_msg) from None

        logging.info("Successfully moved all %s file(s)", len(moved_files))
        moved_list = [f"{src} -> {dst}" for src, dst in moved_files]
        return {"status": "success", "message": f"Successfully moved {len(moved_files)} file(s): {', '.join(moved_list)}"}

    def create_directory(self, directory_path: str) -> dict:
        """Create a directory and any necessary parent directories."""
        try:
            validated_path = FileUtils.validate_file_path(directory_path, self.root_dir)
            path_obj = Path(validated_path)

            if path_obj.exists():
                if path_obj.is_dir():
                    logging.info("Directory already exists: %s", directory_path)
                    return {"status": "success", "message": f"Directory already exists: '{directory_path}'"}
                raise ValueError(f"Path exists but is not a directory: '{directory_path}'")

            path_obj.mkdir(parents=True, exist_ok=True)
            logging.info("Successfully created directory: %s", directory_path)
            return {"status": "success", "message": f"Successfully created directory: '{directory_path}'"}

        except PermissionError as e:
            error_msg = f"Permission denied creating directory: '{directory_path}': {e}"
            logging.error(error_msg)
            raise PermissionError(error_msg) from e
        except ValueError as e:
            raise e
        except Exception as e:  # pylint: disable=broad-exception-caught
            error_msg = f"Failed to create directory '{directory_path}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    def delete_directory(self, directory_path: str) -> dict:
        """Delete a directory and all its contents."""
        try:
            validated_path = FileUtils.validate_file_path(directory_path, self.root_dir)
            path_obj = Path(validated_path)

            if not path_obj.exists():
                raise FileNotFoundError(f"Directory not found: '{directory_path}'")

            if not path_obj.is_dir():
                raise ValueError(f"Path is not a directory: '{directory_path}'")

            # Count items before deletion for informative message
            item_count = sum(1 for _ in path_obj.rglob("*")) + 1  # +1 for the directory itself

            shutil.rmtree(validated_path)
            logging.info("Successfully deleted directory: %s", directory_path)
            return {"status": "success", "message": f"Successfully deleted directory '{directory_path}' and all its contents ({item_count} items)"}

        except PermissionError as e:
            error_msg = f"Permission denied deleting directory: '{directory_path}': {e}"
            logging.error(error_msg)
            raise PermissionError(error_msg) from e
        except ValueError as e:
            raise e
        except Exception as e:  # pylint: disable=broad-exception-caught
            error_msg = f"Failed to delete directory '{directory_path}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e

    def _handle_request(self, line_str):
        """Handle a single JSON-RPC request."""
        try:
            request = json.loads(line_str)
        except json.JSONDecodeError as e:
            self._send_error(f"Invalid JSON in request: {e}")
            return

        request_id = request.get("id")
        method = request.get("method")
        logging.debug("Processing method: %s, ID: %s", method, request_id)

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2025-06-18",
                    "serverInfo": {"name": "Local Files", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
                "id": request_id,
            }
            self._send_response(response)
            return

        if method == "notifications/initialized":
            logging.info("Client initialization complete")
            print("INITIALIZED_NOTIFICATION_SENT_DEBUG_MESSAGE")
            sys.stdout.flush()
            return

        if method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "result": {"tools": get_tool_declarations()},
                "id": request_id,
            }
            self._send_response(response)
            return

        if method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name not in self.tools:
                self._send_error(
                    f"Unknown tool: '{tool_name}'. Available tools: {list(self.tools.keys())}",
                    request_id,
                )
                return

            try:
                logging.info("Executing tool: %s", tool_name)
                filtered_args = self._filter_tool_arguments(tool_name, tool_args)
                result = self.tools[tool_name](**filtered_args)
                # Convert the result to a human-readable YAML string
                formatted_result = yaml.dump(result, indent=2, default_flow_style=False) if isinstance(result, dict) else str(result)

                response = {
                    "jsonrpc": "2.0",
                    "result": {"content": [{"type": "text", "text": formatted_result}]},
                    "id": request_id,
                }
                self._send_response(response)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logging.error("Tool execution failed for %s: %s", tool_name, e, exc_info=True)
                # Check if the exception is a ValueError or PermissionError from FileUtils
                if isinstance(e, ValueError | PermissionError):
                    self._send_error(f"Tool '{tool_name}' execution failed: {e}", request_id)
                else:
                    self._send_error(f"Internal server error during tool '{tool_name}' execution: {e}", request_id)
            return

        self._send_error(
            f"Unknown method: '{method}'. Supported methods: initialize, tools/list, tools/call",
            request_id,
        )

    def run(self):
        """Main server loop to handle JSON-RPC requests."""
        logging.info("MCP File Manipulation Server started")
        print("SERVER_STARTED_DEBUG_MESSAGE")
        sys.stdout.flush()

        while True:
            try:
                line = sys.stdin.buffer.readline()
                if not line:
                    logging.info("stdin closed, shutting down server.")
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                logging.debug("Received request: %s", line_str)
                self._handle_request(line_str)

            except KeyboardInterrupt:
                logging.info("Server interrupted by user")
                break

            except Exception as e:  # pylint: disable=broad-exception-caught
                logging.error("Unexpected server error: %s", e, exc_info=True)
                try:
                    self._send_error(f"Internal server error: {e}")
                except Exception as send_error:  # pylint: disable=broad-exception-caught
                    logging.error("Failed to send error response: %s", send_error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP File Manipulation Server")
    parser.add_argument(
        "--root-dir",
        type=str,
        default=Path.cwd(),
        help="Root directory for file operations",
    )
    args = parser.parse_args()

    try:
        server = LocalFiles(args.root_dir)
        server.run()
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Failed to start server: %s", e, exc_info=True)
        sys.exit(1)
