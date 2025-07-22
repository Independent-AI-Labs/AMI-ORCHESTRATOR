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

- `read_file`: Reads the content of a file.
- `write_file`: Writes content to a file.
- `edit_file_replace_string`: Replaces occurrences of a string in a file.
- `edit_file_replace_lines`: Replaces a range of lines in a file.
- `edit_file_delete_lines`: Deletes a range of lines from a file.
- `edit_file_insert_lines`: Inserts content at a specific line number.
- `delete_files`: Deletes one or more files.
- `move_files`: Moves or renames one or more files.
- `create_directory`: Creates a new directory.
- `delete_directory`: Deletes a directory and its contents.

## Usage

The server is not intended to be run directly. Instead, it should be managed by the `MCPServerManager`, which handles starting, stopping, and communicating with the server process. For testing purposes, the `MCPServerManager` can start the server in a non-detached mode, allowing for direct interaction with the server's `stdin` and `stdout`.
