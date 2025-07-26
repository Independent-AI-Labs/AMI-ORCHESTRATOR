"""
Tool declarations for the LocalFiles server.
"""


def get_tool_declarations():
    """Return tool declarations for the MCP protocol."""
    return [
        {
            "name": "read_file",
            "description": "Read content from a file. Supports text/binary modes, auto line ending normalization.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["text", "binary"],
                        "default": "text",
                        "description": "Read mode: 'text' for text files, 'binary' for binary (returns base64).",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use (ignored in binary mode).",
                    },
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write content to a file. Creates parent dirs. Supports text/binary modes, diffs for text.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write. Base64 for binary mode.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["text", "binary"],
                        "default": "text",
                        "description": "Write mode: 'text' for text, 'binary' for binary (expects base64).",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use (ignored in binary mode).",
                    },
                },
                "required": ["file_path", "content"],
            },
        },
        {
            "name": "edit_file_replace_string",
            "description": "Replaces old_string with new_string. Shows diff. Handles line endings. Binary mode uses base64.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to modify.",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Content to find. Base64 for binary mode.",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Content to replace with. Base64 for binary mode.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["text", "binary"],
                        "default": "text",
                        "description": "Operation mode: 'text' (auto line ending) or 'binary' (exact bytes).",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use (ignored in binary mode).",
                    },
                    "count": {
                        "type": "integer",
                        "default": 0,
                        "description": "Max replacements (0 for all).",
                    },
                },
                "required": ["file_path", "old_string", "new_string"],
            },
        },
        {
            "name": "edit_file_replace_lines",
            "description": "Replaces lines in a range (1-indexed). Shows diff. Handles line endings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to modify.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number (1-based, inclusive).",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number (1-based, inclusive).",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "New content to replace lines with.",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use.",
                    },
                },
                "required": ["file_path", "start_line", "end_line", "new_string"],
            },
        },
        {
            "name": "edit_file_delete_lines",
            "description": "Deletes lines in a range (1-indexed). Shows diff. Handles line endings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to modify.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number to delete (1-based, inclusive).",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number to delete (1-based, inclusive).",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use.",
                    },
                },
                "required": ["file_path", "start_line", "end_line"],
            },
        },
        {
            "name": "edit_file_insert_lines",
            "description": "Inserts content at a line number (1-indexed). Shows diff. Handles line endings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to modify.",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "Line number for insertion (1-based). Use file_length + 1 to append.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to insert.",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use.",
                    },
                },
                "required": ["file_path", "line_number", "content"],
            },
        },
        {
            "name": "delete_files",
            "description": "Deletes multiple files. Provides feedback on success/failure.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to delete.",
                        "minItems": 1,
                    }
                },
                "required": ["file_paths"],
            },
        },
        {
            "name": "move_files",
            "description": "Move/rename files. Can create destination directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of source file paths to move.",
                        "minItems": 1,
                    },
                    "destination_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of destination file paths. Must match source count.",
                        "minItems": 1,
                    },
                    "create_dirs": {
                        "type": "boolean",
                        "default": True,
                        "description": "Create destination directories if they don't exist.",
                    },
                },
                "required": ["source_paths", "destination_paths"],
            },
        },
        {
            "name": "create_directory",
            "description": "Creates a directory and parents. Reports if already exists.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path of the directory to create.",
                    }
                },
                "required": ["directory_path"],
            },
        },
        {
            "name": "delete_directory",
            "description": "Deletes a directory and its contents recursively. Reports deleted item count.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path of the directory to delete.",
                    }
                },
                "required": ["directory_path"],
            },
        },
    ]
