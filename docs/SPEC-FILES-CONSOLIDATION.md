# SPEC: Files Module Tool Consolidation

**Version:** 1.1
**Status:** Planning - Ready for Implementation
**Date:** 2025-11-01
**Last Updated:** 2025-11-01 (v1.1: Corrected document tool signature and git parameter name)

## Executive Summary

Consolidate the Filesys MCP server from 27 individual tools to 4 facade tools (85% reduction) using the action-dispatch pattern proven in the browser module. This improves API discoverability, reduces complexity, and maintains consistency across modules.

---

## 1. Current State Analysis

### 1.1 Existing Tool Count

**Total: 27 tools** registered in `filesys_server.py`:

**Filesystem Tools (8):**
1. list_dir
2. create_dirs
3. find_paths
4. read_from_file
5. write_to_file
6. delete_paths
7. modify_file
8. replace_in_file

**Git Repository Tools (7):**
9. git_status
10. git_stage
11. git_unstage
12. git_commit
13. git_diff
14. git_history
15. git_restore

**Git Remote Tools (4):**
16. git_fetch
17. git_pull
18. git_push
19. git_merge_abort

**Python Execution Tools (5):**
20. python_run
21. python_run_background
22. python_task_status
23. python_task_cancel
24. python_list_tasks

**Document Analysis Tools (3):**
25. index_document
26. read_document
27. read_image

### 1.2 Implementation Structure

```
files/backend/mcp/filesys/tools/
├── filesystem_tools.py (8 implementation functions)
├── git_tools.py (11 implementation functions)
├── python_tools.py (5 implementation functions)
├── document_tools.py (3 implementation functions)
└── __init__.py
```

**Problem:** Each tool is individually registered in `filesys_server.py`, creating:
- Large API surface (27 tools)
- Difficult discoverability (which tool for which task?)
- Inconsistent with browser module architecture
- Verbose server registration code

---

## 2. Browser Module Reference Pattern

### 2.1 Browser Tool Count

**Total: 11 facade tools** in `chrome_server.py`:

1. browser_session (9 actions)
2. browser_navigate (9 actions)
3. browser_interact (7 actions)
4. browser_inspect (3 actions)
5. browser_extract (2 actions)
6. browser_capture (2 actions)
7. browser_execute (2 actions)
8. web_search (1 action)
9. browser_storage (6 actions)
10. browser_react (5 actions)
11. browser_profile (4 actions)

### 2.2 Browser Architecture

**Facade Layer:**
```
browser/backend/mcp/chrome/tools/facade/
├── __init__.py (exports all facade tools)
├── session.py (browser_session_tool)
├── navigation.py (browser_navigate_tool)
├── interaction.py (browser_interact_tool)
├── inspection.py (browser_inspect_tool)
├── extraction.py (browser_extract_tool)
├── capture.py (browser_capture_tool)
├── execution.py (browser_execute_tool)
├── storage.py (browser_storage_tool)
├── react.py (browser_react_tool)
└── profile.py (browser_profile_tool)
```

**Implementation Layer:**
```
browser/backend/mcp/chrome/tools/
├── browser_tools.py
├── extraction_tools.py
├── input_tools.py
├── javascript_tools.py
├── navigation_tools.py
├── react_tools.py
├── screenshot_tools.py
└── search_tools.py
```

**Pattern:**
- Facade tools use action-based dispatch with Literal types
- Handler functions per action: `_handle_<action>()`
- `_ACTION_HANDLERS` dict maps actions to handlers
- Handlers call underlying implementation tools
- Zero code duplication (facades are thin dispatch layer)

### 2.3 Example: browser_navigate_tool

```python
async def browser_navigate_tool(
    manager: ChromeManager,
    action: Literal[
        "goto",
        "back",
        "forward",
        "refresh",
        "get_url",
        "open_tab",
        "close_tab",
        "switch_tab",
        "list_tabs",
    ],
    url: str | None = None,
    wait_for: str | None = None,
    timeout: float = 30,
    tab_id: str | None = None,
    instance_id: str | None = None,
) -> BrowserResponse:
    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return BrowserResponse(success=False, error=f"Unknown action: {action}")

    return await handler(
        manager=manager,
        url=url,
        wait_for=wait_for,
        timeout=timeout,
        tab_id=tab_id,
        instance_id=instance_id,
    )

_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[BrowserResponse]]] = {
    "goto": _handle_goto,
    "back": _handle_back,
    "forward": _handle_forward,
    # ... 6 more handlers
}

async def _handle_goto(
    manager: ChromeManager, url: str | None, instance_id: str | None, wait_for: str | None, timeout: float, **_kwargs: Any
) -> BrowserResponse:
    if not url:
        return BrowserResponse(success=False, error="url required for goto action")
    return await browser_navigate_impl(manager, url, instance_id, wait_for, timeout)
```

