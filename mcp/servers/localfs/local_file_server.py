import base64
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime

from orchestrator.mcp.servers.localfs.file_utils import FileUtils
from orchestrator.mcp.servers.localfs.tool_definitions import get_tool_declarations

# Create a /logs directory in the project root if it doesn't exist
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs"))
os.makedirs(LOGS_DIR, exist_ok=True)

# Generate a unique log file name with a timestamp
LOG_FILE = os.path.join(LOGS_DIR, f"mcp_server_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s",
)


class LocalFiles:
    """Provides file manipulation tools via the MCP protocol."""

    def __init__(self):
        self.tools = {tool_decl["name"]: getattr(self, tool_decl["name"]) for tool_decl in get_tool_declarations()}

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

    def read_file(self, file_path: str, mode: str = "text", encoding: str = "utf-8"):
        """Read content from a file."""
        try:
            logging.info("Reading file: %s (mode: %s, encoding: %s)", file_path, mode, encoding)
            content = FileUtils.read_file_content(file_path, mode, encoding)

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
            return content

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to read file %s: %s", file_path, e)
            raise e

    def write_file(self, file_path: str, content, mode: str = "text", encoding: str = "utf-8"):
        """Write content to a file."""
        try:
            logging.info("Writing file: %s (mode: %s, encoding: %s)", file_path, mode, encoding)

            # Validate inputs
            if not file_path:
                raise ValueError("file_path cannot be empty")

            if content is None:
                raise ValueError("content cannot be None")

            # Handle binary mode content decoding
            if mode == "binary":
                if isinstance(content, str):
                    try:
                        decoded_content = base64.b64decode(content.encode("utf-8"))
                        logging.info("Decoded base64 content: %s bytes", len(decoded_content))
                    except (TypeError, ValueError) as e:
                        raise ValueError(f"Invalid base64 content for binary mode: {e}") from e
                    content = decoded_content
                elif not isinstance(content, bytes):
                    raise ValueError("Binary mode requires base64-encoded string or bytes content")
            else:
                # Text mode - ensure content is a string
                if not isinstance(content, str):
                    try:
                        content = str(content)
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        raise ValueError(f"Cannot convert content to string: {e}") from e

            # Check if file exists to generate diff for text mode
            file_exists = os.path.exists(file_path)
            original_content = ""
            if file_exists and mode == "text":
                try:
                    original_content = FileUtils.read_file_content(file_path, mode, encoding)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logging.warning("Could not read existing file for diff: %s", e)

            # Write the content
            FileUtils.write_file_content(file_path, content, mode, encoding)

            # Generate success message with content statistics
            if mode == "binary":
                content_size = len(content)
                logging.info(
                    "Successfully wrote binary file: %s (%s bytes)",
                    file_path,
                    content_size,
                )
                result_msg = f"Successfully wrote binary content to '{file_path}' ({content_size} bytes)."
            else:
                content_length = len(content)
                line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
                logging.info(
                    "Successfully wrote text file: %s (%s characters, %s lines)",
                    file_path,
                    content_length,
                    line_count,
                )
                result_msg = f"Successfully wrote text content to '{file_path}' ({content_length} characters, {line_count} lines)."

                # Add diff if file existed before and content changed
                if file_exists and original_content != content:
                    diff_output = FileUtils.generate_diff(original_content, content, file_path)
                    if diff_output and diff_output != "No changes detected in diff":
                        result_msg += f"\n\nDiff:\n{diff_output}"

            return result_msg

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to write file %s: %s", file_path, e)
            raise e

    def edit_file_replace_string(
        self,
        file_path: str,
        old_string,
        new_string,
        mode: str = "text",
        encoding: str = "utf-8",
        count: int = 0,
    ):
        """Replace occurrences of old_string with new_string in a file."""
        try:
            logging.info(
                "Replacing string in file: %s (mode: %s, count: %s)",
                file_path,
                mode,
                count,
            )

            # Read original content for diff
            original_content = FileUtils.read_file_content(file_path, mode, encoding)

            if mode == "binary":
                try:
                    old_bytes = base64.b64decode(old_string.encode("utf-8"))
                    new_bytes = base64.b64decode(new_string.encode("utf-8"))
                except (TypeError, ValueError) as e:
                    raise ValueError(f"Invalid base64 content for binary mode: {e}") from e
                old_string, new_string = old_bytes, new_bytes

            current_content = original_content

            if mode == "text":
                if not isinstance(old_string, str) or not isinstance(new_string, str):
                    raise ValueError("old_string and new_string must be strings in text mode")

                # Prevent empty string replacement which would corrupt the file
                if not old_string:
                    raise ValueError("old_string cannot be empty - this would insert new_string between every character")

                # Normalize line endings in search strings to match file content
                old_string_normalized = FileUtils.normalize_line_endings(old_string, "\n")
                new_string_normalized = FileUtils.normalize_line_endings(new_string, "\n")

                # Count occurrences before replacement
                occurrence_count = current_content.count(old_string_normalized)
                if occurrence_count == 0:
                    logging.info("No occurrences found of search string in %s", file_path)
                    return f"No changes made to '{file_path}': search string not found."

                # Perform replacement
                if count == 0:
                    new_content = current_content.replace(old_string_normalized, new_string_normalized)
                    actual_replacements = current_content.count(old_string_normalized)  # Count after replacement
                else:
                    new_content = current_content.replace(old_string_normalized, new_string_normalized, count)
                    actual_replacements = count

            elif mode == "binary":
                if not isinstance(old_string, bytes) or not isinstance(new_string, bytes):
                    raise ValueError("old_string and new_string must be bytes in binary mode")

                # Prevent empty bytes replacement which would corrupt the file
                if not old_string:
                    raise ValueError("old_string cannot be empty - this would insert new_string between every byte")

                occurrence_count = current_content.count(old_string)
                if occurrence_count == 0:
                    logging.info("No occurrences found of search bytes in %s", file_path)
                    return f"No changes made to '{file_path}': search bytes not found."

                if count == 0:
                    new_content = current_content.replace(old_string, new_string)
                    actual_replacements = current_content.count(old_string)  # Count after replacement
                else:
                    new_content = current_content.replace(old_string, new_string, count)
                    actual_replacements = count
            else:
                raise ValueError("Mode must be 'text' or 'binary'")

            if new_content == current_content:
                logging.info(
                    "No changes made to %s - content identical after replacement",
                    file_path,
                )
                return f"No changes made to '{file_path}': replacement resulted in identical content."

            FileUtils.write_file_content(file_path, new_content, mode, encoding)

            # Generate diff for text mode
            diff_output = ""
            if mode == "text":
                diff_output = FileUtils.generate_diff(original_content, new_content, file_path)

            logging.info(
                "Successfully replaced %s occurrences in %s",
                actual_replacements,
                file_path,
            )

            result_msg = f"Successfully replaced {actual_replacements} occurrence(s) in '{file_path}'."
            if diff_output:
                result_msg += f"\n\nDiff:\n{diff_output}"

            return result_msg

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
    ):
        """Replace content within a specified range of lines."""
        try:
            logging.info("Replacing lines %s-%s in file: %s", start_line, end_line, file_path)

            if start_line <= 0 or end_line <= 0:
                raise ValueError("Line numbers must be positive (1-based indexing)")

            if start_line > end_line:
                raise ValueError(f"Start line ({start_line}) must be less than or equal to end line ({end_line})")

            # Read original content for diff
            original_content = FileUtils.read_file_content(file_path, "text", encoding)
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

            FileUtils.write_file_content(file_path, new_content, "text", encoding)

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

            return result_msg

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to replace lines in file %s: %s", file_path, e)
            raise e

    def edit_file_delete_lines(self, file_path: str, start_line: int, end_line: int, encoding: str = "utf-8"):
        """Delete lines within a specified range."""
        try:
            logging.info("Deleting lines %s-%s in file: %s", start_line, end_line, file_path)

            if start_line <= 0 or end_line <= 0:
                raise ValueError("Line numbers must be positive (1-based indexing)")

            if start_line > end_line:
                raise ValueError(f"Start line ({start_line}) must be less than or equal to end line ({end_line})")

            # Read original content for diff
            original_content = FileUtils.read_file_content(file_path, "text", encoding)
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

            FileUtils.write_file_content(file_path, new_content, "text", encoding)

            # Generate diff
            diff_output = FileUtils.generate_diff(original_content, new_content, file_path)

            deleted_lines = end_line - start_line + 1
            remaining_lines = len(modified_lines)

            logging.info("Successfully deleted %s lines from %s", deleted_lines, file_path)

            result_msg = f"Successfully deleted lines {start_line}-{end_line} ({deleted_lines} lines) from '{file_path}'. File now has {remaining_lines} lines."
            if diff_output:
                result_msg += f"\n\nDiff:\n{diff_output}"

            return result_msg

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to delete lines from file %s: %s", file_path, e)
            raise e

    def edit_file_insert_lines(self, file_path: str, line_number: int, content: str, encoding: str = "utf-8"):
        """Insert content at a specified line number."""
        try:
            logging.info("Inserting content at line %s in file: %s", line_number, file_path)

            if line_number <= 0:
                raise ValueError("Line number must be positive (1-based indexing)")

            # Read original content for diff
            original_content = FileUtils.read_file_content(file_path, "text", encoding)
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

            FileUtils.write_file_content(file_path, new_content, "text", encoding)

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

            return result_msg

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to insert lines in file %s: %s", file_path, e)
            raise e

    def delete_files(self, file_paths: list):
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
                validated_path = FileUtils.validate_file_path(file_path)

                if not os.path.exists(validated_path):
                    errors.append(f"File not found: '{file_path}'")
                    continue

                if not os.path.isfile(validated_path):
                    errors.append(f"Path is not a file: '{file_path}'")
                    continue

                os.remove(validated_path)
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

        return f"Successfully deleted {len(deleted_files)} file(s): {', '.join(deleted_files)}"

    def move_files(self, source_paths: list, destination_paths: list, create_dirs: bool = True):
        """Move/rename files from source paths to destination paths."""
        if not isinstance(source_paths, list):
            raise ValueError("source_paths must be a list")

        if not isinstance(destination_paths, list):
            raise ValueError("destination_paths must be a list")

        if not source_paths:
            raise ValueError("source_paths list cannot be empty")

        if not destination_paths:
            raise ValueError("destination_paths list cannot be empty")

        if len(source_paths) != len(destination_paths):
            raise ValueError(f"Number of source paths ({len(source_paths)}) must match destination paths ({len(destination_paths)})")

        moved_files = []
        errors = []

        logging.info("Attempting to move %s file(s)", len(source_paths))

        for source_path, dest_path in zip(source_paths, destination_paths):
            try:
                validated_source = FileUtils.validate_file_path(source_path)
                validated_dest = FileUtils.validate_file_path(dest_path)

                # Check if source exists and is a file
                if not os.path.exists(validated_source):
                    errors.append(f"Source file not found: '{source_path}'")
                    continue

                if not os.path.isfile(validated_source):
                    errors.append(f"Source path is not a file: '{source_path}'")
                    continue

                # Create destination directory if requested and it doesn't exist
                dest_dir = os.path.dirname(validated_dest)
                if dest_dir and not os.path.exists(dest_dir):
                    if create_dirs:
                        try:
                            os.makedirs(dest_dir, exist_ok=True)
                            logging.info("Created destination directory: %s", dest_dir)
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            errors.append(f"Failed to create destination directory '{dest_dir}' for '{source_path}': {e}")
                            continue
                    else:
                        errors.append(f"Destination directory does not exist: '{dest_dir}' for '{source_path}'")
                        continue

                # Check if destination already exists
                if os.path.exists(validated_dest):
                    errors.append(f"Destination already exists: '{dest_path}' for source '{source_path}'")
                    continue

                # Check file size before moving (just for logging)
                try:
                    file_size = os.path.getsize(validated_source)
                except OSError:
                    file_size = 0

                # Perform the move operation
                shutil.move(validated_source, validated_dest)
                moved_files.append((source_path, dest_path))
                logging.info(
                    "Successfully moved file: %s -> %s (%s bytes)",
                    source_path,
                    dest_path,
                    file_size,
                )

            except PermissionError as e:
                errors.append(f"Permission denied moving file: '{source_path}' -> '{dest_path}': {e}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                errors.append(f"Error moving file '{source_path}' -> '{dest_path}': {e}")

        # Prepare result message
        if errors:
            error_msg = f"Some files could not be moved: {'; '.join(errors)}"
            if moved_files:
                moved_list = [f"{src} -> {dst}" for src, dst in moved_files]
                error_msg += f". Successfully moved: {', '.join(moved_list)}"

            logging.error(error_msg)
            raise Exception(error_msg) from None  # pylint: disable=raise-missing-from

        logging.info("Successfully moved all %s file(s)", len(moved_files))
        moved_list = [f"{src} -> {dst}" for src, dst in moved_files]
        return f"Successfully moved {len(moved_files)} file(s): {', '.join(moved_list)}"

    def create_directory(self, directory_path: str):
        """Create a directory and any necessary parent directories."""
        try:
            validated_path = FileUtils.validate_file_path(directory_path)

            if os.path.exists(validated_path):
                if os.path.isdir(validated_path):
                    logging.info("Directory already exists: %s", directory_path)
                    return f"Directory already exists: '{directory_path}'"
                raise ValueError(f"Path exists but is not a directory: '{directory_path}'")

            os.makedirs(validated_path, exist_ok=True)
            logging.info("Successfully created directory: %s", directory_path)
            return f"Successfully created directory: '{directory_path}'"

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

    def delete_directory(self, directory_path: str):
        """Delete a directory and all its contents."""
        try:
            validated_path = FileUtils.validate_file_path(directory_path)

            if not os.path.exists(validated_path):
                raise FileNotFoundError(f"Directory not found: '{directory_path}'")

            if not os.path.isdir(validated_path):
                raise ValueError(f"Path is not a directory: '{directory_path}'")

            # Count items before deletion for informative message
            item_count = sum(1 for _ in os.walk(validated_path))

            shutil.rmtree(validated_path)
            logging.info("Successfully deleted directory: %s", directory_path)
            return f"Successfully deleted directory '{directory_path}' and all its contents ({item_count} items)"

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
                response = {
                    "jsonrpc": "2.0",
                    "result": {"content": [{"type": "text", "text": str(result)}]},
                    "id": request_id,
                }
                self._send_response(response)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logging.error("Tool execution failed for %s: %s", tool_name, e, exc_info=True)
                self._send_error(f"Tool '{tool_name}' execution failed: {e}", request_id)
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
                    # If no line is received, it means no input is available.
                    # In a detached process, stdin might not be actively written to.
                    # We should not break, but rather continue to wait for input.
                    # Add a small sleep to prevent busy-waiting.
                    time.sleep(0.1)
                    continue

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
    try:
        server = LocalFiles()

        server.run()

    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Failed to start server: %s", e, exc_info=True)

        sys.exit(1)
