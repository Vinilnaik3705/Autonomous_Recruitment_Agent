from langchain.tools import Tool
from backend.services.resume_service import parse_resume
from backend.services.scheduling_service import SchedulingService

def get_resume_tools():
    return [
        Tool(
            name="ParseResume",
            func=lambda x: "Please upload file via API", 
            description="Extracts skills and contact info from a resume"
        )
    ]

def get_scheduling_tools():
    scheduler = SchedulingService()
    return [
        Tool(
            name="CheckAvailability",
            func=lambda x: scheduler.get_availability(1, x),                                 
            description="Checks interviewer availability for a given date (YYYY-MM-DD)"
        )
    ]