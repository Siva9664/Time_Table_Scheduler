from app.services.ai_parser import AIConstraintParser
from dotenv import load_dotenv

load_dotenv()
parser = AIConstraintParser()
text = "Siva Kumar Sir Will not Available From 10:15 am to 12.30 pm and 1.15 to 2.45\nSelvi Man Not Available at 10:15 to 12:30 and 3:00 to 4:30"
res = parser.parse_constraints(text)
print("GROQ RETURNED:", res)
