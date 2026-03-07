"""
comparator.py — Stage 4a of LLM-TestLens

Compares LLM predictions from claude_client.py against actual pytest
results from pytest_runner.py, and computes per-file and overall
accuracy metrics.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ComparisonResult:
    """
    Holds the comparison outcome for a single test file.

    Attributes:
        filename:           Name of the test file.
        llm_prediction:     LLM's predicted outcome — 'PASS' or 'FAIL'.
        actual_outcome:     Actual pytest outcome — 'PASS' or 'FAIL'.
        is_correct:         True if prediction matched actual outcome.
        smells_detected:    List of test smells identified by the LLM.
        llm_reason:         LLM's explanation for its prediction.
        passed_count:       Number of individual tests that passed.
        failed_count:       Number of individual tests that failed.
        total_tests:        Total number of individual tests in the file.
        per_test_results:   List of per-test dicts from pytest_runner.
        error:              Optional error message if comparison failed.
    """
    filename: str
    llm_prediction: str
    actual_outcome: str
    is_correct: bool
    smells_detected: list = field(default_factory=list)
    llm_reason: str = ""
    passed_count: int = 0
    failed_count: int = 0
    total_tests: int = 0
    per_test_results: list = field(default_factory=list)
    error: Optional[str] = None


def _normalise_prediction(prediction: str) -> str:
    """
    Normalise LLM prediction string to 'PASS' or 'FAIL'.

    Args:
        prediction: Raw prediction string from claude_client.

    Returns:
        'PASS', 'FAIL', or 'UNKNOWN' if unrecognised.
    """
    p = prediction.strip().upper()
    if p in ("PASS", "PASSED"):
        return "PASS"
    if p in ("FAIL", "FAILED"):
        return "FAIL"
    return "UNKNOWN"


def _actual_outcome(pytest_result: dict) -> str:
    """
    Derive the actual file-level outcome from a pytest_runner result dict.

    A file passes only if every individual test passed.

    Args:
        pytest_result: Dict returned by pytest_runner.run_pytest().

    Returns:
        'PASS' if all tests passed, 'FAIL' otherwise.
    """
    return "PASS" if pytest_result.get("passed", False) else "FAIL"


def compare(llm_results: list, pytest_results: list) -> list:
    """
    Match LLM predictions with actual pytest results by filename and
    return a list of ComparisonResult objects.

    Files present in llm_results but missing from pytest_results (or
    vice versa) are included with an error note so no data is silently
    dropped.

    Args:
        llm_results:    List of dicts from claude_client.analyze_test().
        pytest_results: List of dicts from pytest_runner.run_pytest() or
                        pytest_runner.run_all_tests().

    Returns:
        List of ComparisonResult instances, one per matched file.

    Raises:
        ValueError: If either input list is empty.
    """
    if not llm_results:
        raise ValueError("llm_results is empty — nothing to compare.")
    if not pytest_results:
        raise ValueError("pytest_results is empty — nothing to compare.")

    # Index pytest results by filename for O(1) lookup
    pytest_index = {r["filename"]: r for r in pytest_results}
    llm_index    = {r["filename"]: r for r in llm_results}

    comparisons = []

    # --- files present in both ---
    for filename, llm in llm_index.items():
        if filename not in pytest_index:
            # LLM analysed a file that pytest never ran
            comparisons.append(ComparisonResult(
                filename=filename,
                llm_prediction=llm.get("prediction", "UNKNOWN"),
                actual_outcome="UNKNOWN",
                is_correct=False,
                smells_detected=llm.get("smells", []),
                llm_reason=llm.get("reason", ""),
                error="File was analysed by LLM but not found in pytest results."
            ))
            continue

        pytest = pytest_index[filename]
        normalised_pred   = _normalise_prediction(llm.get("prediction", ""))
        actual            = _actual_outcome(pytest)
        is_correct        = (normalised_pred == actual)

        comparisons.append(ComparisonResult(
            filename=filename,
            llm_prediction=normalised_pred,
            actual_outcome=actual,
            is_correct=is_correct,
            smells_detected=llm.get("smells", []),
            llm_reason=llm.get("reason", ""),
            passed_count=pytest.get("passed_count", 0),
            failed_count=pytest.get("failed_count", 0),
            total_tests=pytest.get("total", 0),
            per_test_results=pytest.get("test_results", []),
        ))

    # --- files pytest ran but LLM never saw ---
    for filename, pytest in pytest_index.items():
        if filename not in llm_index:
            comparisons.append(ComparisonResult(
                filename=filename,
                llm_prediction="UNKNOWN",
                actual_outcome=_actual_outcome(pytest),
                is_correct=False,
                passed_count=pytest.get("passed_count", 0),
                failed_count=pytest.get("failed_count", 0),
                total_tests=pytest.get("total", 0),
                per_test_results=pytest.get("test_results", []),
                error="File was run by pytest but not analysed by LLM."
            ))

    return comparisons


def summarise(comparisons: list) -> dict:
    """
    Compute overall accuracy metrics from a list of ComparisonResult objects.

    Args:
        comparisons: List returned by compare().

    Returns:
        dict with keys:
            - total_files        (int)
            - correct            (int)
            - incorrect          (int)
            - accuracy_pct       (float): percentage of correct predictions
            - total_tests        (int):   total individual test functions across all files
            - smells_found       (int):   total smell instances detected by LLM
            - files_with_smells  (int):   number of files containing at least one smell
            - errors             (int):   files with comparison errors
    """
    if not comparisons:
        return {}

    valid = [c for c in comparisons if c.error is None]
    total_files   = len(valid)
    correct       = sum(1 for c in valid if c.is_correct)
    incorrect     = total_files - correct
    accuracy_pct  = round((correct / total_files * 100), 2) if total_files else 0.0
    total_tests   = sum(c.total_tests for c in valid)
    smells_found  = sum(len(c.smells_detected) for c in valid)
    files_with_smells = sum(1 for c in valid if c.smells_detected)
    errors        = sum(1 for c in comparisons if c.error is not None)

    return {
        "total_files":       total_files,
        "correct":           correct,
        "incorrect":         incorrect,
        "accuracy_pct":      accuracy_pct,
        "total_tests":       total_tests,
        "smells_found":      smells_found,
        "files_with_smells": files_with_smells,
        "errors":            errors,
    }


def print_report(comparisons: list) -> None:
    """
    Print a human-readable comparison report to stdout.

    Args:
        comparisons: List returned by compare().
    """
    summary = summarise(comparisons)

    print("\n" + "=" * 60)
    print("COMPARISON REPORT — LLM Predictions vs Pytest Results")
    print("=" * 60)

    for c in comparisons:
        match_icon = "✅" if c.is_correct else "❌"
        print(f"\n{match_icon} {c.filename}")
        print(f"   LLM predicted : {c.llm_prediction}")
        print(f"   Actual result : {c.actual_outcome}")
        print(f"   Match         : {'YES' if c.is_correct else 'NO'}")
        if c.smells_detected:
            print(f"   Smells found  : {', '.join(c.smells_detected)}")
        if c.llm_reason:
            print(f"   LLM reason    : {c.llm_reason}")
        if c.error:
            print(f"   ⚠️  Error       : {c.error}")

    print("\n" + "-" * 60)
    print("SUMMARY")
    print("-" * 60)
    print(f"Files compared  : {summary.get('total_files', 0)}")
    print(f"Correct         : {summary.get('correct', 0)}")
    print(f"Incorrect       : {summary.get('incorrect', 0)}")
    print(f"Accuracy        : {summary.get('accuracy_pct', 0.0)}%")
    print(f"Total tests     : {summary.get('total_tests', 0)}")
    print(f"Smells detected : {summary.get('smells_found', 0)} across "
          f"{summary.get('files_with_smells', 0)} file(s)")
    if summary.get("errors"):
        print(f"Errors          : {summary.get('errors')} file(s) had comparison errors")
    print("=" * 60)


if __name__ == "__main__":
    # Quick smoke test using sample data
    sample_llm = [
        {
            "filename": "test_math.py",
            "prediction": "PASS",
            "smells": [],
            "reason": "All assertions are straightforward and well-defined."
        }
    ]
    sample_pytest = [
        {
            "filename": "test_math.py",
            "passed": True,
            "passed_count": 3,
            "failed_count": 0,
            "total": 3,
            "test_results": [
                {"test_name": "test_add_positive", "status": "PASSED"},
                {"test_name": "test_add_negative", "status": "PASSED"},
                {"test_name": "test_add_zero",     "status": "PASSED"},
            ]
        }
    ]

    results = compare(sample_llm, sample_pytest)
    print_report(results)
    print("\nSummary dict:", summarise(results))