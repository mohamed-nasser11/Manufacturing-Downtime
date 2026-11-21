"""
Step 3 helper: turn the clean CSVs into an INSERT script for SQL Server.

Reads data/clean/*.csv and writes sql/03_insert_data.sql, so the data can
be loaded by running one script in SSMS (no file paths or import wizard).

Run from the project folder:  python scripts/03_build_sql_inserts.py
"""

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
IN_DIR = BASE_DIR / "data" / "clean"
OUT_FILE = BASE_DIR / "sql" / "03_insert_data.sql"

# Load order: dimensions first, then facts.
TABLES = ["Dim_Product", "Dim_Operator", "Dim_DowntimeFactor", "Dim_Date",
          "Fact_Batch", "Fact_Downtime"]

TEXT_COLUMNS = {"ProductID", "Flavor", "Size", "Operator_Name", "Shift",
                "Description", "Operator_Error", "Factor_Category",
                "Date", "Day_Name", "Start_Time", "End_Time"}

RESERVED = {"Date", "Week", "Month", "Year"}


def sql_value(col, value):
    if col in TEXT_COLUMNS:
        return "'" + str(value).replace("'", "''") + "'"
    return str(value)


def main():
    lines = [
        "/* Step 3.3: Load the clean data (generated from data/clean by",
        "   scripts/03_build_sql_inserts.py). */",
        "USE ManufacturingDowntime;",
        "GO",
        "",
    ]
    for name in TABLES:
        df = pd.read_csv(IN_DIR / f"{name}.csv", dtype=str)
        cols = ", ".join(f"[{c}]" if c in RESERVED else c for c in df.columns)
        lines.append(f"-- {name}: {len(df)} rows")
        lines.append(f"INSERT INTO dbo.{name} ({cols}) VALUES")
        rows = []
        for _, row in df.iterrows():
            values = ", ".join(sql_value(c, row[c]) for c in df.columns)
            rows.append(f"    ({values})")
        lines.append(",\n".join(rows) + ";")
        lines.append("")
    lines.append("GO")

    OUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
