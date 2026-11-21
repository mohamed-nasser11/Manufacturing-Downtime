# Manufacturing Downtime

> **"Why does the plant stop, and when might it stop again?"**

## Project Description

Unplanned downtime is one of the most costly problems in manufacturing. Every hour a production line stands still means lost output, idle resources, and missed delivery targets.

This project is an end-to-end data analytics project that analyzes historical manufacturing and downtime data to uncover **why production lines stop**, and forecasts the **expected downtime for the next day of operation**. Based on that forecast, it estimates the **number of production batches** the plant can deliver, giving management a realistic, data-driven view of the next day's production capacity.

The project goes beyond reporting past stoppages: its key outcome is a forward-looking forecast of next-day downtime and the expected batch output that follows from it.

The work is built with **SQL** and **Python** (pandas, scikit-learn, Matplotlib), and the insights are presented in an interactive **Power BI** dashboard.

## Project Roadmap

| Phase | Objective | Tools | Deliverables |
|:-----:|-----------|-------|--------------|
| **1. Data Modeling & Preprocessing** | Build a data model, then clean and preprocess the data. | SQL, Python (pandas, Matplotlib) | Cleaned dataset ready for analysis · Data preprocessing notebook |
| **2. Exploratory Analysis** | Define all possible analysis questions that can be deduced from the dataset and are of interest to the organization's decision makers. | SQL, Python (pandas, Matplotlib) | Set of analysis questions answerable via the dataset |
| **3. Forecasting** | Define and answer forecasting questions using the trends in the dataset, including the prediction of next-day downtime and, accordingly, the number of batches to be produced. | Python (scikit-learn, pandas, Matplotlib) | Visualization plots answering the forecasting questions |
| **4. Dashboard & Reporting** | Build a dashboard that visualizes the answers to all questions, and prepare a report and presentation covering data analysis, model development, and deployment. | SQL, Python (pandas, Matplotlib), Power BI | Power BI dashboard · Final report and presentation |

## How to Run

**1. Python (split and clean the data)**

```bash
cd project
pip install -r requirements.txt
python scripts/01_split_data.py         # Excel -> 6 CSVs in data/split
python scripts/02_clean_data.py         # cleaned CSVs in data/clean
python scripts/03_build_sql_inserts.py  # rebuilds sql/03_insert_data.sql
python scripts/04_forecast.py           # next-day forecast + sql/07_forecast_table.sql
```

Notebooks (open from `project/notebooks`): `01_exploratory_analysis.ipynb` (charts and analysis) and `02_forecast.ipynb` (forecast results).

**2. SQL Server (in SSMS, connected to `localhost`)**

Open and execute the files in `project/sql` in order:

| Script | What it does |
|--------|--------------|
| `01_create_database.sql` | Creates the `ManufacturingDowntime` database |
| `02_create_tables.sql` | Creates the 6 star schema tables |
| `03_insert_data.sql` | Loads the clean data |
| `04_create_relationships.sql` | Adds the one-to-many relationships |
| `05_check_data.sql` | Checks row counts, totals and relationships |
| `06_analysis_questions.sql` | Answers the analysis questions |
| `07_forecast_table.sql` | Loads the next-day forecast table |
