"""Save the sentence-embedding model inside the project so Sentinel runs fully offline: models/minilm."""
from pathlib import Path
from sentence_transformers import SentenceTransformer

out = Path(__file__).resolve().parents[1] / "models" / "minilm"
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2").save(str(out))
print("saved", out)
