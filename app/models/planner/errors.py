from enum import Enum
from google.api_core import exceptions as google_exceptions

class PlannerErrorCode(str, Enum):
    # 400 Bad Request
    PLANNER_BAD_REQUEST = "PLANNER_BAD_REQUEST"
    PLANNER_INVALID_ARGUMENT = "PLANNER_INVALID_ARGUMENT"
    PLANNER_FAILED_PRECONDITION = "PLANNER_FAILED_PRECONDITION"
    PLANNER_OUT_OF_RANGE = "PLANNER_OUT_OF_RANGE"
    
    # 401 Unauthorized
    PLANNER_UNAUTHENTICATED = "PLANNER_UNAUTHENTICATED"
    
    # 403 Forbidden
    PLANNER_PERMISSION_DENIED = "PLANNER_PERMISSION_DENIED"
    
    # 404 Not Found
    PLANNER_NOT_FOUND = "PLANNER_NOT_FOUND"
    
    # 429 Too Many Requests
    PLANNER_RESOURCE_EXHAUSTED = "PLANNER_RESOURCE_EXHAUSTED"
    
    # 503 Service Unavailable
    PLANNER_SERVICE_UNAVAILABLE = "PLANNER_SERVICE_UNAVAILABLE"
    
    # 504 Gateway Timeout
    PLANNER_TIMEOUT = "PLANNER_TIMEOUT"
    
    # 500 Internal Server Error
    PLANNER_SERVER_ERROR = "PLANNER_SERVER_ERROR"

def map_exception_to_error_code(e: Exception) -> PlannerErrorCode:
    """Exception을 PlannerErrorCode로 매핑"""
    if isinstance(e, google_exceptions.InvalidArgument):
        return PlannerErrorCode.PLANNER_INVALID_ARGUMENT
    elif isinstance(e, google_exceptions.FailedPrecondition):
        return PlannerErrorCode.PLANNER_FAILED_PRECONDITION
    elif isinstance(e, google_exceptions.OutOfRange):
        return PlannerErrorCode.PLANNER_OUT_OF_RANGE
    elif isinstance(e, google_exceptions.Unauthenticated):
        return PlannerErrorCode.PLANNER_UNAUTHENTICATED
    elif isinstance(e, google_exceptions.PermissionDenied):
        return PlannerErrorCode.PLANNER_PERMISSION_DENIED
    elif isinstance(e, google_exceptions.NotFound):
        return PlannerErrorCode.PLANNER_NOT_FOUND
    elif isinstance(e, google_exceptions.ResourceExhausted):
        return PlannerErrorCode.PLANNER_RESOURCE_EXHAUSTED
    elif isinstance(e, google_exceptions.ServiceUnavailable):
        return PlannerErrorCode.PLANNER_SERVICE_UNAVAILABLE
    elif isinstance(e, google_exceptions.DeadlineExceeded):
        return PlannerErrorCode.PLANNER_TIMEOUT
    # ValueError 등 일반적인 에러는 Bad Request 또는 Server Error로 처리
    elif isinstance(e, ValueError):
        return PlannerErrorCode.PLANNER_BAD_REQUEST
    
    return PlannerErrorCode.PLANNER_SERVER_ERROR

def is_retryable_error(error_code: PlannerErrorCode) -> bool:
    """
    에러 코드가 재시작(Retry) 가능한지 판단
    - 5xx 계열 (Server Error, Timeout, Service Unavailable)
    - 429 (Resource Exhausted)
    """
    retryable_codes = {
        PlannerErrorCode.PLANNER_SERVICE_UNAVAILABLE, # 503
        PlannerErrorCode.PLANNER_RESOURCE_EXHAUSTED,  # 429
        PlannerErrorCode.PLANNER_TIMEOUT,             # 504
        PlannerErrorCode.PLANNER_SERVER_ERROR,        # 500
    }
    return error_code in retryable_codes
