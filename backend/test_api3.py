import asyncio
from app.database.database import db
from app.services.scheduler import TimetableScheduler
from app.services.ai_parser import AIConstraintParser
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.DEBUG)

class DummyReq:
    semester = 5
    academic_year = "2024-2028"
    constraints_text = "Siva Kumar Sir Will not Available From 10:15 am to 12.30 pm and 1.15 to 2.45\nSelvi Man Not Available at 10:15 to 12:30 and 3:00 to 4:30"

async def main():
    request = DummyReq()
    parsed_constraints = []
    if request.constraints_text:
        parser = AIConstraintParser()
        parsed_constraints = await parser.parse_constraints(request.constraints_text)
        print("PARSED CONSTRAINTS:", parsed_constraints)
        
    query = {"semester": request.semester, "academic_year": request.academic_year}
    classes = list(db.classes.find(query))
    class_ids = [str(c["_id"]) for c in classes]
    print("Class IDs:", class_ids)

    scheduler = TimetableScheduler(
        db=db,
        working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        periods_per_day=7,
        time_limit_seconds=10,
        custom_constraints=parsed_constraints
    )
    scheduler.load_data(class_ids=class_ids)
    scheduler.create_variables()
    scheduler.add_constraints()
    result = scheduler.solve()
    print("Result status:", result["status"])

asyncio.run(main())