---

## 3. Target State Design

### 3.1 Consolidated Tool Count

**Total: 4 facade tools** (85% reduction):

1. **filesystem** (8 actions)
2. **git** (11 actions)
3. **python** (5 actions)
4. **document** (3 actions)

### 3.2 Action Mapping

**filesystem tool (8 actions):**
- list - List directory contents
- create - Create directories
- find - Find paths matching patterns
- read - Read file contents
- write - Write content to file (with LLM validation)
- delete - Delete files or directories
- modify - Modify file at specific offsets
- replace - Replace text in file

**git tool (11 actions):**
- status - Get repository status
- stage - Stage files for commit
- unstage - Unstage files
- commit - Commit changes (calls scripts/git_commit.sh)
- diff - Show differences
- history - Show commit history
- restore - Restore files
- fetch - Fetch from remote
- pull - Pull from remote
- push - Push to remote (calls scripts/git_push.sh)
- merge_abort - Abort merge

**python tool (5 actions):**
- run - Execute Python script or code
- run_background - Execute Python script in background
- task_status - Get status of background task
- task_cancel - Cancel background task
- list_tasks - List all background tasks

**document tool (3 actions):**
- index - Parse and index documents for searchable storage
- read - Read and parse documents into structured data
- read_image - Analyze images using multimodal LLM

**Note:** Document tool differs from other facades - it does NOT take `root_dir` parameter. Document implementation tools handle paths internally using `Path(path)`.

### 3.3 Target File Structure

```
files/backend/mcp/filesys/tools/
├── facade/
│   ├── __init__.py (exports 4 facade tools)
│   ├── filesystem.py (filesystem_tool with 8 actions)
│   ├── git.py (git_tool with 11 actions)
│   ├── python.py (python_tool with 5 actions)
│   └── document.py (document_tool with 3 actions)
├── filesystem_tools.py (8 implementation functions - UNCHANGED)
├── git_tools.py (11 implementation functions - UNCHANGED)
├── python_tools.py (5 implementation functions - UNCHANGED)
├── document_tools.py (3 implementation functions - UNCHANGED)
└── __init__.py
```

---

## 4. Implementation Plan

### Phase 1: Create Facade Structure ✅ NOT STARTED

**Goal:** Set up facade directory and module structure

**Tasks:**

1. Create facade directory:
   ```bash
   mkdir -p files/backend/mcp/filesys/tools/facade
   ```

2. Create facade module files:
   ```
   files/backend/mcp/filesys/tools/facade/
   ├── __init__.py
   ├── filesystem.py
   ├── git.py
   ├── python.py
   └── document.py
   ```

3. Create `facade/__init__.py` with exports:
   ```python
   """Facade tools for Filesys MCP server."""

   from files.backend.mcp.filesys.tools.facade.filesystem import filesystem_tool
   from files.backend.mcp.filesys.tools.facade.git import git_tool
   from files.backend.mcp.filesys.tools.facade.python import python_tool
   from files.backend.mcp.filesys.tools.facade.document import document_tool

   __all__ = [
       "filesystem_tool",
       "git_tool",
       "python_tool",
       "document_tool",
   ]
   ```

**Deliverables:**
- Directory structure created
- Empty facade modules with docstrings
- `__init__.py` exporting all 4 tools

### Phase 2: Implement Filesystem Facade ✅ NOT STARTED

**Goal:** Create filesystem_tool with 8 actions

**Implementation Pattern:**

