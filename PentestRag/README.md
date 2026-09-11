# Omnivorous Pentest RAG

A high-performance, containerized RAG system for autonomous pentesting and cybersecurity research. Powered by Qdrant (Vector DB), LangChain (Orchestration), and Ollama/OpenRouter (LLMs).

---

## 🛠️ Installation

### 1. Prerequisites
Ensure you have the following installed on your system:
- **Python 3.9+**
- **Docker & Docker Compose**
- **Tesseract OCR** (for image text extraction)
  - **Linux**: `sudo apt install tesseract-ocr`
  - **Windows**: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)

### 2. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd pentest_rag

# Create and activate a Virtual Environment
python -m venv venv

# Windows (Command Prompt)
venv\Scripts\activate
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
Copy the example environment file and fill in your details:
```bash
cp .env.example .env
```
- Set `LLM_PROVIDER` to `ollama` (local) or `openrouter` (cloud).
- If using `openrouter`, add your `OPENROUTER_API_KEY`.
- Qdrant settings default to `localhost:6333`.

---

## 🚀 Running the Project

### Phase 1: Start the Vector Database
The system requires Qdrant to be running.
```bash
docker run -d -p 6333:6333 -p 6334:6334 \
    -v qdrant_storage:/qdrant/storage \
    --name qdrant \
    qdrant/qdrant
```

### Phase 2: Ingest Knowledge
Place your documents in the `data/` folder. The system accepts:
- **Text Files**: `.txt`, `.md`, `.py`, `.json`, `.sql`, etc.
- **Images**: `.png`, `.jpg`, `.jpeg` (via OCR).

Run the ingestion script to process and index documents:
```bash
python main.py --ingest
```
*Note: This will split documents into chunks and store them in Qdrant.*

### Phase 3: Start Quering
You can query the system via the CLI:
```bash
python main.py --query "How do I perform a privilege escalation on Linux?"
```

---

## 🎛️ Knowledge Base Manager
For a more user-friendly experience, use the built-in management script:
```bash
python rag_manager.py
```
This interactive menu allows you to:
1. Query the RAG
2. Feed/Ingest data
3. Change LLM Models
4. Launch the API Server
5. Clean data folders

---

## 🌐 API Support
To launch the REST API server (useful for integration with other tools like Strix):
```bash
# Default port 8000
python main.py --serve
```

---

## 🧹 Maintenance
If you need to clear the database and start over:
1. Delete the Docker volume or container data.
2. Run the ingestion again.
To clean your `data/` folder of junk files:
```bash
python scripts/clean_data.py
```
