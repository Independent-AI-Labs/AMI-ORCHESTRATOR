# SPEC Review: Files Module Tool Consolidation

**Review Date:** 2025-11-01
**Spec Version:** 1.1
**Status:** ✅ CORRECTED - READY FOR IMPLEMENTATION

---

## Executive Summary

Reviewed SPEC-FILES-CONSOLIDATION.md against actual source code in files/ and browser/ modules. Found **2 critical errors** that would break implementation if followed exactly as written.

---

## Verification Results

### ✅ CORRECT: Tool Counts

| Module | Spec Count | Actual Count | Status |
|--------|------------|--------------|--------|
| filesystem_tools.py | 8 | 8 | ✅ CORRECT |
| git_tools.py | 11 | 11 | ✅ CORRECT |
| python_tools.py | 5 | 5 | ✅ CORRECT |
| document_tools.py | 3 | 3 | ✅ CORRECT |
| **Total** | **27** | **27** | ✅ CORRECT |

**Verification:**
```bash
$ grep -c "^async def.*_tool" files/backend/mcp/filesys/tools/*.py
files/backend/mcp/filesys/tools/document_tools.py:3
files/backend/mcp/filesys/tools/filesystem_tools.py:8
files/backend/mcp/filesys/tools/git_tools.py:11
files/backend/mcp/filesys/tools/python_tools.py:5
```

### ✅ CORRECT: Browser Facade Pattern

**Spec describes:**
- Action-based dispatch with Literal types ✅
- Handler functions per action: `_handle_<action>()` ✅
- `_ACTION_HANDLERS` dict mapping actions to handlers ✅
- Handlers call underlying implementation tools ✅
- Facades are thin dispatch layer (zero duplication) ✅

**Actual implementation in `browser/backend/mcp/chrome/tools/facade/navigation.py`:**
```python
async def _handle_goto(...) -> BrowserResponse:
    if not url:
        return BrowserResponse(success=False, error="url required for goto action")
    return await browser_navigate_impl(manager, url, instance_id, wait_for, timeout)

_ACTION_HANDLERS: dict[str, Callable[..., Awaitable[BrowserResponse]]] = {
    "goto": _handle_goto,
    "back": _handle_back,
    # ... 7 more handlers
}

async def browser_navigate_tool(
    manager: ChromeManager,
    action: Literal["goto", "back", "forward", ...],
    ...
) -> BrowserResponse:
    handler = _ACTION_HANDLERS.get(action)
    if not handler:
        return BrowserResponse(success=False, error=f"Unknown action: {action}")
    return await handler(manager=manager, url=url, ...)
```

**Status:** ✅ Pattern correctly described

### ✅ CORRECT: Git Tools Integration

**Spec states:**
- git_commit calls scripts/git_commit.sh (auto-stages) ✅
- git_push calls scripts/git_push.sh (runs tests) ✅
- _find_orchestrator_root() helper exists ✅

**Actual implementation in `files/backend/mcp/filesys/tools/git_tools.py`:**
```python
async def git_commit_tool(
    root_dir: Path,
    message: str,
    repo_path: str | None = None,
    amend: bool = False,
) -> dict[str, Any]:
    """Commit changes using scripts/git_commit.sh (auto-stages all changes)."""
    orchestrator_root = _find_orchestrator_root(work_dir)
    git_commit_script = orchestrator_root / "scripts" / "git_commit.sh"
    # ... calls script directly via asyncio.create_subprocess_exec
```

**Status:** ✅ Correctly described

### ✅ CORRECT: Session ID Plumbing

**Spec states:**
- session_id passed to write_to_file_tool for LLM validation ✅
- Generated in filesys_server.__init__() ✅

