# Critical Tasks Process: Handling Urgent Issues Workflow

This document outlines the immediate response protocol when critical issues, security vulnerabilities, or functional regressions are identified in the AMI Orchestrator system.

## Key Principle: Stop, Assess, Prioritize, Address
When critical issues, security vulnerabilities, or functional regressions are reported, you must immediately stop all ongoing work, assess the issue, create prioritized tasks, and address these critical items before resuming any other work.
- No exceptions to this hierarchy of priorities
- Never continue ongoing work when critical issues are present
- Always address root causes, not just symptoms

## CRITICAL: IMMEDIATE ESCALATION REQUIRED
You MUST immediately stop all other tasks and prioritize critical issues:
- When user reports critical issues, security vulnerabilities, or functional regressions
- When automated systems detect potential security issues
- When any potential vulnerabilities or functional regressions are identified
- This takes absolute precedence over all other tasks

## Phase 1: Critical Assessment & Task Creation

1. **Immediate Task Creation**:
   - Stop current work immediately when critical issues are identified
   - Create new tasks for the TOP of the todo list with "CRITICAL:" prefix
   - Document the specific issue, potential impact, and urgency level
   - Example: `CRITICAL: Security vulnerability in authentication system`, `CRITICAL: Data corruption bug`, etc.

2. **Issue Triage**:
   - All reported critical issues, security vulnerabilities, and functional regressions are treated as maximum priority
   - No assessment of severity needed - all are handled with immediate priority
   - Determine if issue impacts security, data integrity, or core functionality
   - Create detailed task entries with specific action items
   - Add tasks to the top of the todo list regardless of current work

## Phase 2: Task Reorganization & Focus Shift

1. **Todo List Reorganization**:
   - Move all critical tasks to the top of the todo list
   - Mark all ongoing non-critical tasks as PAUSED (not completed)
   - Update current progress state before shifting focus
   - Ensure critical tasks are in proper priority order

2. **Focus Shift Execution**:
   - Only work on critical tasks until resolution is confirmed
   - Do not return to original tasks until critical items are resolved
   - Document all actions taken and their outcomes
   - Verify resolution before resuming other work

## Phase 3: Critical Issue Resolution

1. **Systematic Resolution**:
   - Address each critical task in order of priority
   - Follow architectural patterns and project standards
   - Maintain same quality and security standards as regular work
   - Do not take shortcuts, even under time pressure

2. **Verification & Validation**:
   - Test resolution thoroughly for regressions
   - Ensure no new issues were introduced
   - Validate that original functionality remains intact
   - Confirm issue is fully resolved, not just masked

## Phase 4: Return to Original Work

1. **Post-Critical Recovery**:
   - Only after all critical issues are resolved
   - Resume highest priority non-critical task
   - Review the original work that was paused for context
   - Continue with original objectives while maintaining vigilance

## Quality Assurance Rules for Critical Issues
1. Never ignore or delay critical issues - Always address immediately
2. Maintain same quality standards during critical work - No shortcuts
3. Security first - Address vulnerabilities before functionality
4. Thorough testing - Ensure resolution doesn't create new issues
5. Proper documentation - Maintain clear records of critical issue handling