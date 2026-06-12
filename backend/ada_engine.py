import os
import time
import traceback
from typing import List, Dict, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import google.generativeai as genai
from z3 import Solver, Int, Real, Bool, Ints, Reals, Bools, And, Or, Not, Implies, sat
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from database import memory_db
from memory_retriever import get_relevant_memories

# Schema
class FormalSyntax(BaseModel):
    declarations: str = Field(description="Z3 variable declarations in Python")
    constraints: List[str] = Field(description="List of Z3 constraints in Python")

class ADAState(TypedDict):
    problem: str
    axioms: List[str]
    current_hypothesis: dict
    unsat_core: List[str]
    iteration: int
    status: str
    error_count: int  # Track syntax errors for self-correction loops
    logs: List[dict]  # Track all node execution logs within the graph state

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY") or "mock_key")

def neural_abduction_node(state: ADAState) -> Dict:
    iteration = state.get("iteration", 0) + 1
    
    # Retrieve relevant memories
    memories = get_relevant_memories(state["problem"], state.get("unsat_core", []))
    
    # Check for self-correction prompt if we are in SYNTAX_DEADLOCK
    correction_prompt = ""
    if state.get("status") == "SYNTAX_DEADLOCK" and state.get("unsat_core"):
        error_msg = state["unsat_core"][0]
        correction_prompt = f"\nCRITICAL: Your previous generated Python/Z3 code resulted in a syntax or compilation error: {error_msg}.\nPlease correct the code to avoid this error and generate valid Python syntax using Z3."

    # If GEMINI_API_KEY is mock, return a mock hypothesis
    if not os.getenv("GEMINI_API_KEY") or os.getenv("TESTING") == "true":
        prob = state.get("problem", "").lower()
        axioms = state.get("axioms", [])
        
        if "syntax" in prob:
            if iteration == 1:
                # Syntax error: y is not declared
                current_hypothesis = {
                    "declarations": "x = Int('x')",
                    "constraints": ["y > 5"]
                }
            else:
                # Corrected syntax on subsequent iteration
                current_hypothesis = {
                    "declarations": "x = Int('x')\ny = Int('y')",
                    "constraints": ["y > 5"]
                }
        elif any(kw in prob for kw in ["security", "sandbox", "violation", "import"]):
            # Security violation: forbidden keyword
            current_hypothesis = {
                "declarations": "import os",
                "constraints": ["x > 5"]
            }
        elif any(kw in prob for kw in ["deadlock", "godel", "contradiction", "logic"]):
            if not axioms:
                # Contradiction leading to deadlock
                current_hypothesis = {
                    "declarations": "x = Int('x')",
                    "constraints": ["x > 10", "x < 5"]
                }
            else:
                # Resolved after Oracle intervention
                current_hypothesis = {
                    "declarations": "x = Int('x')",
                    "constraints": ["x > 5"]
                }
        else:
            # Default happy path satisfying constraint
            current_hypothesis = {
                "declarations": "x = Int('x')",
                "constraints": ["x > 5"]
            }

        new_log = {
            "event_type": "neural",
            "status": "GENERATED",
            "unsat_core": state.get("unsat_core", []),
            "iteration": iteration,
            "timestamp": time.time(),
            "hypothesis": current_hypothesis
        }
        return {
            "current_hypothesis": current_hypothesis,
            "iteration": iteration,
            "logs": state.get("logs", []) + [new_log]
        }

    sys_inst = "You are a formal logic engine. Output constraints in JSON."
    if state.get("unsat_core") and state.get("status") != "SYNTAX_DEADLOCK": 
        sys_inst += f"\nCRITICAL: Avoid contradiction: {state['unsat_core']}"

    if memories:
        sys_inst += f"\nHere is context retrieved from past epistemic memories of similar problems or failures. Use this to construct a correct solution and avoid repeating these failures:\n{memories}"

    if correction_prompt:
        sys_inst += correction_prompt

    model = genai.GenerativeModel(
        model_name='gemini-3.5-flash',
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.0,
            "top_p": 1.0
        },
        system_instruction=sys_inst
    )
    
    resp = model.generate_content(
        f"Problem: {state['problem']}\nAxioms: {state['axioms']}\nExpected JSON Schema: FormalSyntax: declarations (str), constraints (list of str)"
    )
    
    current_hypothesis = FormalSyntax.model_validate_json(resp.text).model_dump()
    new_log = {
        "event_type": "neural",
        "status": "GENERATED",
        "unsat_core": state.get("unsat_core", []),
        "iteration": iteration,
        "timestamp": time.time(),
        "hypothesis": current_hypothesis
    }
    return {
        "current_hypothesis": current_hypothesis, 
        "iteration": iteration,
        "logs": state.get("logs", []) + [new_log]
    }

