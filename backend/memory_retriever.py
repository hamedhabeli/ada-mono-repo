from database import memory_db

def get_relevant_memories(problem: str, unsat_core: list[str]) -> str:
    """
    Orchestrates Qdrant similarity searches and Neo4j graph queries 
    to retrieve past failure patterns and their resolved meta-axioms.
    Returns a formatted markdown segment to be injected into Gemini's context.
    """
    context_lines = []
    
    # 1. Similarity search for past contradictions in Qdrant
    similar_contradictions = memory_db.search_contradictions(problem, limit=2)
    if similar_contradictions:
        context_lines.append("### PAST SIMILAR CONTRADICTIONS:")
        for idx, item in enumerate(similar_contradictions):
            text = item.get("payload", {}).get("text", "")
            context_lines.append(f"  - Failure Pattern: {text}")
            
    # 2. Extract resolved axioms from Neo4j for current unsat core or similar historical cores
    resolved_axioms = []
    if unsat_core:
        core_str = " AND ".join(unsat_core)
        resolved_axioms.extend(memory_db.search_resolved_axioms(core_str))
        
    for item in similar_contradictions:
        text = item.get("payload", {}).get("text", "")
        if " | Core: " in text:
            hist_core = text.split(" | Core: ")[-1]
            for ax in memory_db.search_resolved_axioms(hist_core):
                if ax not in resolved_axioms:
                    resolved_axioms.append(ax)
                    
    if resolved_axioms:
        context_lines.append("### PAST RESOLUTION META-AXIOMS (STRONGLY CONSIDER THESE PRINCIPLES):")
        for idx, axiom in enumerate(resolved_axioms):
            context_lines.append(f"  - Resolve Principle: {axiom}")
            
    if not context_lines:
        return ""
        
    return "\n" + "\n".join(context_lines) + "\n"
