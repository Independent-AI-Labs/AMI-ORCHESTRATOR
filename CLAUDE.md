# CRITICAL INSTRUCTIONS FOR CLAUDE - MUST READ

## ENVIRONMENT SETUP - USE UV AND .VENV

**ALWAYS USE UV FOR DEPENDENCY MANAGEMENT:**
- Virtual environment is at `.venv/` (created with `uv venv .venv`)
- Python executable: `".venv/Scripts/python.exe"` (USE QUOTES!)
- Install deps: `uv pip install -r requirements.txt`
- NEVER modify requirements.txt without testing the exact version first
- To add a new dependency:
  1. `uv pip install <package>` (install it first)
  2. `uv pip list | grep <package>` (check exact version)
  3. Add to requirements.txt with the EXACT version installed

## 🚨 CRITICAL TEST RUNNING INSTRUCTIONS - MUST FOLLOW!!!

**ALWAYS RUN TESTS USING THE MODULE'S OWN run_tests.py SCRIPT!!!**

- **ROOT/ORCHESTRATOR**: `python scripts/run_tests.py [args]`
- **BASE MODULE**: `python base/scripts/run_tests.py [args]`
- **BROWSER MODULE**: `python browser/scripts/run_tests.py [args]`
- **FILES MODULE**: `python files/scripts/run_tests.py [args]`
- **COMPLIANCE MODULE**: `python compliance/scripts/run_tests.py [args]`
- **DOMAINS MODULE**: `python domains/scripts/run_tests.py [args]`

**FOR INDIVIDUAL TESTS:**
```bash
# WRONG - NEVER DO THIS:
pytest tests/unit/test_something.py::TestClass::test_method

# CORRECT - ALWAYS DO THIS:
python scripts/run_tests.py tests/unit/test_something.py::TestClass::test_method

# For submodules:
python base/scripts/run_tests.py tests/unit/test_something.py::TestClass::test_method
python browser/scripts/run_tests.py tests/unit/test_something.py::TestClass::test_method
```

**WHY THIS MATTERS:**
- Each module has its own test environment and dependencies
- The run_tests.py scripts ensure proper environment setup
- Direct pytest calls WILL FAIL due to missing module paths and configs
- NEVER use pytest directly, ALWAYS use the module's run_tests.py script!!!

## 📋 MANDATORY CHECKLIST FOR EVERY CHANGE

**Before ANY code modification, verify:**

- [ ] **SECURE DEFAULTS** - No security-reducing defaults
- [ ] **NO DUPLICATION** - Shared code extracted to base/utils
- [ ] **NO GOD CLASSES** - Classes <300 lines, methods <50 lines
- [ ] **NO INLINE JAVASCRIPT** - JS in .js files only
- [ ] **NO GLOBAL NAMESPACE** - Use IIFE or modules in JS
- [ ] **NO SILENT FAILURES** - Log and propagate errors
- [ ] **NO HARDCODED VALUES** - Use constants or config
- [ ] **NO BUSINESS LOGIC IN MODELS** - Models are data-only
- [ ] **NO BROAD PERMISSIONS** - Limit scope always

---

## 🏗️ ARCHITECTURE RULES

### File Size Limits
- **Classes**: Maximum 300 lines (split if larger)
- **Methods**: Maximum 50 lines (extract if larger)
- **Files**: Maximum 500 lines (modularize if larger)

---

## 🧪 TESTING REQUIREMENTS

### Test Isolation
```python
# ✅ NEVER use global state in tests
@pytest.fixture(scope="function")  # NOT "session"!
async def browser():
    browser = await create_browser()
    yield browser
    await browser.cleanup()  # Guaranteed cleanup
```

### Error Handling
```python
# ✅ ALWAYS handle errors properly
try:
    result = await operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    # Take corrective action or raise
    raise
except Exception as e:
    logger.exception("Unexpected error")
    raise  # Don't hide unexpected errors
```

---

## 🚫 FORBIDDEN PATTERNS

