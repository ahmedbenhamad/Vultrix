import argparse
import uvicorn
import os
import sys
import socket
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

# Ajouter le répertoire courant au path pour l'import des modules locaux
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingest import PentestIngestor
from src.query import PentestRAG
from src.config import DEFAULT_MODEL
from src.utils import ensure_qdrant_running

# New Models for Strix Integration
class TargetContext(BaseModel):
    service: Optional[str] = None
    version: Optional[str] = None
    findings: Optional[List[str]] = []
    os: Optional[str] = None

class StructuredRAGResponse(BaseModel):
    vulnerability_id: str
    reasoning: str
    actionable_commands: List[str]
    payloads: List[str]
    exploit_code: Optional[str] = None
    post_exploitation: str
    confidence_score: float

class QueryRequest(BaseModel):
    query: str
    target_context: Optional[TargetContext] = None
    k: Optional[int] = 5
    model: Optional[str] = DEFAULT_MODEL

class QueryResponse(BaseModel):
    answer: str
    context: str

# Instantiate RAG once at startup (Singleton)
rag = PentestRAG()

app = FastAPI(
    title="Pentest RAG API",
    description="API to query the pentesting knowledge base"
)

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

@app.post("/query", response_model=StructuredRAGResponse)
async def query_rag(request: QueryRequest):
    """Entry point to query the RAG for structured exploitation guidance."""
    try:
        # Pass target_context to the RAG pipeline
        result = await rag.query(
            request.query,
            target_context=request.target_context.dict() if request.target_context else None,
            k=request.k,
            model=request.model or DEFAULT_MODEL,
        )

        # The RAG now returns a structured dict that matches StructuredRAGResponse
        return StructuredRAGResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the query: {str(e)}")

@app.post("/retrieve")
async def retrieve_only(request: QueryRequest):
    """Fast-path: retrieve raw context without LLM generation."""
    try:
        context = rag.retrieve_context(
            request.query,
            k=request.k,
            target_context=request.target_context.dict() if request.target_context else None
        )
        return {"context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during retrieval: {str(e)}")

@app.post("/ingest")
async def ingest_data():
    """Entry point to trigger the ingestion of the data/ folder."""
    try:
        ingestor = PentestIngestor()
        ingestor.process_and_index(
            batch_size=100,
            upsert_batch_size=16,
            upsert_timeout=180,
            upsert_retries=6,
        )
        return {"status": "success", "message": "Data successfully ingested and indexed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during ingestion: {str(e)}")

def run_cli():
    """Command line interface for the RAG."""
    parser = argparse.ArgumentParser(description="Pentest RAG CLI")
    parser.add_argument("--ingest", action="store_true", help="Ingest data from the data/ directory")
    parser.add_argument("--query", type=str, help="Ask a question to the RAG system")
    parser.add_argument("--serve", action="store_true", help="Launch the REST API")
    parser.add_argument("--ingest-batch-size", type=int, default=100, help="Number of files loaded per ingest loop")
    parser.add_argument("--upsert-batch-size", type=int, default=16, help="Number of chunks sent per Qdrant upsert")
    parser.add_argument("--upsert-timeout", type=int, default=180, help="Qdrant upsert timeout (seconds)")
    parser.add_argument("--upsert-retries", type=int, default=6, help="Qdrant upsert retry attempts on timeout")

    args = parser.parse_args()

    if args.ingest or args.query or args.serve:
        # Automate Qdrant lifecycle for any RAG actions
        ensure_qdrant_running()

    if args.ingest:
        print("Starting ingestion...")
        ingestor = PentestIngestor()
        ingestor.process_and_index(
            batch_size=args.ingest_batch_size,
            upsert_batch_size=args.upsert_batch_size,
            upsert_timeout=args.upsert_timeout,
            upsert_retries=args.upsert_retries,
        )
    elif args.query:
        print(f"[*] Querying for: '{args.query}'...")
        print("[*] Retrieving knowledge fragments from Vector Database...")
        rag = PentestRAG()
        print("[*] Simulating AI Reasoning... (Please wait while model generates answer)")
        import asyncio
        result = asyncio.run(rag.query(args.query))
        print("\n" + "="*50)
        print("GENERATED STRUCTURED ANSWER")
        print("="*50)

        if 'answer' in result:
            print(result['answer'])
        else:
            # Print structured response for Strix-optimized mode
            print(f"Vulnerability: {result.get('vulnerability_id', 'N/A')}")
            print(f"Confidence:   {result.get('confidence_score', 'N/A')}")
            print(f"Reasoning:    {result.get('reasoning', 'N/A')}")
            print("\n--- Actionable Commands ---")
            for cmd in result.get('actionable_commands', []):
                print(f"  - {cmd}")
            print("\n--- Payloads ---")
            for p in result.get('payloads', []):
                print(f"  - {p}")
            if 'exploit_code' in result and result['exploit_code']:
                print("\n--- Full Exploit Code ---")
                print(result['exploit_code'])
            print(f"\nPost-Exploitation: {result.get('post_exploitation', 'N/A')}")

        print("\n" + "="*50)
        print("CONTEXT USED EXTRACT")
        print("="*50)
        context = result.get('context_used', '')
        print(context[:800] + "..." if context else "No context retrieved.")
    elif args.serve:
        port = 8000
        if is_port_in_use(port):
            print(f"[*] Port {port} is already in use. Falling back to port 8001...")
            port = 8001

        print(f"Launching REST API on http://0.0.0.0:{port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        parser.print_help()

if __name__ == "__main__":
    run_cli()
