import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer

DB_PATH = "regsearch.db"
MODEL_NAME = "all-MiniLM-L6-v2"  # small, fast, runs on CPU, 384-dim vectors


def vector_to_blob(vector):
    """
    Convert a numpy array to bytes for storage in SQLite BLOB column.
    numpy arrays can't be stored directly in SQLite — we serialize them.
    """
    return vector.astype(np.float32).tobytes()


def blob_to_vector(blob):
    """
    Convert bytes back to a numpy array when reading from SQLite.
    """
    return np.frombuffer(blob, dtype=np.float32)


def run_embeddings():
    print(f"Loading model: {MODEL_NAME}")
    print("(First run downloads ~90MB model — subsequent runs are instant)\n")
    model = SentenceTransformer(MODEL_NAME)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all sections that don't have an embedding yet
    cursor.execute("SELECT id, section_text FROM sections WHERE embedding IS NULL")
    rows = cursor.fetchall()

    if not rows:
        print("All sections already have embeddings. Nothing to do.")
        conn.close()
        return

    print(f"Generating embeddings for {len(rows)} sections...")

    # Extract just the texts (section IDs kept separately)
    ids = [row[0] for row in rows]
    texts = [row[1] for row in rows]

    # Encode all texts in one batch — much faster than one at a time
    # show_progress_bar=True gives you a live progress indicator
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    # Store each embedding back in the database
    print("\nStoring embeddings in database...")
    for section_id, embedding_vector in zip(ids, embeddings):
        blob = vector_to_blob(embedding_vector)
        cursor.execute(
            "UPDATE sections SET embedding = ? WHERE id = ?",
            (blob, section_id)
        )

    conn.commit()
    conn.close()

    print(f"\nDone. {len(ids)} embeddings stored.")
    print(f"Each vector is {embeddings.shape[1]} dimensions (float32)")
    print(f"Total embedding data: ~{(len(ids) * embeddings.shape[1] * 4) / 1024:.1f} KB")


if __name__ == "__main__":
    run_embeddings()
