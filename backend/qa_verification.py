import os
import asyncio
import sys
from fastapi.testclient import TestClient

# Ensure backend directory is in python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from main import app
from ada_engine import ada_app

client = TestClient(app)

async def run_scenario_1():
    print("\n=== RUNNING SCENARIO 1: Happy Path (Direct Logic Solution) ===")
    thread_id = "qa-thread-scenario-1"
    
    # 1. Start Solving
    res = client.post("/api/v1/solve", json={
        "thread_id": thread_id,
        "problem": "Find x where x > 5"
    })
    assert res.status_code == 200, "Scenario 1 Start Failed"
    print("[SUCCESS] Solve endpoint called successfully.")
    
    # Wait for background graph task to complete
    await asyncio.sleep(2)
    
    # 2. Verify History
    res = client.get(f"/api/v1/threads/{thread_id}/history")
    assert res.status_code == 200, "Scenario 1 History Failed"
    history = res.json()
    
    print(f"Final Status: {history['status']}")
    assert history['status'] == "SUCCESS", "Scenario 1 failed to reach SUCCESS"
    print("[SUCCESS] Scenario 1 completed with status SUCCESS.")
    for log in history['logs']:
        print(f" - Node: {log['event_type']}, Status: {log['status']}")


async def run_scenario_2():
    print("\n=== RUNNING SCENARIO 2: Syntax Self-Correction ===")
    thread_id = "qa-thread-scenario-2"
    
    # 1. Start Solving with problem containing "syntax"
    res = client.post("/api/v1/solve", json={
        "thread_id": thread_id,
        "problem": "Find x where x is a syntax error"
    })
    assert res.status_code == 200, "Scenario 2 Start Failed"
    
    await asyncio.sleep(3)
    
    # 2. Verify History and self-correction loop
    res = client.get(f"/api/v1/threads/{thread_id}/history")
    assert res.status_code == 200
    history = res.json()
    
    print(f"Final Status: {history['status']}")
    assert history['status'] == "SUCCESS", "Scenario 2 failed to self-correct to SUCCESS"
    
    print("[SUCCESS] Scenario 2 completed. Logs trace:")
    for log in history['logs']:
        print(f" - Node: {log['event_type']}, Status: {log['status']}")
        if log['status'] == "SYNTAX_DEADLOCK":
            print(f"   Parser Error details: {log['unsat_core']}")


async def run_scenario_3():
    print("\n=== RUNNING SCENARIO 3: Sandbox Security Guard Validation ===")
    thread_id = "qa-thread-scenario-3"
    
    # 1. Start Solving with security violation keywords
    res = client.post("/api/v1/solve", json={
        "thread_id": thread_id,
        "problem": "Execute forbidden code or sandbox import violation"
    })
    assert res.status_code == 200, "Scenario 3 Start Failed"
    
    await asyncio.sleep(2)
    
    # 2. Verify Security Guard Blocking
    res = client.get(f"/api/v1/threads/{thread_id}/history")
    assert res.status_code == 200
    history = res.json()
    
    print(f"Final Status: {history['status']}")
    # Under mock, iteration goes to 1, encounters "import os", increments error_count, loops to neural again, and repeats.
    # At error_count >= 3, it should trigger oracle or stay blocked in deadlock.
    print("[SUCCESS] Scenario 3 completed. Sandbox Security Guard Log Trace:")
    has_security_log = False
    for log in history['logs']:
        print(f" - Node: {log['event_type']}, Status: {log['status']}")
        if log['status'] == "SYNTAX_DEADLOCK" and "Security Violation" in log['unsat_core'][0]:
            print(f"   [BLOCKED] Security violation successfully intercepted: {log['unsat_core']}")
            has_security_log = True
    assert has_security_log, "Security Guard failed to block 'import' keyword"


async def run_scenario_4_and_5():
    print("\n=== RUNNING SCENARIO 4 & 5: Gödelian Deadlock, Oracle Injection, and Hydration ===")
    thread_id = "qa-thread-scenario-4"
    
    # 1. Start Solving with contradictory problem
    res = client.post("/api/v1/solve", json={
        "thread_id": thread_id,
        "problem": "Gödel contradiction deadlock problem"
    })
    assert res.status_code == 200, "Scenario 4 Start Failed"
    
    # Wait for contradiction and deadlock checks
    await asyncio.sleep(4)
    
    # 2. Verify that LangGraph interrupted on "oracle" node
    config = {"configurable": {"thread_id": thread_id}}
    state_obj = ada_app.get_state(config)
    print(f"Next Node to run: {state_obj.next}")
    assert "oracle" in state_obj.next, "LangGraph was not interrupted on oracle node"
    print("[SUCCESS] Gödelian Deadlock correctly detected. Execution interrupted before oracle node.")
    
    # 3. Inject new meta-axiom via REST endpoint
    print("Oracle Intervention: Injecting meta-axiom...")
    res = client.post("/api/v1/oracle/inject", json={
        "thread_id": thread_id,
        "meta_axiom": "Introduce meta-axiom x > 5 to resolve contradiction"
    })
    assert res.status_code == 200, "Oracle Intervention Injection Failed"
    print("[SUCCESS] Oracle Meta-Axiom injected. Resuming execution...")
    
    # Wait for the graph to resume and complete under the new axiom
    await asyncio.sleep(3)
    
    # 4. Verify post-intervention history
    res = client.get(f"/api/v1/threads/{thread_id}/history")
    assert res.status_code == 200
    history = res.json()
    
    print(f"Post-Intervention Status: {history['status']}")
    assert history['status'] == "SUCCESS", "Failed to reach SUCCESS after Oracle intervention"
    print("[SUCCESS] Scenario 4/5 resolved contradiction and reached SUCCESS.")
    for log in history['logs']:
        print(f" - Node: {log['event_type']}, Status: {log['status']}")


async def main():
    print("==========================================================")
    print("             ADA FULL-STACK LOGIC TEST SUITE              ")
    print("==========================================================")
    try:
        await run_scenario_1()
        await run_scenario_2()
        await run_scenario_3()
        await run_scenario_4_and_5()
        print("\n==========================================================")
        print("          ALL SCENARIOS PASSED WITH 100% SUCCESS!          ")
        print("==========================================================")
    except Exception as e:
        print(f"\n[FAILURE] QA Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
