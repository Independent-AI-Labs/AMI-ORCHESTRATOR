def get_read_file_declaration():
    return {
        "name": "read_file",
        "description": "Read content from a file. Supports both text and binary modes with automatic line ending normalization for text.",
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
                    "description": "Read mode: 'text' for text files with encoding, 'binary' for binary files (returns base64).",
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding to use (ignored in binary mode).",
                },
            },
            "required": ["file_path"],
        },
    }


def get_write_file_declaration():
    return {
        "name": "write_file",
        "description": "Write content to a file. Creates parent directories if needed. Supports both text and binary modes with diff generation for text files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write. For binary mode, provide base64-encoded data.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["text", "binary"],
                    "default": "text",
                    "description": "Write mode: 'text' for text files with encoding, 'binary' for binary files (expects base64).",
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding to use (ignored in binary mode).",
                },
            },
            "required": ["file_path", "content"],
        },
    }


def get_edit_file_replace_string_declaration():
    return {
        "name": "edit_file_replace_string",
        "description": "Replaces occurrences of old_string with new_string in a file. Shows a diff of changes made. Handles line ending normalization automatically for text mode.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to modify.",
                },
                "old_string": {
                    "type": "string",
                    "description": "The content to find and replace. For binary mode, provide base64-encoded data.",
                },
                "new_string": {
                    "type": "string",
                    "description": "The content to replace with. For binary mode, provide base64-encoded data.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["text", "binary"],
                    "default": "text",
                    "description": "Operation mode: 'text' with automatic line ending handling, 'binary' for exact byte matching.",
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding to use (ignored in binary mode).",
                },
                "count": {
                    "type": "integer",
                    "default": 0,
                    "description": "Maximum number of replacements to make. 0 means replace all occurrences.",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        },
    }


def get_edit_file_replace_lines_declaration():
    return {
        "name": "edit_file_replace_lines",
        "description": "Replaces content within a specified range of lines (1-indexed). Shows a diff of changes made. Handles line ending normalization automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to modify.",
                },
                "start_line": {
                    "type": "integer",
                    "description": "The starting line number (1-based, inclusive).",
                },
                "end_line": {
                    "type": "integer",
                    "description": "The ending line number (1-based, inclusive).",
                },
                "new_string": {
                    "type": "string",
                    "description": "The new content to replace the specified lines with.",
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding to use.",
                },
            },
            "required": ["file_path", "start_line", "end_line", "new_string"],
        },
    }


def get_edit_file_delete_lines_declaration():
    return {
        "name": "edit_file_delete_lines",
        "description": "Deletes lines within a specified range (1-indexed). Shows a diff of changes made. Handles line ending normalization automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to modify.",
                },
                "start_line": {
                    "type": "integer",
                    "description": "The starting line number to delete (1-based, inclusive).",
                },
                "end_line": {
                    "type": "integer",
                    "description": "The ending line number to delete (1-based, inclusive).",
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding to use.",
                },
            },
            "required": ["file_path", "start_line", "end_line"],
        },
    }


def get_edit_file_insert_lines_declaration():
    return {
        "name": "edit_file_insert_lines",
        "description": "Inserts content at a specified line number (1-indexed). Shows a diff of changes made. Handles line ending normalization automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to modify.",
                },
                "line_number": {
                    "type": "integer",
                    "description": "The line number where content should be inserted (1-based). Content will be inserted before this line. Use file_length + 1 to append to the end.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to insert at the specified line.",
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding to use.",
                },
            },
            "required": ["file_path", "line_number", "content"],
        },
    }


def get_delete_files_declaration():
    return {
        "name": "delete_files",
        "description": "Deletes multiple files. Provides detailed feedback about successes and failures.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of file paths to delete.",
                    "minItems": 1,
                }
            },
            "required": ["file_paths"],
        },
    }


def get_move_files_declaration():
    return {
        "name": "move_files",
        "description": "Move/rename files from source paths to destination paths. Can create destination directories if needed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of source file paths to move.",
                    "minItems": 1,
                },
                "destination_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of destination file paths. Must match the number of source paths.",
                    "minItems": 1,
                },
                "create_dirs": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to create destination directories if they don't exist.",
                },
            },
            "required": ["source_paths", "destination_paths"],
        },
    }


def get_create_directory_declaration():
    return {
        "name": "create_directory",
        "description": "Creates a directory and any necessary parent directories. Reports if directory already exists.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "The path of the directory to create.",
                }
            },
            "required": ["directory_path"],
        },
    }


def get_delete_directory_declaration():
    return {
        "name": "delete_directory",
        "description": "Deletes a directory and all its contents recursively. Provides count of deleted items.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "The path of the directory to delete.",
                }
            },
            "required": ["directory_path"],
        },
    }
