import os
import logging
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Suppress annoying HuggingFace and Transformers terminal warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

warnings.filterwarnings('ignore')
warnings.filterwarnings('ignore', category=UserWarning)

# Set logging levels to ERROR for all underlying science libraries
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# Additional effort to silence the BertModel LOAD REPORT
try:
    import transformers
    transformers.logging.set_verbosity_error()
except ImportError:
    pass

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EMBEDDINGS_DIR = BASE_DIR / "embeddings"

# Detect if running inside Docker
IS_DOCKER = os.path.exists('/.dockerenv')

# Configuration Provider & Model
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Ollama logic: Use host.docker.internal if in Docker (to reach host GPU)
DEFAULT_OLLAMA_URL = "http://host.docker.internal:11434" if IS_DOCKER else "http://localhost:11434"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)

DEFAULT_MODEL = os.getenv("LLM_MODEL", "")

# RAG Parameters
CHUNK_SIZE = 500
CHUNK_OVERLAP = 200
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1")

# Reranking Settings
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RETRIEVAL_TOP_K = 100
RERANK_TOP_K = 5

# Context Limits (expanded to ensure full payloads are captured)
CONTEXT_PER_DOC_MAX_CHARS = 8000
CONTEXT_MAX_CHARS = 24000
CONTEXT_SECTION_MAX_CHARS = 2200

# Cache Settings
CACHE_ENABLED = True
CACHE_TTL = 3600  # 1 hour
CACHE_SIZE_LIMIT = 1000

# Qdrant Settings: Use 'qdrant' service name if in Docker
DEFAULT_QDRANT_URL = "http://qdrant" if IS_DOCKER else "http://localhost"
QDRANT_URL = os.getenv("QDRANT_URL", DEFAULT_QDRANT_URL)
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "pentest_rag")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# Generation Parameters
MAX_TOKENS = 2048
TEMPERATURE = 0.1
