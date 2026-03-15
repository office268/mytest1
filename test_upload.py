"""Create test Excel and POST to app via Flask test client (no server needed)."""
import sys
from pathlib import Path

import pandas as pd

# Create test Excel
excel_path = Path("test_data.xlsx")
if excel_path.exists():
    excel_path.unlink()
df = pd.DataFrame({"name": ["Alice", "Bob", "Carol"], "score": [85, 90, 78]})
df.to_excel(excel_path, index=False)
print("Created test_data.xlsx")

# Use Flask test client so we don't need the server running
from app import app

with app.test_client() as client:
    with open(excel_path, "rb") as f:
        data = client.post(
            "/upload",
            data={"table_name": "test_table", "excel_file": (f, "test_data.xlsx")},
            follow_redirects=True,
        )
    code = data.status_code
    print(f"POST /upload -> {code}")
    if code == 200:
        # Check for success message in response
        text = data.get_data(as_text=True)
        if "successfully" in text or "inserted" in text:
            print("Upload succeeded. Table loaded.")
        else:
            print("Response:", text[:300])
    else:
        print("Response:", data.get_data(as_text=True)[:400])
    sys.exit(0 if code == 200 else 1)
