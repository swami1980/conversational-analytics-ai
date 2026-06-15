"""
In-memory TF-IDF vector store — indexes two document types:
  1. OpenAPI specs  (chunked per endpoint)     → answers "which API to call"
  2. Wiki pages     (chunked per H2 section)   → answers "what does X mean / what does this app do"

Same build_index/search interface throughout.
Production swap: Amazon OpenSearch Serverless.
"""
import re
import yaml
import numpy as np
from pathlib import Path
from collections import Counter

SPECS_DIR = Path(__file__).parent.parent / "openapi_specs"
WIKI_DIR  = Path(__file__).parent.parent / "wiki"

_documents: list[str] = []
_metadatas: list[dict] = []
_tfidf_matrix: np.ndarray | None = None
_vocab: dict[str, int] = {}
_idf: np.ndarray | None = None


# ── TF-IDF core ──────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_/-]+", text.lower())


def _build_tfidf_matrix(docs: list[str]) -> None:
    global _vocab, _idf, _tfidf_matrix

    _vocab = {}
    for doc in docs:
        for tok in set(_tokenize(doc)):
            if tok not in _vocab:
                _vocab[tok] = len(_vocab)

    V, N = len(_vocab), len(docs)
    matrix = np.zeros((N, V), dtype=np.float32)

    for i, doc in enumerate(docs):
        tokens = _tokenize(doc)
        if not tokens:
            continue
        tf = Counter(tokens)
        for tok, cnt in tf.items():
            if tok in _vocab:
                matrix[i, _vocab[tok]] = cnt / len(tokens)

    df   = np.sum(matrix > 0, axis=0).astype(np.float32)
    _idf = np.log((N + 1) / (df + 1)).astype(np.float32) + 1.0
    matrix = matrix * _idf

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    _tfidf_matrix = matrix / norms


def _query_vec(query: str) -> np.ndarray:
    tokens = _tokenize(query)
    vec = np.zeros(len(_vocab), dtype=np.float32)
    tf  = Counter(tokens)
    for tok, cnt in tf.items():
        if tok in _vocab:
            vec[_vocab[tok]] = (cnt / len(tokens)) * _idf[_vocab[tok]]
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


# ── OpenAPI spec chunker ──────────────────────────────────────────────────────

def _parse_spec_into_chunks(api_name: str, spec: dict) -> list[dict]:
    chunks = []
    info     = spec.get("info", {})
    api_desc = info.get("description", "").strip()
    base_url = spec.get("servers", [{}])[0].get("url", "")

    for path, path_item in spec.get("paths", {}).items():
        for method, op in path_item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            summary     = op.get("summary", "")
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
                    "source":       "api_spec",
                    "api_name":     api_name,
                    "method":       method.upper(),
                    "path":         path,
                    "full_path":    f"{base_url}{path}",
                    "summary":      summary,
                    "operation_id": op.get("operationId", ""),
                },
            })

    chunks.append({
        "text": f"API: {api_name}\nOverview: {api_desc}\nBase URL: {base_url}",
        "metadata": {
            "source":       "api_spec",
            "api_name":     api_name,
            "method":       "OVERVIEW",
            "path":         "/",
            "full_path":    base_url,
            "summary":      f"{api_name} overview",
            "operation_id": "overview",
        },
    })
    return chunks


# ── Wiki page chunker (split on H2 sections) ─────────────────────────────────

def _parse_wiki_into_chunks(filename: str, content: str) -> list[dict]:
    """Split a markdown wiki page into one chunk per H2 section."""
    chunks  = []
    page_title = ""

    # Extract H1 title
    h1 = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1:
        page_title = h1.group(1).strip()

    # Split on H2 headings
    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Get section heading
        heading_match = re.match(r"^##\s+(.+)$", section, re.MULTILINE)
        heading = heading_match.group(1).strip() if heading_match else page_title

        # Clean markdown: remove heading markers, keep plain text
        plain = re.sub(r"^#+\s+", "", section, flags=re.MULTILINE)
        plain = re.sub(r"\*\*(.+?)\*\*", r"\1", plain)  # bold
        plain = re.sub(r"`(.+?)`", r"\1", plain)         # inline code
        plain = plain.strip()

        if len(plain) < 30:
            continue

        text = f"Wiki: {page_title}\nSection: {heading}\n\n{plain}"
        chunks.append({
            "text": text,
            "metadata": {
                "source":    "wiki",
                "file":      filename,
                "page":      page_title,
                "section":   heading,
                "summary":   f"{page_title} — {heading}",
            },
        })

    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def build_index(persist_dir: str = "./chroma_db") -> None:
    """Index all OpenAPI specs + all wiki pages into the TF-IDF store."""
    global _documents, _metadatas
    _documents, _metadatas = [], []

    # 1. OpenAPI specs
    for spec_file in sorted(SPECS_DIR.glob("*.yaml")):
        api_name = spec_file.stem.replace("_", " ").title()
        spec = yaml.safe_load(spec_file.read_text())
        for chunk in _parse_spec_into_chunks(api_name, spec):
            _documents.append(chunk["text"])
            _metadatas.append(chunk["metadata"])

    # 2. Wiki pages
    if WIKI_DIR.exists():
        for wiki_file in sorted(WIKI_DIR.glob("*.md")):
            for chunk in _parse_wiki_into_chunks(wiki_file.name, wiki_file.read_text()):
                _documents.append(chunk["text"])
                _metadatas.append(chunk["metadata"])

    _build_tfidf_matrix(_documents)

    spec_count = sum(1 for m in _metadatas if m["source"] == "api_spec")
    wiki_count = sum(1 for m in _metadatas if m["source"] == "wiki")
    print(f"✓ Knowledge base indexed: {spec_count} API spec chunks + {wiki_count} wiki chunks")


def search(query: str, n_results: int = 4, persist_dir: str = "./chroma_db") -> list[dict]:
    """
    Return the top-n most relevant chunks for a query.

    Balancing strategy: always return at least 1 result from each source type
    (wiki and api_spec) when both are present, so the agent always has both
    conceptual context and the correct API endpoint available.
    The remaining slots go to whichever source scored highest overall.
    """
    if _tfidf_matrix is None or len(_documents) == 0:
        return []

    qvec   = _query_vec(query)
    scores = _tfidf_matrix @ qvec

    # Split indices by source type
    api_idx  = [i for i, m in enumerate(_metadatas) if m["source"] == "api_spec"]
    wiki_idx = [i for i, m in enumerate(_metadatas) if m["source"] == "wiki"]

    def top_from(indices, k):
        ranked = sorted(indices, key=lambda i: scores[i], reverse=True)
        return ranked[:k]

    # Guarantee at least 1 from each source, fill remaining with best overall
    reserved_api  = top_from(api_idx,  1)
    reserved_wiki = top_from(wiki_idx, 1)
    reserved = set(reserved_api + reserved_wiki)

    remaining_slots = n_results - len(reserved)
    all_ranked = np.argsort(scores)[::-1]
    filler = [i for i in all_ranked if i not in reserved][:remaining_slots]

    final_idx = sorted(reserved | set(filler), key=lambda i: scores[i], reverse=True)

    return [
        {
            "text":     _documents[i],
            "metadata": _metadatas[i],
            "distance": float(1.0 - scores[i]),
        }
        for i in final_idx
    ]
