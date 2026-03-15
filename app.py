import logging
import os
import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from dotenv import load_dotenv

import pandas as pd

load_dotenv()
from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.exc import SQLAlchemyError


def build_database_url() -> str:
    """Always use SQLite (app.db in project folder). DATABASE_URL is ignored."""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "app.db").replace("\\", "/")
    return f"sqlite:///{path}"


def database_label(database_url: str) -> str:
    parsed = urlparse(database_url)
    scheme = parsed.scheme
    if scheme.startswith("postgresql"):
        return "PostgreSQL"
    if scheme.startswith("sqlite"):
        return "SQLite"
    return scheme or "Unknown"


DATABASE_URL = build_database_url()
DATABASE_LABEL = database_label(DATABASE_URL)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret")

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


def normalize_identifier(name: str, fallback: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", str(name).strip().lower())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or fallback


def normalize_table_name(name: str) -> str:
    return normalize_identifier(name, fallback="uploaded_data")


def normalize_columns(columns: List[str]) -> Tuple[List[str], Dict[str, str]]:
    normalized = []
    mapping: Dict[str, str] = {}
    seen = set()

    for index, column_name in enumerate(columns, start=1):
        base_name = normalize_identifier(column_name, fallback=f"column_{index}")
        candidate = base_name
        suffix = 2
        while candidate in seen:
            candidate = f"{base_name}_{suffix}"
            suffix += 1

        seen.add(candidate)
        normalized.append(candidate)
        mapping[str(column_name)] = candidate

    return normalized, mapping


def infer_sqlalchemy_type(series: pd.Series):
    if pd.api.types.is_bool_dtype(series):
        return Boolean
    if pd.api.types.is_integer_dtype(series):
        return BigInteger
    if pd.api.types.is_float_dtype(series):
        return Float
    if pd.api.types.is_datetime64_any_dtype(series):
        return DateTime
    return Text


def sanitize_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    cleaned = df.dropna(how="all").copy()
    if cleaned.empty:
        raise ValueError("The uploaded Excel file has no data rows.")

    cleaned.columns, column_mapping = normalize_columns([str(col) for col in cleaned.columns])
    cleaned = cleaned.dropna(axis=1, how="all")
    if cleaned.empty:
        raise ValueError("The uploaded Excel file has no usable columns.")

    return cleaned, column_mapping


def create_table_from_dataframe(engine, table_name: str, df: pd.DataFrame) -> Table:
    metadata = MetaData()
    columns = [Column("id", Integer, primary_key=True, autoincrement=True)]
    for column_name in df.columns:
        columns.append(Column(column_name, infer_sqlalchemy_type(df[column_name]), nullable=True))

    table = Table(table_name, metadata, *columns)
    metadata.create_all(engine, tables=[table])
    return table


def prepare_for_existing_table(df: pd.DataFrame, table: Table) -> pd.DataFrame:
    table_columns = [column.name for column in table.columns if column.name != "id"]
    dataframe_columns = set(df.columns)

    extra_columns = dataframe_columns - set(table_columns)
    if extra_columns:
        extra = ", ".join(sorted(extra_columns))
        raise ValueError(
            f"Uploaded file contains columns that are not in table '{table.name}': {extra}."
        )

    for missing_column in table_columns:
        if missing_column not in df.columns:
            df[missing_column] = None

    return df[table_columns]


def dataframe_to_records(df: pd.DataFrame) -> List[Dict[str, object]]:
    records = []
    for raw_record in df.to_dict(orient="records"):
        normalized_record = {}
        for key, value in raw_record.items():
            if pd.isna(value):
                normalized_record[key] = None
            elif isinstance(value, pd.Timestamp):
                normalized_record[key] = value.to_pydatetime()
            else:
                normalized_record[key] = value
        records.append(normalized_record)
    return records


@app.get("/")
def index():
    error_from_query = request.args.get("error")
    success_from_query = request.args.get("success")
    return render_template(
        "index.html",
        database_label=DATABASE_LABEL,
        error_from_query=error_from_query,
        success_from_query=success_from_query,
    )


@app.get("/tables")
def tables():
    """List tables in the database and their row counts (for debugging)."""
    try:
        engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        rows = []
        with engine.connect() as conn:
            for name in table_names:
                if name.startswith("sqlite_"):
                    continue
                try:
                    r = conn.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar()
                    rows.append((name, r))
                except Exception:
                    rows.append((name, None))
        return render_template("tables.html", database_label=DATABASE_LABEL, tables=rows, database_url=DATABASE_URL)
    except Exception as e:
        logger.exception("Failed to list tables")
        return f"Error: {e}", 500


def _safe_query_msg(msg: str, max_len: int = 200) -> str:
    """Shorten message for URL query string to avoid truncation."""
    msg = str(msg).replace("&", " ").replace("=", " ").replace("?", " ")[:max_len]
    return msg


@app.post("/upload")
def upload():
    # Log immediately so we see if the request reaches this server
    logger.info("POST /upload received: form_keys=%s, files=%s", list(request.form.keys()), list(request.files.keys()))

    uploaded_file = request.files.get("excel_file")
    table_name_input = request.form.get("table_name", "")
    table_name = normalize_table_name(table_name_input)

    logger.info("Upload attempt: file=%s, table_name=%s", uploaded_file.filename if uploaded_file else None, table_name)

    if uploaded_file is None or uploaded_file.filename == "":
        flash("Please choose an Excel file before uploading.", "error")
        return redirect(url_for("index", error=_safe_query_msg("No file selected")))

    if not uploaded_file.filename.lower().endswith((".xlsx", ".xls", ".xlsm")):
        flash("Unsupported file type. Please upload an Excel file.", "error")
        return redirect(url_for("index", error=_safe_query_msg("Unsupported file type")))

    try:
        dataframe = pd.read_excel(uploaded_file)
        dataframe, _ = sanitize_dataframe(dataframe)

        engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
        inspector = inspect(engine)
        created_new_table = False

        if not inspector.has_table(table_name):
            table = create_table_from_dataframe(engine, table_name, dataframe)
            created_new_table = True
        else:
            metadata = MetaData()
            table = Table(table_name, metadata, autoload_with=engine)
            dataframe = prepare_for_existing_table(dataframe, table)

        records = dataframe_to_records(dataframe)
        if not records:
            raise ValueError("No rows to insert after processing the file.")

        with engine.begin() as connection:
            connection.execute(table.insert(), records)

        logger.info("Inserted %d rows into table '%s'", len(records), table_name)
        success_msg = f"Created table '{table_name}' and inserted {len(records)} rows." if created_new_table else f"Inserted {len(records)} rows into '{table_name}'."
        flash(success_msg, "success")
        return redirect(url_for("index", success=_safe_query_msg(success_msg)))

    except ValueError as error:
        logger.warning("Upload ValueError: %s", error)
        flash(str(error), "error")
        return redirect(url_for("index", error=_safe_query_msg(str(error))))
    except SQLAlchemyError as error:
        logger.exception("Upload SQLAlchemyError")
        flash(f"Database error: {error}", "error")
        return redirect(url_for("index", error=_safe_query_msg(str(error))))
    except Exception as error:  # noqa: BLE001
        logger.exception("Upload failed")
        flash(f"Failed to process file: {error}", "error")
        return redirect(url_for("index", error=_safe_query_msg(str(error))))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
