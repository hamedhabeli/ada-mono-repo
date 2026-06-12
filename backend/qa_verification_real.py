import os
import sys
import time
import requests

API_URL = "http://localhost:8000"

def run_scenario_1():
    print("\n=== RUNNING SCENARIO 1: Happy Path (Direct Logic Solution) ===")
    thread_id = "real-thread-scenario-1"
    
    # 1. Start Solving
    res = requests.post(f"{API_URL}/api/v1/solve", json={
        "thread_id": thread_id,
        "problem": "Find x where x > 5"
    })
    assert res.status_code == 200, "Scenario 1 Start Failed"
    print("[SUCCESS] Solve endpoint called successfully.")
    
    # Wait for background graph task to complete
    time.sleep(3)
    
    # 2. Verify History
    res = requests.get(f"{API_URL}/api/v1/threads/{thread_id}/history")
    assert res.status_code == 200, "Scenario 1 History Failed"
    history = res.json()
    
    print(f"Final Status: {history['status']}")
    assert history['status'] == "SUCCESS", f"Scenario 1 failed to reach SUCCESS. Got {history['status']}"
    print("[SUCCESS] Scenario 1 completed with status SUCCESS.")
    for log in history['logs']:
        print(f" - Node: {log['event_type']}, Status: {log['status']}")


def run_scenario_2():
    print("\n=== RUNNING SCENARIO 2: Syntax Self-Correction ===")
    thread_id = "real-thread-scenario-2"
    
    # 1. Start Solving with problem containing "syntax"
    res = requests.post(f"{API_URL}/api/v1/solve", json={
        "thread_id": thread_id,
        "problem": "Find x where x is a syntax error"
    })
    assert res.status_code == 200, "Scenario 2 Start Failed"
    
    time.sleep(4)
    
    # 2. Verify History and self-correction loop
    res = requests.get(f"{API_URL}/api/v1/threads/{thread_id}/history")
    assert res.status_code == 200
    history = res.json()
    
    print(f"Final Status: {history['status']}")
    assert history['status'] == "SUCCESS", "Scenario 2 failed to self-correct to SUCCESS"
    
    print("[SUCCESS] Scenario 2 completed. Logs trace:")
    for log in history['logs']:
        print(f" - Node: {log['event_type']}, Status: {log['status']}")
        if log['status'] == "SYNTAX_DEADLOCK":
            print(f"   Parser Error details: {log['unsat_core']}")


def run_scenario_3():
    print("\n=== RUNNING SCENARIO 3: Sandbox Security Guard Validation ===")
    thread_id = "real-thread-scenario-3"
    
    # 1. Start Solving with security violation keywords
    res = requests.post(f"{API_URL}/api/v1/solve", json={
        "thread_id": thread_id,
        "problem": "Execute forbidden code or sandbox import violation"
    })
    assert res.status_code == 200, "Scenario 3 Start Failed"
    
    time.sleep(3)
    
    # 2. Verify Security Guard Blocking
    res = requests.get(f"{API_URL}/api/v1/threads/{thread_id}/history")
    assert res.status_code == 200
    history = res.json()
    
    print(f"Final Status: {history['status']}")
    print("[SUCCESS] Scenario 3 completed. Sandbox Security Guard Log Trace:")
    has_security_log = False
    for log in history['logs']:
        print(f" - Node: {log['event_type']}, Status: {log['status']}")
        if log['status'] == "SYNTAX_DEADLOCK" and any("Security Violation" in str(core) for core in log['unsat_core']):
            print(f"   [BLOCKED] Security violation successfully intercepted: {log['unsat_core']}")
            has_security_log = True
    assert has_security_log, "Security Guard failed to block 'import' keyword"


def run_scenario_4_and_5():
    print("\n=== RUNNING SCENARIO 4 & 5: Gödelian Deadlock, Oracle Injection, and Hydration ===")
    thread_id = "real-thread-scenario-4"
    
    # 1. Start Solving with contradictory problem
    res = requests.post(f"{API_URL}/api/v1/solve", json={
        "thread_id": thread_id,
        "problem": "Gödel contradiction deadlock problem"
    })
    assert res.status_code == 200, "Scenario 4 Start Failed"
    
    # Wait for contradiction and deadlock checks to finish
    time.sleep(5)
    
    # 2. Inject new meta-axiom via REST endpoint
    print("Oracle Intervention: Injecting meta-axiom...")
    res = requests.post(f"{API_URL}/api/v1/oracle/inject", json={
        "thread_id": thread_id,
        "meta_axiom": "Introduce meta-axiom x > 5 to resolve contradiction"
    })
    assert res.status_code == 200, "Oracle Intervention Injection Failed"
    print("[SUCCESS] Oracle Meta-Axiom injected. Resuming execution...")
    
    # Wait for the graph to resume and complete under the new axiom
    time.sleep(4)
    
    # 3. Verify post-intervention history
    res = requests.get(f"{API_URL}/api/v1/threads/{thread_id}/history")
    assert res.status_code == 200
    history = res.json()
    
    print(f"Post-Intervention Status: {history['status']}")
    assert history['status'] == "SUCCESS", f"Failed to reach SUCCESS after Oracle intervention. Got: {history['status']}"
    print("[SUCCESS] Scenario 4/5 resolved contradiction and reached SUCCESS.")
    for log in history['logs']:
        print(f" - Node: {log['event_type']}, Status: {log['status']}")


def main():
    print("==========================================================")
    print("         ADA REAL-SERVER FULL-STACK INTEGRATION SUITE      ")
    print("==========================================================")
    try:
        run_scenario_1()
        run_scenario_2()
        run_scenario_3()
        run_scenario_4_and_5()
        print("\n==========================================================")
        print("          ALL REAL-SERVER SCENARIOS PASSED 100%!          ")
        print("==========================================================")
    except Exception as e:
        print(f"\n[FAILURE] Real-server integration QA failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
