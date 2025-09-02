# Quality Assurance - Configuration Management Fix

## CRITICAL ISSUE
Cross-module imports are failing in mypy because pre-commit templates don't properly configure MYPYPATH to find the base module from submodules.

## ROOT CAUSE
1. Base pre-commit templates (`base/configs/*.yaml`) don't set up proper paths for mypy
2. No mypy.ini template exists - each module has inconsistent configuration
3. Orchestrator module_setup.py doesn't update all submodules consistently
4. Python version mismatches between python.ver files and mypy.ini configs

## REQUIREMENTS

### ABSOLUTE REQUIREMENTS - NO EXCEPTIONS
- **NO CHEATING**: Do not use `ignore_missing_imports` for base module
- **NO SHORTCUTS**: Do not use `--no-verify` in commits
- **NO SKIPPING**: All tests must run and pass
- **100% SUCCESS**: ALL modules must have ALL tests passing
- **PROPER FIXES**: Fix root cause in templates, not individual modules

### Technical Requirements
1. **Mypy Configuration**:
   - Must resolve imports from base module (e.g., `base.backend.dataops.models.base_model`)
   - Must use Python version from python.ver file as source of truth
   - Must have consistent strict settings across all modules

2. **Pre-commit Configuration**:
   - Must work on Windows and Unix
   - Must set MYPYPATH or run from parent directory
   - Must not pass filenames to mypy to avoid duplicate module errors

3. **Module Setup Automation**:
   - Orchestrator module_setup.py must update ALL submodules
   - Must copy platform-specific pre-commit configs
   - Must generate mypy.ini from template with correct Python version

## COMPREHENSIVE TODO LIST

### Phase 1: Fix Base Templates
- [ ] Update `base/configs/.pre-commit-config.win.yaml`
  - Change mypy entry to run from parent directory or set MYPYPATH
  - Ensure no filenames are passed to mypy
  - Test on Windows environment

- [ ] Update `base/configs/.pre-commit-config.unix.yaml`  
  - Same fixes as Windows version
  - Test on Unix environment

- [ ] Create `base/configs/mypy.ini.template`
  - Include `mypy_path = ..` for cross-module imports
  - Use placeholder for Python version: `python_version = {{PYTHON_VERSION}}`
  - Include all strict type checking settings

### Phase 2: Update Setup Scripts
- [ ] Update `base/module_setup.py`
  - Add function to generate mypy.ini from template
  - Read Python version from python.ver file
  - Substitute version in template and write mypy.ini

- [ ] Update orchestrator `module_setup.py`
  - Loop through ALL submodules: base, browser, files, compliance, domains, ux, streams
  - Call base/module_setup.py for each module
  - Ensure consistent configuration

### Phase 3: Execute Setup
- [ ] Run orchestrator module_setup.py
  - Verify it processes all modules
  - Check that configs are copied correctly
  - Ensure mypy.ini files are generated

### Phase 4: Verification
- [ ] Test mypy in each module:
  - `cd base && .venv/Scripts/python.exe -m mypy backend`
  - `cd browser && .venv/Scripts/python.exe -m mypy backend`
  - `cd files && .venv/Scripts/python.exe -m mypy backend`
  - etc. for all modules

- [ ] Run tests in each module:
  - `cd base && python scripts/run_tests.py`
  - `cd browser && python scripts/run_tests.py`
  - `cd files && python scripts/run_tests.py`
  - etc. - ALL must achieve 100% pass rate

- [ ] Test pre-commit hooks:
  - Make a test change in each module
  - Verify pre-commit runs and mypy works correctly

### Phase 5: Commit and Push
- [ ] Stage all changes
- [ ] Commit with message: "fix: Centralized configuration management with proper cross-module support"
- [ ] Push to origin/main with 300000ms timeout

## SUCCESS CRITERIA
1. ALL modules have consistent configuration from templates
2. Mypy can resolve cross-module imports without ignore_missing_imports
3. ALL tests pass in ALL modules (100% success rate)
4. Pre-commit hooks work correctly in ALL modules
5. Python versions are synchronized from python.ver files

## AGENT EXECUTION PLAN

### Agent 1: Fix Base Templates
**Task**: Update pre-commit templates and create mypy.ini.template
**Files to modify**:
- base/configs/.pre-commit-config.win.yaml
- base/configs/.pre-commit-config.unix.yaml
- base/configs/mypy.ini.template (create new)

**Requirements**:
- Mypy must run from parent directory OR have MYPYPATH set
- No filenames passed to mypy
- Template must use {{PYTHON_VERSION}} placeholder

### Agent 2: Update Setup Scripts
**Task**: Enhance module_setup.py scripts for proper configuration management
**Files to modify**:
- base/module_setup.py
- module_setup.py (orchestrator root)

**Requirements**:
- Generate mypy.ini from template
- Process ALL submodules
- Maintain python.ver as source of truth

### Agent 3: Execute and Verify
**Task**: Run setup and verify all modules work correctly
**Commands**:
- Run orchestrator module_setup.py
- Test mypy in all modules
- Run tests in all modules

**Requirements**:
- 100% test pass rate
- No mypy errors except expected StorageModel inheritance (if truly unavoidable)
- All pre-commit hooks functional

## TRACKING
- Created: 2025-09-02
- Issue: Cross-module import failures in mypy
- Solution: Centralized configuration with proper path setup
- Status: IN PROGRESS