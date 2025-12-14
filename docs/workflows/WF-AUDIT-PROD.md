# Production Audit Process: Identifying Vibe-Coded Bullshit

This document outlines the steps to systematically identify and address all forms of vibe-coded bullshit in production code that masquerades as functionality but provides no real value or reliability.

## Key Principle: No Vibe-Coded Bullshit Tolerance
You must identify and eliminate ALL placeholder implementations, magical thinking, fake functionality, superficial implementations, unjustified assumptions, and anything that looks like code but doesn't actually function in production. No accepting code that appears to work but doesn't actually deliver on its promises.
- Look for fake "backup" systems that don't backup anything meaningful
- Identify false "validation" that doesn't validate real state
- Reject arbitrary magic numbers without justification
- Address pretended functionality that assumes mythical dependencies exist
- Eliminate surface-level implementations that don't understand actual requirements
- Remove any code that makes unfounded assumptions about system state or dependencies

## Phase 1: List the Targets & Add TODOs

1. **Identify Target Files (ONLY as explicitly instructed by the user)**:
   - DO NOT use grep, find, or any automated detection tools to identify files
   - ONLY list files that the user has explicitly instructed you to audit
   - Create a TODO list for ONLY the specific targets mentioned by the user
   - Example: If user says "audit launcher/production", only list files in that directory
   - DO NOT expand beyond explicitly requested targets

2. **Create Individual TODOs**:
   - For each explicitly requested file/directory, create dedicated TODO entries
   - Example: `TODO: Audit /path/to/file.py for vibe-coded bullshit`
   - Document scope: all files containing placeholder functionality, false claims, magical assumptions, arbitrary limitations

3. **Create Audit Report**:
   - Create individual TODO entries for tracking audit progress
   - Focus ONLY on targets explicitly requested by the user

## Phase 2: Audit Them One by One

1. **Process Each Target File**:
   - Take each file from the TODO list and audit systematically
   - Examine ALL functions that claim to provide critical functionality (backup, rollback, validation, deployment, monitoring, etc.)
   - Check for functions that return hardcoded values without actual implementation
   - Look for "smart" filtering with arbitrary constants (e.g., ports 8000-9999 with no justification)
   - Find validation that only checks file existence, not actual state integrity
   - Look for "get_running_services" that just does pgrep without understanding service topology
   - Find "backup" functions that don't backup meaningful state
   - Identify functions that assume external dependencies exist without verification

2. **Apply Vibe-Coded Bullshit Identification Rules**:
   - Use the complete identification rules (see end of document) to systematically check each function
   - Document findings for each file being audited
   - Mark each TODO as completed after thorough audit

3. **Handle Audit Findings**:
   - Create detailed notes on ALL vibe-coded implementations found
   - Document ALL assumptions that aren't validated in code

## Phase 3: Produce a Final Report .MD Document

1. **Compile Comprehensive Report**:
   - Create `docs/audit/AUDIT_SUMMARY.md` (or appropriate name based on module) with detailed findings from all file audits
   - Include number of files audited, issues found, and status of each TODO
   - Document which vibe-coded implementations were found in each file
   - Track completion status of audit process

2. **Complete Documentation**:
   - Record ALL arbitrary constants without configuration options or justification
   - Note any "validation" that doesn't actually validate system health or consistency
   - Track ALL functions that assume mythical dependencies or services exist
   - Catalog ALL surface-level implementations that don't understand the actual problem
   - Document ALL error handling that ignores failures but continues execution
   - List ALL functions that make assumptions about system state without verification

3. **Final Validation**:
   - Verify all TODOs have been completed
   - Confirm all target files have been audited
   - Ensure comprehensive coverage of all vibe-coded implementations

## Vibe-Coded Bullshit Identification Rules - COMPLETE LIST
1. Magic numbers without justification - Always question arbitrary limits and ranges
2. Fake state management - Functions that claim to track state but only collect surface-level info
3. Assumed dependencies - Code that expects mythical services or data without verification
4. Placebo validation - Checks that verify nothing meaningful about actual system health
5. Pretended complexity - Functions that sound sophisticated but implement trivial logic
6. Fantasy integrations - Assumptions about external systems without actual integration
7. Surface-level inspection - Using pgrep, lsof, etc. as if that represents deep system understanding
8. Meaningless snapshots - Capturing process lists and ports without application context
9. Ignored errors - Try/catch blocks that silently ignore ALL exceptions
10. False success - Functions that claim success when they actually failed
11. Assumption without validation - Code that assumes system state without checking
12. Placeholder implementations - Functions with "TODO", "FIXME", or fake return values
13. Fake configuration - Hardcoded values instead of configurable parameters
14. Pretended security - Security functions that provide no actual protection
15. Fake scalability - Systems designed without consideration for actual load requirements
16. Mythical data sources - Code that assumes data exists without verifying availability
17. Bogus error recovery - Recovery mechanisms that don't actually fix anything
18. Magical thinking - Code that assumes certain conditions are always true
19. Fake monitoring - Monitoring that reports false status or ignores actual failures
20. Placebo deployment - Deployment systems without real rollback capabilities
21. Unvalidated input - Functions that accept parameters without validation
22. False promises - Async functions that don't actually handle async operations properly
23. Fake reliability - Systems without actual redundancy or failover
24. Imagined performance - Code without actual performance considerations
25. Pretended logging - Logging that doesn't provide actionable information
26. False metrics - Metrics that don't represent actual system performance
27. Bogus authentication - Authentication without actual security measures
28. Fake authorization - Authorization that doesn't enforce actual access controls
29. Phantom testing - Tests that don't actually test functionality
30. Surface-level fixes - Fixes that address symptoms but not root causes