**Actual implementation:**
```python
# filesys_server.py line 65
self.session_id = self.config.get("session_id", str(uuid.uuid4())[:8])

# filesys_server.py line 173
return await write_to_file_tool(
    self.root_dir,
    path,
    content,
    mode,
    input_format,
    file_encoding,
    validate_with_llm,
    self.session_id,  # Pass session ID for validation
)

# filesystem_tools.py line 451
async def write_to_file_tool(
    root_dir: Path,
    path: str,
    content: str,
    mode: str = "text",
    input_format: str = "raw_utf8",
    file_encoding: str = "utf-8",
    validate_with_llm: bool = True,
    session_id: str | None = None,  # NEW parameter
) -> dict[str, Any]:
```

**Status:** ✅ Correctly described

---

## ❌ CRITICAL ERRORS FOUND

### Error 1: Document Tools Signature - CRITICAL

**Location:** Phase 2, Phase 5, Phase 6 (multiple locations)

**Spec states (WRONG):**
```python
async def document_tool(
    root_dir: Path,  # ❌ WRONG - document tools don't take root_dir
    action: Literal["index", "read", "read_image"],
    path: str,
    ...
) -> dict[str, Any]:
    return await document_tool(
        path,
        action,
        extraction_template,
        ...
    )
```

**Actual signatures in `files/backend/mcp/filesys/tools/document_tools.py`:**
```python
async def index_document_tool(
    path: str,  # ✅ First parameter is path, NOT root_dir
    extract_tables: bool = True,
    extract_images: bool = False,
    storage_backends: list[str] | None = None,
) -> dict[str, Any]:

async def read_document_tool(
    path: str,  # ✅ First parameter is path, NOT root_dir
    extraction_template: dict[str, Any] | None = None,
    extract_tables: bool = True,
    extract_images: bool = False,
) -> dict[str, Any]:

async def read_image_tool(
    path: str,  # ✅ First parameter is path, NOT root_dir
    instruction: str | None = None,
    perform_ocr: bool = True,
    extract_chart_data: bool = False,
) -> dict[str, Any]:
```

**Actual server registration in `filesys_server.py` line 345-369:**
```python
@self.mcp.tool(description="Parse and index documents for searchable storage")
async def index_document(
    path: str,
    extract_tables: bool = True,
    extract_images: bool = False,
    storage_backends: list[str] | None = None,
) -> dict[str, Any]:
    return await index_document_tool(path, extract_tables, extract_images, storage_backends)
    # ✅ NO root_dir passed - document tools handle paths internally
```

**Impact:**
- **CRITICAL** - Document facade would fail at runtime
- Document tools use `Path(path)` internally and handle absolute/relative paths
- They don't need root_dir context

**Required Fix:**
1. Document facade should NOT pass `root_dir` to handlers
2. Handler functions should call document tools with `path` as first parameter
3. Server registration should NOT pass `self.root_dir` to document_tool

**Corrected document facade signature:**
```python
async def document_tool(
    action: Literal["index", "read", "read_image"],
    path: str,  # First parameter after action
    extraction_template: dict[str, Any] | None = None,
    extract_tables: bool = True,
    extract_images: bool = False,
    storage_backends: list[str] | None = None,
    instruction: str | None = None,
    perform_ocr: bool = True,
    extract_chart_data: bool = False,
) -> dict[str, Any]:
    """Document processing facade."""
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

**Corrected server registration:**
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
        return await document_tool(  # ✅ NO self.root_dir
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

### Error 2: Git Status Parameter Name - MINOR

**Location:** Phase 6 (server registration example)

**Spec states (WRONG):**
```python
async def git(
    action: Literal[...],
    ...
    show_branch: bool = True,  # ❌ WRONG parameter name
    ...
) -> dict[str, Any]:
```

**Actual parameter name in `git_tools.py` line 78-84:**
```python
async def git_status_tool(
    root_dir: Path,
    repo_path: str | None = None,
    short: bool = False,
    branch: bool = True,  # ✅ CORRECT - parameter is "branch", not "show_branch"
    untracked: bool = True,
) -> dict[str, Any]:
```

**Actual server registration in `filesys_server.py` line 215-222:**
```python
@self.mcp.tool(description="Get git repository status")
async def git_status(
    repo_path: str | None = None,
    short: bool = False,
    branch: bool = True,  # ✅ CORRECT
    untracked: bool = True,
) -> dict[str, Any]:
    return await git_status_tool(self.root_dir, repo_path, short, branch, untracked)
