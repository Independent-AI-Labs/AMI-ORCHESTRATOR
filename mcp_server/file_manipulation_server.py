import base64
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Create a /logs directory in the project root if it doesn't exist
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
os.makedirs(LOGS_DIR, exist_ok=True)

# Generate a unique log file name with a timestamp
LOG_FILE = os.path.join(LOGS_DIR, f"mcp_server_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s'
)


class FileManipulationServer:
    def __init__(self):
        self.tools = {
            "write_file": self.write_file,
            "edit_file_replace_string": self.edit_file_replace_string,
            "edit_file_replace_lines": self.edit_file_replace_lines,
            "delete_files": self.delete_files,
            "create_directory": self.create_directory,
            "delete_directory": self.delete_directory,
        }
        self.max_file_size = 100 * 1024 * 1024  # 100MB limit

    def _send_response(self, response):
        """Send a JSON-RPC response to stdout."""
        try:
            response_str = json.dumps(response) + '\n'
            sys.stdout.buffer.write(response_str.encode('utf-8'))
            sys.stdout.buffer.flush()
            logging.info(f"Response sent successfully: {response.get('id', 'unknown')}")
        except Exception as e:
            logging.error(f"Failed to send response: {e}")

    def _send_error(self, message, request_id=None, code=-32602):
        """Send a JSON-RPC error response and raise an exception."""
        logging.error(f"Error response: {message} (request_id: {request_id})")
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": str(message)
            }
        }
        if request_id:
            error_response["id"] = request_id
        self._send_response(error_response)
        raise Exception(message)

    def _validate_file_path(self, file_path: str) -> str:
        """Validate and normalize file path for security."""
        try:
            # Convert to Path object and resolve
            path_obj = Path(file_path).resolve()

            # Basic security check - prevent directory traversal attacks
            if '..' in str(path_obj):
                raise ValueError(f"Invalid file path: directory traversal not allowed")

            return str(path_obj)
        except Exception as e:
            raise ValueError(f"Invalid file path '{file_path}': {e}")

    def _check_file_size(self, file_path: str):
        """Check if file size is within limits."""
        try:
            size = os.path.getsize(file_path)
            if size > self.max_file_size:
                raise ValueError(f"File too large: {size} bytes (max: {self.max_file_size} bytes)")
        except OSError:
            pass  # File doesn't exist yet, which is fine for write operations

    def _normalize_line_endings(self, content: str, target_format: str = '\n') -> str:
        """Normalize line endings in text content."""
        # Replace all variations of line endings with the target format
        return re.sub(r'\r\n|\r|\n', target_format, content)

    def _read_file_content(self, file_path: str, mode: str = 'text', encoding: str = 'utf-8'):
        """Read file content with proper error handling and normalization."""
        validated_path = self._validate_file_path(file_path)

        if not os.path.exists(validated_path):
            raise FileNotFoundError(f"File not found: '{validated_path}'. Please check the path and ensure the file exists.")

        if not os.path.isfile(validated_path):
            raise ValueError(f"Path exists but is not a file: '{validated_path}'")

        self._check_file_size(validated_path)

        try:
            if mode == 'binary':
                with open(validated_path, 'rb') as f:
                    return f.read()
            else:
                with open(validated_path, 'r', encoding=encoding) as f:
                    content = f.read()
                # Normalize line endings to \n for consistent processing
                return self._normalize_line_endings(content, '\n')

        except UnicodeDecodeError as e:
            raise ValueError(
                f"Cannot decode file '{validated_path}' with encoding '{encoding}'. "
                f"Error: {e}. Try using a different encoding or 'binary' mode."
            )
        except PermissionError:
            raise PermissionError(f"Permission denied: cannot read file '{validated_path}'")
        except Exception as e:
            raise Exception(f"Unexpected error reading file '{validated_path}': {e}")

    def _write_file_content(self, file_path: str, content, mode: str = 'text', encoding: str = 'utf-8'):
        """Write file content with proper error handling."""
        validated_path = self._validate_file_path(file_path)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(validated_path), exist_ok=True)

        try:
            if mode == 'binary':
                with open(validated_path, 'wb') as f:
                    f.write(content)
            else:
                with open(validated_path, 'w', encoding=encoding) as f:
                    f.write(content)

        except PermissionError:
            raise PermissionError(f"Permission denied: cannot write to file '{validated_path}'")
        except OSError as e:
            if e.errno == 28:  # No space left on device
                raise OSError(f"No space left on device when writing to '{validated_path}'")
            else:
                raise OSError(f"OS error writing to file '{validated_path}': {e}")
        except Exception as e:
            raise Exception(f"Unexpected error writing to file '{validated_path}': {e}")

    def read_file(self, file_path: str, mode: str = 'text', encoding: str = 'utf-8'):
        """Read content from a file."""
        try:
            logging.info(f"Reading file: {file_path} (mode: {mode}, encoding: {encoding})")
            content = self._read_file_content(file_path, mode, encoding)

            if mode == 'binary':
                # Return base64 encoded content for binary files
                encoded_content = base64.b64encode(content).decode('utf-8')
                logging.info(f"Successfully read binary file: {file_path} ({len(content)} bytes)")
                return encoded_content
            else:
                logging.info(f"Successfully read text file: {file_path} ({len(content)} characters, {content.count(chr(10))} lines)")
                return content

        except Exception as e:
            logging.error(f"Failed to read file {file_path}: {e}")
            raise Exception(f"Read operation failed: {e}")

    def write_file(self, file_path: str, content, mode: str = 'text', encoding: str = 'utf-8'):
        """Write content to a file."""
        try:
            logging.info(f"Writing file: {file_path} (mode: {mode}, encoding: {encoding})")

            if mode == 'binary':
                try:
                    decoded_content = base64.b64decode(content.encode('utf-8'))
                    logging.info(f"Decoded base64 content: {len(decoded_content)} bytes")
                except Exception as e:
                    raise ValueError(f"Invalid base64 content for binary mode: {e}")
                content = decoded_content

            self._write_file_content(file_path, content, mode, encoding)

            # Log success with content info
            if mode == 'binary':
                logging.info(f"Successfully wrote binary file: {file_path} ({len(content)} bytes)")
                return f"Successfully wrote binary content to '{file_path}' ({len(content)} bytes)."
            else:
                line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
                logging.info(f"Successfully wrote text file: {file_path} ({len(content)} characters, {line_count} lines)")
                return f"Successfully wrote text content to '{file_path}' ({len(content)} characters, {line_count} lines)."

        except Exception as e:
            logging.error(f"Failed to write file {file_path}: {e}")
            raise Exception(f"Write operation failed: {e}")

    def edit_file_replace_string(self, file_path: str, old_string, new_string, mode: str = 'text', encoding: str = 'utf-8', count: int = 0):
        """Replace occurrences of old_string with new_string in a file."""
        try:
            logging.info(f"Replacing string in file: {file_path} (mode: {mode}, count: {count})")

            if mode == 'binary':
                try:
                    old_bytes = base64.b64decode(old_string.encode('utf-8'))
                    new_bytes = base64.b64decode(new_string.encode('utf-8'))
                except Exception as e:
                    raise ValueError(f"Invalid base64 content for binary mode: {e}")
                old_string, new_string = old_bytes, new_bytes

            current_content = self._read_file_content(file_path, mode, encoding)

            if mode == 'text':
                if not isinstance(old_string, str) or not isinstance(new_string, str):
                    raise ValueError("old_string and new_string must be strings in text mode")

                # Normalize line endings in search strings to match file content
                old_string = self._normalize_line_endings(old_string, '\n')
                new_string = self._normalize_line_endings(new_string, '\n')

                # Count occurrences before replacement
                occurrence_count = current_content.count(old_string)
                if occurrence_count == 0:
                    logging.info(f"No occurrences found of search string in {file_path}")
                    return f"No changes made to '{file_path}': search string not found."

                # Perform replacement
                if count == 0:
                    new_content = current_content.replace(old_string, new_string)
                    actual_replacements = occurrence_count
                else:
                    new_content = current_content.replace(old_string, new_string, count)
                    actual_replacements = min(count, occurrence_count)

            elif mode == 'binary':
                if not isinstance(old_string, bytes) or not isinstance(new_string, bytes):
                    raise ValueError("old_string and new_string must be bytes in binary mode")

                occurrence_count = current_content.count(old_string)
                if occurrence_count == 0:
                    logging.info(f"No occurrences found of search bytes in {file_path}")
                    return f"No changes made to '{file_path}': search bytes not found."

                if count == 0:
                    new_content = current_content.replace(old_string, new_string)
                    actual_replacements = occurrence_count
                else:
                    new_content = current_content.replace(old_string, new_string, count)
                    actual_replacements = min(count, occurrence_count)
            else:
                raise ValueError("Mode must be 'text' or 'binary'")

            if new_content == current_content:
                logging.info(f"No changes made to {file_path} - content identical after replacement")
                return f"No changes made to '{file_path}': replacement resulted in identical content."

            self._write_file_content(file_path, new_content, mode, encoding)

            logging.info(f"Successfully replaced {actual_replacements} occurrences in {file_path}")
            return f"Successfully replaced {actual_replacements} occurrence(s) in '{file_path}'."

        except Exception as e:
            logging.error(f"Failed to replace string in file {file_path}: {e}")
            raise Exception(f"String replacement failed: {e}")

    def edit_file_replace_lines(self, file_path: str, start_line: int, end_line: int, new_string: str, encoding: str = 'utf-8'):
        """Replace content within a specified range of lines."""
        try:
            logging.info(f"Replacing lines {start_line}-{end_line} in file: {file_path}")

            if start_line <= 0 or end_line <= 0:
                raise ValueError("Line numbers must be positive (1-based indexing)")

            if start_line > end_line:
                raise ValueError(f"Start line ({start_line}) must be less than or equal to end line ({end_line})")

            content = self._read_file_content(file_path, 'text', encoding)
            lines = content.splitlines(keepends=True)
            total_lines = len(lines)

            if start_line > total_lines:
                raise ValueError(f"Start line {start_line} exceeds file length ({total_lines} lines)")

            if end_line > total_lines:
                raise ValueError(f"End line {end_line} exceeds file length ({total_lines} lines)")

            # Convert to 0-based indexing
            start_idx = start_line - 1
            end_idx = end_line

            # Normalize the new string's line endings
            new_string = self._normalize_line_endings(new_string, '\n')

            # Prepare replacement lines
            if new_string == '':
                new_lines = []
            else:
                new_lines = new_string.splitlines(keepends=True)

                # Handle the case where new_string doesn't end with newline
                # but we're replacing complete lines that do end with newlines
                if new_lines and not new_string.endswith('\n'):
                    # Check if we're replacing lines that end with newline
                    if end_idx <= len(lines) and any(line.endswith('\n') for line in lines[start_idx:end_idx]):
                        # Add newline to the last replacement line
                        new_lines[-1] = new_lines[-1] + '\n'

            # Perform replacement
            modified_lines = lines[:start_idx] + new_lines + lines[end_idx:]
            new_content = ''.join(modified_lines)

            self._write_file_content(file_path, new_content, 'text', encoding)

            replaced_lines = end_line - start_line + 1
            new_line_count = len(new_lines)

            logging.info(f"Successfully replaced {replaced_lines} lines with {new_line_count} lines in {file_path}")
            return f"Successfully replaced lines {start_line}-{end_line} ({replaced_lines} lines) with {new_line_count} line(s) in '{file_path}'."

        except Exception as e:
            logging.error(f"Failed to replace lines in file {file_path}: {e}")
            raise Exception(f"Line replacement failed: {e}")

    def delete_files(self, file_paths: list):
        """Delete multiple files."""
        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list")

        if not file_paths:
            raise ValueError("file_paths list cannot be empty")

        deleted_files = []
        errors = []

        logging.info(f"Attempting to delete {len(file_paths)} file(s)")

        for file_path in file_paths:
            try:
                validated_path = self._validate_file_path(file_path)

                if not os.path.exists(validated_path):
                    errors.append(f"File not found: '{file_path}'")
                    continue

                if not os.path.isfile(validated_path):
                    errors.append(f"Path is not a file: '{file_path}'")
                    continue

                os.remove(validated_path)
                deleted_files.append(file_path)
                logging.info(f"Successfully deleted file: {file_path}")

            except PermissionError:
                errors.append(f"Permission denied deleting file: '{file_path}'")
            except Exception as e:
                errors.append(f"Error deleting file '{file_path}': {e}")

        if errors:
            error_msg = f"Some files could not be deleted: {'; '.join(errors)}"
            if deleted_files:
                error_msg += f". Successfully deleted: {', '.join(deleted_files)}"
            logging.error(error_msg)
            raise Exception(error_msg)

        logging.info(f"Successfully deleted all {len(deleted_files)} file(s)")
        return f"Successfully deleted {len(deleted_files)} file(s): {', '.join(deleted_files)}"

    def create_directory(self, directory_path: str):
        """Create a directory and any necessary parent directories."""
        try:
            validated_path = self._validate_file_path(directory_path)

            if os.path.exists(validated_path):
                if os.path.isdir(validated_path):
                    logging.info(f"Directory already exists: {directory_path}")
                    return f"Directory already exists: '{directory_path}'"
                else:
                    raise ValueError(f"Path exists but is not a directory: '{directory_path}'")

            os.makedirs(validated_path, exist_ok=True)
            logging.info(f"Successfully created directory: {directory_path}")
            return f"Successfully created directory: '{directory_path}'"

        except PermissionError:
            error_msg = f"Permission denied creating directory: '{directory_path}'"
            logging.error(error_msg)
            raise PermissionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to create directory '{directory_path}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg)

    def delete_directory(self, directory_path: str):
        """Delete a directory and all its contents."""
        try:
            validated_path = self._validate_file_path(directory_path)

            if not os.path.exists(validated_path):
                raise FileNotFoundError(f"Directory not found: '{directory_path}'")

            if not os.path.isdir(validated_path):
                raise ValueError(f"Path is not a directory: '{directory_path}'")

            # Count items before deletion for informative message
            item_count = sum(1 for _ in os.walk(validated_path))

            shutil.rmtree(validated_path)
            logging.info(f"Successfully deleted directory: {directory_path}")
            return f"Successfully deleted directory '{directory_path}' and all its contents ({item_count} items)"

        except PermissionError:
            error_msg = f"Permission denied deleting directory: '{directory_path}'"
            logging.error(error_msg)
            raise PermissionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to delete directory '{directory_path}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg)

    def get_tool_declarations(self):
        """Return tool declarations for the MCP protocol."""
        return [
            {
                "name": "write_file",
                "description": "Writes content to a file. Creates parent directories if they don't exist. Supports both text and binary modes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to write to."
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write. For binary mode, provide base64-encoded data."
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["text", "binary"],
                            "default": "text",
                            "description": "Writing mode: 'text' for text files, 'binary' for binary files (content must be base64-encoded)."
                        },
                        "encoding": {
                            "type": "string",
                            "default": "utf-8",
                            "description": "Text encoding to use (ignored in binary mode)."
                        }
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "edit_file_replace_string",
                "description": "Replaces occurrences of old_string with new_string in a file. Handles line ending normalization automatically for text mode.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to modify."
                        },
                        "old_string": {
                            "type": "string",
                            "description": "The content to find and replace. For binary mode, provide base64-encoded data."
                        },
                        "new_string": {
                            "type": "string",
                            "description": "The content to replace with. For binary mode, provide base64-encoded data."
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["text", "binary"],
                            "default": "text",
                            "description": "Operation mode: 'text' with automatic line ending handling, 'binary' for exact byte matching."
                        },
                        "encoding": {
                            "type": "string",
                            "default": "utf-8",
                            "description": "Text encoding to use (ignored in binary mode)."
                        },
                        "count": {
                            "type": "integer",
                            "default": 0,
                            "description": "Maximum number of replacements to make. 0 means replace all occurrences."
                        }
                    },
                    "required": ["file_path", "old_string", "new_string"]
                }
            },
            {
                "name": "edit_file_replace_lines",
                "description": "Replaces content within a specified range of lines (1-indexed). Handles line ending normalization automatically.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to modify."
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "The starting line number (1-based, inclusive)."
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "The ending line number (1-based, inclusive)."
                        },
                        "new_string": {
                            "type": "string",
                            "description": "The new content to replace the specified lines with."
                        },
                        "encoding": {
                            "type": "string",
                            "default": "utf-8",
                            "description": "Text encoding to use."
                        }
                    },
                    "required": ["file_path", "start_line", "end_line", "new_string"]
                }
            },
            {
                "name": "delete_files",
                "description": "Deletes multiple files. Provides detailed feedback about successes and failures.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "A list of file paths to delete.",
                            "minItems": 1
                        }
                    },
                    "required": ["file_paths"]
                }
            },
            {
                "name": "create_directory",
                "description": "Creates a directory and any necessary parent directories. Reports if directory already exists.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory_path": {
                            "type": "string",
                            "description": "The path of the directory to create."
                        }
                    },
                    "required": ["directory_path"]
                }
            },
            {
                "name": "delete_directory",
                "description": "Deletes a directory and all its contents recursively. Provides count of deleted items.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory_path": {
                            "type": "string",
                            "description": "The path of the directory to delete."
                        }
                    },
                    "required": ["directory_path"]
                }
            }
        ]

    def run(self):
        """Main server loop to handle JSON-RPC requests."""
        logging.info("MCP File Manipulation Server started")

        while True:
            try:
                line = sys.stdin.buffer.readline()
                if not line:
                    logging.info("EOF received, shutting down server")
                    break

                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue

                logging.debug(f"Received request: {line_str}")

                try:
                    request = json.loads(line_str)
                except json.JSONDecodeError as e:
                    self._send_error(f"Invalid JSON in request: {e}")
                    continue

                request_id = request.get("id")
                method = request.get("method")

                logging.debug(f"Processing method: {method}, ID: {request_id}")

                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "result": {
                            "protocolVersion": "2025-06-18",
                            "serverInfo": {
                                "name": "Local Files",
                                "version": "1.0.0"
                            },
                            "capabilities": {
                                "tools": {}
                            }
                        },
                        "id": request_id
                    }
                    self._send_response(response)
                    continue

                if method == "notifications/initialized":
                    logging.info("Client initialization complete")
                    continue

                if method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "result": {
                            "tools": self.get_tool_declarations()
                        },
                        "id": request_id
                    }
                    self._send_response(response)
                    continue

                if method == "tools/call":
                    params = request.get("params", {})
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})

                    if tool_name not in self.tools:
                        self._send_error(f"Unknown tool: '{tool_name}'. Available tools: {list(self.tools.keys())}", request_id)
                        continue

                    try:
                        logging.info(f"Executing tool: {tool_name}")
                        result = self.tools[tool_name](**tool_args)
                        response = {
                            "jsonrpc": "2.0",
                            "result": {
                                "result": result
                            },
                            "id": request_id
                        }
                        self._send_response(response)

                    except Exception as e:
                        logging.error(f"Tool execution failed for {tool_name}: {e}", exc_info=True)
                        self._send_error(f"Tool '{tool_name}' execution failed: {e}", request_id)
                    continue

                # Unknown method
                self._send_error(f"Unknown method: '{method}'. Supported methods: initialize, tools/list, tools/call", request_id)

            except KeyboardInterrupt:
                logging.info("Server interrupted by user")
                break
            except Exception as e:
                logging.error(f"Unexpected server error: {e}", exc_info=True)
                self._send_error(f"Internal server error: {e}")


if __name__ == "__main__":
    try:
        server = FileManipulationServer()
        server.run()
    except Exception as e:
        logging.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)
