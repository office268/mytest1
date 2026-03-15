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

### Option A: SQLite (no database setup)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:8000`. The app uses `sqlite:///app.db` by default.

### Option B: PostgreSQL (local or Docker)

1. **Start PostgreSQL**

   - **Docker:** from the project root run:
     ```bash
     docker compose up -d
     ```
     This starts Postgres with user `postgres`, password `postgres`, database `appdb` on port 5432.

   - **Installed locally:** ensure Postgres is running and create a database (e.g. `appdb`).

2. **Set the database URL**

   - **Option 1 – use a `.env` file:** copy `.env.example` to `.env`, set `DATABASE_URL` (and optionally `SECRET_KEY`). For the Docker setup above use:
     ```
     DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/appdb
     ```
   - **Option 2 – set in the shell:**
     - PowerShell: `$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/appdb"`
     - Bash: `export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/appdb"`

3. **Run the app**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

Open: `http://localhost:8000`

## Deploy on Railway (PostgreSQL)

1. Create a Railway project and add a **PostgreSQL** service.
2. Railway will inject `DATABASE_URL` automatically.
3. Set `SECRET_KEY` in Railway Variables.
4. Use this Start Command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

### Railway/Postgres compatibility

- The app automatically converts `postgres://...` to `postgresql+psycopg://...` for SQLAlchemy.
- The Postgres driver is included via `psycopg[binary]`.

## Notes

- Column and table names are normalized to safe SQL identifiers.
- If a later Excel file contains extra columns that do not exist in the table, upload is rejected.
