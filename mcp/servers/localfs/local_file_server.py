import argparse
import base64
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

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
            return content

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to read file %s: %s", file_path, e)
            raise e

    def _get_write_success_message(self, file_path: str, content: str | bytes, mode: str, original_content: str | bytes | None) -> dict:
        """Generates the success message for write_file, dispatching to specific handlers."""
        if mode == "binary":
            # MyPy knows content is bytes here due to the mode check
            message = FileUtils.get_write_success_message_binary(file_path, cast(bytes, content))
            return {"message": message, "diff": None}
        # MyPy knows content is str here due to the mode check
        # MyPy knows original_content is str | None here
        message, diff_output = FileUtils.get_write_success_message_text(file_path, cast(str, content), cast(str | None, original_content))
        return {"message": message, "diff": diff_output}

    def write_file(self, file_path: str, content: str | bytes, mode: str = "text", encoding: str = "utf-8") -> str:
        """Write content to a file."""
        try:
            logging.info("Writing file: %s (mode: %s, encoding: %s)", file_path, mode, encoding)

            if not file_path:
                raise ValueError("file_path cannot be empty")

            processed_content_raw = FileUtils.validate_and_decode_content(content, mode)
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
            return result_dict["message"]

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to write file %s: %s", file_path, e)
            raise e

    def edit_file_replace_string(
        self,
        file_path: str,
        old_string: str | bytes,
        new_string: str | bytes,
        mode: str = "text",
        encoding: str = "utf-8",
        count: int = 0,
    ) -> str:
        """Replace occurrences of old_string with new_string in a file."""
        try:
            logging.info(
                "Replacing string in file: %s (mode: %s, count: %s)",
                file_path,
                mode,
                count,
            )
            original_content = FileUtils.read_file_content(file_path, self.root_dir, mode, encoding)
            new_content: str | bytes
            actual_replacements: int

            new_content, actual_replacements = FileUtils.perform_replacement(original_content, old_string, new_string, mode, count)

            if actual_replacements == 0:
                logging.info(
                    "No changes made to %s - search string not found or no replacements occurred",
                    file_path,
                )
                return FileUtils.handle_no_replacements(file_path)

            if new_content == original_content:
                return FileUtils.handle_identical_content(file_path)

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

            return result_msg
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
    ) -> str:
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

            new_content = FileUtils.replace_lines(original_content, start_line, end_line, new_string)

            FileUtils.write_file_content(file_path, new_content, self.root_dir, "text", encoding)

            # Generate diff
            diff_output = FileUtils.generate_diff(original_content, new_content, file_path)

            replaced_lines = end_line - start_line + 1
            new_line_count = len(new_content.splitlines(keepends=True))

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

    def edit_file_delete_lines(self, file_path: str, start_line: int, end_line: int, encoding: str = "utf-8") -> str:
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

            new_content = FileUtils.delete_lines(original_content, start_line, end_line)

            FileUtils.write_file_content(file_path, new_content, self.root_dir, "text", encoding)

            # Generate diff
            diff_output = FileUtils.generate_diff(original_content, new_content, file_path)

            deleted_lines = end_line - start_line + 1
            remaining_lines = len(new_content.splitlines(keepends=True))

            logging.info("Successfully deleted %s lines from %s", deleted_lines, file_path)

            result_msg = f"Successfully deleted lines {start_line}-{end_line} ({deleted_lines} lines) from '{file_path}'. File now has {remaining_lines} lines."
            if diff_output:
                result_msg += f"\n\nDiff:\n{diff_output}"

            return result_msg

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to delete lines from file %s: %s", file_path, e)
            raise e

    def edit_file_insert_lines(self, file_path: str, line_number: int, content: str, encoding: str = "utf-8") -> str:
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

            new_content = FileUtils.insert_lines(original_content, line_number, content)

            FileUtils.write_file_content(file_path, new_content, self.root_dir, "text", encoding)

            # Generate diff
            diff_output = FileUtils.generate_diff(original_content, new_content, file_path)

            inserted_line_count = len(new_content.splitlines(keepends=True)) - len(original_content.splitlines(keepends=True)) + (line_number - 1)

            logging.info(
                "Successfully inserted %s lines at line %s in %s",
                inserted_line_count,
                line_number,
                file_path,
            )

            result_msg = f"Successfully inserted content at line {line_number} in '{file_path}'."
            if diff_output:
                result_msg += f"\n\nDiff:\n{diff_output}"

            return result_msg

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to insert lines in file %s: %s", file_path, e)
            raise e

    def delete_files(self, file_paths: list) -> dict:
        """Delete multiple files."""
        try:
            logging.info("Deleting files: %s", file_paths)
            result = FileUtils.delete_files(file_paths, self.root_dir)
            logging.info("Successfully deleted files: %s", file_paths)
            return result["message"]
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to delete files %s: %s", file_paths, e)
            raise e

    def move_files(self, source_paths: list, destination_paths: list, create_dirs: bool = True) -> dict:
        """Move/rename files from source paths to destination paths."""
        try:
            logging.info("Moving files: %s to %s", source_paths, destination_paths)
            result = FileUtils.move_files(source_paths, destination_paths, create_dirs, self.root_dir)
            logging.info("Successfully moved files: %s to %s", source_paths, destination_paths)
            return result["message"]
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to move files %s to %s: %s", source_paths, destination_paths, e)
            raise e

    def create_directory(self, directory_path: str) -> dict:
        """Create a directory and any necessary parent directories."""
        try:
            logging.info("Creating directory: %s", directory_path)
            result = FileUtils.create_directory(directory_path, self.root_dir)
            logging.info("Successfully created directory: %s", directory_path)
            return result["message"]
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to create directory %s: %s", directory_path, e)
            raise e

    def delete_directory(self, directory_path: str) -> dict:
        """Delete a directory and all its contents."""
        try:
            logging.info("Deleting directory: %s", directory_path)
            result = FileUtils.delete_directory(directory_path, self.root_dir)
            logging.info("Successfully deleted directory: %s", directory_path)
            return result["message"]
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to delete directory %s: %s", directory_path, e)
            raise e

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
                response = {
                    "jsonrpc": "2.0",
                    "result": {"content": [{"type": "text", "text": str(result)}]},
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
