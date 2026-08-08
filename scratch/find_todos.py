import os
import re

frontend_dir = r"c:\Users\Bhavya vennapusa\App\campus_multi_agent\frontend"
files = [f for f in os.listdir(frontend_dir) if os.path.isfile(os.path.join(frontend_dir, f))]

todo_pattern = re.compile(r'TODO[:\s].*', re.IGNORECASE)

by_file = {}
total_count = 0

for filename in sorted(files):
    filepath = os.path.join(frontend_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    file_todos = []
    for idx, line in enumerate(lines, 1):
        if 'TODO' in line:
            clean_line = line.strip()
            file_todos.append((idx, clean_line))
            total_count += 1
            
    if file_todos:
        by_file[filename] = file_todos

print(f"Total TODOs found in frontend/: {total_count} across {len(by_file)} files:\n")

for fname, todos in by_file.items():
    print(f"=== {fname} ({len(todos)} TODOs) ===")
    for line_num, text in todos:
        print(f"  Line {line_num}: {text}")
    print()
