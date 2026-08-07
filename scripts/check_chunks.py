import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def semantic_markdown_chunker(markdown_text, min_chunk_size=50):
    """
    Splits markdown by headings (##, ###) while preserving semantic context,
    merging standalone heading stubs into sub-clauses/subsections, and ensuring
    no chunk is under min_chunk_size.
    """
    lines = markdown_text.split("\n")
    raw_sections = []
    current_lines = []
    
    for line in lines:
        # Match headings: #, ##, ### or ## 1. / ### 1.1 patterns
        if re.match(r"^#{1,3}\s+", line):
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    raw_sections.append(text)
                current_lines = []
        current_lines.append(line)
        
    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            raw_sections.append(text)

    # Merge pass: combine small stubs (< min_chunk_size) forward
    merged_chunks = []
    buffer = ""

    for section in raw_sections:
        combined = (buffer + "\n\n" + section).strip() if buffer else section
        if len(combined) < min_chunk_size:
            buffer = combined
        else:
            merged_chunks.append(combined)
            buffer = ""

    if buffer:
        if merged_chunks:
            merged_chunks[-1] = (merged_chunks[-1] + "\n\n" + buffer).strip()
        else:
            merged_chunks.append(buffer)

    return merged_chunks


def main():
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "docs", "academic", "attendance_policy.md"
    )

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = semantic_markdown_chunker(content, min_chunk_size=50)
    
    total_chunks = len(chunks)
    under_50_count = sum(1 for c in chunks if len(c) < 50)
    max_chunk_size = max(len(c) for c in chunks) if chunks else 0

    print("=" * 85)
    print("IMPROVED SEMANTIC CHUNK ANALYSIS REPORT")
    print("=" * 85)
    print(f"Target File         : attendance_policy.md")
    print(f"Total Chunks        : {total_chunks}")
    print(f"Chunks < 50 Chars   : {under_50_count}")
    print(f"Max Chunk Size      : {max_chunk_size} chars")
    print("=" * 85 + "\n")

    print("CHUNK BREAKDOWN:")
    print("-" * 85)
    for idx, c in enumerate(chunks, 1):
        lines = c.split("\n")
        header = lines[0][:60]
        print(f"Chunk {idx}: Length={len(c)} chars | Lines={len(lines)} | Start: '{header}'")
    
    print("\n" + "=" * 85)
    print("3 REPRESENTATIVE EXAMPLE CHUNKS FOR QUALITY CHECK")
    print("=" * 85)

    # Pick 3 diverse example chunks
    sample_indices = [0, min(3, total_chunks - 1), total_chunks - 1]
    for i in sample_indices:
        print(f"\n--- EXAMPLE CHUNK #{i + 1} ({len(chunks[i])} chars) ---")
        print(chunks[i])
        print("-" * 50)

if __name__ == "__main__":
    main()
