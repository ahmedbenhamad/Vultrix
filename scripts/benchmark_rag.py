import asyncio
import json
import time
import statistics
from typing import List, Dict, Any
from src.query import PentestRAG

async def run_benchmark():
    print("[*] Starting RAG Benchmark...")

    # Load dataset
    try:
        with open("benchmarks/dataset.json", "r") as f:
            dataset = json.load(f)
    except FileNotFoundError:
        print("[!] Dataset file not found at benchmarks/dataset.json")
        return

    rag = PentestRAG()
    results = []

    print(f"[*] Testing {len(dataset)} queries...\n")
    print(f"{'Query':<60} | {'Retr(s)':<8} | {'Gen(s)':<8} | {'Total(s)':<8} | {'Accuracy'}")
    print("-" * 100)

    for case in dataset:
        query = case["query"]
        target_context = case.get("target_context")
        expected = case["expected_answer"]

        try:
            # Execute query
            start_time = time.perf_counter()
            response = await rag.query(query, target_context=target_context)
            total_time = time.perf_counter() - start_time

            # Metrics extraction
            retr_time = response.get("retrieval_time", 0)
            gen_time = response.get("generation_time", 0)

            # Accuracy evaluation (Keyword match & ID match)
            # 1. ID match (loose)
            id_match = expected["vulnerability_id"].lower() in response.get("vulnerability_id", "").lower()

            # 2. Keyword match
            found_keywords = []
            reasoning_text = (response.get("reasoning", "") + " " + " ".join(response.get("actionable_commands", []))).lower()
            for kw in expected["keywords"]:
                if kw.lower() in reasoning_text:
                    found_keywords.append(kw)

            kw_score = len(found_keywords) / len(expected["keywords"]) if expected["keywords"] else 0

            # Combined accuracy score
            accuracy = (1.0 if id_match else 0.0) * 0.4 + (kw_score * 0.6)

            results.append({
                "query": query,
                "retrieval_time": retr_time,
                "generation_time": gen_time,
                "total_time": total_time,
                "accuracy": accuracy
            })

            print(f"{query[:57]+'...':<60} | {retr_time:<8.3f} | {gen_time:<8.3f} | {total_time:<8.3f} | {accuracy:.2%}")

        except Exception as e:
            print(f"Error querying {query[:30]}... : {e}")

    # Final Reporting
    print("\n" + "="*50)
    print("FINAL BENCHMARK REPORT")
    print("="*50)

    total_times = [r["total_time"] for r in results]
    retr_times = [r["retrieval_time"] for r in results]
    gen_times = [r["generation_time"] for r in results]
    accuracies = [r["accuracy"] for r in results]

    print(f"Total Queries:      {len(results)}")
    print(f"Avg Total Latency: {statistics.mean(total_times):.3f}s")
    print(f"Avg Retrieval Time: {statistics.mean(retr_times):.3f}s")
    print(f"Avg Generation Time: {statistics.mean(gen_times):.3f}s")
    print(f"Average Accuracy:   {statistics.mean(accuracies):.2%}")
    if len(total_times) >= 2:
        # Using simple sort for P95 as statistics.quantiles needs more data
        sorted_times = sorted(total_times)
        p95_idx = int(len(sorted_times) * 0.95) - 1
        print(f"P95 Total Latency: {sorted_times[max(0, p95_idx)]:.3f}s")
    else:
        print(f"P95 Total Latency: N/A")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
