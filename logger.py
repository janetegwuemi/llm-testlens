"""
logger.py — Stage 4b of LLM-TestLens

Persists pipeline results to disk in two formats:
  - JSON  : machine-readable full record for downstream analysis
  - TXT   : human-readable summary report for quick review

Logs data from three pipeline stages:
  - loader.py        : filenames and content loaded
  - claude_client.py : LLM predictions, smells, and reasons
  - comparator.py    : per-file comparison results and summary metrics

Usage:
    from logger import Logger

    log = Logger(output_dir="results")
    log.log_run(llm_results, comparisons, summary)
"""

import json
import os
from datetime import datetime
from comparator import ComparisonResult


class Logger:
    """
    Handles all file-based logging for a single LLM-TestLens pipeline run.

    Each run creates a timestamped subfolder inside output_dir containing:
        - results.json  : full structured record of the run
        - report.txt    : human-readable summary matching Comparator.print_report()

    Attributes:
        output_dir: Root directory where run folders are created.
        run_dir:    Timestamped folder for the current run.
    """

    def __init__(self, output_dir: str = "results"):
        """
        Initialise the Logger and create the output directory for this run.

        Args:
            output_dir: Path to the root results folder. Created if absent.
        """
        self.output_dir = output_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join(output_dir, f"run_{timestamp}")
        os.makedirs(self.run_dir, exist_ok=True)
        print(f"Logger initialised — results will be saved to: {self.run_dir}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_run(
        self,
        llm_results: list,
        comparisons: list,
        summary: dict,
    ) -> None:
        """
        Persist all results from a complete pipeline run to disk.

        Writes two files into the run directory:
            - results.json
            - report.txt

        Args:
            llm_results:  List of dicts from claude_client.analyze_test().
            comparisons:  List of ComparisonResult objects from comparator.compare().
            summary:      Dict from comparator.summarise().
        """
        self._write_json(llm_results, comparisons, summary)
        self._write_txt(comparisons, summary)
        print(f"Run logged successfully to {self.run_dir}")

    def log_llm_results(self, llm_results: list) -> None:
        """
        Persist only the LLM results (useful for debugging Stage 3 in isolation).

        Args:
            llm_results: List of dicts from claude_client.analyze_test().
        """
        path = os.path.join(self.run_dir, "llm_results.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(llm_results, f, indent=2)
        print(f"LLM results saved to {path}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _write_json(
        self,
        llm_results: list,
        comparisons: list,
        summary: dict,
    ) -> None:
        """
        Write a full structured JSON record of the run.

        Schema:
        {
            "run_timestamp": "YYYY-MM-DD HH:MM:SS",
            "summary": { ...summarise() output... },
            "files": [
                {
                    "filename":       str,
                    "llm_prediction": str,
                    "actual_outcome": str,
                    "is_correct":     bool,
                    "smells_detected": [...],
                    "llm_reason":     str,
                    "passed_count":   int,
                    "failed_count":   int,
                    "total_tests":    int,
                    "per_test_results": [...],
                    "error":          str | null
                },
                ...
            ]
        }

        Args:
            llm_results:  List of dicts from claude_client.
            comparisons:  List of ComparisonResult objects.
            summary:      Dict from comparator.summarise().
        """
        record = {
            "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "files": [self._comparison_to_dict(c) for c in comparisons],
        }

        path = os.path.join(self.run_dir, "results.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        print(f"JSON results saved to {path}")

    def _write_txt(self, comparisons: list, summary: dict) -> None:
        """
        Write a human-readable plain-text report matching the style of
        comparator.print_report(), but directed to a file instead of stdout.

        Args:
            comparisons: List of ComparisonResult objects.
            summary:     Dict from comparator.summarise().
        """
        path = os.path.join(self.run_dir, "report.txt")
        lines = []

        lines.append("=" * 60)
        lines.append("COMPARISON REPORT — LLM Predictions vs Pytest Results")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)

        for c in comparisons:
            match_icon = "CORRECT" if c.is_correct else "INCORRECT"
            lines.append(f"\n[{match_icon}] {c.filename}")
            lines.append(f"   LLM predicted : {c.llm_prediction}")
            lines.append(f"   Actual result : {c.actual_outcome}")
            lines.append(f"   Match         : {'YES' if c.is_correct else 'NO'}")
            if c.smells_detected:
                lines.append(f"   Smells found  : {', '.join(c.smells_detected)}")
            if c.llm_reason:
                lines.append(f"   LLM reason    : {c.llm_reason}")
            if c.error:
                lines.append(f"   ERROR         : {c.error}")

        lines.append("\n" + "-" * 60)
        lines.append("SUMMARY")
        lines.append("-" * 60)
        lines.append(f"Files compared  : {summary.get('total_files', 0)}")
        lines.append(f"Correct         : {summary.get('correct', 0)}")
        lines.append(f"Incorrect       : {summary.get('incorrect', 0)}")
        lines.append(f"Accuracy        : {summary.get('accuracy_pct', 0.0)}%")
        lines.append(f"Total tests     : {summary.get('total_tests', 0)}")
        lines.append(
            f"Smells detected : {summary.get('smells_found', 0)} across "
            f"{summary.get('files_with_smells', 0)} file(s)"
        )
        if summary.get("errors"):
            lines.append(f"Errors          : {summary.get('errors')} file(s) had comparison errors")
        lines.append("=" * 60)

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Text report saved to {path}")

    @staticmethod
    def _comparison_to_dict(c: ComparisonResult) -> dict:
        """
        Convert a ComparisonResult dataclass to a JSON-serialisable dict.

        Args:
            c: A ComparisonResult instance.

        Returns:
            Plain dict representation of the comparison result.
        """
        return {
            "filename":        c.filename,
            "llm_prediction":  c.llm_prediction,
            "actual_outcome":  c.actual_outcome,
            "is_correct":      c.is_correct,
            "smells_detected": c.smells_detected,
            "llm_reason":      c.llm_reason,
            "passed_count":    c.passed_count,
            "failed_count":    c.failed_count,
            "total_tests":     c.total_tests,
            "per_test_results": c.per_test_results,
            "error":           c.error,
        }


if __name__ == "__main__":
    # Smoke test using sample data matching comparator.py's sample
    from comparator import compare, summarise

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

    comparisons = compare(sample_llm, sample_pytest)
    summary = summarise(comparisons)

    log = Logger(output_dir="results")
    log.log_run(sample_llm, comparisons, summary)