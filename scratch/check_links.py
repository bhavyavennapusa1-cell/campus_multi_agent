import os
import re

frontend_dir = r"c:\Users\Bhavya vennapusa\App\campus_multi_agent\frontend"
html_files = [f for f in os.listdir(frontend_dir) if f.endswith(".html")]

href_pattern = re.compile(r'href=["\']([^"\']+)["\']')

dead_links = []
all_links = []

for hfile in html_files:
    filepath = os.path.join(frontend_dir, hfile)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    matches = href_pattern.findall(content)
    for m in matches:
        all_links.append((hfile, m))
        # Ignore external links, anchor links (#), javascript/mailto/tel, etc.
        if m.startswith("http://") or m.startswith("https://") or m.startswith("#") or m.startswith("javascript:"):
            continue
        
        # Strip query strings or fragment identifiers (e.g. chat.html?prompt=...)
        target_file = m.split("?")[0].split("#")[0]
        if not target_file:
            continue
        
        # Check if target exists in frontend_dir
        target_path = os.path.join(frontend_dir, target_file)
        if not os.path.exists(target_path):
            dead_links.append((hfile, m, target_file))

print(f"Total HTML files checked: {len(html_files)}")
print(f"Total href attributes checked: {len(all_links)}")
print(f"Dead links found: {len(dead_links)}")
for source, raw_link, target in dead_links:
    print(f"  Source: {source} -> Link: '{raw_link}' (Missing target: {target})")