```python
"""Filesystem operations facade tool."""

from pathlib import Path
from typing import Any, Literal
from collections.abc import Awaitable, Callable

from loguru import logger

from files.backend.mcp.filesys.tools.filesystem_tools import (
    list_dir_tool,
    create_dirs_tool,
    find_paths_tool,
    read_from_file_tool,
    write_to_file_tool,
    delete_paths_tool,
    modify_file_tool,
    replace_in_file_tool,
)


async def _handle_list(root_dir: Path, path: str | None, recursive: bool, pattern: str | None, limit: int, **_kwargs: Any) -> dict[str, Any]:
    """Handle list action."""
    return await list_dir_tool(root_dir, path or ".", recursive, pattern, limit)


async def _handle_create(root_dir: Path, paths: list[str] | None, **_kwargs: Any) -> dict[str, Any]:
    """Handle create action."""
    if not paths:
        return {"error": "paths required for create action"}
    return await create_dirs_tool(root_dir, paths)


async def _handle_find(
    root_dir: Path,
    patterns: list[str] | None,
    path: str | None,
    keywords_path_name: list[str] | None,
    keywords_file_content: list[str] | None,
    regex_keywords: bool,
    use_fast_search: bool,
    max_workers: int,
    recursive: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle find action."""
    return await find_paths_tool(
        root_dir,
        patterns,
        path or ".",
        keywords_path_name,
        keywords_file_content,
        regex_keywords,
        use_fast_search,
        max_workers,
        recursive,
    )


async def _handle_read(
    root_dir: Path,
    path: str | None,
    start_line: int | None,
    end_line: int | None,
    start_offset_inclusive: int,
    end_offset_inclusive: int,
    offset_type: str,
    output_format: str,
    file_encoding: str,
    add_line_numbers: bool | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle read action."""
    if not path:
        return {"error": "path required for read action"}
    return await read_from_file_tool(
        root_dir,
        path,
        start_line,
        end_line,
        start_offset_inclusive,
        end_offset_inclusive,
        offset_type,
        output_format,
        file_encoding,
        add_line_numbers,
    )


async def _handle_write(
    root_dir: Path,
    path: str | None,
    content: str | None,
    mode: str,
    input_format: str,
    file_encoding: str,
    validate_with_llm: bool,
    session_id: str | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle write action."""
    if not path:
        return {"error": "path required for write action"}
    if content is None:
        return {"error": "content required for write action"}
    return await write_to_file_tool(
        root_dir,
        path,
        content,
        mode,
        input_format,
        file_encoding,
        validate_with_llm,
        session_id,
    )


async def _handle_delete(root_dir: Path, paths: list[str] | None, **_kwargs: Any) -> dict[str, Any]:
    """Handle delete action."""
    if not paths:
        return {"error": "paths required for delete action"}
    return await delete_paths_tool(root_dir, paths)


async def _handle_modify(
    root_dir: Path,
    path: str | None,
    start_offset_inclusive: int,
    end_offset_inclusive: int,
    new_content: str | None,
    offset_type: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle modify action."""
    if not path:
        return {"error": "path required for modify action"}
    if new_content is None:
        return {"error": "new_content required for modify action"}
    return await modify_file_tool(
        root_dir,
        path,
        start_offset_inclusive,
        end_offset_inclusive,
        new_content,
        offset_type,
    )


async def _handle_replace(
    root_dir: Path,
    path: str | None,
    old_content: str | None,
    new_content: str | None,
    is_regex: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle replace action."""
    if not path:
        return {"error": "path required for replace action"}
    if old_content is None:
        return {"error": "old_content required for replace action"}
    if new_content is None:
        return {"error": "new_content required for replace action"}
    return await replace_in_file_tool(root_dir, path, old_content, new_content, is_regex)


_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "list": _handle_list,
    "create": _handle_create,
    "find": _handle_find,
    "read": _handle_read,
    "write": _handle_write,
    "delete": _handle_delete,
    "modify": _handle_modify,
    "replace": _handle_replace,
}


async def filesystem_tool(
    root_dir: Path,
    action: Literal["list", "create", "find", "read", "write", "delete", "modify", "replace"],
    path: str | None = None,
    paths: list[str] | None = None,
    content: str | None = None,
    recursive: bool = False,
    pattern: str | None = None,
    limit: int = 100,
    patterns: list[str] | None = None,
    keywords_path_name: list[str] | None = None,
    keywords_file_content: list[str] | None = None,
    regex_keywords: bool = False,
    use_fast_search: bool = True,
    max_workers: int = 8,
    start_line: int | None = None,
    end_line: int | None = None,
    start_offset_inclusive: int = 0,
    end_offset_inclusive: int = -1,
    offset_type: str = "line",
    output_format: str = "raw_utf8",
    file_encoding: str = "utf-8",
    add_line_numbers: bool | None = None,
    mode: str = "text",
    input_format: str = "raw_utf8",
    validate_with_llm: bool = True,
    session_id: str | None = None,
    new_content: str | None = None,
    old_content: str | None = None,
    is_regex: bool = False,
) -> dict[str, Any]:
    """Filesystem operations facade.

    Args:
        root_dir: Root directory for operations
        action: Action to perform (list, create, find, read, write, delete, modify, replace)
        path: File or directory path (required for most actions)
        paths: List of paths (required for create, delete)
        content: File content (required for write)
        recursive: Recursive directory listing
        pattern: Glob pattern for filtering
        limit: Maximum results to return
        patterns: List of glob patterns (for find)
        keywords_path_name: Keywords to search in paths
        keywords_file_content: Keywords to search in file contents
        regex_keywords: Treat keywords as regex
        use_fast_search: Use optimized search algorithm
        max_workers: Maximum parallel workers
        start_line: Start line number (for read)
        end_line: End line number (for read)
        start_offset_inclusive: Start offset (for read/modify)
        end_offset_inclusive: End offset (for read/modify)
        offset_type: Offset type (line or byte)
        output_format: Output format (raw_utf8, base64, etc.)
        file_encoding: File encoding
        add_line_numbers: Add line numbers to output
        mode: Write mode (text or binary)
        input_format: Input format for content
        validate_with_llm: Run LLM validation for Python files
        session_id: Session ID for validation context
        new_content: New content (for modify/replace)
        old_content: Content to replace (for replace)
        is_regex: Treat old_content as regex (for replace)

    Returns:
        Dict with action-specific results
    """
    logger.debug(f"filesystem_tool: action={action}, path={path}")

    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return {"error": f"Unknown action: {action}"}

    return await handler(
        root_dir=root_dir,
        path=path,
        paths=paths,
        content=content,
        recursive=recursive,
        pattern=pattern,
        limit=limit,
        patterns=patterns,
        keywords_path_name=keywords_path_name,
        keywords_file_content=keywords_file_content,
        regex_keywords=regex_keywords,
        use_fast_search=use_fast_search,
        max_workers=max_workers,
        start_line=start_line,
        end_line=end_line,
        start_offset_inclusive=start_offset_inclusive,
        end_offset_inclusive=end_offset_inclusive,
        offset_type=offset_type,
        output_format=output_format,
        file_encoding=file_encoding,
        add_line_numbers=add_line_numbers,
        mode=mode,
        input_format=input_format,
        validate_with_llm=validate_with_llm,
        session_id=session_id,
        new_content=new_content,
        old_content=old_content,
        is_regex=is_regex,
    )
```

