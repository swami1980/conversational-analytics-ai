import os
import yaml
import chromadb
from pathlib import Path
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

SPECS_DIR = Path(__file__).parent.parent / "openapi_specs"
COLLECTION_NAME = "recruiting_api_specs"

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def _get_client(persist_dir: str) -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=persist_dir)
    return _client


def _parse_spec_into_chunks(api_name: str, spec: dict) -> list[dict]:
    """Split an OpenAPI spec into per-endpoint documents for fine-grained retrieval."""
    chunks = []
    info = spec.get("info", {})
    api_description = info.get("description", "").strip()
    base_url = ""
    if spec.get("servers"):
        base_url = spec["servers"][0].get("url", "")

    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            summary = operation.get("summary", "")
            description = operation.get("description", "").strip()
            params = [
                f"- {p['name']} ({p['in']}): {p.get('description', p.get('schema', {}).get('type', ''))}"
                for p in operation.get("parameters", [])
            ]
            chunk_text = (
                f"API: {api_name}\n"
                f"API Description: {api_description}\n"
                f"Endpoint: {method.upper()} {base_url}{path}\n"
                f"Summary: {summary}\n"
                f"Description: {description}\n"
                f"Parameters:\n" + "\n".join(params)
            )
            chunks.append({
                "id": f"{api_name}::{method.upper()}::{path}",
                "text": chunk_text,
                "metadata": {
                    "api_name": api_name,
                    "method": method.upper(),
                    "path": path,
                    "full_path": f"{base_url}{path}",
                    "summary": summary,
                    "operation_id": operation.get("operationId", ""),
                },
            })

    # Also add a top-level API description chunk for broad queries
    chunks.append({
        "id": f"{api_name}::overview",
        "text": f"API: {api_name}\nOverview: {api_description}\nBase URL: {base_url}",
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


def build_index(persist_dir: str) -> None:
    """Load all OpenAPI YAML specs and index them into ChromaDB."""
    client = _get_client(persist_dir)

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=DefaultEmbeddingFunction(),
    )

    all_ids, all_texts, all_metadatas = [], [], []

    for spec_file in sorted(SPECS_DIR.glob("*.yaml")):
        api_name = spec_file.stem.replace("_", " ").title()
        with open(spec_file) as f:
            spec = yaml.safe_load(f)
        chunks = _parse_spec_into_chunks(api_name, spec)
        for chunk in chunks:
            all_ids.append(chunk["id"])
            all_texts.append(chunk["text"])
            all_metadatas.append(chunk["metadata"])

    collection.add(documents=all_texts, ids=all_ids, metadatas=all_metadatas)
    global _collection
    _collection = collection


def search(query: str, n_results: int = 4, persist_dir: str = "./chroma_db") -> list[dict]:
    """Retrieve the most relevant API spec chunks for a natural language query."""
    global _collection
    if _collection is None:
        client = _get_client(persist_dir)
        _collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=DefaultEmbeddingFunction(),
        )
    results = _collection.query(query_texts=[query], n_results=n_results)
    hits = []
    for i, doc in enumerate(results["documents"][0]):
        hits.append({
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return hits
