import os
import sys

PROJECT_ROOT = r"c:\Users\Bhavya vennapusa\App\campus_multi_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import chromadb
from chromadb.utils import embedding_functions

chroma_path = os.path.join(PROJECT_ROOT, "knowledge", "chroma_db")
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=chroma_path)
collection = client.get_collection(name="campus_kb", embedding_function=embedding_fn)

print(f"Collection Name: {collection.name}")
print(f"Total Document Chunks Count: {collection.count()}")

query_text = "placement eligibility Google CGPA"
res = collection.query(
    query_texts=[query_text],
    n_results=2,
    where={"category": "placement"}
)

print("\n--- RAW RETRIEVED CHUNKS FROM CHROMADB ---")
for i in range(len(res["ids"][0])):
    chunk_id = res["ids"][0][i]
    document = res["documents"][0][i]
    metadata = res["metadatas"][0][i]
    distance = res["distances"][0][i] if "distances" in res and res["distances"] else "N/A"
    
    print(f"\n[Chunk #{i+1}] ID: {chunk_id}")
    print(f"Distance Score: {distance}")
    print(f"Source File: {metadata.get('source_file')}")
    print(f"Title: {metadata.get('title')} | Section: {metadata.get('section_title')}")
    print("RAW TEXT:")
    print(document)
