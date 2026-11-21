/* Step 3.1: Create the database (run once). */
IF DB_ID('ManufacturingDowntime') IS NULL
    CREATE DATABASE ManufacturingDowntime;
GO