def symbolic_verification_node(state: ADAState) -> Dict:
    current_syntax = FormalSyntax(**state["current_hypothesis"])
    solver = Solver()
    solver.set(unsat_core=True)
    solver.set("timeout", 5000) # 5 seconds
    
    # Safe sandbox verification
    code_to_check = f"{current_syntax.declarations}\n" + "\n".join(current_syntax.constraints)
    forbidden_keywords = ["import", "exec", "eval", "__builtins__", "open", "os", "sys", "subprocess", "requests", "shutil", "socket", "class", "def "]
    for kw in forbidden_keywords:
        if kw in code_to_check:
            err_msg = f"Security Violation: forbidden keyword '{kw}' detected"
            new_log = {
                "event_type": "symbolic",
                "status": "SYNTAX_DEADLOCK",
                "unsat_core": [err_msg],
                "iteration": state.get("iteration", 0),
                "timestamp": time.time()
            }
            return {
                "status": "SYNTAX_DEADLOCK",
                "unsat_core": [err_msg],
                "error_count": state.get("error_count", 0) + 1,
                "logs": state.get("logs", []) + [new_log]
            }

    try:
        local_env = {"Int": Int, "Real": Real, "Bool": Bool, "Ints": Ints, "Reals": Reals, "Bools": Bools, "And": And, "Or": Or, "Not": Not, "Implies": Implies}
        exec(current_syntax.declarations, {}, local_env)
        for i, constr in enumerate(current_syntax.constraints):
            solver.assert_and_track(eval(constr, {}, local_env), f"C_{i}")
    except Exception as e:
        err_msg = str(e)
        new_log = {
            "event_type": "symbolic",
            "status": "SYNTAX_DEADLOCK",
            "unsat_core": [err_msg],
            "iteration": state.get("iteration", 0),
            "timestamp": time.time()
        }
        return {
            "status": "SYNTAX_DEADLOCK",
            "unsat_core": [err_msg],
            "error_count": state.get("error_count", 0) + 1,
            "logs": state.get("logs", []) + [new_log]
        }

    if solver.check() == sat:
        new_log = {
            "event_type": "symbolic",
            "status": "SUCCESS",
            "unsat_core": [],
            "iteration": state.get("iteration", 0),
            "timestamp": time.time()
        }
        return {
            "status": "SUCCESS",
            "unsat_core": [],
            "logs": state.get("logs", []) + [new_log]
        }
    else:
        core = [str(c) for c in solver.unsat_core()]
        memory_db.store_contradiction(state["problem"], str(current_syntax.model_dump()), core)
        new_log = {
            "event_type": "symbolic",
            "status": "CONTRADICTION",
            "unsat_core": core,
            "iteration": state.get("iteration", 0),
            "timestamp": time.time()
        }
        return {
            "status": "CONTRADICTION",
            "unsat_core": core,
            "logs": state.get("logs", []) + [new_log]
        }

def oracle_intervention_node(state: ADAState) -> Dict:
    new_log = {
        "event_type": "oracle",
        "status": "INTERVENTED",
        "unsat_core": state.get("unsat_core", []),
        "iteration": state.get("iteration", 0),
        "timestamp": time.time()
    }
    return {
        "logs": state.get("logs", []) + [new_log]
    }

def check_deadlock(state: ADAState) -> Literal["neural", "oracle", "end"]:
    if state.get("status") == "SUCCESS":
        return "end"
    if state.get("status") == "SYNTAX_DEADLOCK":
        if state.get("error_count", 0) < 3:
            return "neural"
        else:
            return "oracle"
    if state.get("iteration", 0) >= 5:
        return "oracle"
    return "neural"

# ساخت گراف
workflow = StateGraph(ADAState)
workflow.add_node("neural", neural_abduction_node)
workflow.add_node("symbolic", symbolic_verification_node)
workflow.add_node("oracle", oracle_intervention_node)

workflow.set_entry_point("neural")
workflow.add_edge("neural", "symbolic")
workflow.add_conditional_edges("symbolic", check_deadlock, {"neural": "neural", "oracle": "oracle", "end": END})
workflow.add_edge("oracle", "neural")

# استفاده از MemorySaver برای امکان توقف (Suspend) و ادامه (Resume)
ada_app = workflow.compile(checkpointer=MemorySaver(), interrupt_before=["oracle"])