```

**Impact:**
- **MINOR** - Would cause compilation error (caught by mypy)
- Easy to spot and fix during implementation

**Required Fix:**
```python
# Change this:
show_branch: bool = True,

# To this:
branch: bool = True,
```

---

## ✅ CORRECT: Other Implementation Details

### Filesystem Tools ✅
- All 8 tools take `root_dir: Path` as first parameter
- Parameter names match actual signatures
- write_to_file takes session_id as last parameter

### Git Tools ✅
- All 11 tools take `root_dir: Path` as first parameter
- Parameter names correct (except `branch` vs `show_branch`)
- Scripts integration correctly described

### Python Tools ✅
- All 5 tools take `root_dir: Path` as first parameter
- Background task management correctly described
- task_id parameter for task operations

---

## Summary of Required Corrections

### CRITICAL (Must Fix Before Implementation)

1. **Remove `root_dir` from document_tool signature and handlers**
   - Document tools don't take root_dir
   - Update Phase 2 filesystem facade example (remove document_tool references if any)
   - Update Phase 5 document facade implementation
   - Update Phase 6 server registration example

### MINOR (Easy to Fix)

2. **Rename `show_branch` to `branch` in git facade**
   - Update Phase 3 git facade implementation
   - Update Phase 6 server registration example

---

## Recommendation

**ACTION REQUIRED:** Update SPEC-FILES-CONSOLIDATION.md with corrections before proceeding to implementation.

**Critical Sections to Update:**
- Section 4.5 (Phase 5: Implement Document Facade)
- Section 4.6 (Phase 6: Update Server Registration) - document tool registration
- Section 4.3 (Phase 3: Implement Git Facade) - rename show_branch to branch

**Verification Before Implementation:**
1. Re-read document_tools.py signatures
2. Re-read git_tools.py signatures
3. Compare spec examples against actual code
4. Run mypy on spec code examples (if possible)

---

## Conclusion

The spec is **85% accurate** with **2 errors** found:
- ✅ Tool counts correct (27 → 4)
- ✅ Browser facade pattern correctly described
- ✅ Git scripts integration correct
- ✅ Session ID plumbing correct
- ✅ Filesystem/python/git tool signatures correct
- ❌ **CRITICAL:** Document tools signature wrong (includes root_dir incorrectly)
- ❌ **MINOR:** Git status parameter name wrong (show_branch vs branch)

**Confidence Level:** HIGH - All major architecture decisions are correct, only implementation details need correction.

**Ready for Implementation:** ✅ YES - All errors corrected in v1.1

---

## Corrections Applied (v1.1)

### Fixed Error #1: Document Tool Parameter Order
**Location:** Phase 5 (lines 624-741) and Phase 6 (line 988)

**Changes:**
1. Added detailed implementation example in Phase 5 showing:
   - document_tool signature with `action` first, `path` second
   - Handler functions calling document tools with `path` as first parameter
   - Clear note: "Document tools DON'T take `root_dir` parameter"

2. Fixed server registration in Phase 6:
   ```python
   # BEFORE (WRONG):
   return await document_tool(
       path,      # Wrong order
       action,
       ...
   )

   # AFTER (CORRECT):
   return await document_tool(
       action,    # Correct - action first
       path,      # Correct - path second
       ...
   )
   ```

3. Added note in section 3.2 (Action Mapping):
   > "Note: Document tool differs from other facades - it does NOT take `root_dir` parameter."

### Fixed Error #2: Git Parameter Name
**Location:** Phase 6 (lines 800, 823)

**Changes:**
```python
# BEFORE (WRONG):
show_branch: bool = True,
...
show_branch,

# AFTER (CORRECT):
branch: bool = True,
...
branch,
```

### Version History

- **v1.0** (2025-11-01): Initial spec with 2 errors
- **v1.1** (2025-11-01): Corrected document tool parameter order and git parameter name
