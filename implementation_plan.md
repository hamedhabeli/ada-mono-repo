# Implementation Plan

[Overview]
Establish a resilient, highly integrated neuro-symbolic multi-agent reasoning architecture by bridging memory, stability, and safety gaps.

This implementation plan outlines the steps required to transition the ADA (Abductive Dialectic Architect) platform from its current basic prototype status into a production-grade, highly resilient research tool. Currently, the system executes a dialectic loop using LangGraph, Google Gemini, and Z3, with database logging and human oracle intervention. However, there is no loop integration of historical knowledge, Z3 code execution poses security and stability risks, and WebSocket disconnects cause complete loss of active session state. 

By integrating full epistemic memory retrieval (Qdrant & Neo4j), establishing automated syntax self-correction within the LangGraph workflow, adding robust sandbox-like execution guards for Z3 compilation, and implementing REST-based state hydration for WebSocket resilience, we will create a robust, production-ready, and highly performant platform.

[Types]
Type system enhancements to track system history, error states, and memory injection vectors.

Detailed type definitions and state updates:
- **Backend Types (`backend/ada_engine.py`)**:
  - Update `ADAState` (TypedDict):
    ```python
    class ADAState(TypedDict):
        problem: str
        axioms: List[str]
        current_hypothesis: dict
        unsat_core: List[str]
        iteration: int
        status: str
        error_count: int  # Track syntax errors for self-correction loops
        logs: List[dict]  # Track all node execution logs within the graph state
    ```
- **Pydantic Models (`backend/main.py`)**:
  - Add `ThreadHistoryResponse` model:
    ```python
    class ThreadLogEntry(BaseModel):
        event_type: str
        status: str
        unsat_core: List[str]
        iteration: int
        timestamp: float

    class ThreadHistoryResponse(BaseModel):
        thread_id: str
        problem: str
        status: str
        logs: List[ThreadLogEntry]
    ```

[Files]
File modifications to enable memory retrieval, safe execution, self-correction, and state hydration.

Detailed breakdown:
- **New Files**:
  - `backend/memory_retriever.py`: Module to perform Qdrant vector similarity search and Neo4j relationship lookup to fetch related resolved axioms.
- **Existing Files to be Modified**:
  - `backend/database.py`: Add querying and retrieval methods (`search_contradictions` and `search_resolved_axioms`) to `CloudEpistemicMemory`.
  - `backend/ada_engine.py`: Integrate the memory retriever module, implement Z3 code validation, track `error_count`, and construct the self-correction routing edge.
  - `backend/main.py`: Create `/api/v1/threads/{thread_id}/history` GET endpoint, persist state events, wrap Z3 execution with exceptions, and handle resume logic robustly.
  - `frontend/src/App.jsx`: Store thread ID in localStorage, fetch and hydrate session logs and React Flow nodes upon reload, handle WebSocket reconnects cleanly.
  - `frontend/src/AxiomGraph.jsx`: Style nodes for Memory Retrieval events and allow interactive click-to-view detail modals.
  - `frontend/src/DialecticStream.jsx`: Style system and memory logs with distinct color-coding.

[Functions]
Detailed breakdown of function creations and modifications.

Detailed breakdown:
- **New Functions**:
  - `CloudEpistemicMemory.search_contradictions(self, problem: str, limit: int = 2) -> List[dict]` (`backend/database.py`): Performs similarity search in Qdrant.
  - `CloudEpistemicMemory.search_resolved_axioms(self, unsat_core: str) -> List[str]` (`backend/database.py`): Finds meta-axioms that resolved similar unsat cores in Neo4j.
  - `get_relevant_memories(problem: str, unsat_core: List[str]) -> str` (`backend/memory_retriever.py`): Orchestrates Qdrant and Neo4j queries to generate a prompt segment for Gemini.
  - `get_thread_history(thread_id: str)` (`backend/main.py`): GET API endpoint to return logs of a previous session.
- **Modified Functions**:
  - `neural_abduction_node(state: ADAState) -> Dict` (`backend/ada_engine.py`): Retrieve relevant memories using `get_relevant_memories` and append them to Gemini's prompt. Increment `iteration` and log status.
  - `symbolic_verification_node(state: ADAState) -> Dict` (`backend/ada_engine.py`): Validate and execute generated Python-Z3 constraints under strict safety guards (timeout and local variable limits).
  - `check_deadlock(state: ADAState) -> Literal["neural", "oracle", "end"]` (`backend/ada_engine.py`): Modify routing. If `status == "SYNTAX_DEADLOCK"` and `error_count < 3`, return `"neural"` to attempt self-correction. Otherwise, return `"oracle"` or `"end"`.
  - `run_graph_and_stream(thread_id: str, state: dict)` (`backend/main.py`): Push each state change event to the thread memory storage buffer.
  - `/api/v1/oracle/inject` (`backend/main.py`): Resume the interrupted thread graph correctly while maintaining state consistency.

