import asyncio
import os
from app.services.ai_parser import AIConstraintParser
from dotenv import load_dotenv

load_dotenv()
async def main():
    parser = AIConstraintParser(context={"faculty_names": ["Siva Kumar", "Selvi Mam"], "subject_names": [], "class_names": []})
    text = "Siva Kumar Sir Will not Available From 10:15 am to 12.30 pm and 1.15 to 2.45\nSelvi Man Not Available at 10:15 to 12:30 and 3:00 to 4:30"
    res = parser.parse_constraints_with_diagnostics(text)
    print("PARSED:", res)

asyncio.run(main())
