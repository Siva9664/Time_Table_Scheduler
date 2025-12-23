import os
import sys
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Parse DATABASE_URL manually since we might not have sqlalchemy set up yet
# Expected format: mysql://user:password@host:port/dbname
db_url = os.getenv("DATABASE_URL", "mysql://root:@localhost:3306/ai_timetable_scheduler")

try:
    # Basic parsing logic
    url_parts = db_url.replace("mysql://", "").split("@")
    credentials = url_parts[0].split(":")
    server_info = url_parts[1].split("/")
    
    user = credentials[0]
    password = credentials[1] if len(credentials) > 1 else ""
    
    host_port = server_info[0].split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306
    
    # Database name from URL or schema default
    target_db_name = server_info[1] if len(server_info) > 1 else "ai_timetable_scheduler"

    print(f"Connecting to MySQL at {host}:{port} as {user}...")
    
    # Connect to MySQL Server (no database selected yet)
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        port=port
    )

    if connection.is_connected():
        cursor = connection.cursor()
        
        # Read schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')
        print(f"Reading schema from {schema_path}...")
        
        with open(schema_path, 'r', encoding='utf-8', errors='replace') as f:
            schema_sql = f.read()
            
        # Execute statements
        # We need to split by semicolon but handle cases where semicolon is inside strings if possible.
        # For this simple schema, splitting by ';' and filtering empty lines usually works.
        statements = schema_sql.split(';')
        
        print("Executing schema statements...")
        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                except Error as e:
                    print(f"Error executing statement: {e}")
                    
        print("Database setup completed successfully!")

except Error as e:
    print(f"Error connecting to MySQL: {e}")
    print("Please ensure MySQL is running and credentials in .env are correct.")
finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
        print("MySQL connection is closed")
