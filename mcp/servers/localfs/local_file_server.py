import argparse
import base64
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

from orchestrator.mcp.servers.localfs.file_utils import FileUtils, OffsetType
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

    def read_file(self, path: str, start_offset_inclusive: int = 0, end_offset_inclusive: int = -1, offset_type: str = "BYTE") -> str:
        """Read content from a file with offset support."""
        try:
            offset_type_enum = OffsetType[offset_type.upper()]
            logging.info("Reading file: %s (offset_type: %s, start: %s, end: %s)", path, offset_type_enum.name, start_offset_inclusive, end_offset_inclusive)

            content = FileUtils.read_file_content(path, self.root_dir, start_offset_inclusive, end_offset_inclusive, offset_type_enum)

            if isinstance(content, bytes):
                encoded_content = base64.b64encode(content).decode("utf-8")
                logging.info(
                    "Successfully read binary file: %s (%s bytes)",
                    path,
                    len(content),
                )
                return encoded_content
            return content

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to read file %s: %s", path, e)
            raise e

    def _get_write_success_message(self, file_path: str, content: str | bytes, mode: str, original_content: str | bytes | None) -> dict:
        """Generates the success message for write_file, dispatching to specific handlers."""
        if mode == "binary":
            message = FileUtils.get_write_success_message_binary(file_path, cast(bytes, content))
            return {"message": message, "diff": None}
        message, diff_output = FileUtils.get_write_success_message_text(file_path, cast(str, content), cast(str | None, original_content))
        return {"message": message, "diff": diff_output}

    def write_file(self, path: str, new_content: str | bytes, mode: str = "text", encoding: str = "utf-8") -> str:
        """Write content to a file."""
        try:
            logging.info("Writing file: %s (mode: %s, encoding: %s)", path, mode, encoding)

            if not path:
                raise ValueError("path cannot be empty")

            processed_content_raw = FileUtils.validate_and_decode_content(new_content, mode)
            processed_content: str | bytes

            if mode == "binary":
                assert isinstance(processed_content_raw, bytes)
                processed_content = processed_content_raw
            else:  # mode == "text"
                assert isinstance(processed_content_raw, str)
                processed_content = processed_content_raw

            file_path_obj = Path(path)
            file_exists = file_path_obj.exists()
            original_content: str | bytes | None = None

            if file_exists:
                try:
                    read_content = FileUtils.read_file_content(
                        path, self.root_dir, offset_type=OffsetType.BYTE if mode == "binary" else OffsetType.CHAR, encoding=encoding
                    )
                    original_content = cast(bytes, read_content) if mode == "binary" else cast(str, read_content)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logging.warning("Could not read existing file for diff: %s", e)

            FileUtils.write_file_content(path, processed_content, self.root_dir, mode, encoding)
            result_dict = self._get_write_success_message(path, processed_content, mode, original_content)
            return result_dict["message"]

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to write file %s: %s", path, e)
            raise e

    def list_dir(self, path: str, limit: int = 100, recursive: bool = False) -> str:
        """Lists the names of files and subdirectories within a specified directory path."""
        try:
            logging.info("Listing directory: %s (limit: %s, recursive: %s)", path, limit, recursive)
            return FileUtils.list_directory_contents(path, self.root_dir, limit, recursive)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to list directory %s: %s", path, e)
            raise e

    def create_dirs(self, path: str) -> str:
        """Creates a directory and any necessary parent directories."""
        try:
            logging.info("Creating directory: %s", path)
            result = FileUtils.create_dirs(path, self.root_dir)
            return result["message"]
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to create directory %s: %s", path, e)
            raise e

    def find_paths(
        self, path: str, keywords_path_name: list[str] | None = None, kewords_file_content: list[str] | None = None, regex_keywords: bool = False
    ) -> list[str]:
        """Searches for files based on keywords in path/name or content."""
        try:
            logging.info(
                "Finding paths in %s (path_keywords: %s, content_keywords: %s, regex: %s)", path, keywords_path_name, kewords_file_content, regex_keywords
            )
            if keywords_path_name is None:
                keywords_path_name = []
            if kewords_file_content is None:
                kewords_file_content = []
            return FileUtils.find_files(path, self.root_dir, keywords_path_name, kewords_file_content, regex_keywords)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to find paths in %s: %s", path, e)
            raise e

    def delete_paths(self, paths: list[str]) -> str:
        """Delete multiple files or directories."""
        try:
            logging.info("Deleting paths: %s", paths)
            result = FileUtils.delete_paths(paths, self.root_dir)
            return result["message"]
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to delete paths %s: %s", paths, e)
            raise e

    def modify_file(self, path: str, start_offset_inclusive: int, end_offset_inclusive: int, offset_type: str, new_content: str | bytes) -> str:
        """Modifies a file by replacing a range of content with new content."""
        try:
            offset_type_enum = OffsetType[offset_type.upper()]
            logging.info("Modifying file %s (offset_type: %s, start: %s, end: %s)", path, offset_type_enum.name, start_offset_inclusive, end_offset_inclusive)
            return FileUtils.modify_file(path, self.root_dir, start_offset_inclusive, end_offset_inclusive, offset_type_enum, new_content)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to modify file %s: %s", path, e)
            raise e

    def replace_content_in_file(self, path: str, old_content: str | bytes, new_content: str | bytes, number_of_occurrences: int = -1) -> str:
        """Replaces all occurrences of old_content with new_content within a file."""
        try:
            logging.info("Replacing content in file %s", path)
            return FileUtils.replace_content_in_file(path, self.root_dir, old_content, new_content, number_of_occurrences)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to replace content in file %s: %s", path, e)
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
                response = {
                    "jsonrpc": "2.0",
                    "result": {"content": [{"type": "text", "text": str(result)}]},
                    "id": request_id,
                }
                self._send_response(response)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logging.error("Tool execution failed for %s: %s", tool_name, e, exc_info=True)
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
