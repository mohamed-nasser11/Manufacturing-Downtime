/* Step 3.2: Create the 6 star schema tables with their primary keys.
   Re-running this script drops and recreates the tables. */
USE ManufacturingDowntime;
GO

IF OBJECT_ID('dbo.Fact_Downtime', 'U')      IS NOT NULL DROP TABLE dbo.Fact_Downtime;
IF OBJECT_ID('dbo.Fact_Batch', 'U')         IS NOT NULL DROP TABLE dbo.Fact_Batch;
IF OBJECT_ID('dbo.Dim_Product', 'U')        IS NOT NULL DROP TABLE dbo.Dim_Product;
IF OBJECT_ID('dbo.Dim_Operator', 'U')       IS NOT NULL DROP TABLE dbo.Dim_Operator;
IF OBJECT_ID('dbo.Dim_DowntimeFactor', 'U') IS NOT NULL DROP TABLE dbo.Dim_DowntimeFactor;
IF OBJECT_ID('dbo.Dim_Date', 'U')           IS NOT NULL DROP TABLE dbo.Dim_Date;
GO

CREATE TABLE dbo.Dim_Product (
    ProductID       VARCHAR(10)  NOT NULL PRIMARY KEY,
    Flavor          VARCHAR(50)  NOT NULL,
    Size            VARCHAR(10)  NOT NULL,
    Size_ml         INT          NOT NULL,
    Min_Batch_Time  INT          NOT NULL
);

CREATE TABLE dbo.Dim_Operator (
    OperatorID      INT          NOT NULL PRIMARY KEY,
    Operator_Name   VARCHAR(50)  NOT NULL,
    Shift           VARCHAR(10)  NOT NULL
);

CREATE TABLE dbo.Dim_DowntimeFactor (
    FactorID        INT          NOT NULL PRIMARY KEY,
    Description     VARCHAR(50)  NOT NULL,
    Operator_Error  VARCHAR(3)   NOT NULL,
    Factor_Category VARCHAR(20)  NOT NULL
);

CREATE TABLE dbo.Dim_Date (
    DateKey         INT          NOT NULL PRIMARY KEY,
    [Date]          DATE         NOT NULL,
    Day_Name        VARCHAR(10)  NOT NULL,
    [Week]          INT          NOT NULL,
    [Month]         INT          NOT NULL,
    [Year]          INT          NOT NULL
);

CREATE TABLE dbo.Fact_Batch (
    BatchID             INT          NOT NULL PRIMARY KEY,
    ProductID           VARCHAR(10)  NOT NULL,
    OperatorID          INT          NOT NULL,
    DateKey             INT          NOT NULL,
    Start_Time          TIME(0)      NOT NULL,
    End_Time            TIME(0)      NOT NULL,
    Batch_Duration_Min  INT          NOT NULL,
    Total_Downtime_Min  INT          NOT NULL,
    Efficiency_Pct      DECIMAL(5,2) NOT NULL
);

CREATE TABLE dbo.Fact_Downtime (
    DowntimeID          INT          NOT NULL PRIMARY KEY,
    BatchID             INT          NOT NULL,
    FactorID            INT          NOT NULL,
    Downtime_Minutes    INT          NOT NULL
);
GO
