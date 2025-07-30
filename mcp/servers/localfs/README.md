# Local Files MCP Server

## Overview

The Local Files MCP server is a standalone Python script that provides a set of file manipulation tools through the Model-Controller-Presenter (MCP) protocol. It is designed to run as a background process, managed by the `MCPServerManager`, and communicates over `stdin` and `stdout` using JSON-RPC.

## Features

- **File I/O:** Read from and write to files in both text and binary modes.
- **File Editing:** Perform targeted edits, such as replacing strings or lines, inserting content, and deleting lines.
- **File System Operations:** Create, delete, and move files and directories.
- **Cross-Platform:** All tools are designed to be compatible with both Windows and Unix-like operating systems.
- **Security:** Includes basic security measures to prevent directory traversal attacks.
- **Logging:** All operations are logged to a file in the `orchestrator/logs` directory.

## Tools

The server exposes the following tools:

- `list_dir`: Lists the names of files and subdirectories directly within a specified directory path.
- `create_dirs`: Creates a directory and any necessary parent directories.
- `find_paths`: Searches for files based on keywords in path/name or content.
- `read_file`: Reads the content of a file, with support for specifying `file_encoding` and `output_format`.
- `write_file`: Writes content to a file, with support for specifying `file_encoding` and `input_format`.
- `delete_paths`: Deletes multiple files or directories.
- `modify_file`: Modifies a file by replacing a range of content with new content, with support for specifying `file_encoding` and `input_format`.
- `replace_content_in_file`: Replaces all occurrences of old_content with new_content within a file, with support for specifying `file_encoding` and `input_format`.

## Usage

The server is not intended to be run directly. Instead, it should be managed by the `MCPServerManager`, which handles starting, stopping, and communicating with the server process. For testing purposes, the `MCPServerManager` can start the server in a non-detached mode, allowing for direct interaction with the server's `stdin` and `stdout`.