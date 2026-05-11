![Demo](https://github.com/user-attachments/assets/2d938624-cc39-4f8b-b35b-485b23e93355)

# Mazemaker Plugin

Local semantic memory with knowledge graph, spreading activation, auto-connections, and biological-sleep-inspired dream consolidation.

## Features

- **Semantic search** via vector embeddings (FastEmbed, sentence-transformers, tfidf, hash)
- **Knowledge graph** with automatic connection discovery between related memories
- **Spreading activation** for exploring connected ideas beyond direct similarity
- **Dream consolidation** — NREM strengthens edges, REM bridges isolated nodes, Insight detects communities
- **Fully offline** — no API keys, no cloud, everything in local SQLite (or Postgres for Pro)

## Configuration

```yaml
# ~/.hermes/config.yaml
memory:
  provider: mazemaker
  mazemaker:
    db_path: ~/.mazemaker/memory.db
    embedding_backend: auto   # auto | fastembed | sentence-transformers | tfidf | hash
    retrieval_mode: advanced  # semantic | hybrid | advanced | skynet | lean
```

Or environment overrides:
- `MAZEMAKER_DB_PATH` — SQLite database path
- `MAZEMAKER_EMBEDDING_BACKEND` — embedding backend selection

## Tools

| Tool | Description |
|------|-------------|
| `mazemaker_remember` | Store a memory (auto-embedded, auto-connected) |
| `mazemaker_recall` | Semantic search over stored memories |
| `mazemaker_think` | Spreading activation — explore connected ideas |
| `mazemaker_graph` | Knowledge graph statistics |
| `mazemaker_dream` | Trigger a dream cycle on demand |

## CLI

```bash
hermes mazemaker status
hermes mazemaker remember "User prefers fish shell"
hermes mazemaker recall "shell preferences"
hermes mazemaker think 1234 --depth 3
hermes mazemaker graph
```

## Embedding backends

- **FastEmbed** (ONNX, no PyTorch conflict) — recommended default
- **sentence-transformers** — best quality, requires PyTorch
- **tfidf** — trained on seen corpus, no external deps
- **hash** — fastest, deterministic, no deps

All backends produce 1024-dimensional vectors.

## Dependencies

Core: `sqlite3` (stdlib), `numpy`

Optional for production-grade embeddings:
```bash
pip install fastembed              # recommended
# or
pip install sentence-transformers  # if PyTorch available
```
