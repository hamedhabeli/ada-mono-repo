import os
import traceback
from typing import List, Dict, TypedDict, Literal
from pydantic import BaseModel, Field
import google.generativeai as genai
from z3 import Solver, Int, Real, Bool, Ints, Reals, Bools, And, Or, Not, Implies, sat
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from database import memory_db

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

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY") or "mock_key")

def neural_abduction_node(state: ADAState) -> Dict:
    # If GEMINI_API_KEY is mock, return a mock hypothesis
    if not os.getenv("GEMINI_API_KEY") or os.getenv("TESTING") == "true":
        return {
            "current_hypothesis": {
                "declarations": "x = Int('x')",
                "constraints": ["x > 5"]
            },
            "iteration": state["iteration"] + 1
        }

    sys_inst = "You are a formal logic engine. Output constraints in JSON."
    if state["unsat_core"]: 
        sys_inst += f"\nCRITICAL: Avoid contradiction: {state['unsat_core']}"

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
    return {"current_hypothesis": FormalSyntax.model_validate_json(resp.text).model_dump(), "iteration": state["iteration"] + 1}

def symbolic_verification_node(state: ADAState) -> Dict:
    current_syntax = FormalSyntax(**state["current_hypothesis"])
    solver = Solver()
    solver.set(unsat_core=True)
    
    try:
        local_env = {"Int": Int, "Real": Real, "Bool": Bool, "Ints": Ints, "Reals": Reals, "Bools": Bools, "And": And, "Or": Or, "Not": Not, "Implies": Implies}
        exec(current_syntax.declarations, {}, local_env)
        for i, constr in enumerate(current_syntax.constraints):
            solver.assert_and_track(eval(constr, {}, local_env), f"C_{i}")
    except Exception as e:
        return {"status": "SYNTAX_DEADLOCK", "unsat_core": [str(e)]}

    if solver.check() == sat:
        return {"status": "SUCCESS", "unsat_core": []}
    else:
        core = [str(c) for c in solver.unsat_core()]
        memory_db.store_contradiction(state["problem"], str(current_syntax.model_dump()), core)
        return {"status": "CONTRADICTION", "unsat_core": core}

def oracle_intervention_node(state: ADAState) -> Dict:
    return state # توقف گراف در این نقطه انجام می‌شود

def check_deadlock(state: ADAState) -> Literal["neural", "oracle", "end"]:
    if state["status"] == "SUCCESS": return "end"
    if state["iteration"] >= 5 or state["status"] == "SYNTAX_DEADLOCK": return "oracle"
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