"""
Tool declarations for the LocalFiles server.
"""


def get_tool_declarations():
    """Return tool declarations for the MCP protocol."""
    return [
        {
            "name": "list_dir",
            "description": "Lists the names of files and subdirectories directly within a specified directory path.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute path to the directory to list."},
                    "limit": {"type": "integer", "default": 100, "description": "The maximum number of items (files + directories) to return."},
                    "recursive": {
                        "type": "boolean",
                        "default": False,
                        "description": "If True, the listing will include contents of subdirectories recursively.",
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "create_dirs",
            "description": "Creates a directory and any necessary parent directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path of the directory to create.",
                    }
                },
                "required": ["path"],
            },
        },
        {
            "name": "find_paths",
            "description": "Searches for files based on keywords in path/name or content.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute path to the directory to start the search."},
                    "keywords_path_name": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "A list of strings to search for within the file's path or name.",
                    },
                    "kewords_file_content": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "A list of strings to search for within the file's content.",
                    },
                    "regex_keywords": {
                        "type": "boolean",
                        "default": False,
                        "description": "If True, keywords_path_name and kewords_file_content will be treated as regular expressions.",
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "read_from_file",
            "description": (
                "Reads file content with support for offsets, various file types (text, binary, image), "
                "and line numbering for text files. Returns content in the specified output format."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to read.",
                    },
                    "start_offset_inclusive": {
                        "type": "integer",
                        "default": 0,
                        "description": "The starting offset (byte, char, or line number, 0-indexed).",
                    },
                    "end_offset_inclusive": {
                        "type": "integer",
                        "default": -1,
                        "description": "The ending offset (byte, char, or line number, -1 for end of file).",
                    },
                    "offset_type": {
                        "type": "string",
                        "enum": ["line", "char", "byte"],
                        "default": "line",
                        "description": "Specifies how offsets are interpreted (Line, Char, or Byte).",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["raw_utf8", "quoted-printable", "base64"],
                        "default": "raw_utf8",
                        "description": "The format of the `new_content` (Raw UTF-8, Quoted-Printable or Base64 string)",
                    },
                    "file_encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use when reading text files.",
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "write_to_file",
            "description": "Writes content to a file, creating parent directories if needed. Supports text/binary modes; generates diffs for text.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to write.",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "The content to write. Format depends on `input_format`.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["text", "binary"],
                        "default": "text",
                        "description": "Write mode: 'text' for text files, 'binary' for binary files.",
                    },
                    "input_format": {
                        "type": "string",
                        "enum": ["raw_utf8", "quoted-printable", "base64"],
                        "default": "raw_utf8",
                        "description": "The format of the `new_content` (Raw UTF-8, Quoted-Printable or Base64 string)",
                    },
                    "file_encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use when writing text files (ignored in binary mode).",
                    },
                },
                "required": ["path", "new_content"],
            },
        },
        {
            "name": "delete_paths",
            "description": "Deletes multiple files or directories.",
            "inputSchema": {
                "type": "object",
                "properties": {"paths": {"type": "array", "items": {"type": "string"}, "description": "A list of absolute file or directory paths to delete."}},
                "required": ["paths"],
            },
        },

        {
            "name": "replace_in_file",
            "description": "Replaces occurrences of old_content with new_content within a file, with regex support.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute path to the file."},
                    "old_content": {
                        "type": "string",
                        "description": "The content to find. Format depends on `input_format`.",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "The content to replace with. Format depends on `input_format`.",
                    },
                    "number_of_occurrences": {
                        "type": "integer",
                        "default": -1,
                        "description": "The number of occurrences to replace (-1 for all).",
                    },
                    "is_regex": {
                        "type": "boolean",
                        "default": False,
                        "description": "If True, old_content will be treated as a regular expression.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["text", "binary"],
                        "default": "text",
                        "description": "File mode: 'text' for text files, 'binary' for binary files.",
                    },
                    "input_format": {
                        "type": "string",
                        "enum": ["raw_utf8", "quoted-printable", "base64"],
                        "default": "raw_utf8",
                        "description": "The format of the `old_content` and `new_content` (Raw UTF-8, Quoted-Printable or Base64 string).",
                    },
                    "file_encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use when replacing content in text files (ignored in binary mode).",
                    },
                },
                "required": ["path", "old_content", "new_content"],
            },
        },
        {
            "name": "modify_file",
            "description": "Modifies a file by replacing a range of content with new content.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute path to the file."},
                    "start_offset_inclusive": {"type": "integer", "default": 0, "description": "The 0-indexed starting offset (inclusive)."},
                    "end_offset_inclusive": {"type": "integer", "default": -1, "description": "The 0-indexed ending offset (inclusive, -1 for end of file)."},
                    "offset_type": {
                        "type": "string",
                        "enum": ["line", "char", "byte"],
                        "default": "line",
                        "description": "Specifies how offsets are interpreted (Line, Char, or Byte).",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "The new content to replace the specified range. Format depends on `input_format`.",
                    },
                    "input_format": {
                        "type": "string",
                        "enum": ["raw_utf8", "quoted-printable", "base64"],
                        "default": "raw_utf8",
                        "description": "The format of the `new_content` (Raw UTF-8, Quoted-Printable or Base64 string).",
                    },
                    "file_encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "Text encoding to use when modifying text files (ignored in binary mode).",
                    },
                },
                "required": ["path", "new_content"],
            },
        },
    ]
