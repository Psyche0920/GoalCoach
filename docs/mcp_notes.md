# Model Context Protocol (MCP) & System Architecture Study Notes

---

## 1. Executive Summary & Core Definitions

### What is MCP?
The **Model Context Protocol (MCP)** is an open communication standard (introduced by Anthropic) based on **JSON-RPC 2.0**. It standardizes how Large Language Models (LLMs) connect to external tools, databases, and prompt templates without hardcoding custom integration code for every provider.

### The Universal Analogy
* **Before MCP:** Every AI model needed custom adapters, similar to proprietary smartphone charging cables. Switching models or changing tools required rewriting agent logic ($N \times M$ integration problem).
* **With MCP:** MCP functions like a universal **USB-C cable for AI**. It establishes a single protocol allowing any AI host to execute actions and read data from external systems.

### The Architectural Boundary
* **MCP is not an LLM:** It contains no neural weights, training algorithms, or natural language generation capabilities.
* **MCP is a Courier, not a Translator:** MCP transports tool calls from the AI to your backend, and returns raw structured data back to the AI. **The LLM remains the only component that composes natural language replies for the user.**

---

## 2. Architecture Comparison: MCP vs. SQLAlchemy

A common misconception is that MCP replaces database tools like SQLAlchemy. They operate at distinct layers of the software stack:

| Dimension | SQLAlchemy (ORM) | Model Context Protocol (MCP) |
| :--- | :--- | :--- |
| **Layer** | Data Access Layer (Internal) | Protocol / Application Boundary (External/Agent) |
| **Who is talking?** | **Python Backend $\rightarrow$ Database** | **AI Model / Agent $\rightarrow$ Backend Services** |
| **Data Format** | Python Objects / SQL Expressions | JSON-RPC 2.0 Packets |
| **Primary Job** | Maps relational database rows into Python classes safely without raw SQL injection risks. | Exposes functions, schemas, and read-only data as standardized tools for AI models. |
| **GoalCoach Role** | Queries the local `goalcoach.db` SQLite file for teaching cards and learner states. | Delivers the AI agent's tool execution requests to the Python functions executing those queries. |

---

## 3. End-to-End Data Flow

The diagram below illustrates how a learner query travels through the system without MCP ever touching the database directly, and without SQLAlchemy ever talking to the user:

```
[ 1. User ]
│ (Natural language question via Streamlit UI)
▼
[ 2. LLM / AI Teaching Agent ]
│ (Decides it needs curriculum facts; emits structured tool call)
▼
[ 3. MCP Protocol Layer (Courier) ]
│ (Serializes request over JSON-RPC stdio)
▼
[ 4. Python Backend / MCP Server ]
│ (Executes the registered tool function)
▼
[ 5. SQLAlchemy ORM ]
│ (Translates function parameters into SQL query: SELECT * ...)
▼
[ 6. SQLite Database ]
│ (Returns table rows: concept_id, explanation, examples)
▼
[ 7. Python Backend / MCP Server ]
│ (Formats rows into a Python dictionary/JSON)
▼
[ 8. MCP Protocol Layer (Courier Return) ]
│ (Delivers JSON payload back into the context window)
▼
[ 9. LLM / AI Teaching Agent ]
│ (Reads facts; synthesizes pedagogical, natural language response)
▼
[ 10. User reads the final explanation ]
```

---

## 4. MCP Technical Anatomy: Transports and Primitives

### Transport Options
There is only **one MCP protocol specification**, but communication can run over two transport layers:
1. **`stdio` (Standard Input/Output):** The host process spawns the MCP server as a local child process and communicates via standard input/output streams. Fast, sandboxed, zero network latency; optimal for local development, CLI agents, and developer tooling.
2. **Streamable HTTP / SSE (Server-Sent Events):** The server runs as a standalone network service. The client makes HTTP POST calls, and the server pushes streaming responses via SSE. Used for cloud microservices and remote tool hosting.

#### Decision Framework: Criteria to Choose Transport
Use these four criteria when deciding whether an MCP server should use stdio or Streamable HTTP:
1. Deployment Proximity (Where are the data and execution context?):
- Criterion: Are the tool scripts, SQLite files, and ChromaDB directories hosted on the same server instance as the backend?  
- Choice: If yes → Use stdio. If the tool runs as an external cloud microservice → Use Streamable HTTP.
2. Network Overhead & Latency Tolerance:
- Criterion: In GoalCoach, an interactive session must avoid latency explosion during the teach-grade-retrieve loop.  
- Choice: stdio bypasses TCP handshakes, DNS resolution, and SSL handshakes entirely, giving direct pipe throughput.
3. Authentication & Operational Complexity:
- Criterion: Does your tool require token-based access control, port management, firewall rules, or CORS handling?
- Choice: stdio requires no open network ports or authentication keys. Streamable HTTP requires managing HTTP servers, endpoints, error codes, and request auth.
4. Lifecycle Management:
- Criterion: Should the tool server automatically start and die with the application host?
- Choice: stdio is spawned and terminated directly by the parent process. Streamable HTTP servers must be deployed, monitored, health-checked, and scaled independently as daemons.

