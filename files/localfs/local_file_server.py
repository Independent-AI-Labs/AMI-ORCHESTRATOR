import argparse
import base64
import io
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import cast
import subprocess
import tempfile
import shutil

from orchestrator.core.process_manager import ProcessManager
from orchestrator.mcp.servers.localfs.file_utils import (FileUtils, InputFormat, OffsetType, OutputFormat)
from orchestrator.mcp.servers.localfs.tool_definitions import get_tool_declarations
from orchestrator.mcp.exceptions import MCPError


class LocalFiles:
    """Provides file manipulation tools via the MCP protocol."""

    def __init__(self, root_dir: str):
        self.tools = {tool_decl["name"]: getattr(self, tool_decl["name"]) for tool_decl in get_tool_declarations()}
        self.root_dir = root_dir
        self._running = False

        # Create a /logs directory in the project root if it doesn't exist
        logs_dir = Path(self.root_dir) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate a unique log file name with a timestamp
        log_file = logs_dir / f"mcp_server_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format="[%(asctime)s] [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s]",
        )
        self.logger = logging.getLogger(__name__)
        self.file_types = self._load_file_types()

        # Ensure logging is configured to a file for debugging hangs
        if not logging.root.handlers:
            logs_dir = Path(self.root_dir) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / f"mcp_server_debug_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
            logging.basicConfig(
                filename=log_file,
                level=logging.DEBUG,
                format="[%(asctime)s] [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s]",
            )

        # Ensure logging is configured to a file for debugging hangs
        if not logging.root.handlers:
            logs_dir = Path(self.root_dir) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / f"mcp_server_debug_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
            logging.basicConfig(
                filename=log_file,
                level=logging.DEBUG,
                format="[%(asctime)s] [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s]",
            )

    def _load_file_types(self) -> dict:
        file_types_path = Path(__file__).parent / "file_types.csv"
        file_types = {}
        try:
            with open(file_types_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    return file_types
                
                # Assuming the first line is the header
                header = lines[0].strip().split(',')
                
                for line in lines[1:]:
                    parts = line.strip().split(',')
                    if len(parts) == len(header):
                        entry = {header[i].strip('"'): parts[i].strip('"') for i in range(len(header))}
                        extension = entry.get('extension')
                        if extension:
                            file_types[extension] = {
                                "type": entry.get('type'),
                                "description": entry.get('description'),
                                "mime_type": entry.get('mime_type'),
                                "validation_command": entry.get('validation_command')
                            }
        except FileNotFoundError:
            self.logger.error(f"file_types.csv not found at {file_types_path}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Error loading file_types.csv: {e}")
        return file_types

    def _send_response(self, response, stdout):
        """Send a JSON-RPC response to the given stream."""
        try:
            response_str = json.dumps(response) + "\n"
            stdout.write(response_str.encode("utf-8"))
            stdout.flush()
            self.logger.debug("Response sent successfully: %s. Raw response: %s", response.get("id", "unknown"), response_str)
        except Exception as e:
            self.logger.error("Failed to send response: %s", e)

    def _send_error(self, message, request_id=None, code=-32602, stdout=None):
        """Send a JSON-RPC error response."""
        stdout = stdout or sys.stdout.buffer
        self.logger.error("Error response: %s (request_id: %s)", message, request_id)
        
        # Ensure message is a string, even if it's an exception object
        error_message = str(message)
        
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": error_message},
        }
        if request_id:
            error_response["id"] = request_id
        self._send_response(error_response, stdout)

    def _validate_file(self, file_path: str) -> tuple[bool, str]:
        self.logger.info(f"Validating file: {file_path}")
        file_extension = Path(file_path).suffix
        file_type_info = self.file_types.get(file_extension)

        if not (file_type_info and file_type_info.get("validation_command") and file_type_info["validation_command"] != "none"):
            self.logger.info(f"No validation command specified or found for {file_path}.")
            return True, "No validation command specified or found."

        if not FileUtils.is_text_file(Path(file_path)):
            self.logger.info(f"Skipping text-based validation for non-text file: {file_path}")
            return True, "Skipped validation for binary file."

        # Ensure the file path is quoted for shell safety
        quoted_file_path = f'"{str(Path(file_path).resolve())}"'
        validation_command_str = file_type_info["validation_command"].replace("<file>", quoted_file_path)

        try:
            process_manager = ProcessManager(self.root_dir)
            result = process_manager.execute(validation_command_str, timeout=1)

            output = (result.stdout + result.stderr).strip()

            if result.timed_out:
                self.logger.error(f"Validation command '{validation_command_str}' timed out for {file_path}.")
                return False, "Validation command timed out after 15 seconds."

            if result.return_code == 0:
                self.logger.info(f"Validation command '{validation_command_str}' succeeded for {file_path}. Output: {output or 'No issues found.'}")
                return True, output or "No issues found."
            
            self.logger.error(f"Validation command '{validation_command_str}' failed for {file_path} with exit code {result.return_code}. Error: {output}")
            return False, output

        except FileNotFoundError:
            # This is unlikely to be caught now with shell=True, but kept for safety
            self.logger.warning(f"Validation command not found: {validation_command_str}")
            return True, f"Validation command not found: {validation_command_str}"
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during validation for {file_path}: {e}", exc_info=True)
            return False, f"An unexpected error occurred during validation: {e}"

    def _filter_tool_arguments(self, tool_name: str, tool_args: dict) -> dict:
        """Filter tool arguments to only include expected parameters."""
        tool_declarations = get_tool_declarations()
        expected_params: set[str] = set()
        for tool_decl in tool_declarations:
            if tool_decl["name"] == tool_name:
                expected_params = set(tool_decl["inputSchema"]["properties"].keys())
                break

        if not expected_params:
            self.logger.info(f"_filter_tool_arguments: No expected parameters for {tool_name}. Returning original args: {tool_args}")
            return tool_args

        self.logger.info(f"_filter_tool_arguments: Original arguments for {tool_name}: {tool_args}")
        filtered_args = {k: v for k, v in tool_args.items() if k in expected_params}
        return filtered_args

    def read_from_file(
        self,
        path: str,
        start_offset_inclusive: int = 0,
        end_offset_inclusive: int = -1,
        offset_type: str = "line",
        file_encoding: str = "utf-8",
        output_format: str = "raw_utf8",
    ) -> str | bytes:
        """Read content from a file with offset support."""
        try:
            self.logger.info(f"Attempting to read file: {path}")
            self.logger.info(f"Raw output_format: {output_format}")
            
            # Determine if the file is binary to force BYTE offset type
            is_binary = not FileUtils.is_text_file(Path(path))
            
            if is_binary:
                offset_type_enum = OffsetType.BYTE
                self.logger.info(f"File is binary, forcing offset_type to BYTE.")
            else:
                offset_type_enum = OffsetType[offset_type.upper()]
                self.logger.info(f"Offset type enum: {offset_type_enum.name}")

            output_format_upper = output_format.upper()
            self.logger.info(f"output_format.upper(): {output_format_upper}")
            output_format_enum = OutputFormat[output_format.replace('-', '_').upper()]
            self.logger.info(f"Output format enum: {output_format_enum.name}")

            self.logger.info(
                "Reading file: %s (offset_type: %s, start: %s, end: %s, file_encoding: %s, output_format: %s)",
                path,
                offset_type_enum.name,
                start_offset_inclusive,
                end_offset_inclusive,
                file_encoding,
                output_format_enum.name,
            )

            content = FileUtils.read_file_content(
                path, self.root_dir, start_offset_inclusive, end_offset_inclusive, offset_type_enum, file_encoding, output_format_enum
            )

            # If RAW_UTF8 is requested, return the content as is (str for text, bytes for binary)
            if output_format_enum == OutputFormat.RAW_UTF8:
                self.logger.info("Returning raw UTF-8 content.")
                return content
            
            # For other output formats (QP, BASE64), content from FileUtils.read_file_content will be str (encoded)
            # or bytes (for binary files when QP/BASE64 is requested, which then needs to be decoded to ascii string)
            if isinstance(content, bytes):
                self.logger.info("Content is bytes, decoding to ascii.")
                return content.decode("ascii") # Should be ascii for QP or Base64
            self.logger.info("Returning content as string.")
            return content # This handles str content for QP or Base64

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to read file %s: %s (Type: %s)", path, e, type(e))
            raise e

    def _get_write_success_message(self, file_path: str, content: str | bytes, mode: str, original_content: str | bytes | None) -> dict:
        """Generates the success message for write_file, dispatching to specific handlers."""
        if mode == "binary":
            message = FileUtils.get_write_success_message_binary(file_path, cast(bytes, content))
            return {"message": message, "diff": None}
        message, diff_output = FileUtils.get_write_success_message_text(file_path, cast(str, content), cast(str | None, original_content))
        return {"message": message, "diff": diff_output}

    def write_to_file(self, path: str, new_content: str | bytes, mode: str = "text", input_format: str = "raw_utf8", file_encoding: str = "utf-8") -> str:
        """Write content to a file."""
        try:
            input_format_enum = InputFormat[input_format.upper()]
            self.logger.info("Writing file: %s (mode: %s, input_format: %s, file_encoding: %s)", path, mode, input_format_enum.name, file_encoding)

            if not path:
                raise ValueError("path cannot be empty")

            processed_content_raw = FileUtils.validate_and_decode_content(new_content, mode, input_format_enum)
            processed_content: str | bytes

            if mode == "binary":
                processed_content = cast(bytes, processed_content_raw)
            else:  # mode == "text"
                processed_content = cast(str, processed_content_raw)

            file_path_obj = Path(path)
            file_exists = file_path_obj.exists()
            original_content: str | bytes | None = None

            if file_exists:
                try:
                    read_content = FileUtils.read_file_content(
                        path,
                        self.root_dir,
                        offset_type=OffsetType.BYTE,
                        output_format=OutputFormat.RAW_UTF8,  # Read raw for diffing
                    )
                    if mode == "binary":
                        # If original file is binary, read_file_content with RAW_UTF8 returns bytes. Decode it.
                        original_content = read_content
                    else:
                        original_content = read_content
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.warning("Could not read existing file for diff: %s", e)

            # Create a temporary file to write content to and validate within the root_dir
            tmp_file_name = f"temp_write_{Path(path).name}"
            tmp_file_path = Path(self.root_dir) / tmp_file_name
            with open(tmp_file_path, "w+" if mode == "text" else "wb+", encoding=file_encoding if mode == "text" else None) as tmp_file:
                tmp_file.write(processed_content)

            try:
                # Validate the temporary file
                is_valid, validation_output = self._validate_file(str(tmp_file_path))
                if not is_valid:
                    raise ValueError(f"Validation failed for temporary file {tmp_file_path}. Original file {path} remains unchanged. Validator output: {validation_output}")

                # If validation passes, overwrite the original file with the temporary file's content
                shutil.copy2(tmp_file_path, Path(self.root_dir) / path)
                
                result_dict = self._get_write_success_message(path, processed_content, mode, cast(str | bytes | None, original_content))
                return result_dict["message"]
            finally:
                # Clean up the temporary file
                tmp_file_path.unlink(missing_ok=True)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to write file %s: %s", path, e)
            raise e

    def list_dir(self, path: str, limit: int = 100, recursive: bool = False) -> str:
        """Lists the names of files and subdirectories within a specified directory path."""
        try:
            self.logger.info("Listing directory: %s (limit: %s, recursive: %s)", path, limit, recursive)
            return FileUtils.list_directory_contents(path, self.root_dir, limit, recursive)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to list directory %s: %s", path, e)
            raise e

    def create_dirs(self, path: str) -> str:
        """Creates a directory and any necessary parent directories."""
        try:
            self.logger.info("Creating directory: %s", path)
            result = FileUtils.create_dirs(path, self.root_dir)
            return result["message"]
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to create directory %s: %s", path, e)
            raise e

    def find_paths(
        self, path: str, keywords_path_name: list[str] | None = None, kewords_file_content: list[str] | None = None, regex_keywords: bool = False
    ) -> list[str]:
        """Searches for files based on keywords in path/name or content."""
        try:
            self.logger.info(
                "Finding paths in %s (path_keywords: %s, content_keywords: %s, regex: %s)", path, keywords_path_name, kewords_file_content, regex_keywords
            )
            if keywords_path_name is None:
                keywords_path_name = []
            if kewords_file_content is None:
                kewords_file_content = []
            return FileUtils.find_files(path, self.root_dir, keywords_path_name, kewords_file_content, regex_keywords)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to find paths in %s: %s", path, e)
            raise e

    def delete_paths(self, paths: list[str]) -> str:
        """Delete multiple files or directories."""
        try:
            self.logger.info("Deleting paths: %s", paths)
            result = FileUtils.delete_paths(paths, self.root_dir)
            return result["message"]
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to delete paths %s: %s", paths, e)
            raise e

    def modify_file(
        self,
        path: str,
        start_offset_inclusive: int,
        end_offset_inclusive: int,
        new_content: str | bytes,
        offset_type: str = "line",
        input_format: str = "raw_utf8",
        file_encoding: str = "utf-8",
        mode: str = "text",
    ) -> str:
        """Modifies a file by replacing a range of content with new content."""
        try:
            offset_type_enum = OffsetType[offset_type.upper()]
            input_format_enum = InputFormat[input_format.upper()]
            self.logger.info(
                "Modifying file %s (offset_type: %s, start: %s, end: %s, input_format: %s, file_encoding: %s, mode: %s)",
                path,
                offset_type_enum.name,
                start_offset_inclusive,
                end_offset_inclusive,
                input_format_enum.name,
                file_encoding,
                mode,
            )
            self.logger.info(f"New content type: {type(new_content)}")

            original_content: str | bytes | None = None
            file_exists = Path(path).exists()

            if file_exists:
                try:
                    original_content = FileUtils.read_file_content(
                        path, self.root_dir, offset_type=OffsetType.BYTE, output_format=OutputFormat.RAW_UTF8
                    )
                    self.logger.info(f"Original content type: {type(original_content)}")
                except Exception as e:
                    self.logger.warning(f"Could not read original file content for modification: {e}")

            # Create a temporary file to write content to and validate within the root_dir
            tmp_file_name = f"temp_modify_{Path(path).name}"
            tmp_file_path = Path(self.root_dir) / tmp_file_name
            
            # Determine mode for opening temporary file
            open_mode = "w+" if mode == "text" else "wb+"
            
            with open(tmp_file_path, open_mode, encoding=file_encoding if mode == "text" else None) as tmp_file:
                if original_content is not None:
                    if mode == "text":
                        # Ensure original_content is str for text mode
                        content_to_write = cast(str, original_content) if isinstance(original_content, str) else original_content.decode(file_encoding)
                        tmp_file.write(content_to_write)
                    else:
                        # Ensure original_content is bytes for binary mode
                        content_to_write = cast(bytes, original_content) if isinstance(original_content, bytes) else original_content
                        tmp_file.write(content_to_write)

            try:
                # Apply modification to the temporary file
                self.logger.info(f"Calling FileUtils.modify_file with: tmp_file_path={str(tmp_file_path)}, root_dir={self.root_dir}, start_offset_inclusive={start_offset_inclusive}, end_offset_inclusive={end_offset_inclusive}, offset_type_enum={offset_type_enum}, new_content_type={type(new_content)}, input_format_enum={input_format_enum}, file_encoding={file_encoding}, mode={mode}")
                FileUtils.modify_file(
                    str(tmp_file_path), self.root_dir, start_offset_inclusive, end_offset_inclusive, offset_type_enum, new_content, input_format_enum, file_encoding, mode
                )

                # Validate the temporary file
                is_valid, validation_output = self._validate_file(str(tmp_file_path))
                if not is_valid:
                    raise ValueError(f"Validation failed for temporary file {tmp_file_path}. Original file {path} remains unchanged. Validator output: {validation_output}")

                # If validation passes, overwrite the original file with the temporary file's content
                shutil.copy2(tmp_file_path, Path(self.root_dir) / path)
                return f"File {path} modified successfully."
            finally:
                # Clean up the temporary file
                tmp_file_path.unlink(missing_ok=True)

        except ValueError as e:
            self.logger.error("Failed to modify file %s: %s (Type: %s)", path, e, type(e))
            # Re-raise as MCPError for consistency with client expectations
            raise MCPError(f"Path outside root directory: {e}") from e
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to modify file %s: %s (Type: %s)", path, e, type(e))
            raise e

    def replace_in_file(
        self,
        path: str,
        old_content: str | bytes,
        new_content: str | bytes,
        number_of_occurrences: int = -1,
        is_regex: bool = False,
        mode: str = "text",
        input_format: str = "raw_utf8",
        file_encoding: str = "utf-8",
    ) -> str:
        """Replaces all occurrences of old_content with new_content within a file."""
        try:
            input_format_enum = InputFormat[input_format.upper()]
            logging.info("Replacing content in file %s (input_format: %s, file_encoding: %s)", path, input_format_enum.name, file_encoding)

            original_content: str | bytes | None = None
            file_exists = Path(path).exists()

            if file_exists:
                try:
                    read_content = FileUtils.read_file_content(
                        path, self.root_dir, offset_type=OffsetType.BYTE, output_format=OutputFormat.RAW_UTF8
                    )
                    if mode == "binary":
                        original_content = base64.b64decode(read_content.encode("ascii"))
                    else:
                        original_content = read_content
                except Exception as e:
                    logging.warning(f"Could not read original file content for replacement: {e}")

            # Create a temporary file with the original content within the root_dir
            tmp_file_name = f"temp_replace_{Path(path).name}"
            tmp_file_path = Path(self.root_dir) / tmp_file_name

            # Determine mode for opening temporary file
            open_mode = "w+" if mode == "text" else "wb+"

            with open(tmp_file_path, open_mode, encoding=file_encoding if mode == "text" else None) as tmp_file:
                if original_content is not None:
                    if mode == "text":
                        # Ensure original_content is str for text mode
                        content_to_write = cast(str, original_content) if isinstance(original_content, str) else original_content.decode(file_encoding)
                        tmp_file.write(content_to_write)
                    else:
                        # Ensure original_content is bytes for binary mode
                        content_to_write = cast(bytes, original_content) if isinstance(original_content, bytes) else original_content.encode(file_encoding)
                        tmp_file.write(content_to_write)

            try:
                # Apply replacement to the temporary file
                FileUtils.replace_in_file(
                    str(tmp_file_path), self.root_dir, old_content, new_content, number_of_occurrences, is_regex, mode, input_format_enum, file_encoding
                )

                # Validate the temporary file
                is_valid, validation_output = self._validate_file(str(tmp_file_path))
                if not is_valid:
                    raise ValueError(f"Validation failed for temporary file {tmp_file_path}. Original file {path} remains unchanged. Validator output: {validation_output}")

                # If validation passes, overwrite the original file with the temporary file's content
                shutil.copy2(tmp_file_path, Path(self.root_dir) / path)
                return f"Content replaced in {path} successfully."
            finally:
                # Clean up the temporary file
                tmp_file_path.unlink(missing_ok=True)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to replace content in file %s: %s", path, e)
            raise e

    def _handle_request(self, line_str, stdout):
        """Handle a single JSON-RPC request."""
        try:
            request = json.loads(line_str)
        except json.JSONDecodeError as e:
            self._send_error(f"Invalid JSON in request: {e}", stdout=stdout)
            return

        request_id = request.get("id")
        method = request.get("method")
        self.logger.debug("Processing method: %s, ID: %s", method, request_id)

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
            self._send_response(response, stdout)
            return
        if method == "notifications/initialized":
            self.logger.info("Client initialization complete")
            # This is a notification, no response needed, but we can log it.
            return

        if method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "result": {"tools": get_tool_declarations()},
                "id": request_id,
            }
            self._send_response(response, stdout)
            return

        if method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name not in self.tools:
                self._send_error(
                    f"Unknown tool: '{tool_name}'. Available tools: {list(self.tools.keys())}",
                    request_id,
                    stdout=stdout
                )
                return

            try:
                self.logger.info("Executing tool: %s", tool_name)
                filtered_args = self._filter_tool_arguments(tool_name, tool_args)
                result = self.tools[tool_name](**filtered_args)
                response = {
                    "jsonrpc": "2.0",
                    "result": {"content": [{"type": "text", "text": str(result)}]},
                    "id": request_id
                }
                self._send_response(response, stdout)
            except Exception as e:
                self.logger.error("Tool execution failed for %s: %s", tool_name, e, exc_info=True)
                if isinstance(e, (ValueError, PermissionError, FileNotFoundError)):
                    self._send_error(f"Tool '{tool_name}' execution failed: {e}", request_id, stdout=stdout)
                else:
                    self._send_error(f"Internal server error during tool '{tool_name}' execution: {e}", request_id, stdout=stdout)
            return

        self._send_error(
            f"Unknown method: '{method}'. Supported methods: initialize, tools/list, tools/call",
            request_id,
            stdout=stdout
        )

    def stop(self):
        """Stops the server loop."""
        self.logger.info("Received stop signal. Shutting down server.")
        self._running = False

    def run(self, stdin=None, stdout=None):
        """Main server loop to handle JSON-RPC requests."""
        self._running = True
        # If no streams are provided, use system stdin/stdout
        stdin = stdin or sys.stdin.buffer
        stdout = stdout or sys.stdout.buffer

        self.logger.info("MCP File Manipulation Server started")
        # A simple print for test synchronization
        print("SERVER_STARTED_DEBUG_MESSAGE", file=sys.stderr)
        sys.stderr.flush()

        while self._running:
            try:
                # Use a non-blocking read with a timeout to keep the loop responsive
                # This is a conceptual change; actual implementation depends on stream type.
                # For testing with BytesIO, we can just read. For real stdin, this would need select/poll.
                line = stdin.readline()
                if not line:
                    # If stdin is a BytesIO stream and we get an empty line, it means EOF.
                    # For real streams, this might mean no data yet, so we sleep to avoid busy-waiting.
                    if isinstance(stdin, io.BytesIO):
                        self.logger.info("EOF received on stdin. Shutting down server.")
                        self._running = False
                        break
                    else:
                        time.sleep(0.1) # Avoid busy-waiting on real streams
                        continue

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                self.logger.debug("Received request: %s", line_str)
                self._handle_request(line_str, stdout)

            except (KeyboardInterrupt, SystemExit):
                self.logger.info("Server interrupted.")
                self._running = False
                break
            except Exception as e:
                self.logger.error("Unexpected server error: %s", e, exc_info=True)
                try:
                    self._send_error(f"Internal server error: {e}", stdout=stdout)
                except Exception as send_error:
                    self.logger.error("Failed to send error response: %s", send_error)
        self.logger.info("MCP File Manipulation Server has shut down.")


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
