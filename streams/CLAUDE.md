# CRITICAL INSTRUCTIONS FOR CLAUDE - MUST READ

## ENVIRONMENT SETUP - USE UV AND .VENV

**ALWAYS USE UV FOR DEPENDENCY MANAGEMENT:**
- Virtual environment is at `.venv/` (created with `uv venv .venv`)
- Python executable: `".venv/Scripts/python.exe"` (USE QUOTES!)
- Install deps: `uv pip install -r requirements.txt`
- Run tests: `python run_tests.py [args]` or `".venv/Scripts/python.exe" -m pytest`
- NEVER modify requirements.txt without testing the exact version first
- To add a new dependency:
  1. `uv pip install <package>` (install it first)
  2. `uv pip list | grep <package>` (check exact version)
  3. Add to requirements.txt with the EXACT version installed

## CHROME AND CHROMEDRIVER PATHS - ALWAYS CONFIGURED

**NEVER ASK WHERE CHROME IS - IT'S ALWAYS HERE:**
- Chrome binary: `./chromium-win/chrome.exe` (relative to project root)
- ChromeDriver: `./chromedriver.exe` (relative to project root)
- These are automatically configured in `backend/utils/config.py`
- The Config class automatically converts these to absolute paths
- Tests will use these paths automatically
- STOP LOOKING FOR CHROME - IT'S FUCKING CONFIGURED

## 🚨 ABSOLUTE REQUIREMENTS

### NO POLLING - USE EVENTS ONLY
**Polling is FORBIDDEN. Use event-driven architecture ALWAYS.**

```python
# ❌ FORBIDDEN - NO POLLING AT ALL
while True:
    check_something()  # NO!
    time.sleep(ANY_VALUE)  # NO POLLING!

# ❌ FORBIDDEN - JavaScript polling
setInterval(() => { check(); }, ANY_INTERVAL);  # NO!

# ✅ REQUIRED - Event-driven only
await page.on('target.created', handle_new_tab)
# Use CDP events, MutationObserver, callbacks, promises
# If you can't use events, DON'T IMPLEMENT IT
```

### SECURE BY DEFAULT - NO EXCEPTIONS
```python
# ❌ NEVER SET THESE AS DEFAULTS - EVER!
"--disable-web-security"  # FORBIDDEN as default
"--disable-features=IsolateOrigins"  # FORBIDDEN as default
"--allow-running-insecure-content"  # FORBIDDEN as default
server_host = "0.0.0.0"  # FORBIDDEN - security disaster!

# ✅ REQUIRED DEFAULTS
server_host = "127.0.0.1"  # Local only
headless = True  # Safe default
# Security flags ONLY when user explicitly requests with warnings
```

### NO CODE DUPLICATION - PERIOD
```python
# If code appears in 2+ places, it MUST be extracted
# Create base classes, utilities, or services
# NO COPY-PASTE EVER
```

---

## 📋 MANDATORY CHECKLIST FOR EVERY CHANGE

**Before ANY code modification, verify:**

- [ ] **NO POLLING** - Events only, no loops checking state
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

### Module Organization
```python
# ✅ CORRECT MODULE STRUCTURE
module/
├── __init__.py          # Minimal exports only
├── base.py             # Base classes with shared code
├── models.py           # Data models (NO business logic)
├── services.py         # Business logic here
├── utils.py            # Stateless utilities
└── constants.py        # All constants in one place
```

### JavaScript Management
```javascript
// ✅ ALWAYS use this pattern for browser scripts
(function() {
    'use strict';
    try {
        // Your code here - NO POLLING
    } catch (e) {
        // Silent fail, don't expose automation
    }
})();
```

---

## ⚡ PERFORMANCE REQUIREMENTS

### Event-Driven Architecture
```python
# ✅ REQUIRED - Use events
page.on('load', handle_load)
page.on('domcontentloaded', handle_dom)
driver.implicitly_wait(timeout)  # Let driver handle waiting

# ❌ FORBIDDEN - Polling
while not element_found:  # NO!
    time.sleep(0.1)  # NO POLLING!
```

### Timing Constants (USE THESE!)
```python
# constants.py - Create this file!
class Timing:
    DEFAULT_WAIT = 0.5            # Standard wait time
    DEFAULT_TIMEOUT = 30          # Standard timeout
    # NO POLLING INTERVALS - WE DON'T POLL
```

---

## 🔒 SECURITY REQUIREMENTS

### Default Configuration
```python
# ✅ SECURE DEFAULTS - NO EXCEPTIONS
DEFAULT_CONFIG = {
    "server_host": "127.0.0.1",  # NEVER 0.0.0.0
    "headless": True,             # NEVER False by default
    "disable_security": False,    # NEVER True by default
    "permissions": "limited"      # NEVER "all" by default
}
```

### Input Validation
```python
# ✅ ALWAYS sanitize JavaScript inputs
def sanitize_selector(selector: str) -> str:
    # Escape special characters
    return selector.replace("'", "\\'").replace('"', '\\"')

# ✅ ALWAYS validate paths
def validate_path(path: str) -> Path:
    path = Path(path).resolve()
    if not path.is_relative_to(BASE_DIR):
        raise SecurityError("Path traversal attempt")
    return path
```

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

### NEVER Use These Patterns
```python
# ❌ ALL FORBIDDEN
except: pass                     # Silent failure
except Exception: pass           # Swallowing exceptions
while True: time.sleep(X)        # NO POLLING
for i in range(N): time.sleep(X) # NO POLLING
"<all_urls>"                     # Broad permissions
lambda in Pydantic fields        # Serialization issues
_private_var access from outside # Encapsulation violation
```

---

## ✅ REQUIRED PATTERNS

### Event-Driven Only
```python
# ✅ Use WebDriverWait
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

element = WebDriverWait(driver, timeout).until(
    EC.presence_of_element_located((By.ID, "myId"))
)

# ✅ Use CDP events
await page.on('framenavigated', handle_navigation)

# ✅ Use MutationObserver in JS
const observer = new MutationObserver(callback);
observer.observe(document, config);
```

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

### Resource Management
```python
# ✅ ALWAYS use context managers
async with get_browser() as browser:
    # Use browser
    pass  # Automatic cleanup

# ✅ ALWAYS cleanup in finally
resource = None
try:
    resource = acquire_resource()
    # Use resource
finally:
    if resource:
        resource.cleanup()
```

### Configuration
```python
# ✅ ALWAYS use configuration files
CONFIG = Config.load("config.yaml")
timeout = CONFIG.get("timeout", DEFAULT_TIMEOUT)

# ❌ NEVER hardcode
timeout = 30  # Bad!
```

---

## 📝 CODE REVIEW CHECKLIST

Before committing, verify:

1. **Performance**
   - [ ] NO polling loops (use events only)
   - [ ] No unnecessary sleeps
   - [ ] WebDriverWait or CDP events used

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

## 🎯 WHEN IN DOUBT

If you're unsure about something:

1. **Use events, not polling** - If you can't use events, don't implement it
2. **Secure by default** - Make the safe choice
3. **Extract shared code** - Don't duplicate
4. **Keep it simple** - Readable > clever
5. **Ask for clarification** - Better to ask than assume

---

## CONSEQUENCES OF VIOLATIONS

**Every violation creates technical debt that compounds.**

---

## FINAL REMINDER

**QUALITY OVER SPEED**

Write less code that's correct rather than more code with issues.

**Rules are NOT optional:**
- NO POLLING - Use events or don't implement
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