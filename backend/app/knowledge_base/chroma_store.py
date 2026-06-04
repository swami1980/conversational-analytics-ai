"""
In-memory TF-IDF vector store — same build_index/search interface as ChromaDB.
Uses numpy only (no native deps), making it compatible with Python 3.13 arm64.

Production swap: replace this module with chromadb.PersistentClient +
OpenSearch Serverless for scalable semantic search on AWS.
"""
import re
import math
import yaml
import numpy as np
from pathlib import Path
from collections import Counter

SPECS_DIR = Path(__file__).parent.parent / "openapi_specs"

_documents: list[str] = []
_metadatas: list[dict] = []
_tfidf_matrix: np.ndarray | None = None
_vocab: dict[str, int] = {}
_idf: np.ndarray | None = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_/-]+", text.lower())


def _build_tfidf_matrix(docs: list[str]):
    global _vocab, _idf, _tfidf_matrix

    # Build vocabulary from all documents
    _vocab = {}
    for doc in docs:
        for tok in set(_tokenize(doc)):
            if tok not in _vocab:
                _vocab[tok] = len(_vocab)

    V = len(_vocab)
    N = len(docs)
    matrix = np.zeros((N, V), dtype=np.float32)

    for i, doc in enumerate(docs):
        tokens = _tokenize(doc)
        if not tokens:
            continue
        tf = Counter(tokens)
        for tok, cnt in tf.items():
            if tok in _vocab:
                matrix[i, _vocab[tok]] = cnt / len(tokens)

    # IDF with smoothing
    df = np.sum(matrix > 0, axis=0).astype(np.float32)
    _idf = np.log((N + 1) / (df + 1)).astype(np.float32) + 1.0
    matrix = matrix * _idf

    # L2 normalise rows
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    _tfidf_matrix = matrix / norms


def _query_vec(query: str) -> np.ndarray:
    tokens = _tokenize(query)
    vec = np.zeros(len(_vocab), dtype=np.float32)
    tf = Counter(tokens)
    for tok, cnt in tf.items():
        if tok in _vocab:
            vec[_vocab[tok]] = (cnt / len(tokens)) * _idf[_vocab[tok]]
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def _parse_spec_into_chunks(api_name: str, spec: dict) -> list[dict]:
    chunks = []
    info = spec.get("info", {})
    api_desc = info.get("description", "").strip()
    base_url = spec.get("servers", [{}])[0].get("url", "")

    for path, path_item in spec.get("paths", {}).items():
        for method, op in path_item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            summary = op.get("summary", "")
            description = op.get("description", "").strip()
            params = [
                f"- {p['name']} ({p['in']}): {p.get('description', p.get('schema', {}).get('type', ''))}"
                for p in op.get("parameters", [])
            ]
            text = (
                f"API: {api_name}\n"
                f"API Description: {api_desc}\n"
                f"Endpoint: {method.upper()} {base_url}{path}\n"
                f"Summary: {summary}\n"
                f"Description: {description}\n"
                f"Parameters:\n" + "\n".join(params)
            )
            chunks.append({
                "text": text,
                "metadata": {
                    "api_name": api_name,
                    "method": method.upper(),
                    "path": path,
                    "full_path": f"{base_url}{path}",
                    "summary": summary,
                    "operation_id": op.get("operationId", ""),
                },
            })

    # Top-level overview chunk
    chunks.append({
        "text": f"API: {api_name}\nOverview: {api_desc}\nBase URL: {base_url}",
        "metadata": {
            "api_name": api_name,
            "method": "OVERVIEW",
            "path": "/",
            "full_path": base_url,
            "summary": f"{api_name} overview",
            "operation_id": "overview",
        },
    })
    return chunks


def build_index(persist_dir: str = "./chroma_db") -> None:
    """Index all 7 OpenAPI specs into the in-memory TF-IDF store."""
    global _documents, _metadatas

    _documents, _metadatas = [], []
    for spec_file in sorted(SPECS_DIR.glob("*.yaml")):
        api_name = spec_file.stem.replace("_", " ").title()
        spec = yaml.safe_load(spec_file.read_text())
        for chunk in _parse_spec_into_chunks(api_name, spec):
            _documents.append(chunk["text"])
            _metadatas.append(chunk["metadata"])

    _build_tfidf_matrix(_documents)


def search(query: str, n_results: int = 4, persist_dir: str = "./chroma_db") -> list[dict]:
    """Return the top-n most relevant API spec chunks for a query."""
    if _tfidf_matrix is None or len(_documents) == 0:
        return []

    qvec = _query_vec(query)
    scores = _tfidf_matrix @ qvec          # cosine similarity (rows already normalised)
    top_idx = np.argsort(scores)[::-1][:n_results]

    return [
        {
            "text": _documents[i],
            "metadata": _metadatas[i],
            "distance": float(1.0 - scores[i]),
        }
        for i in top_idx
    ]
