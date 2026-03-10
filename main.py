"""
main.py — Stage 4c of LLM-TestLens

Entry point for the full pipeline. Orchestrates all five components:

    Stage 1  — loader.py       : Load test files from a folder
    Stage 2  — claude_client.py: Analyse each file with Claude LLM
    Stage 3  — pytest_runner.py: Run pytest on each file
    Stage 4a — comparator.py  : Compare LLM predictions vs pytest results
    Stage 4b — logger.py      : Save results to JSON + TXT

Usage:
    python main.py                        # runs on default 'sample_tests/' folder
    python main.py --folder my_tests/     # runs on a custom folder
    python main.py --folder my_tests/ --output my_results/
"""

import argparse
import os
import sys

from loader import load_test_files
from claude_client import analyze_test
from pytest_runner import run_pytest
from comparator import compare, summarise, print_report
from logger import Logger


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Namespace with:
            folder (str): path to folder containing test files
            output (str): path to root results directory
    """
    parser = argparse.ArgumentParser(
        description="LLM-TestLens — LLM-based test smell detection and outcome prediction"
    )
    parser.add_argument(
        "--folder",
        type=str,
        default="sample_tests",
        help="Path to folder containing test_*.py files (default: sample_tests)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results",
        help="Path to root results directory (default: results)"
    )
    return parser.parse_args()


def run_pipeline(folder: str, output: str) -> dict:
    """
    Execute the full LLM-TestLens pipeline end-to-end.

    Args:
        folder: Path to folder containing test_*.py files.
        output: Path to root results directory for logger.

    Returns:
        summary dict from comparator.summarise(), or empty dict on failure.
    """

    # ------------------------------------------------------------------
    # Stage 1 — Load test files
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STAGE 1 — Loading test files")
    print("=" * 60)

    test_files = load_test_files(folder)

    if not test_files:
        print(f"No test files found in '{folder}'. Aborting pipeline.")
        return {}

    print(f"\n✅ Loaded {len(test_files)} file(s) from '{folder}'")

    # ------------------------------------------------------------------
    # Stage 2 — LLM analysis via Claude
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STAGE 2 — LLM analysis (Claude)")
    print("=" * 60)

    llm_results = []
    for i, file in enumerate(test_files, start=1):
        print(f"\n[{i}/{len(test_files)}] Analysing: {file['filename']}")
        try:
            result = analyze_test(file["filename"], file["content"])
            llm_results.append(result)
            print(f"  Prediction : {result.get('prediction', 'UNKNOWN')}")
            smells = result.get("smells", [])
            print(f"  Smells     : {', '.join(smells) if smells else 'None'}")
            print(f"  Reason     : {result.get('reason', '')}")
        except Exception as e:
            print(f"  ⚠️  LLM analysis failed for {file['filename']}: {e}")
            llm_results.append({
                "filename": file["filename"],
                "prediction": "UNKNOWN",
                "smells": [],
                "reason": f"LLM error: {str(e)}"
            })

    print(f"\n✅ LLM analysis complete for {len(llm_results)} file(s)")

    # ------------------------------------------------------------------
    # Stage 3 — Run pytest on each file
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STAGE 3 — Running pytest")
    print("=" * 60)

    pytest_results = []
    for i, file in enumerate(test_files, start=1):
        file_path = os.path.join(folder, file["filename"])
        print(f"\n[{i}/{len(test_files)}] Running pytest: {file['filename']}")
        try:
            result = run_pytest(file_path)
            pytest_results.append(result)
            status = "✅ PASSED" if result["passed"] else "❌ FAILED"
            print(f"  Result : {status} "
                  f"({result['passed_count']} passed, "
                  f"{result['failed_count']} failed, "
                  f"{result['total']} total)")
        except Exception as e:
            print(f"  ⚠️  pytest failed for {file['filename']}: {e}")
            pytest_results.append({
                "filename": file["filename"],
                "exit_code": -1,
                "passed": False,
                "total": 0,
                "passed_count": 0,
                "failed_count": 0,
                "test_results": [],
                "output": str(e),
                "stderr": str(e)
            })

    print(f"\n✅ pytest complete for {len(pytest_results)} file(s)")

    # ------------------------------------------------------------------
    # Stage 4a — Compare LLM predictions vs pytest results
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STAGE 4a — Comparing predictions vs actual results")
    print("=" * 60)

    try:
        comparisons = compare(llm_results, pytest_results)
        summary = summarise(comparisons)
        print_report(comparisons)
    except ValueError as e:
        print(f"⚠️  Comparison failed: {e}")
        return {}

    # ------------------------------------------------------------------
    # Stage 4b — Log results to disk
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STAGE 4b — Logging results")
    print("=" * 60)

    log = Logger(output_dir=output)
    log.log_run(llm_results, comparisons, summary)

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Files analysed : {summary.get('total_files', 0)}")
    print(f"Accuracy       : {summary.get('accuracy_pct', 0.0)}%")
    print(f"Smells found   : {summary.get('smells_found', 0)} across "
          f"{summary.get('files_with_smells', 0)} file(s)")
    print(f"Results saved  : {output}/")
    print("=" * 60)

    return summary


def main() -> None:
    """
    Main entry point. Parses arguments and runs the pipeline.
    """
    args = parse_args()

    print("\nLLM-TestLens Pipeline")
    print(f"  Folder : {args.folder}")
    print(f"  Output : {args.output}")

    summary = run_pipeline(folder=args.folder, output=args.output)

    if not summary:
        print("\n⚠️  Pipeline did not complete successfully.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()