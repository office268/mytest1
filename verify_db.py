"""Verify test_table exists and has data."""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()
url = os.getenv("DATABASE_URL", "sqlite:///app.db")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg://", 1)
if url.startswith("postgresql://") and "psycopg" not in url:
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(url)
insp = inspect(engine)
tables = insp.get_table_names()
print("Tables in DB:", tables)
if "test_table" in tables:
    with engine.connect() as c:
        r = c.execute(text("SELECT * FROM test_table"))
        rows = r.fetchall()
        print("Rows in test_table:", len(rows))
        for row in rows:
            print(" ", row)
else:
    print("test_table not found")
