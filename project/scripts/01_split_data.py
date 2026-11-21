"""
Step 1: Split the Excel workbook into the star schema tables.

Reads data/raw/Manufacturing_Line_Productivity.xlsx and writes one CSV per
table to data/split/:

    Dim_Product, Dim_Operator, Dim_DowntimeFactor, Dim_Date,
    Fact_Batch, Fact_Downtime

Columns that do not exist in the workbook are generated here
(OperatorID, Shift, Factor_Category, Dim_Date columns, DowntimeID).
Derived columns (durations, totals, efficiency) are calculated in
step 2 after the data is cleaned.

Run from the project folder:  python scripts/01_split_data.py
"""

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_FILE = BASE_DIR / "data" / "raw" / "Manufacturing_Line_Productivity.xlsx"
OUT_DIR = BASE_DIR / "data" / "split"


def shift_from_time(t):
    """Morning 06:00-13:59, Evening 14:00-21:59, Night 22:00-05:59."""
    hour = t.hour
    if 6 <= hour < 14:
        return "Morning"
    if 14 <= hour < 22:
        return "Evening"
    return "Night"


def factor_category(row):
    """Group downtime factors into Human, Material, Machine or Other."""
    if str(row["Operator Error"]).strip().lower() == "yes":
        return "Human"
    description = str(row["Description"]).strip().lower()
    if description == "inventory shortage":
        return "Material"
    if description == "other":
        return "Other"
    return "Machine"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    productivity = pd.read_excel(RAW_FILE, sheet_name="Line productivity")
    products = pd.read_excel(RAW_FILE, sheet_name="Products")
    factors = pd.read_excel(RAW_FILE, sheet_name="Downtime factors")
    # Line downtime has a two-row header: the first row is a title,
    # the second row holds "Batch" and the factor IDs 1-12.
    downtime_wide = pd.read_excel(RAW_FILE, sheet_name="Line downtime", header=1)

    # ---------- Dim_Product ----------
    dim_product = products.rename(columns={
        "Product": "ProductID",
        "Min batch time": "Min_Batch_Time",
    })
    dim_product["Size_ml"] = dim_product["Size"]  # converted to a number in step 2
    dim_product = dim_product[["ProductID", "Flavor", "Size", "Size_ml", "Min_Batch_Time"]]

    # ---------- Dim_Operator ----------
    operators = productivity[["Operator", "Start Time"]].copy()
    operators["Operator"] = operators["Operator"].astype(str).str.strip()
    operators["Shift"] = operators["Start Time"].apply(shift_from_time)
    # Each operator gets the shift they work in most often.
    main_shift = (
        operators.groupby("Operator")["Shift"]
        .agg(lambda s: s.value_counts().idxmax())
        .reset_index()
        .sort_values("Operator")
        .reset_index(drop=True)
    )
    main_shift.insert(0, "OperatorID", range(1, len(main_shift) + 1))
    dim_operator = main_shift.rename(columns={"Operator": "Operator_Name"})

    # ---------- Dim_DowntimeFactor ----------
    dim_factor = factors.copy()
    dim_factor["Factor_Category"] = dim_factor.apply(factor_category, axis=1)
    dim_factor = dim_factor.rename(columns={
        "Factor": "FactorID",
        "Operator Error": "Operator_Error",
    })[["FactorID", "Description", "Operator_Error", "Factor_Category"]]

    # ---------- Dim_Date ----------
    dates = pd.to_datetime(productivity["Date"])
    all_dates = pd.date_range(dates.min(), dates.max(), freq="D")
    dim_date = pd.DataFrame({"Date": all_dates})
    dim_date["DateKey"] = dim_date["Date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["Day_Name"] = dim_date["Date"].dt.day_name()
    dim_date["Week"] = dim_date["Date"].dt.isocalendar().week.astype(int)
    dim_date["Month"] = dim_date["Date"].dt.month
    dim_date["Year"] = dim_date["Date"].dt.year
    dim_date["Date"] = dim_date["Date"].dt.date
    dim_date = dim_date[["DateKey", "Date", "Day_Name", "Week", "Month", "Year"]]

    # ---------- Fact_Batch ----------
    operator_ids = dict(zip(dim_operator["Operator_Name"], dim_operator["OperatorID"]))
    fact_batch = pd.DataFrame({
        "BatchID": productivity["Batch"],
        "ProductID": productivity["Product"],
        "OperatorID": productivity["Operator"].astype(str).str.strip().map(operator_ids),
        "DateKey": pd.to_datetime(productivity["Date"]).dt.strftime("%Y%m%d").astype(int),
        "Start_Time": productivity["Start Time"],
        "End_Time": productivity["End Time"],
    })

    # ---------- Fact_Downtime ----------
    downtime_wide = downtime_wide.rename(columns={downtime_wide.columns[0]: "Batch"})
    fact_downtime = downtime_wide.melt(
        id_vars="Batch", var_name="FactorID", value_name="Downtime_Minutes"
    )
    # Keep only the batch/factor pairs that actually had downtime.
    fact_downtime = fact_downtime.dropna(subset=["Downtime_Minutes"])
    fact_downtime = fact_downtime.rename(columns={"Batch": "BatchID"})
    fact_downtime = fact_downtime.sort_values(["BatchID", "FactorID"]).reset_index(drop=True)
    fact_downtime.insert(0, "DowntimeID", range(1, len(fact_downtime) + 1))

    tables = {
        "Dim_Product": dim_product,
        "Dim_Operator": dim_operator,
        "Dim_DowntimeFactor": dim_factor,
        "Dim_Date": dim_date,
        "Fact_Batch": fact_batch,
        "Fact_Downtime": fact_downtime,
    }
    for name, table in tables.items():
        path = OUT_DIR / f"{name}.csv"
        table.to_csv(path, index=False)
        print(f"{name:<20} {len(table):>4} rows -> {path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
