"""
Step 2: Clean the split tables and prepare them for SQL Server.

Reads the 6 CSVs in data/split/, then for every table:
  - explores it (shape, data types, missing values, duplicates)
  - cleans text (extra spaces / characters, consistent values)
  - checks numbers (no negative or impossible values)
  - handles missing values
  - sets the data types from the schema
Then it calculates the derived columns, checks that every key in the
fact tables exists in its dimension, and writes the clean CSVs to
data/clean/.

Run from the project folder:  python scripts/02_clean_data.py
"""

from pathlib import Path
import re

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
IN_DIR = BASE_DIR / "data" / "split"
OUT_DIR = BASE_DIR / "data" / "clean"

TABLES = ["Dim_Product", "Dim_Operator", "Dim_DowntimeFactor", "Dim_Date",
          "Fact_Batch", "Fact_Downtime"]

PRIMARY_KEYS = {
    "Dim_Product": "ProductID",
    "Dim_Operator": "OperatorID",
    "Dim_DowntimeFactor": "FactorID",
    "Dim_Date": "DateKey",
    "Fact_Batch": "BatchID",
    "Fact_Downtime": "DowntimeID",
}


# ---------------------------------------------------------------- helpers
def explore(name, df):
    print(f"\n=== {name} ===")
    print(f"shape: {df.shape[0]} rows x {df.shape[1]} columns")
    print("data types:", dict(df.dtypes.astype(str)))
    missing = df.isna().sum()
    print("missing values:", dict(missing[missing > 0]) or "none")
    print("duplicate rows:", int(df.duplicated().sum()))


def clean_text(df):
    """Trim spaces, collapse repeated spaces and drop stray characters."""
    text_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c])]
    for col in text_cols:
        df[col] = (
            df[col].astype(str)
            .str.replace(r"[^\w\s\-:./]", "", regex=True)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .replace({"nan": pd.NA, "": pd.NA})
        )
    return df


def drop_duplicates(name, df):
    before = len(df)
    df = df.drop_duplicates()
    key = PRIMARY_KEYS[name]
    df = df.drop_duplicates(subset=key, keep="first")
    if len(df) != before:
        print(f"removed {before - len(df)} duplicate rows")
    return df


def check_not_negative(df, cols):
    for col in cols:
        bad = df[df[col] < 0]
        if not bad.empty:
            raise ValueError(f"{col} has negative values:\n{bad}")


def parse_time(value):
    """Return the time part of values like '14:05:00' or '1900-01-01 01:05:00'."""
    text = str(value).strip()
    match = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?$", text)
    if not match:
        raise ValueError(f"Unreadable time: {value!r}")
    h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
    return pd.Timestamp(year=1900, month=1, day=1, hour=h, minute=m, second=s).time()


def size_to_ml(size):
    """'600 ml' -> 600, '2 L' -> 2000."""
    match = re.match(r"([\d.]+)\s*(ml|l)$", str(size).strip().lower())
    if not match:
        raise ValueError(f"Unreadable size: {size!r}")
    number, unit = float(match.group(1)), match.group(2)
    return int(number * 1000) if unit == "l" else int(number)


def standard_yes_no(series):
    mapping = {"yes": "Yes", "y": "Yes", "no": "No", "n": "No"}
    return series.str.lower().map(mapping)


# ---------------------------------------------------------------- tables
def clean_dim_product(df):
    df["ProductID"] = df["ProductID"].str.upper()
    df["Flavor"] = df["Flavor"].str.title()
    # Source data spells this flavor "Root Berry"; the product is root beer.
    df["Flavor"] = df["Flavor"].replace({"Root Berry": "Root Beer"})
    # Consistent size text: "600 ml", "2 L".
    df["Size"] = df["Size"].str.replace(
        r"(?i)^([\d.]+)\s*(ml|l)$",
        lambda m: f"{m.group(1)} {'ml' if m.group(2).lower() == 'ml' else 'L'}",
        regex=True,
    )
    df["Size_ml"] = df["Size"].apply(size_to_ml).astype(int)
    df["Min_Batch_Time"] = pd.to_numeric(df["Min_Batch_Time"], errors="raise").astype(int)
    check_not_negative(df, ["Size_ml", "Min_Batch_Time"])
    return df


def clean_dim_operator(df):
    df["OperatorID"] = df["OperatorID"].astype(int)
    df["Operator_Name"] = df["Operator_Name"].str.title()
    df["Shift"] = df["Shift"].str.title()
    return df


def clean_dim_factor(df):
    df["FactorID"] = df["FactorID"].astype(int)
    df["Operator_Error"] = standard_yes_no(df["Operator_Error"])
    if df["Operator_Error"].isna().any():
        raise ValueError("Operator_Error has values other than Yes/No")
    return df


