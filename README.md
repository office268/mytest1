# Excel to Database Loader

Simple Flask application to upload an Excel file and load it into a database table.

## How it works

1. Choose a table name and upload an Excel file (`.xlsx`, `.xls`, `.xlsm`).
2. If the table does not exist yet, the app creates it from the uploaded columns.
3. Rows are inserted into that table.
4. On later uploads to the same table, data is appended.

## Database

The app uses **SQLite** and stores data in `app.db` in the project directory. No database server is required.

Optional: set `DATABASE_URL` in `.env` to use a different SQLite path (e.g. `sqlite:///other.db`).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:8000`

## Deploy on Railway

1. Create a Railway project and deploy from GitHub.
2. Set `SECRET_KEY` in Railway Variables.
3. Use this Start Command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Note: On Railway the filesystem is ephemeral, so SQLite data in `app.db` will not persist across redeploys unless you add a volume.

## Notes

- Column and table names are normalized to safe SQL identifiers.
- If a later Excel file contains extra columns that do not exist in the table, upload is rejected.
