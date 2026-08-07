import os
import re

patterns = [
    r"sk-[a-zA-Z0-9]{20,}",
    r"sk-proj-[a-zA-Z0-9]{20,}",
    r"AIzaSy[a-zA-Z0-9_-]{30,}",
    r"ghp_[a-zA-Z0-9]{36}"
]

found_keys = []
repo_dir = r"c:\Users\Sree Vadrevu\Desktop\campus_multi_agent"

for root, dirs, files in os.walk(repo_dir):
    if ".git" in root or "__pycache__" in root or ".venv" in root:
        continue
    for file in files:
        if file.endswith((".py", ".json", ".txt", ".md", ".env")):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for p in patterns:
                        matches = re.findall(p, content)
                        if matches:
                            found_keys.append((filepath, matches))
            except Exception:
                pass

print(f"API Key Audit Found: {len(found_keys)} hardcoded keys.")
for fp, matches in found_keys:
    print(f"  File: {fp} -> Matches: {matches}")
