"""
Step 4: Forecast next-day downtime and the number of batches.

1. Expected downtime per batch is estimated from history in two ways:
     - Baseline: average downtime per batch for each product
     - Model:    linear regression on product, operator and shift
   Both, plus the plain overall average, are tested with leave-one-out
   cross-validation (every batch is predicted from all the others), and
   the method with the lowest error is used.
2. For each product:
       batches = available minutes / (min batch time + expected downtime)

Outputs
    data/forecast/model_comparison.csv
    data/forecast/next_day_forecast.csv
    reports/figures/06_forecast_batches.png
    sql/07_forecast_table.sql   (loads the forecast into SQL Server)

Run from the project folder:  python scripts/04_forecast.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

BASE_DIR = Path(__file__).resolve().parent.parent
DATA = BASE_DIR / "data" / "clean"
OUT_DIR = BASE_DIR / "data" / "forecast"
FIGURES = BASE_DIR / "reports" / "figures"
SQL_FILE = BASE_DIR / "sql" / "07_forecast_table.sql"

# Minutes the line can run tomorrow (24 hours). Change if the plant
# runs fewer hours.
AVAILABLE_MINUTES = 24 * 60

FEATURES = ["ProductID", "Operator_Name", "Shift"]
TARGET = "Total_Downtime_Min"


def load_batches():
    batch = pd.read_csv(DATA / "Fact_Batch.csv")
    product = pd.read_csv(DATA / "Dim_Product.csv")
    operator = pd.read_csv(DATA / "Dim_Operator.csv")
    date = pd.read_csv(DATA / "Dim_Date.csv", parse_dates=["Date"])
    df = (batch.merge(product, on="ProductID")
               .merge(operator, on="OperatorID")
               .merge(date, on="DateKey"))
    return df, product


def baseline_loo(df):
    """Leave-one-out predictions from the product average."""
    preds = []
    for i in df.index:
        rest = df.drop(index=i)
        same = rest[rest["ProductID"] == df.at[i, "ProductID"]]
        preds.append(same[TARGET].mean() if len(same) else rest[TARGET].mean())
    return np.array(preds)


def build_model():
    encode = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES),
    ])
    # Ridge = linear regression with a small penalty, stable on few rows.
    return make_pipeline(encode, Ridge(alpha=1.0))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    df, product = load_batches()
    y = df[TARGET]

    # ---------- 1. compare methods ----------
    overall_pred = np.array([y.drop(index=i).mean() for i in df.index])
    baseline_pred = baseline_loo(df)
    model_pred = cross_val_predict(build_model(), df[FEATURES], y, cv=LeaveOneOut())

    comparison = pd.DataFrame({
        "Method": ["Overall average", "Product average (baseline)",
                   "Regression (product + operator + shift)"],
        "MAE_Minutes": [mean_absolute_error(y, overall_pred),
                        mean_absolute_error(y, baseline_pred),
                        mean_absolute_error(y, model_pred)],
    }).round(2)
    comparison.to_csv(OUT_DIR / "model_comparison.csv", index=False)
    print("Leave-one-out error (mean absolute error, minutes per batch):")
    print(comparison.to_string(index=False))

    best = int(comparison["MAE_Minutes"].idxmin())
    method = comparison.loc[best, "Method"]
    print(f"\nUsing: {method}")

    # ---------- 2. expected downtime per product ----------
    if best == 0:
        expected = pd.Series(y.mean(), index=product["ProductID"])
    elif best == 2:
        model = build_model().fit(df[FEATURES], y)
        # Average the prediction over the operator/shift mix seen in history.
        mix = df[["Operator_Name", "Shift"]].drop_duplicates()
        rows = []
        for pid in product["ProductID"]:
            grid = mix.assign(ProductID=pid)
            rows.append((pid, model.predict(grid[FEATURES]).mean()))
        expected = pd.Series(dict(rows))
    else:
        expected = df.groupby("ProductID")[TARGET].mean()

    next_day = df["Date"].max() + pd.Timedelta(days=1)
    forecast = product[["ProductID", "Flavor", "Size", "Min_Batch_Time"]].copy()
    forecast.insert(0, "Forecast_Date", next_day.date())
    forecast["Expected_Downtime_Per_Batch"] = forecast["ProductID"].map(expected).round(1)
    forecast["Expected_Cycle_Min"] = (forecast["Min_Batch_Time"]
                                      + forecast["Expected_Downtime_Per_Batch"]).round(1)
    forecast["Available_Min"] = AVAILABLE_MINUTES
    forecast["Planned_Batches"] = np.floor(
        AVAILABLE_MINUTES / forecast["Expected_Cycle_Min"]).astype(int)
    forecast["Batches_If_No_Downtime"] = np.floor(
        AVAILABLE_MINUTES / forecast["Min_Batch_Time"]).astype(int)
    forecast["Expected_Downtime_Day"] = (forecast["Planned_Batches"]
                                         * forecast["Expected_Downtime_Per_Batch"]).round(0).astype(int)
    forecast["Method"] = method
    forecast.to_csv(OUT_DIR / "next_day_forecast.csv", index=False)
    print(f"\nForecast for {next_day.date()} ({AVAILABLE_MINUTES} available minutes):")
    print(forecast[["ProductID", "Expected_Downtime_Per_Batch", "Expected_Cycle_Min",
                    "Planned_Batches", "Batches_If_No_Downtime"]].to_string(index=False))

    # ---------- 3. chart ----------
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(forecast))
    ax.bar(x - 0.2, forecast["Batches_If_No_Downtime"], 0.4, color="#bcc9d6",
           label="If no downtime")
    ax.bar(x + 0.2, forecast["Planned_Batches"], 0.4, color="#1f4e79",
           label="Planned (expected downtime)")
    ax.set_xticks(x, forecast["ProductID"])
    ax.set_ylabel("Batches per day")
    ax.set_title(f"Next-day batch plan by product ({next_day:%d %b %Y}, 24 h)")
    ax.set_ylim(0, forecast["Batches_If_No_Downtime"].max() * 1.3)
    ax.legend(frameon=False, ncol=2, loc="upper center")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "06_forecast_batches.png", dpi=150)

    # ---------- 4. SQL script ----------
    def q(v):
        return "'" + str(v).replace("'", "''") + "'"
    values = ",\n".join(
        f"    ({q(r.Forecast_Date)}, {q(r.ProductID)}, {r.Expected_Downtime_Per_Batch}, "
        f"{r.Expected_Cycle_Min}, {r.Available_Min}, {r.Planned_Batches}, "
        f"{r.Batches_If_No_Downtime}, {r.Expected_Downtime_Day}, {q(r.Method)})"
        for r in forecast.itertuples()
    )
    SQL_FILE.write_text(f"""/* Step 4: Next-day forecast table (generated by scripts/04_forecast.py). */
