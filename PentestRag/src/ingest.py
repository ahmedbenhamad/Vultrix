"""
Ingest module – Production-grade ingestion pipeline with multi-level deduplication and data cleaning.
Optimized for high-quality knowledge retrieval by filtering noise and redundant chunks.
"""

import os
import glob
import logging
import hashlib
import json
import string
import time
from typing import List, Set

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.exceptions import ResponseHandlingException

from .config import (
    DATA_DIR, 
    CHUNK_SIZE, 
    CHUNK_OVERLAP, 
    EMBEDDING_MODEL_NAME,
    QDRANT_URL,
    QDRANT_PORT,
    QDRANT_COLLECTION_NAME,
    QDRANT_API_KEY
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Logic Helpers
# ---------------------------------------------------------------------------
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".php", ".rb", ".pl", 
    ".lua", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".sh", 
    ".bash", ".ps1", ".sql", ".nse", ".rules"
}

TEXT_EXTENSIONS = frozenset({
    ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".log", ".conf", ".env", ".properties",
    *CODE_EXTENSIONS
})

IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp",
})

NOISY_JSON_KEYS = {
    "references",
    "reference",
    "tags",
    "tag",
    "url",
    "urls",
    "refsource",
    "datepublished",
    "datereserved",
    "dateupdated",
    "assignershortname",
    "datatype",
    "dataversion",
    "providermetadata",
    "credits",
    "containers",
    "metrics",
    "timeline",
    "taxonomy_mappings",
}

USEFUL_JSON_KEYS = {
    "cveid",
    "title",
    "description",
    "descriptions",
    "problemtypes",
    "problemtype",
    "value",
    "solution",
    "impact",
    "attackvector",
    "affected",
    "affected_versions",
    "versions",
    "product",
    "products",
    "vendor",
    "module",
    "component",
    "steps",
    "exploit",
    "payload",
    "poc",
}

# ---------------------------------------------------------------------------
# Data Quality Helpers
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Conserver les retours à la ligne pour la structure des exploits
    text = "".join(c for c in text if c.isprintable() or c in "\n\t")
    # Supprimer les espaces multiples mais garder les sauts de ligne
    import re
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


def is_mostly_binary(text: str, threshold: float = 0.8) -> bool:
    if not text:
        return True
    printable_count = sum(1 for c in text if c.isprintable())
    return (printable_count / len(text)) < threshold


def _looks_like_noisy_json_line(text: str) -> bool:
    return False


def extract_text_from_json_node(node, parent_key: str | None = None) -> list[str]:
    parts: list[str] = []

    if isinstance(node, dict):
        for key, value in node.items():
            lowered_key = key.lower()
            if lowered_key in NOISY_JSON_KEYS:
                continue

            if lowered_key in USEFUL_JSON_KEYS:
                parts.extend(extract_text_from_json_node(value, lowered_key))
            elif lowered_key in {"lang", "state"}:
                continue
            else:
                parts.extend(extract_text_from_json_node(value, lowered_key))
    elif isinstance(node, list):
        for item in node:
            parts.extend(extract_text_from_json_node(item, parent_key))
    elif isinstance(node, str):
        text = node.strip()
        if len(text) < 3:
            return parts
        if _looks_like_noisy_json_line(text):
            return parts

        if parent_key in {"cveid", "title", "description", "value", "problemtype", "problemtypes"}:
            parts.append(text)
        elif any(char.isspace() for char in text) and len(text) >= 40:
            parts.append(text)

    return parts


def clean_json_content(raw_text: str) -> str:
    try:
        parsed = json.loads(raw_text)
    except Exception:
        return raw_text

    extracted_parts = extract_text_from_json_node(parsed)
    deduped_parts = []
    seen = set()
    for part in extracted_parts:
        normalized = clean_text(part)
        if not normalized or len(normalized) < 3:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped_parts.append(normalized)

    if deduped_parts:
        return "\n\n".join(deduped_parts)

    return raw_text
# ---------------------------------------------------------------------------
# OCR helper
# ---------------------------------------------------------------------------
_TESSERACT_AVAILABLE: bool | None = None

