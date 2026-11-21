/* Step 3.6: Business questions answered from the star schema. */
USE ManufacturingDowntime;
GO

/* Q1. What is total downtime, and what share of production time is it? */
SELECT
    COUNT(*)                                   AS Batches,
    SUM(Batch_Duration_Min)                    AS Production_Min,
    SUM(Total_Downtime_Min)                    AS Downtime_Min,
    CAST(100.0 * SUM(Total_Downtime_Min)
         / SUM(Batch_Duration_Min) AS DECIMAL(5,2)) AS Downtime_Pct,
    CAST(AVG(Efficiency_Pct) AS DECIMAL(5,2))  AS Avg_Efficiency_Pct
FROM dbo.Fact_Batch;

/* Q2. Which factors cause the most lost minutes? (Pareto) */
WITH by_factor AS (
    SELECT f.Description, f.Factor_Category,
           SUM(d.Downtime_Minutes) AS Downtime_Min,
           COUNT(*)                AS Occurrences
    FROM dbo.Fact_Downtime d
    JOIN dbo.Dim_DowntimeFactor f ON f.FactorID = d.FactorID
    GROUP BY f.Description, f.Factor_Category
)
SELECT Description, Factor_Category, Occurrences, Downtime_Min,
       CAST(100.0 * Downtime_Min / SUM(Downtime_Min) OVER () AS DECIMAL(5,2)) AS Pct_Of_Total,
       CAST(100.0 * SUM(Downtime_Min) OVER (ORDER BY Downtime_Min DESC, Description
                                            ROWS UNBOUNDED PRECEDING)
            / SUM(Downtime_Min) OVER () AS DECIMAL(5,2))                    AS Cumulative_Pct
FROM by_factor
ORDER BY Downtime_Min DESC;

/* Q3. Is downtime driven more by operator error or by machines and materials? */
SELECT f.Factor_Category,
       SUM(d.Downtime_Minutes) AS Downtime_Min,
       CAST(100.0 * SUM(d.Downtime_Minutes)
            / SUM(SUM(d.Downtime_Minutes)) OVER () AS DECIMAL(5,2)) AS Pct_Of_Total
FROM dbo.Fact_Downtime d
JOIN dbo.Dim_DowntimeFactor f ON f.FactorID = d.FactorID
GROUP BY f.Factor_Category
ORDER BY Downtime_Min DESC;

/* Q4. What is each operator's efficiency and average downtime per batch? */
SELECT o.Operator_Name, o.Shift,
       COUNT(*)                                           AS Batches,
       SUM(b.Total_Downtime_Min)                          AS Downtime_Min,
       CAST(AVG(1.0 * b.Total_Downtime_Min) AS DECIMAL(6,2)) AS Avg_Downtime_Per_Batch,
       CAST(100.0 * SUM(p.Min_Batch_Time)
            / SUM(b.Batch_Duration_Min) AS DECIMAL(5,2))  AS Efficiency_Pct
FROM dbo.Fact_Batch b
JOIN dbo.Dim_Operator o ON o.OperatorID = b.OperatorID
JOIN dbo.Dim_Product  p ON p.ProductID  = b.ProductID
GROUP BY o.Operator_Name, o.Shift
ORDER BY Efficiency_Pct DESC;

/* Q5. Which operator errors does each operator make most? */
SELECT o.Operator_Name, f.Description,
       SUM(d.Downtime_Minutes) AS Downtime_Min
FROM dbo.Fact_Downtime d
JOIN dbo.Fact_Batch         b ON b.BatchID    = d.BatchID
JOIN dbo.Dim_Operator       o ON o.OperatorID = b.OperatorID
JOIN dbo.Dim_DowntimeFactor f ON f.FactorID   = d.FactorID
WHERE f.Operator_Error = 'Yes'
GROUP BY o.Operator_Name, f.Description
ORDER BY o.Operator_Name, Downtime_Min DESC;

/* Q6. Which products or sizes are least efficient? */
SELECT p.ProductID, p.Flavor, p.Size,
       COUNT(*)                  AS Batches,
       SUM(b.Total_Downtime_Min) AS Downtime_Min,
       CAST(100.0 * SUM(p.Min_Batch_Time)
            / SUM(b.Batch_Duration_Min) AS DECIMAL(5,2)) AS Efficiency_Pct
FROM dbo.Fact_Batch b
JOIN dbo.Dim_Product p ON p.ProductID = b.ProductID
GROUP BY p.ProductID, p.Flavor, p.Size
ORDER BY Efficiency_Pct;

/* Q7. Does downtime differ between shifts? */
SELECT o.Shift,
       COUNT(*)                                              AS Batches,
       SUM(b.Total_Downtime_Min)                             AS Downtime_Min,
       CAST(AVG(1.0 * b.Total_Downtime_Min) AS DECIMAL(6,2)) AS Avg_Downtime_Per_Batch
FROM dbo.Fact_Batch b
JOIN dbo.Dim_Operator o ON o.OperatorID = b.OperatorID
GROUP BY o.Shift
ORDER BY Avg_Downtime_Per_Batch DESC;

/* Q8. How does downtime change day to day? */
SELECT dt.[Date], dt.Day_Name,
       COUNT(*)                  AS Batches,
       SUM(b.Batch_Duration_Min) AS Production_Min,
       SUM(b.Total_Downtime_Min) AS Downtime_Min,
       CAST(100.0 * SUM(b.Total_Downtime_Min)
            / SUM(b.Batch_Duration_Min) AS DECIMAL(5,2)) AS Downtime_Pct
FROM dbo.Fact_Batch b
JOIN dbo.Dim_Date dt ON dt.DateKey = b.DateKey
GROUP BY dt.[Date], dt.Day_Name
ORDER BY dt.[Date];

/* Q9. Which batches had the most downtime, and why? */
SELECT TOP 5 b.BatchID, b.ProductID, o.Operator_Name,
       b.Total_Downtime_Min,
       STRING_AGG(f.Description + ' (' + CAST(d.Downtime_Minutes AS VARCHAR(5)) + ')', ', ')
           WITHIN GROUP (ORDER BY d.Downtime_Minutes DESC) AS Causes
FROM dbo.Fact_Batch b
JOIN dbo.Dim_Operator       o ON o.OperatorID = b.OperatorID
JOIN dbo.Fact_Downtime      d ON d.BatchID    = b.BatchID
JOIN dbo.Dim_DowntimeFactor f ON f.FactorID   = d.FactorID
GROUP BY b.BatchID, b.ProductID, o.Operator_Name, b.Total_Downtime_Min
ORDER BY b.Total_Downtime_Min DESC;

/* Q10. How many batches took at least 50% longer than their minimum batch time? */
SELECT COUNT(*) AS Batches_Over_150_Pct,
       CAST(100.0 * COUNT(*) / (SELECT COUNT(*) FROM dbo.Fact_Batch) AS DECIMAL(5,2)) AS Pct_Of_Batches
FROM dbo.Fact_Batch b
JOIN dbo.Dim_Product p ON p.ProductID = b.ProductID
WHERE b.Batch_Duration_Min >= 1.5 * p.Min_Batch_Time;
GO
