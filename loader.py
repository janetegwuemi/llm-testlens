
import os

def load_test_files(folder_path):
    """
    Loads all Python test files from a given folder.
    Returns a list of dictionaries with file name and content.
    """
    test_files = []

    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return test_files

    for filename in os.listdir(folder_path):
        if filename.startswith("test_") and filename.endswith(".py"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            test_files.append({
                "filename": filename,
                "content": content
            })
            print(f"Loaded: {filename}")

    print(f"\nTotal test files loaded: {len(test_files)}")
    return test_files


if __name__ == "__main__":
    load_test_files("sample_tests")
```

