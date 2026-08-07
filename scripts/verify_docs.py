import os
import glob
import re
import sys
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "docs")
REQUIRED_FIELDS = ["doc_id", "title", "category", "version", "effective_date", "last_updated"]
PLACEHOLDERS = ["TBD", "LOREM IPSUM", "XXX", "[INSERT", "TODO"]


def parse_frontmatter(content):
    """Extracts YAML frontmatter and body from markdown content."""
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return None, content
    yaml_str = match.group(1)
    body = match.group(2)
    try:
        data = yaml.safe_load(yaml_str)
        return data, body
    except Exception:
        return None, body


def extract_numeric_values(doc_id, text):
    """Extracts percentages, CGPA, CTC, currency values with context sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    numeric_findings = []
    
    value_pattern = r'(\b\d+(?:\.\d+)?%\b|\bCGPA\s*(?:>=|<=|=|>|<)?\s*\d+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\s*LPA\b|₹\s*\d+(?:,\d+)*(?:\.\d+)?|\b\d+(?:\.\d+)?\s*grade points?\b)'
    
    for sentence in sentences:
        clean_sentence = sentence.strip().replace("\n", " ")
        if not clean_sentence:
            continue
        matches = re.findall(value_pattern, clean_sentence, re.IGNORECASE)
        for m in matches:
            numeric_findings.append({
                "doc_id": doc_id,
                "value": m,
                "context": clean_sentence[:110] + ("..." if len(clean_sentence) > 110 else "")
            })
    return numeric_findings


def verify_documents():
    md_files = glob.glob(os.path.join(DATA_DOCS_DIR, "**", "*.md"), recursive=True)
    md_files = [f for f in md_files if os.path.basename(f).lower() != "readme.md"]
    
    doc_ids = set()
    all_numeric_values = []
    
    total_files = len(md_files)
    passed_files = 0
    failed_files = 0

    print("=" * 85)
    print("DOCUMENT VERIFICATION REPORT")
    print("=" * 85 + "\n")

    for file_path in sorted(md_files):
        rel_path = os.path.relpath(file_path, DATA_DOCS_DIR)
        subfolder = os.path.dirname(rel_path).replace("\\", "/")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        failures = []

        # 1. YAML frontmatter check
        frontmatter, body = parse_frontmatter(content)
        if not frontmatter:
            failures.append("Missing or invalid YAML frontmatter")
            doc_id = "UNKNOWN"
        else:
            missing_fields = [field for field in REQUIRED_FIELDS if field not in frontmatter or frontmatter[field] is None]
            if missing_fields:
                failures.append(f"Missing required frontmatter fields: {missing_fields}")
            
            doc_id = str(frontmatter.get("doc_id", "UNKNOWN"))

            # 2. Unique doc_id check
            if doc_id in doc_ids:
                failures.append(f"Duplicate doc_id found: '{doc_id}'")
            else:
                doc_ids.add(doc_id)

            # 3. Category match check
            category = str(frontmatter.get("category", "")).strip()
            if category != subfolder:
                failures.append(f"Category mismatch: expected '{subfolder}', got '{category}'")

        # 4. Heading structure check (## 1. and sub-clauses like 2.1 or ### 2.1)
        has_h1_heading = bool(re.search(r"^##\s+1\.", body, re.MULTILINE))
        has_subclauses = bool(re.search(r"^\d+\.\d+", body, re.MULTILINE) or re.search(r"###\s+\d+\.\d+", body, re.MULTILINE))
        if not has_h1_heading:
            failures.append("Body missing '## 1.' heading structure")
        if not has_subclauses:
            failures.append("Body missing numbered sub-clauses (e.g. 2.1 or 2.2)")

        # 5. Word count check (250-600 words)
        words = body.split()
        word_count = len(words)
        if word_count < 250 or word_count > 600:
            failures.append(f"Word count outlier: {word_count} words (expected 250-600)")

        # 6. Placeholder text check
        found_placeholders = []
        for ph in PLACEHOLDERS:
            if ph in body.upper():
                found_placeholders.append(ph)
        if found_placeholders:
            failures.append(f"Found placeholder text: {found_placeholders}")

        # 7. Collect numeric values
        if doc_id != "UNKNOWN":
            numerics = extract_numeric_values(doc_id, body)
            all_numeric_values.extend(numerics)

        # Status output
        status = "PASS" if not failures else "FAIL"
        if status == "PASS":
            passed_files += 1
        else:
            failed_files += 1

        print(f"[{status}] File: {rel_path} (doc_id: {doc_id})")
        print(f"       Word Count: {word_count}")
        if failures:
            for fail in failures:
                print(f"       - ERROR: {fail}")
        print("-" * 85)

    print("\n" + "=" * 85)
    print("NUMERIC VALUES & CONTEXT SUMMARY TABLE")
    print("=" * 85)
    print(f"{'Doc ID':<15} | {'Extracted Value':<22} | {'Context Sentence'}")
    print("-" * 85)

    for item in all_numeric_values:
        print(f"{item['doc_id']:<15} | {item['value']:<22} | {item['context']}")

    print("\n" + "=" * 85)
    print("SUMMARY")
    print("=" * 85)
    print(f"Total Files Checked : {total_files}")
    print(f"Passed              : {passed_files}")
    print(f"Failed              : {failed_files}")
    print("=" * 85)

    return failed_files == 0


if __name__ == "__main__":
    success = verify_documents()
    exit(0 if success else 1)
