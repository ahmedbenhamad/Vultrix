# User Guide: Optimizing Pentest RAG Queries

To achieve maximum precision and weaponized output from the Pentest RAG system, use a structured and contextual query approach.

## 1. Recommended Query Structure

Instead of simple questions, use a three-part structure in your `query` field:

**[Precise Identifier]** $\rightarrow$ **[Technical Objective]** $\rightarrow$ **[Environment Constraints]**

### Example of an Optimized Query:
*"Exploitation RCE pour CVE-2021-44228 sur Log4j 2.14.1. Fournir un payload JNDI/LDAP complet et les étapes pour obtenir un reverse shell sur Ubuntu."*

- **Precise Identifier**: CVE-2021-44228 / Log4j 2.14.1
- **Technical Objective**: Complete JNDI/LDAP payload and reverse shell steps.
- **Environment Constraints**: Ubuntu.

---

## 2. Leveraging `target_context`

The `target_context` parameter is a precision filter used by the Reranker (Cross-Encoder) before the LLM generates the answer. **Never leave this empty.**

| Field | Usage Advice | Example |
| :--- | :--- | :--- |
| `service` | Exact name of the service. | `Apache`, `Jenkins`, `PostgreSQL` |
| `version` | Precise version number. Avoid "latest". | `2.4.49`, `12.1` |
| `os` | Target operating system. | `Ubuntu 22.04`, `Windows Server 2019` |
| `findings` | Service banners or specific HTTP errors encountered. | `Server: Apache/2.4.49 (Unix)`, `403 Forbidden` |

---

## 3. Pro Tips for Maximum Recall

- **Avoid Ambiguous Abbreviations**: While the system handles common terms (RCE, LFI), using the full name (e.g., "Remote Code Execution") reinforces semantic search.
- **Specify Output Format**: If you need a Python script instead of a curl command, explicitly state it in the query.
- **Iterative Feedback Loop**: If a payload fails, add the specific error received to the `findings` field of the `target_context` and run the query again. This allows the RAG to find alternative bypasses based on the real-time failure.
