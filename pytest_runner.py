import os
import subprocess
import json
from pathlib import Path

def run_pytest(test_file_path: str) -> dict:
    """
    Run pytest on a single test file and capture results.
    
    Returns:
        dict with keys: filename, passed, failed, errors, total, details
    """
    try:
        # Run pytest with JSON output
        result = subprocess.run(
            ["pytest", test_file_path, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Parse output
        output = result.stdout + result.stderr
        
        return {
            "filename": os.path.basename(test_file_path),
            "exit_code": result.returncode,
            "passed": result.returncode == 0,
            "output": output,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "filename": os.path.basename(test_file_path),
            "exit_code": -1,
            "passed": False,
            "output": "Test execution timed out",
            "stderr": "Timeout after 30 seconds"
        }
    except Exception as e:
        return {
            "filename": os.path.basename(test_file_path),
            "exit_code": -1,
            "passed": False,
            "output": f"Error running pytest: {str(e)}",
            "stderr": str(e)
        }

def run_all_tests(folder_path: str) -> list:
    """
    Run pytest on all test files in a folder.
    
    Returns:
        list of dicts with test results
    """
    results = []
    test_files = []
    
    # Find all test_*.py files
    for filename in os.listdir(folder_path):
        if filename.startswith("test_") and filename.endswith(".py"):
            test_files.append(os.path.join(folder_path, filename))
    
    print(f"Found {len(test_files)} test files")
    
    for test_file in test_files:
        print(f"\nRunning: {os.path.basename(test_file)}")
        result = run_pytest(test_file)
        results.append(result)
        print(f"  Result: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
    
    return results

if __name__ == "__main__":
    results = run_all_tests("sample_tests")
    
    print("\n" + "="*60)
    print("PYTEST RESULTS SUMMARY")
    print("="*60)
    
    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{result['filename']}: {status}")
        if not result["passed"]:
            print(f"  Output: {result['output'][:200]}...")