import os
import re

frontend_dir = r"c:\Users\Bhavya vennapusa\App\campus_multi_agent\frontend"
html_files = [f for f in os.listdir(frontend_dir) if f.endswith(".html")]

href_pattern = re.compile(r'href=["\']([^"\']+)["\']')

for hfile in html_files:
    filepath = os.path.join(frontend_dir, hfile)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"=== {hfile} ===")
    matches = href_pattern.findall(content)
    for m in matches:
        if not m.startswith("http") and not m.startswith("#") and not m.startswith("javascript:") and not m.startswith("${"):
            clean = m.split("?")[0].split("#")[0]
            exists = os.path.exists(os.path.join(frontend_dir, clean))
            print(f"  href='{m}' -> file '{clean}' exists: {exists}")