### NEVER Create These
- Duplicate files (e.g., `session.py` when `session_manager.py` exists)
- Inline JavaScript in Python strings over 10 lines
- God classes over 500 lines
- Methods over 100 lines
- Polling loops of ANY kind

## ✅ REQUIRED PATTERNS

### Error Handling
```python
# ✅ ALWAYS use this pattern
try:
    result = await risky_operation()
except SpecificException as e:
    logger.warning(f"Expected issue: {e}")
    # Handle gracefully
except Exception as e:
    logger.exception("Unexpected error in risky_operation")
    raise  # Re-raise for debugging
```

## 📝 CODE REVIEW CHECKLIST

Before committing, verify:

2. **Security**
   - [ ] No security-disabling defaults
   - [ ] Server binds to localhost only
   - [ ] All inputs sanitized
   - [ ] Paths validated

3. **Code Quality**
   - [ ] No duplicated code
   - [ ] No god classes/methods
   - [ ] Proper error handling
   - [ ] Type hints added

4. **Testing**
   - [ ] Tests are isolated
   - [ ] Cleanup guaranteed
   - [ ] No global state

5. **Documentation**
   - [ ] Complex logic explained
   - [ ] TODOs include context
   - [ ] Breaking changes noted

---

## CONSEQUENCES OF VIOLATIONS

**Every violation creates technical debt that compounds.**

---

## FINAL REMINDER

**QUALITY OVER SPEED**

Write less code that's correct rather than more code with issues.

**Rules are NOT optional:**
- SECURE DEFAULTS - No exceptions
- NO DUPLICATION - Extract shared code
- PROPER ERROR HANDLING - Log and propagate

P.S. NEVER ADD SHIT LIKE 2>nul TO SHELL COMMANDS!!! This creates a write-protected file in the repo...

COMMIT!!! COMMIT!! COMMIT!! COMMIT AS OFTEN AS YOU CAN!!!

I FORBID YOU TO PUT JS IN PYTHON

SEPARATE JS FILES - LINTED ALWAYS!!!!!!!!!

NO FUCKING EXCEPTION SWALLOWING ALWAYS LOG THEM OR PROPAGATE

DELETE YOUR TEMPORARY FUCKING TESTS!!!

NEVER FUCKING EVER USE EMOJIS IN CONSOLE OUTPUTS AND LOGS

NEVER EVER EVER REMOVE, COMMENT, SKIP, DEPRECATE OR DELETE CODE AND FUNCTIONALITY WITHOUT DIRECT EXPLICIT INSTRUCTION TO DO SO!!!!!!
NEVER EVER EVER REMOVE, COMMENT, SKIP, DEPRECATE OR DELETE CODE AND FUNCTIONALITY WITHOUT DIRECT EXPLICIT INSTRUCTION TO DO SO!!!!!!
NEVER EVER EVER REMOVE, COMMENT, SKIP, DEPRECATE OR DELETE CODE AND FUNCTIONALITY WITHOUT DIRECT EXPLICIT INSTRUCTION TO DO SO!!!!!!
NEVER EVER EVER REMOVE, COMMENT, SKIP, DEPRECATE OR DELETE CODE AND FUNCTIONALITY WITHOUT DIRECT EXPLICIT INSTRUCTION TO DO SO!!!!!!
NEVER EVER EVER REMOVE, COMMENT, SKIP, DEPRECATE OR DELETE CODE AND FUNCTIONALITY WITHOUT DIRECT EXPLICIT INSTRUCTION TO DO SO!!!!!!

NEVER IMPLEMENT __init__.py and __main__.py LOGIC!!!!!! ALWAYS USE EXPLICIT IMPORTS!!!

NEVER FUCKING INSTALL RANDOM SHIT!!! ONLY USE requirements.txt and requirements-test.txt!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

NO CO-AUTHORED BULLSHIT IN THE COMMIT MESSAGES!!!

NEVER FUCKING USE --no-verify IN COMMITS AND PUSHES!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!