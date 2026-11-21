/* Step 3.4: One-to-many relationships, exactly as in the schema. */
USE ManufacturingDowntime;
GO

ALTER TABLE dbo.Fact_Batch ADD CONSTRAINT FK_FactBatch_Product
    FOREIGN KEY (ProductID) REFERENCES dbo.Dim_Product (ProductID);

ALTER TABLE dbo.Fact_Batch ADD CONSTRAINT FK_FactBatch_Operator
    FOREIGN KEY (OperatorID) REFERENCES dbo.Dim_Operator (OperatorID);

ALTER TABLE dbo.Fact_Batch ADD CONSTRAINT FK_FactBatch_Date
    FOREIGN KEY (DateKey) REFERENCES dbo.Dim_Date (DateKey);

ALTER TABLE dbo.Fact_Downtime ADD CONSTRAINT FK_FactDowntime_Batch
    FOREIGN KEY (BatchID) REFERENCES dbo.Fact_Batch (BatchID);

ALTER TABLE dbo.Fact_Downtime ADD CONSTRAINT FK_FactDowntime_Factor
    FOREIGN KEY (FactorID) REFERENCES dbo.Dim_DowntimeFactor (FactorID);
GO