#### Why stdio is Recommended for GoalCoach
1. Embedded Data Storage: Your project uses SQLite (data/database1/goalcoach.db) and ChromaDB (data/chroma_db). Both are embedded engines running on the local filesystem, not remote database servers.  

2. No Distributed Boundary: Your FastAPI backend and tool scripts run in the same runtime environment. Running an HTTP network server just to query a local SQLite file adds serialisation overhead and point-of-failure risks without architectural benefit.  

3. Sprint Pragmatism: GoalCoach has a 4-week delivery timeline where core branching logic and grader evaluation must be proven first. Configuring HTTP ports, managing URL routes, and debugging network connectivity between two internal Python modules introduces avoidable complexity.  

Streamable HTTP becomes relevant only if you decouple the curriculum into a standalone, hosted microservice deployed on a separate remote server that multiple independent backend clusters query over the internet. For the current architecture, keeping it on stdio is the cleanest engineering approach

### The Three MCP Primitives
MCP servers expose capabilities across three explicit constructs:
* **Resources (`resources/read`, `resources/list`):** Passive, read-only data context (e.g., schemas, reference documents, or file contents).
* **Tools (`tools/call`, `tools/list`):** Executable functions that the LLM autonomously decides to trigger (e.g., semantic search, calculations, database mutations).
* **Prompts (`prompts/get`, `prompts/list`):** Pre-engineered, versioned prompt templates and evaluation rubrics exposed directly by the server.

---

## 5. Architectural Assessment for GoalCoach

Following senior engineering best practices, **we avoid over-agentification and minimize unnecessary LLM/RPC calls**.

| Component | MCP Suitability | Recommendation & Rationale |
| :--- | :--- | :--- |
| **Workflow State Machine** | **Strictly Avoid** | Keep the Workflow Orchestrator as a deterministic, in-process Python state machine. Adding JSON-RPC protocol round-trips to internal state transitions introduces network/serialization latency and unnecessary failure points. |
| **Progress & Mastery Math** | **Avoid** | Keep $\sum (Mastery \times Retention)$ in pure Python and SQLAlchemy. Deterministic mathematical aggregation should not be exposed to or mediated by an LLM protocol. |
| **Curriculum Retrieval (RAG)** | **High** | Wrap `ChromaService` and SQLite curriculum lookups into an MCP Server (`goalcoach-curriculum-mcp`). Decouples LLM agents from specific database clients. |
| **Grading & Evaluation Harness** | **Medium / High** | Wrap the 6-dimension evaluation rubric into MCP prompts and benchmark tools (`goalcoach-eval-mcp`). Allows switching between hosted LLMs (DeepSeek-V3/Qwen) and local SLMs (Gemma/Qwen-7B) cleanly during testing. |

---

## 6. Implementation Reference: Custom FastMCP Server

Rather than running generic community servers that permit arbitrary SQL queries, implement a targeted custom server using Python's official `FastMCP` SDK to preserve schema boundaries:

```python
"""
src/goalcoach/infrastructure/mcp/curriculum_server.py
MCP Server exposing curriculum retrieval tools to AI Agents.
"""

from mcp.server.fastmcp import FastMCP
from goalcoach.infrastructure.retrieval.chroma_service import ChromaService
import sqlite3

# 1. Initialize the FastMCP Server
mcp = FastMCP("GoalCoach-Curriculum-Server")
chroma_service = ChromaService()

# 2. Register Semantic Retrieval as an MCP Tool
@mcp.tool()
def search_remedial_cards(student_mistake: str, top_k: int = 2) -> list:
    """
    Searches curriculum cards for remedial learning when a student makes a grammar error.
    Returns matched concept IDs and pedagogical content.
    """
    return chroma_service.retrieve_remedial_material(
        semantic_query=student_mistake,
        hsk_level=1,
        top_k=top_k
    )

# 3. Register Deterministic SQL Lookup as an MCP Tool
@mcp.tool()
def get_card_by_id(card_id: int) -> dict:
    """Fetches an exact teaching card from SQLite using its unique card ID."""
    conn = sqlite3.connect("data/database1/goalcoach.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT concept_id, prompt_zh, explanation_en FROM teaching_cards WHERE card_id = ?",
        (card_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"concept_id": row[0], "pattern": row[1], "explanation": row[2]}
    return {"error": f"Card ID {card_id} not found"}

# 4. Entrypoint for stdio communication
if __name__ == "__main__":
    mcp.run(transport="stdio")

```

---

## 7. Delivery Roadmap Alignment (4-Week Sprint)

* **Week 1 (Can it run?):** Prototype the MCP server locally over `stdio`. Verify that basic agent calls trigger retrieval tools before connecting the web interface.


* **Week 2 (Can it adapt?):** Expose the 6-dimension grading rubric via MCP Prompts to standardize evaluations across model benchmarks.


* **Week 3 (Can it work as an app?):** Integrate the backend via FastAPI while preserving deterministic state machines in SQLite.


* **Week 4 (Can we prove it?):** Run automated test suites across the benchmark dataset (30–50 human-labeled examples) using the evaluation harness.

