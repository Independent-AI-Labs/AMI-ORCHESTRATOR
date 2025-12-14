# Handling Incomplete TODOs: Workflow Recovery Process

This document outlines the process for addressing situations where work was incorrectly marked as complete or tasks were skipped in the TODO list.

## Key Principle: Complete, Accurate, and Honest Tracking
You must maintain accurate TODO tracking and address any gaps or false completions. When incomplete work is identified:
- Assess the current actual state of all tasks
- Restore TODOs to their correct status
- Complete any skipped work
- Be transparent about what was missed

## Phase 1: Situation Assessment & State Restoration

1. **Assess Current State**:
   - Review all TODOs to identify which were incorrectly marked as complete
   - Determine which quality issues were actually resolved vs. marked resolved
   - Check git status and any quality check results to validate completion
   - Identify any skipped steps in proper workflow sequence

2. **Restore Accurate TODO State**:
   - Reset all TODOs to their actual status (not assumed completion)
   - Maintain original task IDs for consistency
   - Ensure all work-in-progress or incomplete tasks are marked appropriately
   - Add any missing tasks that should have been created based on quality check results

## Phase 2: Damage Assessment & Reporting

1. **Report Incomplete Work**:
   - Document which specific quality checks or fixes were skipped
   - Identify any potential issues that may have been overlooked
   - Report any false completions to maintain transparency
   - Outline the scope of work that needs to be recovered

2. **Validate Current State**:
   - Run quality checks to confirm which issues still exist
   - Verify actual code state vs. assumed state
   - Check commit readiness and any pending work
   - Ensure no issues were masked by incorrect status reporting

## Phase 3: Recovery & Completion

1. **Resume Proper Workflow**:
   - Address all incomplete tasks in proper order
   - Execute any skipped quality checks
   - Complete all required fixes systematically
   - Follow original workflow steps without taking shortcuts

## Quality Assurance Rules for Recovery
1. Always verify completion before marking tasks complete - No assumption of completion
2. Address all issues systematically - No skipping steps
3. Be transparent about gaps - Report any incomplete work immediately
4. Maintain honest tracking - Accurate status is critical for process integrity