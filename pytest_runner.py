"""
pytest_runner.py — Stage 3 of LLM-TestLens

Runs pytest on test files and captures per-test pass/fail results
to compare against LLM predictions in Stage 4.
"""

import os
import re
import subprocess
from pathlib import Path


def run_pytest(test_file_path: str) -> dict:
    """
    Run pytest on a single test file and capture per-test results.

    Args:
        test_file_path: Path to the test file to run.

    Returns:
        dict with keys:
            - filename (str)
            - exit_code (int)
            - passed (bool): True if all tests in file passed
            - total (int)
            - passed_count (int)
            - failed_count (int)
            - test_results (list of dicts): per-test name + status
            - output (str)
            - stderr (str)

    Raises:
        FileNotFoundError: If test_file_path does not exist.
    """
    path = Path(test_file_path)
    if not path.exists():
        raise FileNotFoundError(f"Test file not found: {test_file_path}")

    try:
        result = subprocess.run(
            ["pytest", str(path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout + result.stderr
        test_results = _parse_test_results(result.stdout)
        passed_count = sum(1 for t in test_results if t["status"] == "PASSED")
        failed_count = sum(1 for t in test_results if t["status"] == "FAILED")

        return {
            "filename": path.name,
            "exit_code": result.returncode,
            "passed": result.returncode == 0,
            "total": len(test_results),
            "passed_count": passed_count,
            "failed_count": failed_count,
            "test_results": test_results,
            "output": output,
            "stderr": result.stderr
        }

    except subprocess.TimeoutExpired:
        return {
            "filename": path.name,
            "exit_code": -1,
            "passed": False,
            "total": 0,
            "passed_count": 0,
            "failed_count": 0,
            "test_results": [],
            "output": "Test execution timed out after 30 seconds",
            "stderr": "TimeoutExpired"
        }
    except Exception as e:
        return {
            "filename": path.name,
            "exit_code": -1,
            "passed": False,
            "total": 0,
            "passed_count": 0,
            "failed_count": 0,
            "test_results": [],
            "output": f"Unexpected error running pytest: {str(e)}",
            "stderr": str(e)
        }


def _parse_test_results(output: str) -> list:
    """
    Parse pytest -v output to extract per-test name and status.

    Args:
        output: stdout string from pytest -v run.

    Returns:
        list of dicts with keys: test_name (str), status (str: PASSED/FAILED/ERROR)
    """
    results = []
    # pytest -v lines look like: "test_file.py::test_name PASSED"
    pattern = re.compile(r"(\S+::(\S+))\s+(PASSED|FAILED|ERROR)")
    for match in pattern.finditer(output):
        results.append({
            "test_name": match.group(2),
            "full_id": match.group(1),
            "status": match.group(3)
        })
    return results


def run_all_tests(folder_path: str) -> list:
    """
    Run pytest on all test files discovered in a folder.

    Args:
        folder_path: Path to folder containing test_*.py files.

    Returns:
        list of result dicts from run_pytest().

    Raises:
        FileNotFoundError: If folder_path does not exist.
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Test folder not found: {folder_path}")

    test_files = sorted(folder.glob("test_*.py"))

    if not test_files:
        print(f"No test files found in: {folder_path}")
        return []

    print(f"Found {len(test_files)} test file(s) in '{folder_path}'")

    results = []
    for test_file in test_files:
        print(f"\nRunning: {test_file.name}")
        result = run_pytest(str(test_file))
        results.append(result)
        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        print(f"  Result: {status} "
              f"({result['passed_count']} passed, {result['failed_count']} failed)")

    return results


if __name__ == "__main__":
    results = run_all_tests("sample_tests")

    print("\n" + "=" * 60)
    print("PYTEST RESULTS SUMMARY")
    print("=" * 60)

    total_passed = sum(r["passed_count"] for r in results)
    total_failed = sum(r["failed_count"] for r in results)

    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"\n{result['filename']}: {status}")
        for t in result["test_results"]:
            icon = "  ✅" if t["status"] == "PASSED" else "  ❌"
            print(f"{icon} {t['test_name']} — {t['status']}")

    print(f"\nTOTAL: {total_passed} passed, {total_failed} failed")