def clean_dim_date(df):
    df["DateKey"] = df["DateKey"].astype(int)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    for col in ["Week", "Month", "Year"]:
        df[col] = df[col].astype(int)
    return df


def clean_fact_batch(df, dim_product, fact_downtime):
    df["BatchID"] = df["BatchID"].astype(int)
    df["ProductID"] = df["ProductID"].str.upper()
    df["OperatorID"] = df["OperatorID"].astype(int)
    df["DateKey"] = df["DateKey"].astype(int)
    df["Start_Time"] = df["Start_Time"].apply(parse_time)
    df["End_Time"] = df["End_Time"].apply(parse_time)

    # Batch duration in minutes; a batch ending after midnight gets +24 h.
    start = df["Start_Time"].apply(lambda t: t.hour * 60 + t.minute)
    end = df["End_Time"].apply(lambda t: t.hour * 60 + t.minute)
    duration = end - start
    duration[duration < 0] += 24 * 60
    df["Batch_Duration_Min"] = duration.astype(int)

    totals = fact_downtime.groupby("BatchID")["Downtime_Minutes"].sum()
    df["Total_Downtime_Min"] = df["BatchID"].map(totals).fillna(0).astype(int)

    min_time = df["ProductID"].map(dim_product.set_index("ProductID")["Min_Batch_Time"])
    df["Efficiency_Pct"] = (min_time / df["Batch_Duration_Min"] * 100).round(2)

    check_not_negative(df, ["Batch_Duration_Min", "Total_Downtime_Min"])
    if (df["Batch_Duration_Min"] == 0).any():
        raise ValueError("Some batches have a duration of 0 minutes")
    return df


def clean_fact_downtime(df):
    df["DowntimeID"] = df["DowntimeID"].astype(int)
    df["BatchID"] = df["BatchID"].astype(int)
    df["FactorID"] = pd.to_numeric(df["FactorID"], errors="raise").astype(int)
    # An empty cell in the source sheet means no downtime for that factor.
    df["Downtime_Minutes"] = pd.to_numeric(df["Downtime_Minutes"], errors="coerce").fillna(0)
    df = df[df["Downtime_Minutes"] > 0].copy()
    df["Downtime_Minutes"] = df["Downtime_Minutes"].round().astype(int)
    check_not_negative(df, ["Downtime_Minutes"])
    return df


def check_keys(child, child_name, col, parent, parent_name):
    missing = set(child[col]) - set(parent[col])
    if missing:
        raise ValueError(f"{child_name}.{col} has values not in {parent_name}: {sorted(missing)}")
    print(f"OK  {child_name}.{col} -> {parent_name}.{col}")


# ---------------------------------------------------------------- main
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data = {}
    for name in TABLES:
        df = pd.read_csv(IN_DIR / f"{name}.csv", dtype=str)
        explore(name, df)
        df = clean_text(df)
        df = drop_duplicates(name, df)
        data[name] = df

    data["Dim_Product"] = clean_dim_product(data["Dim_Product"])
    data["Dim_Operator"] = clean_dim_operator(data["Dim_Operator"])
    data["Dim_DowntimeFactor"] = clean_dim_factor(data["Dim_DowntimeFactor"])
    data["Dim_Date"] = clean_dim_date(data["Dim_Date"])
    data["Fact_Downtime"] = clean_fact_downtime(data["Fact_Downtime"])
    data["Fact_Batch"] = clean_fact_batch(
        data["Fact_Batch"], data["Dim_Product"], data["Fact_Downtime"]
    )

    print("\n=== Key checks ===")
    check_keys(data["Fact_Batch"], "Fact_Batch", "ProductID", data["Dim_Product"], "Dim_Product")
    check_keys(data["Fact_Batch"], "Fact_Batch", "OperatorID", data["Dim_Operator"], "Dim_Operator")
    check_keys(data["Fact_Batch"], "Fact_Batch", "DateKey", data["Dim_Date"], "Dim_Date")
    check_keys(data["Fact_Downtime"], "Fact_Downtime", "BatchID", data["Fact_Batch"], "Fact_Batch")
    check_keys(data["Fact_Downtime"], "Fact_Downtime", "FactorID",
               data["Dim_DowntimeFactor"], "Dim_DowntimeFactor")

    print("\n=== Missing values after cleaning ===")
    for name, df in data.items():
        n = int(df.isna().sum().sum())
        if n:
            raise ValueError(f"{name} still has {n} missing values")
        print(f"OK  {name}: none")

    print("\n=== Output ===")
    for name, df in data.items():
        path = OUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"{name:<20} {len(df):>4} rows -> {path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