**Deliverables:**
- `facade/filesystem.py` with filesystem_tool
- 8 handler functions
- Action dispatch logic
- Parameter validation

### Phase 3: Implement Git Facade ✅ NOT STARTED

**Goal:** Create git_tool with 11 actions

**Actions:**
- status, stage, unstage, commit, diff, history, restore
- fetch, pull, push, merge_abort

**Pattern:** Same as filesystem facade (handler functions + dispatch)

**Special Handling:**
- commit action calls scripts/git_commit.sh (auto-stages)
- push action calls scripts/git_push.sh (runs tests)
- Preserve all existing git_tools.py behavior

**Deliverables:**
- `facade/git.py` with git_tool
- 11 handler functions
- Action dispatch logic

### Phase 4: Implement Python Facade ✅ NOT STARTED

**Goal:** Create python_tool with 5 actions

**Actions:**
- run, run_background, task_status, task_cancel, list_tasks

**Pattern:** Same as filesystem facade

**Deliverables:**
- `facade/python.py` with python_tool
- 5 handler functions
- Action dispatch logic

### Phase 5: Implement Document Facade ✅ NOT STARTED

**Goal:** Create document_tool with 3 actions

**Actions:**
- index, read, read_image

**Pattern:** Same as filesystem facade (handler functions + dispatch)

**Special Note:** Document tools DON'T take `root_dir` parameter (unlike filesystem/git/python tools). They handle paths internally using `Path(path)`.