[Classes]
Enhancements to existing singleton classes to handle queries and memory.

Detailed breakdown:
- **Modified Classes**:
  - `CloudEpistemicMemory` (`backend/database.py`):
    - Implement embedding creation and Qdrant search queries (using mock vectors if in-memory test mode).
    - Implement Cypher queries in Neo4j to search for `(:UnsatCore)-[:RESOLVED_BY]->(:MetaAxiom)` matching high-similarity contradictions.
  - `ConnectionManager` (`backend/main.py`):
    - Introduce an in-memory thread storage buffer `thread_histories: dict[str, dict]` to cache events, active status, and problem details per `thread_id`.

[Dependencies]
No new external library dependencies are required.

- Confirm the system has:
  - `google-generativeai` (for Gemini)
  - `z3-solver` (for Z3 Prover)
  - `langgraph` (for Agent Orchestration)
  - `neo4j` & `qdrant-client` (with FastEmbed) for Database persistence.

[Implementation Order]
The sequential steps for executing the code modification phase.

1. **Step 1: Database Search Integration**
   - Add search methods in `CloudEpistemicMemory` (`backend/database.py`) to search both Qdrant and Neo4j. Return formatted search results or mock responses when running in mock mode.
2. **Step 2: Memory Retriever Module**
   - Create `backend/memory_retriever.py`. Coordinate similarity search and graph query to create a highly structured context prompt block (e.g., "Past similar failure: ... Resolved by injecting: ...").
3. **Step 3: Graph State and Routing Upgrades**
   - In `backend/ada_engine.py`, update `ADAState` definition. Update `check_deadlock` to support the Self-Correction routing back to the neural node for up to 3 attempts when experiencing syntax deadlocks.
4. **Step 4: Safe Symbolic Verification & Self-Correction**
   - In `backend/ada_engine.py`, strengthen `symbolic_verification_node`. Prevent dangerous execution patterns (add checks to ensure code only uses safe Z3 terms) and correctly raise `SYNTAX_DEADLOCK` with detailed syntax error feedback so Gemini knows exactly what to correct.
5. **Step 5: Epistemic Neural Abduction Node**
   - In `backend/ada_engine.py`, update `neural_abduction_node` to check for similar memories and self-correction logs in the state. Add this rich context to Gemini's prompt so it avoids repeating past mistakes and corrects syntax.
6. **Step 6: Thread State Buffer & REST Hydration**
   - In `backend/main.py`, implement an in-memory or database-backed `thread_histories` dictionary inside `ConnectionManager`. Append every websocket stream log to this buffer.
   - Add the GET `/api/v1/threads/{thread_id}/history` endpoint to return this buffered state.
7. **Step 7: Robust Websocket & Resumption Endpoint**
   - Ensure `/api/v1/oracle/inject` handles state resume cleanly and websocket communication stays alive.
8. **Step 8: Frontend Session Persistence & History Loading**
   - In `frontend/src/App.jsx`, save the current `thread_id` to `localStorage`.
   - On component mount, if a `thread_id` exists in `localStorage`, call `/api/v1/threads/{thread_id}/history` to hydrate `logs`, `nodes`, and `edges` immediately.
9. **Step 9: React Flow layout & Styling Upgrades**
   - Update `frontend/src/AxiomGraph.jsx` and styling in `App.jsx` to render specialized memory-retrieval nodes, self-correction attempt indicators, and interactive click handler support.
10. **Step 10: Validation & Testing**
    - Run Python pytest suite (`backend/test_unit.py` and `backend/test_integration.py`).
    - Run Frontend vitest suite (`frontend/src/OracleModal.test.jsx`).
    - Verify complete functional pipeline locally.

task_progress Items:
- [ ] Step 1: Implement Database Search Integration in database.py
- [ ] Step 2: Implement Epistemic Memory Retriever module
- [ ] Step 3: Upgrade Graph State and Routing in ada_engine.py
- [ ] Step 4: Implement Safe Symbolic Verification & Self-Correction in ada_engine.py
- [ ] Step 5: Update Neural Abduction node with Memory context
- [ ] Step 6: Implement Thread History Cache & REST Hydration API in main.py
- [ ] Step 7: Refactor Websocket Resilience & Resume endpoint in main.py
- [ ] Step 8: Implement Frontend Session Persistence & History Hydration in App.jsx
- [ ] Step 9: Upgrade React Flow styling & layout visual representation
- [ ] Step 10: Run full backend and frontend test suites and verify integration
