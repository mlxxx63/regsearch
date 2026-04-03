from flask import Flask, request, jsonify, render_template
from search import search  # import our search function from Phase 5

app = Flask(__name__)


@app.route("/")
def index():
    """Serve the HTML frontend."""
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search_endpoint():
    """
    Accepts: POST /search with JSON body {"query": "...", "top_k": 5}
    Returns: JSON array of search results
    """
    data = request.get_json()

    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' field in request body"}), 400

    query = data.get("query", "").strip()
    top_k = data.get("top_k", 5)

    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    try:
        results = search(query, top_k=top_k)
        return jsonify({"query": query, "results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stats")
def stats():
    """Return basic database stats."""
    import sqlite3
    conn = sqlite3.connect("regsearch.db")
    reg_count = conn.execute("SELECT COUNT(*) FROM regulations").fetchone()[0]
    sec_count = conn.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
    emb_count = conn.execute("SELECT COUNT(*) FROM sections WHERE embedding IS NOT NULL").fetchone()[0]
    conn.close()

    return jsonify({
        "regulations": reg_count,
        "sections": sec_count,
        "sections_with_embeddings": emb_count
    })


if __name__ == "__main__":
    print("Starting RegSearch server...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
