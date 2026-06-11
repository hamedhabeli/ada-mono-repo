import asyncio
import time
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ada_engine import ada_app
from database import memory_db

app = FastAPI(title="ADA Cloud Backend")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for REST API validation
class ThreadLogEntry(BaseModel):
    event_type: str
    status: str
    unsat_core: List[str]
    iteration: int
    timestamp: float
    hypothesis: Optional[dict] = None

class ThreadHistoryResponse(BaseModel):
    thread_id: str
    problem: str
    status: str
    logs: List[ThreadLogEntry]

class ProblemRequest(BaseModel):
    thread_id: str
    problem: str

class OracleRequest(BaseModel):
    thread_id: str
    meta_axiom: str

# Connection Manager with Thread History Cache
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        # Caches active thread states and event logs: thread_id -> {"problem": str, "status": str, "logs": list}
        self.thread_histories: dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, thread_id: str):
        await websocket.accept()
        self.active_connections[thread_id] = websocket

    def disconnect(self, thread_id: str):
        if thread_id in self.active_connections:
            del self.active_connections[thread_id]

    async def send_message(self, message: dict, thread_id: str):
        if thread_id in self.active_connections:
            try:
                await self.active_connections[thread_id].send_json(message)
            except Exception as e:
                print(f"Failed to send websocket message on thread {thread_id}: {e}")

manager = ConnectionManager()

# Run the Graph in background and stream state changes via Websocket
async def run_graph_and_stream(thread_id: str, state: Optional[dict]):
    config = {"configurable": {"thread_id": thread_id}}
    
    # astream streams graph node execution updates
    async for event in ada_app.astream(state, config=config):
        node_name = list(event.keys())[0]
        node_data = event[node_name]
        
        # Pull complete current state values from LangGraph checkpointer
        state_obj = ada_app.get_state(config)
        current_values = state_obj.values if state_obj else {}
        
        status = node_data.get("status", "PROCESSING")
        unsat_core = node_data.get("unsat_core", [])
        iteration = node_data.get("iteration", 0)
        
        # Populate log entry
        event_log = {
            "event_type": node_name,
            "status": status,
            "unsat_core": unsat_core,
            "iteration": iteration,
            "timestamp": time.time(),
            "hypothesis": node_data.get("current_hypothesis") or current_values.get("current_hypothesis")
        }
        
        # Update connection manager thread history cache
        if thread_id in manager.thread_histories:
            manager.thread_histories[thread_id]["status"] = status
            if "logs" in current_values:
                manager.thread_histories[thread_id]["logs"] = current_values["logs"]
            else:
                manager.thread_histories[thread_id]["logs"].append(event_log)
        else:
            manager.thread_histories[thread_id] = {
                "problem": current_values.get("problem", state.get("problem", "") if state else ""),
                "status": status,
                "logs": current_values.get("logs", [event_log])
            }
            
        # Stream the update back to the frontend websocket connection
        await manager.send_message({
            "event_type": node_name,
            "status": status,
            "unsat_core": unsat_core,
            "iteration": iteration,
            "logs": manager.thread_histories[thread_id]["logs"]
        }, thread_id)

        # Trigger oracle pop-up if we reach a logic contradiction deadlock or a compiler loop deadlock
        if node_name == "symbolic" and (iteration >= 5 or (status == "SYNTAX_DEADLOCK" and current_values.get("error_count", 0) >= 3)):
            await manager.send_message({"event_type": "GODELIAN_DEADLOCK"}, thread_id)

@app.post("/api/v1/solve")
async def start_solving(req: ProblemRequest):
    initial_state = {
        "problem": req.problem, 
        "axioms": [], 
        "current_hypothesis": {}, 
        "unsat_core": [], 
        "iteration": 0, 
        "status": "INIT",
        "error_count": 0,
        "logs": []
    }
    
    # Pre-populate cache so that /history REST endpoints can be queried immediately
    manager.thread_histories[req.thread_id] = {
        "problem": req.problem,
        "status": "INIT",
        "logs": []
    }
    
    # Run the graph asynchronously in the background
    asyncio.create_task(run_graph_and_stream(req.thread_id, initial_state))
    return {"thread_id": req.thread_id, "status": "processing_started"}

@app.websocket("/ws/v1/stream/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await manager.connect(websocket, thread_id)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(thread_id)

@app.get("/api/v1/threads/{thread_id}/history", response_model=ThreadHistoryResponse)
async def get_thread_history(thread_id: str):
    # If not in cache, try to hydrate from LangGraph checkpointer
    if thread_id not in manager.thread_histories:
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state_obj = ada_app.get_state(config)
            if state_obj and state_obj.values:
                vals = state_obj.values
                manager.thread_histories[thread_id] = {
                    "problem": vals.get("problem", ""),
                    "status": vals.get("status", ""),
                    "logs": vals.get("logs", [])
                }
            else:
                raise HTTPException(status_code=404, detail="Thread not found")
        except Exception:
            raise HTTPException(status_code=404, detail="Thread not found")
            
    hist = manager.thread_histories[thread_id]
    return ThreadHistoryResponse(
        thread_id=thread_id,
        problem=hist.get("problem", ""),
        status=hist.get("status", ""),
        logs=hist.get("logs", [])
    )

@app.post("/api/v1/oracle/inject")
async def inject_axiom(req: OracleRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        current_state = ada_app.get_state(config)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Not waiting for oracle")
    
    if not current_state or "oracle" not in current_state.next:
        raise HTTPException(status_code=400, detail="Not waiting for oracle")
    
    st_vals = current_state.values
    # Save the new axiom to the epistemic graph database
    memory_db.store_meta_axiom(st_vals["problem"], st_vals["unsat_core"], req.meta_axiom)
    
    # Reset error_count and clear status to INIT on resume
    ada_app.update_state(config, {
        "axioms": st_vals["axioms"] + [req.meta_axiom], 
        "iteration": 0, 
        "unsat_core": [], 
        "status": "INIT",
        "error_count": 0
    })
    
    # Resume the dialectic graph execution in the background
    asyncio.create_task(run_graph_and_stream(req.thread_id, None))
    return {"status": "axiom_accepted", "action": "resuming_dialectic_loop"}
