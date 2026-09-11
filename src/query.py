"""
Query module - optimized for accuracy with reranking and caching.
Integrates Cross-Encoder/ms-marco-MiniLM-L-6-v2 for reranking.
"""

import httpx
import json
import time
import logging
import re
from typing import Dict, Any, Optional

from sentence_transformers import CrossEncoder
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_huggingface import HuggingFaceEmbeddings

from .config import (
    EMBEDDING_MODEL_NAME,
    LLM_PROVIDER,
    OPENROUTER_API_KEY,
    OLLAMA_BASE_URL,
    DEFAULT_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    QDRANT_URL,
    QDRANT_PORT,
    QDRANT_COLLECTION_NAME,
    QDRANT_API_KEY,
    RERANK_MODEL_NAME,
    RETRIEVAL_TOP_K,
    RERANK_TOP_K,
    CACHE_ENABLED,
    CACHE_TTL,
    CACHE_SIZE_LIMIT,
    CONTEXT_PER_DOC_MAX_CHARS,
    CONTEXT_MAX_CHARS,
    CONTEXT_SECTION_MAX_CHARS,
)

logger = logging.getLogger(__name__)


class QueryCache:
    def __init__(self, ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
        self.max_size = CACHE_SIZE_LIMIT

    def get(self, query: str) -> Optional[str]:
        if not CACHE_ENABLED:
            return None
        if query in self.cache:
            entry = self.cache[query]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["response"]
            del self.cache[query]
        return None

    def set(self, query: str, response: str):
        if not CACHE_ENABLED:
            return
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache, key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
        self.cache[query] = {
            "response": response,
            "timestamp": time.time(),
        }


class PentestRAG:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PentestRAG, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        self.client = QdrantClient(url=QDRANT_URL, port=QDRANT_PORT, api_key=QDRANT_API_KEY)

        try:
            self.vector_db = QdrantVectorStore(
                client=self.client,
                collection_name=QDRANT_COLLECTION_NAME,
                embedding=self.embeddings,
            )
        except Exception as e:
            err_msg = str(e).lower()
            if "dimensions" in err_msg:
                print("[!] Dimension mismatch detected. Deleting collection to force recreation...")
                try:
                    self.client.delete_collection(collection_name=QDRANT_COLLECTION_NAME)
                except Exception:
                    pass
                self.vector_db = None
            elif "not found" in err_msg or "404" in err_msg:
                print("[!] Collection not found. It will be created during ingestion.")
                self.vector_db = None
            else:
                raise

        print(f"[*] Loading reranker model: {RERANK_MODEL_NAME}...")
        self.reranker = CrossEncoder(RERANK_MODEL_NAME)
        self.cache = QueryCache(ttl=CACHE_TTL)
        self._initialized = True

    def _initialize_vector_store(self) -> None:
        self.vector_db = QdrantVectorStore(
            client=self.client,
            collection_name=QDRANT_COLLECTION_NAME,
            embedding=self.embeddings,
        )

    def _ensure_vector_store(self) -> bool:
        if self.vector_db is not None:
            return True

        try:
            self._initialize_vector_store()
            return True
        except Exception as exc:
            err_msg = str(exc).lower()
            if "not found" in err_msg or "404" in err_msg:
                logger.warning("Qdrant collection '%s' is not available yet.", QDRANT_COLLECTION_NAME)
                return False
            raise

    def _keyword_hits(self, text: str, query_tokens: set[str]) -> int:
        lowered = text.lower()
        return sum(1 for token in query_tokens if token in lowered)

    def _extract_relevant_excerpt(
        self,
        text: str,
        query_tokens: set[str],
        max_chars: int,
        section_chars: int,
    ) -> str:
        """
        Prefer the most query-relevant sections from long writeups.

        This keeps exploit and payload content while reducing irrelevant prompt
        bulk from the front of large documents.
        """
        if len(text) <= max_chars:
            return text

        sections = [section.strip() for section in re.split(r"\n\s*\n", text) if section.strip()]
        if not sections:
            return text[:max_chars]

        ranked_sections = []
        for idx, section in enumerate(sections):
            hits = self._keyword_hits(section, query_tokens)
            lowered = section.lower()
            bonus = 0
            if "cve-" in lowered:
                bonus += 2
            if "payload" in lowered or "exploit" in lowered:
                bonus += 2
            if "curl " in lowered or "python " in lowered or "nc " in lowered:
                bonus += 1
            ranked_sections.append((hits + bonus, -idx, section))

        ranked_sections.sort(reverse=True)

        selected_sections = []
        total = 0
        for score, _, section in ranked_sections:
            if score <= 0 and selected_sections:
                continue

            excerpt = section[:section_chars]
            addition_len = len(excerpt) + (2 if selected_sections else 0)
            if total + addition_len > max_chars:
                remaining = max_chars - total
                if remaining > 200:
                    selected_sections.append(excerpt[:remaining])
                break

            selected_sections.append(excerpt)
            total += addition_len
            if total >= max_chars:
                break

        if not selected_sections:
            return text[:max_chars]

        return "\n\n".join(selected_sections)

    def _looks_like_weak_chunk(self, text: str) -> bool:
        return False

    def _technical_signal_score(self, text: str) -> int:
        lowered = text.lower()
        score = 0
        signals = (
            " exploit",
            "payload",
            " poc",
            "cve-",
            "curl ",
            "python ",
            "nc ",
            "manager",
            "/manager",
            "authorization",
            "authentication",
            "upload",
            "reverse shell",
            "request smuggling",
            "rce",
            "0x",
            "\\x",
            "base64",
            "etc/passwd",
            "bin/sh",
        )
        for signal in signals:
            if signal in lowered:
                score += 1
        return score

    def _target_match_score(self, text: str, target_context: Optional[Dict]) -> float:
        if not target_context:
            return 0.0

        lowered = text.lower()
        score = 0.0

        service = (target_context.get("service") or "").strip().lower()
        version = (target_context.get("version") or "").strip().lower()
        os_info = (target_context.get("os") or "").strip().lower()
        findings = [str(item).strip().lower() for item in target_context.get("findings", []) if str(item).strip()]
        service_present = False

        if service:
            service_tokens = [token for token in re.split(r"[\s/:-]+", service) if len(token) > 2]
            matched_service_tokens = sum(1 for token in service_tokens if token in lowered)
            score += 0.12 * matched_service_tokens
            if service in lowered:
                score += 0.2
                service_present = True
            elif matched_service_tokens >= max(1, len(service_tokens) // 2):
                service_present = True
            else:
                score -= 0.35

        if version:
            if version in lowered:
                score += 0.45
            elif any(part and part in lowered for part in re.split(r"[._-]", version) if len(part) > 1):
                score += 0.1
            else:
                score -= 0.12

        if os_info and os_info in lowered:
            score += 0.08

        matched_findings = 0
        for finding in findings:
            finding_tokens = [token for token in re.split(r"[\s/:-]+", finding) if len(token) > 2]
            token_hits = sum(1 for token in finding_tokens if token in lowered)
            if token_hits >= 2:
                matched_findings += 1
                score += 0.12

        if "/manager" in lowered or "manager" in lowered:
            score += 0.18
        if "403" in lowered or "forbidden" in lowered:
            score += 0.12

        if service_present and ("/manager" in lowered or "manager" in lowered):
            score += 0.18

        if service and version and service in lowered and version in lowered:
            score += 0.25
        if matched_findings >= 1 and service and service in lowered:
            score += 0.15

        return score

    def _score_candidate(
        self,
        doc: Any,
        expanded_query: str,
        query_tokens: set[str],
        target_context: Optional[Dict] = None,
    ) -> tuple[float, float, int, float]:
        base_score = float(self.reranker.predict([[expanded_query, doc.page_content]], batch_size=1)[0])
        lexical_score = self._keyword_hits(doc.page_content, query_tokens)
        technical_score = self._technical_signal_score(doc.page_content)
        target_score = self._target_match_score(doc.page_content, target_context)
        final_score = base_score + (0.03 * lexical_score) + (0.08 * technical_score) + target_score
        return final_score, base_score, technical_score, target_score

    def retrieve_context(self, query: str, k: int = 5, target_context: Optional[Dict] = None) -> str:
        if not self._ensure_vector_store():
            return ""

        expanded_query = query.replace("RCE", "Remote Code Execution (RCE)").replace(
            "LFI", "Local File Inclusion (LFI)"
        )
        expanded_query = expanded_query.replace("SQLi", "SQL Injection (SQLi)").replace(
            "XSS", "Cross-Site Scripting (XSS)"
        )

        if target_context:
            service = target_context.get("service")
            version = target_context.get("version")
            os_info = target_context.get("os")
            findings = " ".join(target_context.get("findings", []))
            expanded_query += f" Target: {service} {version} {os_info}. Findings: {findings}"

        initial_results = self.vector_db.similarity_search(expanded_query, k=max(RETRIEVAL_TOP_K, 40))
        if not initial_results:
            return ""

        query_tokens = {
            token.lower()
            for token in expanded_query.replace("/", " ").replace(":", " ").split()
            if len(token) > 2
        }

        scored_results = []
        for doc in initial_results:
            final_score, base_score, technical_score, target_score = self._score_candidate(
                doc,
                expanded_query,
                query_tokens,
                target_context=target_context,
            )
            scored_results.append((doc, final_score, base_score, technical_score, target_score))

        scored_results.sort(key=lambda item: item[1], reverse=True)
        strong_results = scored_results
        targeted_results = [item for item in strong_results if item[4] > 0]

        if len(targeted_results) < max(3, k):
            fallback_query = f"{expanded_query} exploit writeup poc payload authentication bypass verification steps"
            fallback_results = self.vector_db.similarity_search(fallback_query, k=max(RETRIEVAL_TOP_K, 40))
            seen_contents = {doc.page_content for doc, *_ in scored_results}
            for doc in fallback_results:
                if doc.page_content in seen_contents:
                    continue
                final_score, base_score, technical_score, target_score = self._score_candidate(
                    doc,
                    fallback_query,
                    query_tokens,
                    target_context=target_context,
                )
                scored_results.append((doc, final_score, base_score, technical_score, target_score))
                seen_contents.add(doc.page_content)

            scored_results.sort(key=lambda item: item[1], reverse=True)
            strong_results = scored_results
            targeted_results = [item for item in strong_results if item[4] > 0]

        if targeted_results:
            candidate_results = targeted_results
        elif strong_results:
            candidate_results = strong_results
        else:
            candidate_results = scored_results
        top_results = [item[0] for item in candidate_results[: min(k, RERANK_TOP_K)]]

        if candidate_results and candidate_results[0][2] < 0.1:
            lexical_results = sorted(
                initial_results,
                key=lambda doc: (
                    self._target_match_score(doc.page_content, target_context),
                    self._keyword_hits(doc.page_content, query_tokens),
                    self._technical_signal_score(doc.page_content),
                    0 if self._looks_like_weak_chunk(doc.page_content) else 1,
                ),
                reverse=True,
            )
            seen = set()
            deduplicated_results = []
            for doc in top_results[:2] + lexical_results[: max(k - 2, 0)]:
                if doc.page_content not in seen:
                    deduplicated_results.append(doc)
                    seen.add(doc.page_content)
            top_results = deduplicated_results[:k]

        context_chunks = []
        total_chars = 0
        for doc in top_results:
            doc_text = self._extract_relevant_excerpt(
                doc.page_content,
                query_tokens=query_tokens,
                max_chars=CONTEXT_PER_DOC_MAX_CHARS,
                section_chars=CONTEXT_SECTION_MAX_CHARS,
            )
            block = f"[Source: {doc.metadata.get('source', 'Unknown')}]\n{doc_text}"
            block_len = len(block)
            if total_chars + block_len > CONTEXT_MAX_CHARS:
                break
            context_chunks.append(block)
            total_chars += block_len

        return "\n\n---\n\n".join(context_chunks)

    async def generate_response(
        self,
        query: str,
        context: str,
        target_context: Optional[Dict] = None,
        model: str = DEFAULT_MODEL,
    ) -> str:
        if not context.strip():
            return json.dumps(
                {
                    "vulnerability_id": "Insufficient Context",
                    "reasoning": (
                        "The knowledge base did not return enough relevant context to ground a reliable exploit plan. "
                        "Collect a more precise service name, version, endpoint behavior, or concrete error message and query again."
                    ),
                    "actionable_commands": [],
                    "payloads": [],
                    "exploit_code": "",
                    "post_exploitation": "",
                    "confidence_score": 0.0,
                }
            )

        target_info = "Not specified"
        if target_context:
            target_info = (
                f"Service: {target_context.get('service')}, "
                f"Version: {target_context.get('version')}, "
                f"OS: {target_context.get('os')}, "
                f"Findings: {', '.join(target_context.get('findings', []))}"
            )

        prompt = f"""You are a Machine-Readable API for a Senior Offensive Security Researcher and Exploit Developer.
Your output must be a single JSON object. Do not include conversational text, apologies, or markdown outside the JSON block.

### TARGET STATE:
{target_info}

### CORE OBJECTIVE:
Accurately identify the vulnerability and deliver FULLY WEAPONIZED exploitation steps.
Prioritize technical accuracy and precise vulnerability identification in the 'vulnerability_id' field.
Do NOT summarize. Provide the exact, final payloads and scripts required to achieve the objective.

### REQUIRED JSON SCHEMA:
{{
    "vulnerability_id": "Precise CVE-XXXX-XXXX or standard vulnerability name (e.g., 'Local File Inclusion')",
    "reasoning": "Detailed technical explanation of the vulnerability, how it works, and why it applies to this target",
    "actionable_commands": [
        "Step-by-step terminal commands (e.g., listener setup, trigger commands)",
        "Exact command to verify the vulnerability"
    ],
    "payloads": [
        "CRITICAL: Every exploit MUST have its raw payload string duplicated here. This field is the primary payload index.",
        "At least 3 variations of the payload for different bypasses",
        "Include the exact curl/command payload, the encoded version, and the reverse shell payload"
    ],
    "exploit_code": "Full Python/Bash/C script if applicable. If no script, provide the complete multi-line payload block here.",
    "post_exploitation": "Detailed steps for stability, persistence, and privilege escalation",
    "confidence_score": 0.0 to 1.0
}}

### STRICT CONSTRAINTS:
1. IDENTIFICATION: The 'vulnerability_id' must be a precise, standard identifier.
2. NO SUMMARIES: If a payload is 100 lines of code, provide all 100 lines.
3. NO PLACEHOLDERS: Use TARGET_IP, ATTACKER_IP, etc., but the syntax must be 100% correct.
4. VERBOSITY: Be technically exhaustive in the 'reasoning' and 'post_exploitation' sections.
5. JSON ONLY: Any text outside the JSON block will cause the agent to fail.
6. MANDATORY PAYLOADS: The 'payloads' array MUST contain the raw exploit strings (curl commands, encoded payloads, reverse shells). Do NOT leave this field empty or put only descriptions - put the actual payload text.

### CONTEXT:
{context}

### QUESTION:
{query}

ANSWER:"""

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a machine-readable API. Output ONLY valid JSON matching the requested schema. Provide full-length, weaponized exploit code. No prose.",
                },
                {"role": "user", "content": prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                if LLM_PROVIDER == "openrouter":
                    headers = {
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    }
                    payload.update(
                        {
                            "temperature": TEMPERATURE,
                            "max_tokens": MAX_TOKENS,
                            "response_format": {"type": "json_object"},
                        }
                    )
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    return response.json()["choices"][0]["message"]["content"]

                ollama_payload = {
                    "model": model,
                    "messages": payload["messages"],
                    "options": {
                        "temperature": TEMPERATURE,
                        "num_predict": MAX_TOKENS,
                    },
                    "stream": False,
                    "format": "json",
                }
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/chat",
                    json=ollama_payload,
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def query(
        self,
        user_query: str,
        target_context: Optional[Dict] = None,
        k: int = 5,
        model: str = DEFAULT_MODEL,
    ) -> Dict[str, Any]:
        import hashlib

        context_str = json.dumps(target_context, sort_keys=True)
        cache_key = hashlib.md5(f"{user_query}_{context_str}".encode()).hexdigest()
        cached_res = self.cache.get(cache_key)
        if cached_res:
            res = json.loads(cached_res) if isinstance(cached_res, str) else cached_res
            return {**res, "source": "cache", "retrieval_time": 0.0, "generation_time": 0.0}

        start_retrieval = time.perf_counter()
        context = self.retrieve_context(user_query, k=k, target_context=target_context)
        retrieval_time = time.perf_counter() - start_retrieval

        if not context.strip():
            answer_data = json.loads(
                await self.generate_response(
                    user_query,
                    context,
                    target_context=target_context,
                    model=model,
                )
            )
            return {
                **answer_data,
                "context_used": "",
                "source": "live",
                "retrieval_time": retrieval_time,
                "generation_time": 0.0,
                "total_time": retrieval_time,
            }

        start_generation = time.perf_counter()
        answer_json_str = await self.generate_response(
            user_query,
            context,
            target_context=target_context,
            model=model,
        )
        generation_time = time.perf_counter() - start_generation

        try:
            cleaned_json = re.sub(r"```json\n?|```", "", answer_json_str).strip()
            answer_data = json.loads(cleaned_json)
        except json.JSONDecodeError:
            answer_data = {
                "vulnerability_id": "Error",
                "reasoning": f"LLM failed to produce valid JSON: {answer_json_str}",
                "actionable_commands": [],
                "payloads": [],
                "post_exploitation": "",
                "confidence_score": 0.0,
            }

        self.cache.set(cache_key, answer_data)

        return {
            **answer_data,
            "context_used": context,
            "source": "live",
            "retrieval_time": retrieval_time,
            "generation_time": generation_time,
            "total_time": retrieval_time + generation_time,
        }
