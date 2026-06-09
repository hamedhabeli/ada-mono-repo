import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from ada_engine import ada_app
from database import memory_db

app = FastAPI(title="ADA Cloud Backend")

# مدیریت اتصالات WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, thread_id: str):
        await websocket.accept()
        self.active_connections[thread_id] = websocket

    def disconnect(self, thread_id: str):
        if thread_id in self.active_connections:
            del self.active_connections[thread_id]

    async def send_message(self, message: dict, thread_id: str):
        if thread_id in self.active_connections:
            await self.active_connections[thread_id].send_json(message)

manager = ConnectionManager()

class ProblemRequest(BaseModel):
    thread_id: str
    problem: str

class OracleRequest(BaseModel):
    thread_id: str
    meta_axiom: str

# اجرای گراف در پس‌زمینه و ارسال لاگ‌ها به WebSocket
async def run_graph_and_stream(thread_id: str, state: dict):
    config = {"configurable": {"thread_id": thread_id}}
    
    # astream اجازه می‌دهد رویدادهای گراف را به صورت زنده دریافت کنیم
    async for event in ada_app.astream(state, config=config):
        node_name = list(event.keys())[0]
        node_data = event[node_name]
        
        await manager.send_message({
            "event_type": node_name,
            "status": node_data.get("status", "PROCESSING"),
            "unsat_core": node_data.get("unsat_core", []),
            "iteration": node_data.get("iteration", 0)
        }, thread_id)

        # اگر به بن‌بست رسیدیم، به فرانت‌اند خبر می‌دهیم تا پاپ‌آپ اوراکل را باز کند
        if node_name == "symbolic" and (node_data.get("iteration", 0) >= 5 or node_data.get("status") == "SYNTAX_DEADLOCK"):
            await manager.send_message({"event_type": "GODELIAN_DEADLOCK"}, thread_id)

@app.post("/api/v1/solve")
async def start_solving(req: ProblemRequest):
    initial_state = {
        "problem": req.problem, "axioms": [], "current_hypothesis": {}, 
        "unsat_core": [], "iteration": 0, "status": "INIT"
    }
    # اجرای گراف به صورت Task در پس‌زمینه تا API بلاک نشود
    asyncio.create_task(run_graph_and_stream(req.thread_id, initial_state))
    return {"thread_id": req.thread_id, "status": "processing_started"}

@app.websocket("/ws/v1/stream/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await manager.connect(websocket, thread_id)
    try:
        while True:
            await websocket.receive_text() # زنده نگه‌داشتن کانکشن
    except WebSocketDisconnect:
        manager.disconnect(thread_id)

@app.post("/api/v1/oracle/inject")
async def inject_axiom(req: OracleRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    current_state = ada_app.get_state(config)
    
    if "oracle" not in current_state.next:
        raise HTTPException(status_code=400, detail="System is not waiting for an oracle.")
    
    st_vals = current_state.values
    # ذخیره اصل جدید در دیتابیس گراف
    memory_db.store_meta_axiom(st_vals["problem"], st_vals["unsat_core"], req.meta_axiom)
    
    # آپدیت وضعیت گراف و ادامه اجرا (Resume)
    ada_app.update_state(config, {
        "axioms": st_vals["axioms"] + [req.meta_axiom], 
        "iteration": 0, "unsat_core": [], "status": "INIT"
    })
    
    asyncio.create_task(run_graph_and_stream(req.thread_id, None))
    return {"status": "axiom_accepted", "action": "resuming_dialectic_loop"}