**Implementation Pattern:**

```python
"""Document processing facade tool."""

from typing import Any, Literal
from collections.abc import Awaitable, Callable

from loguru import logger

from files.backend.mcp.filesys.tools.document_tools import (
    index_document_tool,
    read_document_tool,
    read_image_tool,
)


async def _handle_index(
    path: str,
    extract_tables: bool,
    extract_images: bool,
    storage_backends: list[str] | None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle index action."""
    return await index_document_tool(path, extract_tables, extract_images, storage_backends)


async def _handle_read(
    path: str,
    extraction_template: dict[str, Any] | None,
    extract_tables: bool,
    extract_images: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle read action."""
    return await read_document_tool(path, extraction_template, extract_tables, extract_images)


async def _handle_read_image(
    path: str,
    instruction: str | None,
    perform_ocr: bool,
    extract_chart_data: bool,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Handle read_image action."""
    return await read_image_tool(path, instruction, perform_ocr, extract_chart_data)


_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "index": _handle_index,
    "read": _handle_read,
    "read_image": _handle_read_image,
}


async def document_tool(
    action: Literal["index", "read", "read_image"],
    path: str,
    extraction_template: dict[str, Any] | None = None,
    extract_tables: bool = True,
    extract_images: bool = False,
    storage_backends: list[str] | None = None,
    instruction: str | None = None,
    perform_ocr: bool = True,
    extract_chart_data: bool = False,
) -> dict[str, Any]:
    """Document processing facade.

    Args:
        action: Action to perform (index, read, read_image)
        path: Path to document or image file (required)
        extraction_template: Template for guided extraction (read only)
        extract_tables: Whether to extract tables
        extract_images: Whether to extract images
        storage_backends: Storage backends for indexing (index only)
        instruction: Analysis instruction (read_image only)
        perform_ocr: Perform OCR on image (read_image only)
        extract_chart_data: Extract chart data (read_image only)

    Returns:
        Dict with action-specific results
    """
    logger.debug(f"document_tool: action={action}, path={path}")

    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return {"error": f"Unknown action: {action}"}

    return await handler(
        path=path,
        extraction_template=extraction_template,
        extract_tables=extract_tables,
        extract_images=extract_images,
        storage_backends=storage_backends,
        instruction=instruction,
        perform_ocr=perform_ocr,
        extract_chart_data=extract_chart_data,
    )
```

**Deliverables:**
- `facade/document.py` with document_tool
- 3 handler functions
- Action dispatch logic
- NO root_dir parameter (document tools handle paths internally)

### Phase 6: Update Server Registration ✅ NOT STARTED

**Goal:** Replace 27 individual registrations with 4 facade registrations

**Changes to `filesys_server.py`:**

1. Update imports:
   ```python
   # OLD
   from files.backend.mcp.filesys.tools.filesystem_tools import (
       create_dirs_tool,
       delete_paths_tool,
       find_paths_tool,
       list_dir_tool,
       modify_file_tool,
       read_from_file_tool,
       replace_in_file_tool,
       write_to_file_tool,
   )
   from files.backend.mcp.filesys.tools.git_tools import (
       git_commit_tool,
       git_diff_tool,
       # ... 9 more imports
   )
   # ... more imports

   # NEW
   from files.backend.mcp.filesys.tools.facade import (
       filesystem_tool,
       git_tool,
       python_tool,
       document_tool,
   )
   ```

2. Replace `_register_tools()` method:
   ```python
   def _register_tools(self) -> None:
       """Register facade tools with FastMCP."""
       self._register_filesystem_tool()
       self._register_git_tool()
       self._register_python_tool()
       self._register_document_tool()
   ```

