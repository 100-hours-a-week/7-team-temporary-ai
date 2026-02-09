from typing import Dict, Literal, List
import logfire
from langgraph.graph import StateGraph, END
from app.models.planner.internal import PlannerGraphState

# Import Nodes
from app.services.planner.nodes.node1_structure import node1_structure_analysis, node1_fallback
from app.services.planner.nodes.node2_importance import node2_importance
from app.services.planner.nodes.node3_chain_generator import node3_chain_generator, node3_fallback
from app.services.planner.nodes.node4_chain_judgement import node4_chain_judgement
from app.services.planner.nodes.node5_time_assignment import node5_time_assignment

# Conditional Logic for Node 1
def check_node1_result(state: PlannerGraphState) -> Literal["retry", "fallback", "success"]:
    # 1. 성공여부 판단: taskFeatures가 채워졌는지 확인 + Warnings가 없는지? 
    # (여기서는 taskFeatures 존재 여부로 판단)
    if state.taskFeatures and len(state.taskFeatures) > 0:
        return "success"
    
    # 2. 재시도 한도 초과
    if state.retry_node1 >= 4:
        return "fallback"
        
    # 3. 재시도
    return "retry"

# Conditional Logic for Node 3
def check_node3_result(state: PlannerGraphState) -> Literal["retry", "fallback", "success"]:
    # 1. 성공여부 판단: chainCandidates 존재 여부
    if state.chainCandidates and len(state.chainCandidates) > 0:
        return "success"
        
    # 2. 재시도 한도 초과
    if state.retry_node3 >= 4:
        return "fallback"
        
    # 3. 재시도
    return "retry"

# Graph Definition
workflow = StateGraph(PlannerGraphState)

# Add Nodes
workflow.add_node("node1_structure_analysis", node1_structure_analysis)
workflow.add_node("node1_fallback", node1_fallback)
workflow.add_node("node2_importance", node2_importance)
workflow.add_node("node3_chain_generator", node3_chain_generator)
workflow.add_node("node3_fallback", node3_fallback)
workflow.add_node("node4_chain_judgement", node4_chain_judgement)
workflow.add_node("node5_time_assignment", node5_time_assignment)

# Define Edges

# Start -> Node 1
workflow.set_entry_point("node1_structure_analysis")

# Node 1 -> Conditional
workflow.add_conditional_edges(
    "node1_structure_analysis",
    check_node1_result,
    {
        "success": "node2_importance",
        "retry": "node1_structure_analysis",
        "fallback": "node1_fallback"
    }
)

# Fallback -> Node 2
workflow.add_edge("node1_fallback", "node2_importance")

# Node 2 -> Node 3
workflow.add_edge("node2_importance", "node3_chain_generator")

# Node 3 -> Conditional
workflow.add_conditional_edges(
    "node3_chain_generator",
    check_node3_result,
    {
        "success": "node4_chain_judgement",
        "retry": "node3_chain_generator",
        "fallback": "node3_fallback"
    }
)

# Fallback -> Node 4
workflow.add_edge("node3_fallback", "node4_chain_judgement")

# Node 4 -> Node 5
workflow.add_edge("node4_chain_judgement", "node5_time_assignment")

# Node 5 -> End
workflow.add_edge("node5_time_assignment", END)

# Compile
planner_graph = workflow.compile()

# Visualize (Optional, for debugging)
try:
    if logfire.current_span():
       logfire.info("Planner Graph Initialized", graph=planner_graph.get_graph().draw_ascii())
except Exception:
    pass
