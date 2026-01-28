from fastapi import APIRouter, HTTPException, BackgroundTasks, Body
from app.models.planner.request import ArrangementState
from app.models.planner.response import PlannerResponse, AssignmentResult
from app.models.planner.internal import PlannerGraphState, FreeSession
from app.models.planner.weights import WeightParams
from app.services.planner.nodes.node1_structure import node1_structure_analysis
from app.services.planner.nodes.node2_importance import node2_importance
from app.services.planner.nodes.node3_chain_generator import node3_chain_generator
from app.services.planner.nodes.node4_chain_judgement import node4_chain_judgement
from app.services.planner.nodes.node5_time_assignment import node5_time_assignment
from app.services.planner.utils.session_utils import calculate_free_sessions
import time
import logfire
import json
import os
from pathlib import Path

router = APIRouter()

# Load Test Request Example
# Calculate Project Root: app/api/v1/endpoints/planners.py -> ... -> MOLIP-AI
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
TEST_DATA_PATH = BASE_DIR / "tests" / "data" / "test_request.json"

try:
    with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
        TEST_REQUEST_EXAMPLE = json.load(f)
except Exception as e:
    print(f"WARNING: Failed to load test_request.json for Swagger example: {e}")
    TEST_REQUEST_EXAMPLE = {}

@router.post("/test", response_model=PlannerResponse)
async def generate_planner_test(
    request: ArrangementState = Body(
        ...,
        example=TEST_REQUEST_EXAMPLE
    )
):
    """
    [Test] LangGraph Pipeline-based Planner Generation (V1)
    """
    start_time = time.time()
    
    with logfire.span("api.v1.planners.test"):
        try:
            # 1. State Initialization
            # Calculate Free Sessions
            fixed_tasks = [t for t in request.schedules if t.type == "FIXED"]
            flex_tasks = [t for t in request.schedules if t.type == "FLEX"]
            
            sessions = calculate_free_sessions(
                start_arrange_str=request.startArrange,
                day_end_time_str=request.user.dayEndTime,
                fixed_schedules=fixed_tasks
            )
            
            state = PlannerGraphState(
                request=request,
                weights=WeightParams(), # Use default weights for now
                fixedTasks=fixed_tasks,
                flexTasks=flex_tasks,
                freeSessions=sessions
            )
            
            # 2. Pipeline Execution
            # Node 1
            state = await node1_structure_analysis(state)
            
            # Node 2
            state = node2_importance(state)
            
            # Node 3
            state = await node3_chain_generator(state)
            
            # Node 4
            state = node4_chain_judgement(state)
            
            # Node 5
            state = node5_time_assignment(state)
            
            # 3. Response Construction
            final_results = state.finalResults
            
            # Mix with Fixed Tasks if needed? 
            # The API spec says "results" list. Usually includes everything or just assigned FLEX? 
            # "assignedBy: USER" for FIXED tasks.
            # Node 5 excludes FIXED tasks from `finalResults` by default (it processes FLEX).
            # We should probably combine them or check if `finalResults` has them.
            # Currently `node5` only outputs FLEX assignment results.
            
            # Let's add FIXED tasks to the result list for completeness
            combined_results = []
            
            # 3.1 FLEX Results (already AssignmentResult objects, but missing userId if model didn't have it before)
            # We updated the model to have userId. We need to inject it.
            # Node 5 creation of AssignmentResult likely doesn't have userId yet because we just added it.
            # We should update Node 5 or inject it here.
            # Injecting here is safer to avoid breaking Node 5 internal logic for a moment if it's strict.
            # But AssignmentResult is a Pydantic model. 
            
            for res in final_results:
                # Copy and update userId
                res_dict = res.model_dump()
                res_dict['userId'] = request.user.userId
                combined_results.append(AssignmentResult(**res_dict))
                
            # 3.2 FIXED Results
            for ft in state.fixedTasks:
                combined_results.append(AssignmentResult(
                    userId=request.user.userId,
                    taskId=ft.taskId,
                    dayPlanId=ft.dayPlanId,
                    title=ft.title,
                    type="FIXED",
                    assignedBy="USER",
                    assignmentStatus="ASSIGNED",
                    startAt=ft.startAt,
                    endAt=ft.endAt,
                    children=None
                ))
            
            # Sort by startAt
            # Handle None startAt (EXCLUDED) -> push to end
            combined_results.sort(key=lambda x: x.startAt if x.startAt else "99:99")
            
            process_time = time.time() - start_time
            
            return PlannerResponse(
                success=True,
                processTime=round(process_time, 2),
                results=combined_results,
                message="Planner generated successfully"
            )
            
        except Exception as e:
            # Error handling mapping can be added here
            raise HTTPException(status_code=500, detail=str(e))