3. Register filesystem tool:
   ```python
   def _register_filesystem_tool(self) -> None:
       """Register filesystem facade tool."""

       @self.mcp.tool(
           description=(
               "Filesystem operations (list, create, find, read, write, delete, modify, replace). "
               "Write operations run LLM validation for Python files using scripts/automation validators. "
               "Session-based validation with fail-open behavior."
           )
       )
       async def filesystem(
           action: Literal["list", "create", "find", "read", "write", "delete", "modify", "replace"],
           path: str | None = None,
           paths: list[str] | None = None,
           content: str | None = None,
           recursive: bool = False,
           pattern: str | None = None,
           limit: int = 100,
           patterns: list[str] | None = None,
           keywords_path_name: list[str] | None = None,
           keywords_file_content: list[str] | None = None,
           regex_keywords: bool = False,
           use_fast_search: bool = True,
           max_workers: int = 8,
           start_line: int | None = None,
           end_line: int | None = None,
           start_offset_inclusive: int = 0,
           end_offset_inclusive: int = -1,
           offset_type: str = "line",
           output_format: str = "raw_utf8",
           file_encoding: str = "utf-8",
           add_line_numbers: bool | None = None,
           mode: str = "text",
           input_format: str = "raw_utf8",
           validate_with_llm: bool = True,
           new_content: str | None = None,
           old_content: str | None = None,
           is_regex: bool = False,
       ) -> dict[str, Any]:
           return await filesystem_tool(
               self.root_dir,
               action,
               path,
               paths,
               content,
               recursive,
               pattern,
               limit,
               patterns,
               keywords_path_name,
               keywords_file_content,
               regex_keywords,
               use_fast_search,
               max_workers,
               start_line,
               end_line,
               start_offset_inclusive,
               end_offset_inclusive,
               offset_type,
               output_format,
               file_encoding,
               add_line_numbers,
               mode,
               input_format,
               validate_with_llm,
               self.session_id,
               new_content,
               old_content,
               is_regex,
           )
   ```

4. Register git tool:
   ```python
   def _register_git_tool(self) -> None:
       """Register git facade tool."""

       @self.mcp.tool(
           description=(
               "Git operations (status, stage, unstage, commit, diff, history, restore, fetch, pull, push, merge_abort). "
               "Commit calls scripts/git_commit.sh (auto-stages all changes). "
               "Push calls scripts/git_push.sh (runs tests before push)."
           )
       )
       async def git(
           action: Literal[
               "status",
               "stage",
               "unstage",
               "commit",
               "diff",
               "history",
               "restore",
               "fetch",
               "pull",
               "push",
               "merge_abort",
           ],
           repo_path: str | None = None,
           message: str | None = None,
           files: list[str] | None = None,
           stage_all: bool = False,
           unstage_all: bool = False,
           amend: bool = False,
           staged: bool = False,
           limit: int = 10,
           oneline: bool = False,
           grep: str | None = None,
           remote: str = "origin",
           branch: str | None = None,
           fetch_all: bool = False,
           rebase: bool = False,
           force: bool = False,
           set_upstream: bool = False,
           short: bool = False,
           branch: bool = True,
           untracked: bool = True,
       ) -> dict[str, Any]:
           return await git_tool(
               self.root_dir,
               action,
               repo_path,
               message,
               files,
               stage_all,
               unstage_all,
               amend,
               staged,
               limit,
               oneline,
               grep,
               remote,
               branch,
               fetch_all,
               rebase,
               force,
               set_upstream,
               short,
               branch,
               untracked,
           )
   ```

5. Register python tool:
   ```python
   def _register_python_tool(self) -> None:
       """Register python facade tool."""

       @self.mcp.tool(
           description=(
               "Python execution (run, run_background, task_status, task_cancel, list_tasks). "
               "Background tasks return task_id for monitoring and cancellation."
           )
       )
       async def python(
           action: Literal["run", "run_background", "task_status", "task_cancel", "list_tasks"],
           script: str | None = None,
           args: list[str] | None = None,
           timeout: int = 300,
           cwd: str | None = None,
           python: str = "venv",
           task_id: str | None = None,
       ) -> dict[str, Any]:
           return await python_tool(
               self.root_dir,
               action,
               script,
               args,
               timeout,
               cwd,
               python,
               task_id,
           )
   ```

6. Register document tool:
   ```python
   def _register_document_tool(self) -> None:
       """Register document facade tool."""

       @self.mcp.tool(
           description=(
               "Document processing (index, read, read_image). "
               "Index stores documents for search. Read extracts structured data. "
               "read_image analyzes images using multimodal LLM."
           )
       )
       async def document(
           action: Literal["index", "read", "read_image"],
           path: str,
           extraction_template: dict[str, Any] | None = None,
           extract_tables: bool = True,
           extract_images: bool = False,
           storage_backends: list[str] | None = None,
           instruction: str | None = None,
           perform_ocr: bool = True,
           extract_chart_data: bool = False,
       ) -> dict[str, Any]:
           return await document_tool(
               action,
               path,
               extraction_template,
               extract_tables,
               extract_images,
               storage_backends,
               instruction,
               perform_ocr,
               extract_chart_data,
           )
   ```

