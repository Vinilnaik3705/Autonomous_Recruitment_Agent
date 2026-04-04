from datetime import datetime


def log_phase_completion(phase_name: str, details: str = "") -> None:
    """Print a standardized completion line for workflow visibility in backend logs."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    suffix = f" | {details}" if details else ""
    print(f"[{timestamp}] PHASE COMPLETED: {phase_name}{suffix}")