def _check_tesseract() -> bool:
    global _TESSERACT_AVAILABLE
    if _TESSERACT_AVAILABLE is not None:
        return _TESSERACT_AVAILABLE
    try:
        import pytesseract
        from PIL import Image
        pytesseract.get_tesseract_version()
        _TESSERACT_AVAILABLE = True
    except Exception:
        _TESSERACT_AVAILABLE = False
        logger.warning("Tesseract OCR NOT available.")
    return _TESSERACT_AVAILABLE

def _ocr_image(file_path: str) -> str | None:
    if not _check_tesseract():
        return None
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img).strip()
        # Initial cleanup and length check
        if text and len(text) >= 30:
            return text
        return None
    except Exception as exc:
        logger.warning("OCR failed for %s: %s", file_path, exc)
        return None

# ---------------------------------------------------------------------------
# Main ingestor class
# ---------------------------------------------------------------------------
class PentestIngestor:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
            add_start_index=True,
        )
        self.client = QdrantClient(url=QDRANT_URL, port=QDRANT_PORT, api_key=QDRANT_API_KEY)
        self.seen_file_hashes: Set[str] = set()
        self.seen_chunk_hashes: Set[str] = set()

    def _get_hash(self, text: str) -> str:
        """Generate SHA256 hash for deduplication."""
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    def load_single_document(self, file_path: str) -> Document | None:
        """Loads a document with file-level deduplication and metadata preservation."""
        ext = os.path.splitext(file_path)[1].lower()
        content = None

        try:
            if ext in TEXT_EXTENSIONS:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if ext == ".json":
                        content = clean_json_content(content)
                except Exception as e:
                    logger.warning("Failed to read %s: %s", file_path, e)
                    return None
            elif ext in IMAGE_EXTENSIONS:
                content = _ocr_image(file_path)
            
            if not content or not content.strip():
                return None

            # 1. File-level Deduplication
            content_hash = self._get_hash(content)
            if content_hash in self.seen_file_hashes:
                return None
            self.seen_file_hashes.add(content_hash)

            # Metadata setup
            lower_path = file_path.lower()
            source_type = "general"
            if "cve" in lower_path:
                source_type = "cve"
            elif "attack" in lower_path or "mitre" in lower_path:
                source_type = "attack"
            elif "exploit" in lower_path or "exploitdb" in lower_path:
                source_type = "exploit"
            elif "log" in lower_path:
                source_type = "log"
            elif "writeup" in lower_path or "ctf" in lower_path:
                source_type = "writeup"
            elif "tool" in lower_path or "nmap" in lower_path or "metasploit" in lower_path or "burp" in lower_path:
                source_type = "tool"

            metadata = {
                "source": os.path.abspath(file_path),
                "type": ext.lstrip("."),
                "is_code": ext in CODE_EXTENSIONS,
                "file_hash": content_hash,
                "source_type": source_type
            }
            
            return Document(page_content=content, metadata=metadata)
        except Exception as e:
            logger.error("Error loading %s: %s", file_path, e)
            return None

    def _upsert_with_retry(self, chunks, upsert_timeout: int, upsert_retries: int) -> None:
        """Upsert documents to Qdrant with timeout/retry handling."""
        last_exc = None
        for attempt in range(1, upsert_retries + 1):
            try:
                # Direct client upsert with manual embedding to bypass LangChain version issues
                texts = [c.page_content for c in chunks]
                metadatas = [c.metadata for c in chunks]
                embeddings = self.embeddings.embed_documents(texts)
                
                points = []
                for idx, (text, meta, emb) in enumerate(zip(texts, metadatas, embeddings)):
                    point_id = hashlib.md5(text.encode()).hexdigest()
                    points.append(rest.PointStruct(
                        id=point_id,
                        vector=emb,
                        payload={**meta, "page_content": text}
                    ))

                self.client.upsert(
                    collection_name=QDRANT_COLLECTION_NAME,
                    points=points,
                    wait=True,
                    timeout=upsert_timeout
                )
                return
            except Exception as exc:
                last_exc = exc
                if "timeout" in str(exc).lower() or "deadline" in str(exc).lower():
                    sleep_for = min(2 ** attempt, 10)
                    logger.warning(
                        "Qdrant upsert timeout (attempt %s/%s, batch=%s). Retrying in %ss...",
                        attempt,
                        upsert_retries,
                        len(chunks),
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                else:
                    logger.error("Error during Qdrant upsert (attempt %s/%s): %s", attempt, upsert_retries, exc)
                    time.sleep(1)

        raise RuntimeError(f"Qdrant upsert failed after {upsert_retries} retries: {last_exc}")

    def process_and_index(
        self,
        batch_size: int = 100,
        upsert_batch_size: int = 16,
        upsert_retries: int = 6,
        upsert_timeout: int = 180,
    ):
        """Memory-safe ingestion with multi-level deduplication and text cleaning."""
        print(f"[*] Initializing Production Ingestion from {DATA_DIR}...")
        
        # Setup Collection
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == QDRANT_COLLECTION_NAME for c in collections):
                sample_emb = self.embeddings.embed_query("sample")
                self.client.create_collection(
                    collection_name=QDRANT_COLLECTION_NAME,
                    vectors_config=rest.VectorParams(size=len(sample_emb), distance=rest.Distance.COSINE),
                )
        except Exception as e:
            print(f"Error initializing collection: {e}")

        # Scan files
        all_files = []
        for root, _, files in os.walk(DATA_DIR):
            for f in files:
                all_files.append(os.path.join(root, f))
        
        print(f"[*] Found {len(all_files)} files. Starting processing...")

        total_chunks = 0
        skipped_duplicates = 0
        skipped_weak = 0
        skipped_binary = 0

        # Batch Processing
        for i in range(0, len(all_files), batch_size):
            file_batch = all_files[i : i + batch_size]
            batch_docs = []
            
            for f_path in file_batch:
                doc = self.load_single_document(f_path)
                if doc:
                    batch_docs.append(doc)
            
            if not batch_docs:
                continue

            # Chunking
            raw_chunks = self.text_splitter.split_documents(batch_docs)
            cleaned_chunks = []

            for chunk in raw_chunks:
                # 2. Text Cleaning & Normalization
                cleaned_text = clean_text(chunk.page_content)
                
                # 3. Filter Small/Weak Chunks
                if len(cleaned_text) < 30:
                    skipped_weak += 1
                    continue
                
                # 4. Filter Binary Noise
                if is_mostly_binary(cleaned_text):
                    skipped_binary += 1
                    continue

                # 5. Chunk-level Deduplication
                chunk_hash = self._get_hash(cleaned_text)
                if chunk_hash in self.seen_chunk_hashes:
                    skipped_duplicates += 1
                    continue
                
                self.seen_chunk_hashes.add(chunk_hash)
                
                # Update chunk content and add metadata
                chunk.page_content = cleaned_text
                chunk.metadata["chunk_hash"] = chunk_hash
                cleaned_chunks.append(chunk)

            if cleaned_chunks:
                for j in range(0, len(cleaned_chunks), upsert_batch_size):
                    qdrant_batch = cleaned_chunks[j : j + upsert_batch_size]
                    self._upsert_with_retry(
                        qdrant_batch,
                        upsert_timeout=upsert_timeout,
                        upsert_retries=upsert_retries,
                    )
                total_chunks += len(cleaned_chunks)
                print(f"  -> Progress: Batch {i//batch_size + 1} | +{len(cleaned_chunks)} valid chunks")

        print(f"\n[+] Ingestion Complete:")
        print(f"    - Total Chunks Indexed:  {total_chunks}")
        print(f"    - Duplicate Chunks:      {skipped_duplicates}")
        print(f"    - Weak/Small Chunks:     {skipped_weak}")
        print(f"    - Binary Noise Chunks:   {skipped_binary}")
        
        return self.client

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    ingestor = PentestIngestor()
    ingestor.process_and_index(
        batch_size=100,
        upsert_batch_size=16,
        upsert_timeout=180,
        upsert_retries=6,
    )
