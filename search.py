import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer

DB_PATH = "regsearch.db"
MODEL_NAME = "all-MiniLM-L6-v2"

# Load model once at module level so it's not reloaded on every search call
print("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)
print("Model ready.\n")


def blob_to_vector(blob):
    return np.frombuffer(blob, dtype=np.float32)


def cosine_similarity(vec_a, vec_b):
    """
    Compute cosine similarity between two vectors.
    Returns a float between -1 and 1 (higher = more similar).
    """
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def load_all_embeddings():
    """
    Load every section and its embedding from the database.
    Returns a list of dicts with keys: id, regulation_title, section_number, section_text, vector
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            s.id,
            r.title AS regulation_title,
            s.section_number,
            s.section_text,
            s.embedding
        FROM sections s
        JOIN regulations r ON s.regulation_id = r.id
        WHERE s.embedding IS NOT NULL
    """)

    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        section_id, reg_title, sec_num, sec_text, embedding_blob = row
        vector = blob_to_vector(embedding_blob)
        data.append({
            "id": section_id,
            "regulation_title": reg_title,
            "section_number": sec_num,
            "section_text": sec_text,
            "vector": vector
        })

    return data


def search(query, top_k=5):
    """
    Semantic search: embed the query, compare against all section embeddings,
    return the top_k most similar sections with their similarity scores.
    """
    # Step 1: embed the query
    query_vector = model.encode(query)

    # Step 2: load all section embeddings
    all_sections = load_all_embeddings()

    if not all_sections:
        print("No embeddings in database yet. Run embeddings.py first.")
        return []

    # Step 3: compute cosine similarity for every section
    results = []
    for section in all_sections:
        score = cosine_similarity(query_vector, section["vector"])
        results.append({
            "score": float(score),
            "regulation_title": section["regulation_title"],
            "section_number": section["section_number"],
            "section_text": section["section_text"]
        })

    # Step 4: sort by score descending, return top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def print_results(query, results):
    print(f"\nQuery: '{query}'")
    print("=" * 60)
    for i, result in enumerate(results, 1):
        print(f"\n#{i} — Score: {result['score']:.4f}")
        print(f"  Regulation: {result['regulation_title']}")
        print(f"  Section:    {result['section_number']}")
        print(f"  Text:       {result['section_text'][:200]}...")
    print()


if __name__ == "__main__":
    # Test queries — try a few different ones
    test_queries = [
        "minister may grant a permit",
        "environmental protection standards",
        "penalty for violation of regulations",
        "public health and safety requirements",
    ]

    for query in test_queries:
        results = search(query, top_k=3)
        print_results(query, results)
