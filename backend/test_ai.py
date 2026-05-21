import sys
import os
from app.services.ai_parser import AIConstraintParser
from app.core.config import settings

def test():
    parser = AIConstraintParser(
        model=settings.AI_MODEL,
        timeout_seconds=settings.OPENAI_TIMEOUT_SECONDS,
        api_key=settings.OPENAI_API_KEY,
        api_base=settings.OPENAI_API_BASE,
        context={
            "faculty_names": ["Benazir", "Dr. Smith"],
            "subject_names": ["Mathematics", "Physics"],
            "class_names": ["CSE-A", "CSE-B"]
        }
    )
    
    text = "Benazir mam will available at monday. All POST Periods Should Be Before Lunch Break"
    print("Testing with text:", text)
    try:
        constraints = parser.parse_constraints(text)
        print("Successfully parsed constraints:", constraints)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
