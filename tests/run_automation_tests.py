#!/usr/bin/env python3
"""Run comprehensive automation infrastructure tests and generate report.

Executes all automation tests and generates a detailed report with:
- Test results summary
- Pass/fail counts by category
- Detailed failure information
- Recommendations
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_tests() -> dict:
    """Run all automation tests and collect results.

    Returns:
        Dictionary with test results
    """
    test_files = [
        "tests/test_automation_hooks.py",
        "tests/test_automation_wrappers.py",
    ]

    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "categories": {},
        "total_passed": 0,
        "total_failed": 0,
        "total_errors": 0,
    }

    for test_file in test_files:
        print(f"\n{'=' * 80}")
        print(f"Running: {test_file}")
        print("=" * 80)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                test_file,
                "-v",
                "--tb=short",
                "--color=yes",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        category = Path(test_file).stem
        results["categories"][category] = {
            "file": test_file,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

        # Print output
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)

        # Parse results
        if "passed" in result.stdout:
            import re

            # Extract passed/failed counts
            match = re.search(r"(\d+) passed", result.stdout)
            if match:
                results["total_passed"] += int(match.group(1))

            match = re.search(r"(\d+) failed", result.stdout)
            if match:
                results["total_failed"] += int(match.group(1))

            match = re.search(r"(\d+) error", result.stdout)
            if match:
                results["total_errors"] += int(match.group(1))

    return results


def generate_report(results: dict) -> str:
    """Generate markdown report from test results.

    Args:
        results: Test results dictionary

    Returns:
        Markdown report string
    """
    lines = [
        "# Automation Infrastructure Test Report",
        "",
        f"**Generated:** {results['timestamp']}",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"- **Total Passed:** {results['total_passed']}",
        f"- **Total Failed:** {results['total_failed']}",
        f"- **Total Errors:** {results['total_errors']}",
        "",
    ]

    # Overall status
    if results["total_failed"] == 0 and results["total_errors"] == 0:
        lines.extend(
            [
                "**Status:** ✅ ALL TESTS PASSED",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"**Status:** ❌ {results['total_failed']} FAILURES, {results['total_errors']} ERRORS",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "## Test Categories",
            "",
        ]
    )

    # Category breakdown
    for category, data in results["categories"].items():
        lines.append(f"### {category}")
        lines.append("")
        lines.append(f"**File:** `{data['file']}`")
        lines.append("")

        if data["returncode"] == 0:
            lines.append("**Result:** ✅ PASSED")
        else:
            lines.append("**Result:** ❌ FAILED")

        lines.append("")
        lines.append("**Output:**")
        lines.append("```")
        lines.append(data["stdout"])
        lines.append("```")
        lines.append("")

        if data["stderr"]:
            lines.append("**Errors:**")
            lines.append("```")
            lines.append(data["stderr"])
            lines.append("```")
            lines.append("")

    # Recommendations
    lines.extend(
        [
            "---",
            "",
            "## Test Coverage",
            "",
            "This test suite validates:",
            "",
            "1. **Hook System**",
            "   - CommandValidator (Bash command guard)",
            "   - CodeQualityValidator (LLM-based diff audit)",
            "   - ResponseScanner (Communication rules)",
            "",
            "2. **Wrapper Scripts**",
            "   - ami-run.sh (Python execution)",
            "   - ami-uv (UV commands)",
            "   - git_commit.sh (Auto-staging commits)",
            "   - git_push.sh (Test-before-push)",
            "",
            "3. **Pattern Detection**",
            "   - Python quality patterns (15 rules)",
            "   - JavaScript quality patterns (15 rules)",
            "   - Security patterns (15 rules)",
            "",
            "4. **Integration**",
            "   - Hook registration and execution",
            "   - Error handling and timeouts",
            "   - Tool restrictions",
            "",
            "---",
            "",
            "## Next Steps",
            "",
        ]
    )

    if results["total_failed"] > 0 or results["total_errors"] > 0:
        lines.extend(
            [
                "### Action Required",
                "",
                "1. Review failed tests above",
                "2. Fix underlying issues",
                "3. Re-run test suite",
                "4. Verify all tests pass",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "### Validation Complete",
                "",
                "All automation infrastructure tests passed successfully.",
                "The system is ready for production use.",
                "",
                "**Key Validations:**",
                "- ✅ All hooks functioning correctly",
                "- ✅ All wrapper scripts working",
                "- ✅ All pattern detection rules active",
                "- ✅ Integration tests passing",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0=all passed, 1=failures)
    """
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║     AUTOMATION INFRASTRUCTURE COMPREHENSIVE TEST SUITE        ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()

    # Run tests
    results = run_tests()

    # Generate report
    report = generate_report(results)

    # Save report
    report_dir = Path("/home/ami/Projects/AMI-ORCHESTRATOR/tests/reports")
    report_dir.mkdir(exist_ok=True)

    report_file = report_dir / f"automation_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_file.write_text(report)

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Passed: {results['total_passed']}")
    print(f"Total Failed: {results['total_failed']}")
    print(f"Total Errors: {results['total_errors']}")
    print()
    print(f"Report saved to: {report_file}")
    print()

    if results["total_failed"] > 0 or results["total_errors"] > 0:
        print("❌ SOME TESTS FAILED - Review report for details")
        return 1
    print("✅ ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
