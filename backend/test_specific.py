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
            "subject_names": ["Mathematics", "Physics", "Chemistry"],
            "class_names": ["CSE-A", "CSE-B"]
        }
    )
    
    text = "Physics must be scheduled on Monday in period 2. Chemistry must be in period 3."
    print("Testing with text:", text)
    try:
        constraints = parser.parse_constraints(text)
        import json
        print("Successfully parsed constraints:", json.dumps(constraints, indent=2))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
