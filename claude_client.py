import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

def analyze_test(filename: str, content: str) -> dict:
    prompt = f"""You are an expert software tester. Analyze the following Python test file.

File: {filename}
```python
{content}
```

Respond in exactly this format:
PREDICTION: PASS or FAIL
SMELLS: comma-separated list of test smells found, or NONE
REASON: one sentence explaining your prediction"""

    message = client.messages.create(
        model="claude-opus-4-1-20250805",
        max_tokens=500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return parse_response(filename, message.content[0].text)

def parse_response(filename: str, text: str) -> dict:
    result = {"filename": filename, "prediction": "UNKNOWN", "smells": [], "reason": ""}
    for line in text.strip().splitlines():
        if line.startswith("PREDICTION:"):
            result["prediction"] = line.split(":", 1)[1].strip()
        elif line.startswith("SMELLS:"):
            smells = line.split(":", 1)[1].strip()
            result["smells"] = [] if smells == "NONE" else [s.strip() for s in smells.split(",")]
        elif line.startswith("REASON:"):
            result["reason"] = line.split(":", 1)[1].strip()
    return result

if __name__ == "__main__":
    from loader import load_test_files
    files = load_test_files("sample_tests")
    for f in files:
        result = analyze_test(f["filename"], f["content"])
        print(result)