7. Delete old registration methods:
   - `_register_filesystem_tools()` (8 tools)
   - `_register_git_tools()` and `_register_git_repo_tools()` + `_register_git_remote_tools()` (11 tools)
   - `_register_python_tools()` (5 tools)
   - `_register_document_tools()` (3 tools)

**Deliverables:**
- Updated `filesys_server.py` with 4 tool registrations
- Removed 27 individual tool registrations
- Updated imports
- Comprehensive descriptions for each facade tool

### Phase 7: Update Tests ✅ NOT STARTED

**Goal:** Update test imports and verify all actions work

**Tasks:**

1. Update test imports:
   ```python
   # OLD
   from files.backend.mcp.filesys.tools.filesystem_tools import list_dir_tool

   # NEW
   from files.backend.mcp.filesys.tools.facade import filesystem_tool
   ```

2. Update test calls:
   ```python
   # OLD
   result = await list_dir_tool(root_dir, ".", False, None, 100)

   # NEW
   result = await filesystem_tool(root_dir, "list", path=".", recursive=False, pattern=None, limit=100)
   ```

3. Test all actions for each facade:
   - filesystem: 8 actions
   - git: 11 actions
   - python: 5 actions
   - document: 3 actions

4. Test error handling:
   - Missing required parameters
   - Invalid action names
   - Invalid parameter combinations

5. Test parameter passing:
   - Verify all parameters reach underlying implementations
   - Verify defaults work correctly
   - Verify session_id plumbing for filesystem write

**Deliverables:**
- Updated test files with facade tool calls
- All existing tests passing
- New tests for action dispatch logic

---

## 5. Architecture Principles

### DO:
✅ Create thin facade layer with action dispatch
✅ Keep all implementation logic in existing tool modules
✅ Use Literal types for type-safe action dispatch
✅ Follow browser facade pattern exactly
✅ Maintain backward compatibility in implementation layer
✅ Pass all parameters through to implementations
✅ Validate required parameters in handler functions
✅ Use `**_kwargs` in handlers to ignore unused parameters
✅ Preserve session_id plumbing for validation

### DON'T:
❌ Duplicate implementation code in facades
❌ Delete existing tool modules (filesystem_tools.py, git_tools.py, python_tools.py, document_tools.py)
❌ Change implementation function signatures
❌ Add business logic to facade layer
❌ Create wrapper classes or unnecessary abstractions
❌ Add fallback code or deprecation warnings
❌ Change git_commit.sh or git_push.sh integration

---

## 6. Migration Path

### Backward Compatibility

**Implementation Tools:**
- Keep filesystem_tools.py, git_tools.py, python_tools.py, document_tools.py unchanged
- All 27 implementation functions remain callable
- No breaking changes to function signatures
- Facades are additive (call implementations)

**Server Registration:**
- MCP clients see 4 tools instead of 27
- Each facade tool has action parameter with Literal type
- All original parameters available in facades
- MCP schema changes (fewer tools, action-based)

### Rollback Plan

If issues arise:
1. Revert `filesys_server.py` to old registration methods
2. Keep facade directory (no harm, just unused)
3. Implementation tools still work (unchanged)
4. No data migration required

---

## 7. Testing Strategy

### Unit Tests

**Facade Layer:**
- Test action dispatch logic for each facade
- Test handler functions call correct implementations
- Test parameter passing (all params reach implementations)
- Test error handling (invalid actions, missing params)
- Test `**_kwargs` filtering in handlers

**Implementation Layer:**
- All existing tests pass (unchanged implementation)
- No new tests needed for implementations

### Integration Tests

**MCP Server:**
- Test 4 facade tools registered correctly
- Test MCP schema includes all actions
- Test action parameter validation (Literal types)
- Test all 27 original operations work through facades

### End-to-End Tests

**Real Workflows:**
- Filesystem: list → find → read → write (with validation)
- Git: status → stage → commit → push (scripts integration)
- Python: run → run_background → task_status → task_cancel
- Document: read → index → read_image

---

## 8. Success Criteria

### Functional Requirements

