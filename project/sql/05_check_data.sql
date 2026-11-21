/* Step 3.5: Quick checks after loading. */
USE ManufacturingDowntime;
GO

SELECT 'Dim_Product' AS TableName, COUNT(*) AS Row_Count FROM dbo.Dim_Product
UNION ALL SELECT 'Dim_Operator',       COUNT(*) FROM dbo.Dim_Operator
UNION ALL SELECT 'Dim_DowntimeFactor', COUNT(*) FROM dbo.Dim_DowntimeFactor
UNION ALL SELECT 'Dim_Date',           COUNT(*) FROM dbo.Dim_Date
UNION ALL SELECT 'Fact_Batch',         COUNT(*) FROM dbo.Fact_Batch
UNION ALL SELECT 'Fact_Downtime',      COUNT(*) FROM dbo.Fact_Downtime;

-- Total downtime in Fact_Batch must match the detail rows in Fact_Downtime.
SELECT
    (SELECT SUM(Total_Downtime_Min) FROM dbo.Fact_Batch)    AS Batch_Total,
    (SELECT SUM(Downtime_Minutes)   FROM dbo.Fact_Downtime) AS Downtime_Total;

-- Relationships created.
SELECT name AS ForeignKey,
       OBJECT_NAME(parent_object_id)     AS FromTable,
       OBJECT_NAME(referenced_object_id) AS ToTable
FROM sys.foreign_keys
ORDER BY FromTable, ToTable;
GO
