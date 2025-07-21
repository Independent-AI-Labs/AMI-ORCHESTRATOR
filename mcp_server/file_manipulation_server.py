import sys
import json
import base64
import os

class FileManipulationServer:
    def __init__(self):
        self.tools = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "replace_content": self.replace_content,
        }

    def _send_response(self, response):
        sys.stdout.write(json.dumps(response) + '\n')
        sys.stdout.flush()

    def _send_error(self, message):
        self._send_response({"error": message})

    def _read_file_content(self, file_path: str, mode: str = 'text', encoding: str = 'utf-8'):
        try:
            if mode == 'text':
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            elif mode == 'binary':
                with open(file_path, 'rb') as f:
                    return f.read()
            else:
                raise ValueError("Invalid mode. Use 'text' or 'binary'.")
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found at {file_path}")
        except Exception as e:
            raise Exception(f"Error reading file {file_path}: {e}")

    def _write_file_content(self, file_path: str, content, mode: str = 'text', encoding: str = 'utf-8'):
        try:
            if mode == 'text':
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(content)
            elif mode == 'binary':
                with open(file_path, 'wb') as f:
                    f.write(content)
            else:
                raise ValueError("Invalid mode. Use 'text' or 'binary'.")
        except Exception as e:
            raise Exception(f"Error writing to file {file_path}: {e}")

    def read_file(self, file_path: str, mode: str = 'text', encoding: str = 'utf-8'):
        try:
            content = self._read_file_content(file_path, mode, encoding)
            if mode == 'binary':
                return base64.b64encode(content).decode('utf-8')
            return content
        except Exception as e:
            self._send_error(str(e))
            return None

    def write_file(self, file_path: str, content, mode: str = 'text', encoding: str = 'utf-8'):
        try:
            if mode == 'binary':
                content = base64.b64decode(content.encode('utf-8'))
            self._write_file_content(file_path, content, mode, encoding)
            return "Success"
        except Exception as e:
            self._send_error(str(e))
            return None

    def replace_content(self, file_path: str, old_content, new_content, mode: str = 'text', encoding: str = 'utf-8', count: int = 0):
        try:
            if mode == 'binary':
                old_content = base64.b64decode(old_content.encode('utf-8'))
                new_content = base64.b64decode(new_content.encode('utf-8'))

            current_content = self._read_file_content(file_path, mode, encoding)

            if mode == 'text':
                if not isinstance(old_content, str) or not isinstance(new_content, str):
                    raise ValueError("old_content and new_content must be strings in text mode.")
                if count == 0:
                    new_file_content = current_content.replace(old_content, new_content)
                else:
                    new_file_content = current_content.replace(old_content, new_content, count)
            elif mode == 'binary':
                if not isinstance(old_content, bytes) or not isinstance(new_content, bytes):
                    raise ValueError("old_content and new_content must be bytes in binary mode.")
                if count == 0:
                    new_file_content = current_content.replace(old_content, new_content)
                else:
                    new_file_content = current_content.replace(old_content, new_content, count)
            else:
                raise ValueError("Invalid mode. Use 'text' or 'binary'.")

            if new_file_content == current_content:
                return "No changes made (content not found or already replaced)"

            self._write_file_content(file_path, new_file_content, mode, encoding)
            return "Success"
        except Exception as e:
            self._send_error(str(e))
            return None

    def run(self):
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            try:
                request = json.loads(line)
                tool_name = request.get("tool_name")
                tool_args = request.get("tool_args", {})

                if tool_name in self.tools:
                    result = self.tools[tool_name](**tool_args)
                    self._send_response({"result": result})
                else:
                    self._send_error(f"Unknown tool: {tool_name}")
            except json.JSONDecodeError:
                self._send_error("Invalid JSON request")
            except Exception as e:
                self._send_error(f"Server error: {e}")

if __name__ == "__main__":
    server = FileManipulationServer()
    server.run()