USE ManufacturingDowntime;
GO

IF OBJECT_ID('dbo.Fact_Forecast', 'U') IS NOT NULL DROP TABLE dbo.Fact_Forecast;
GO

CREATE TABLE dbo.Fact_Forecast (
    Forecast_Date               DATE          NOT NULL,
    ProductID                   VARCHAR(10)   NOT NULL
        CONSTRAINT FK_FactForecast_Product REFERENCES dbo.Dim_Product (ProductID),
    Expected_Downtime_Per_Batch DECIMAL(6,1)  NOT NULL,
    Expected_Cycle_Min          DECIMAL(6,1)  NOT NULL,
    Available_Min               INT           NOT NULL,
    Planned_Batches             INT           NOT NULL,
    Batches_If_No_Downtime      INT           NOT NULL,
    Expected_Downtime_Day       INT           NOT NULL,
    Method                      VARCHAR(60)   NOT NULL,
    CONSTRAINT PK_FactForecast PRIMARY KEY (Forecast_Date, ProductID)
);

INSERT INTO dbo.Fact_Forecast (Forecast_Date, ProductID, Expected_Downtime_Per_Batch,
    Expected_Cycle_Min, Available_Min, Planned_Batches, Batches_If_No_Downtime,
    Expected_Downtime_Day, Method) VALUES
{values};
GO

SELECT * FROM dbo.Fact_Forecast ORDER BY ProductID;
GO
""", encoding="utf-8")
    print(f"\nWrote {SQL_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