- ✅ **FR-1:** 4 facade tools registered in MCP server
- ✅ **FR-2:** All 27 original operations accessible via facades
- ✅ **FR-3:** Literal types enforce valid actions at compile time
- ✅ **FR-4:** All parameters passed correctly to implementations
- ✅ **FR-5:** session_id plumbing preserved for validation
- ✅ **FR-6:** Git scripts integration preserved (git_commit.sh, git_push.sh)
- ✅ **FR-7:** Error messages include action name for debugging

### Quality Requirements

- ✅ **QR-1:** Zero code duplication (facades are pure dispatch)
- ✅ **QR-2:** No changes to implementation functions
- ✅ **QR-3:** All existing tests pass
- ✅ **QR-4:** Consistent pattern with browser module
- ✅ **QR-5:** Clean handler function structure (one per action)
- ✅ **QR-6:** Comprehensive docstrings in facades

### Performance Requirements

- ✅ **PR-1:** No performance regression (facades add negligible overhead)
- ✅ **PR-2:** Action dispatch is O(1) via dict lookup

---

## 9. Benefits

### API Improvements

1. **Reduced Surface Area:**
   - Before: 27 tools to learn
   - After: 4 tools with clear domains

2. **Better Discoverability:**
   - Before: Which tool for staging files? (git_stage)
   - After: Use git tool with action="stage"

3. **Consistent Pattern:**
   - Browser: 11 facade tools
   - Files: 4 facade tools
   - Same action-dispatch pattern across modules

4. **Type Safety:**
   - Literal types enforce valid actions
   - IDE autocomplete shows available actions
   - Compile-time validation

### Maintainability

1. **Single Entry Point:**
   - One tool per domain (filesystem, git, python, document)
   - Easy to add new actions (add handler + update Literal)
   - Clear separation: facades dispatch, implementations execute

2. **No Duplication:**
   - Facades are thin (50-200 lines each)
   - Implementation logic stays in tool modules (unchanged)
   - Zero code duplication

3. **Easier Testing:**
   - Test facades: action dispatch logic
   - Test implementations: business logic (already tested)
   - Clear separation of concerns

### Developer Experience

1. **Intuitive API:**
   - `filesystem(action="list")` vs 27 tool names
   - Action names match common CLI tools (git status, git commit)
   - Grouped by domain (all git operations in one tool)

2. **Better Documentation:**
   - Comprehensive descriptions per facade
   - Action-specific parameter docs
   - Clear examples in docstrings

3. **Consistent with Browser:**
   - Same pattern across modules
   - Easy to predict API shape
   - Copy-paste facade structure for new modules

---

## 10. Implementation Status

### Phase 1: Create Facade Structure ❌ NOT STARTED

**Status:** Planning

### Phase 2: Implement Filesystem Facade ❌ NOT STARTED

**Status:** Planning

### Phase 3: Implement Git Facade ❌ NOT STARTED

**Status:** Planning

### Phase 4: Implement Python Facade ❌ NOT STARTED

**Status:** Planning

### Phase 5: Implement Document Facade ❌ NOT STARTED

**Status:** Planning

### Phase 6: Update Server Registration ❌ NOT STARTED

**Status:** Planning

### Phase 7: Update Tests ❌ NOT STARTED

**Status:** Planning

---

## 11. Conclusion

This spec defines consolidation of the Filesys MCP server from 27 individual tools to 4 facade tools using the proven action-dispatch pattern from the browser module. The approach eliminates API surface complexity while maintaining zero code duplication through thin dispatch layers.

**Key Principles:**
- Facades are pure dispatch (no business logic)
- Implementations unchanged (all 27 functions remain)
- Consistent with browser module architecture
- Type-safe action dispatch with Literal types
- Backward compatible (implementations still callable)

**Next Steps:**
1. ✅ Review and approve this spec (v1.1 - corrected and verified)
2. Implement Phase 1 (facade structure)
3. Implement Phases 2-5 (facade tools)
4. Implement Phase 6 (server registration)
5. Implement Phase 7 (update tests)
6. Commit and push changes

**v1.1 Corrections:**
- Fixed document_tool parameter order (action first, path second)
- Fixed git facade parameter name (branch, not show_branch)
- Added detailed document facade implementation example in Phase 5
- Clarified that document tools don't take root_dir parameter
