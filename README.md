# Excel to Database Loader

Simple Flask application to upload an Excel file and load it into a database table.

## How it works

1. Choose a table name and upload an Excel file (`.xlsx`, `.xls`, `.xlsm`).
2. If the table does not exist yet, the app creates it from the uploaded columns.
3. Rows are inserted into that table.
4. On later uploads to the same table, data is appended.

## Database connection

Set `DATABASE_URL` to your existing database connection string.

Examples:

- PostgreSQL: `postgresql+psycopg://user:password@host:5432/dbname`
- MySQL: `mysql+pymysql://user:password@host:3306/dbname`
- SQL Server: `mssql+pyodbc://...`

If not set, SQLite is used: `sqlite:///app.db`.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://user:password@host:5432/dbname"
python app.py
```

Open: `http://localhost:8000`

## Notes

- Column and table names are normalized to safe SQL identifiers.
- If a later Excel file contains extra columns that do not exist in the table, upload is rejected.
