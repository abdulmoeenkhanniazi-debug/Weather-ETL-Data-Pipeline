🌦️ End-to-End Weather ETL Data PipelineThis is an end-to-end Data Engineering project that ingests real-time weather and air quality (AQI) data from an external API, stores it in a raw relational database, transforms it using SQL, and loads it into a Star Schema Data Warehouse. The finalized data is then visualized using Power BI.🏗️ System ArchitectureThe pipeline follows the industry-standard Medallion/Stage-Warehouse Architecture:[ Weather API ] 
       │ (Python Ingestion)
       ▼
[ OLTP Database: niazi ] ──► (dbo.raw_weather_logs)
       │ 
       ▼ (SQL Stored Procedure - ETL)
[ Data Warehouse: niazi_dw ]
 ├── dim_city (Dimension Table)
 ├── dim_date (Dimension Table)
 └── fact_weather (Fact Table)
       │
       ▼ (Import Connection)
[ Power BI Dashboard ]
📁 Repository Structure & Codes1. Data Ingestion Pipeline (weather_pipeline.py)This Python script connects to the WeatherAPI, fetches live data for multiple cities, performs connection handling with SQL Server using Windows Authentication, and inserts raw logs into the staging database.Pythonimport pyodbc
import requests

API_KEY = "YOUR_API_KEY"
CITIES = ["Lahore", "Karachi", "Islamabad", "London"]

# SQL Server Connection
conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=YOUR_SERVER_NAME;" 
    "Database=niazi;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("Database connection successful!")

    for city in CITIES:
        url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={city}&aqi=yes"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            city_name = data['location']['name']
            country = data['location']['country']
            
            # Convert Celsius to Kelvin
            temp_kelvin = data['current']['temp_c'] + 273.15
            humidity = data['current']['humidity']
            
            # Convert wind speed km/h to m/s
            wind_ms = round(data['current']['wind_kph'] / 3.6, 2)
            aqi_index = data['current']['air_quality']['us-epa-index']
            
            insert_query = """
                INSERT INTO raw_weather_logs (city_name, country, temperature_kelvin, humidity, wind_speed, aqi_index)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (city_name, country, temp_kelvin, humidity, wind_ms, aqi_index))
            print(f"Successfully fetched and saved raw data for {city_name}!")
            
    conn.commit()
    cursor.close()
    conn.close()
    print("ETL Step 1 (Ingestion) Completed!")
except Exception as e:
    print(f"Error: {e}")
2. Data Warehouse Schema (niazi_dw)The warehouse is modeled using a Star Schema to optimize query performance and reporting.dim_city: Stores unique location attributes.dim_date: Contains pre-calculated calendar dates, years, quarters, and months.fact_weather: Stores measures (metrics) and links dimensions using foreign keys.SQL-- Create Dimension Tables
CREATE TABLE dim_city (
    city_key INT IDENTITY(1,1) PRIMARY KEY,
    city_name VARCHAR(100),
    country VARCHAR(100)
);

CREATE TABLE dim_date (
    date_key INT PRIMARY KEY, -- Format: YYYYMMDD
    full_date DATE,
    year INT,
    quarter INT,
    month_number INT,
    month_name VARCHAR(20)
);

-- Create Fact Table
CREATE TABLE fact_weather (
    fact_key INT IDENTITY(1,1) PRIMARY KEY,
    city_key INT FOREIGN KEY REFERENCES dim_city(city_key),
    date_key INT FOREIGN KEY REFERENCES dim_date(date_key),
    temperature_celsius DECIMAL(5,2),
    humidity INT,
    aqi_index INT,
    aqi_desc VARCHAR(20),
    wind_speed_kmh DECIMAL(5,2)
);
3. Transformation & Load Logic (Stored Procedure)The ETL process is encapsulated in a SQL Stored Procedure (sp_run_weather_etl). It cleans, transforms, loads the data, and ensures Idempotency (preventing duplicates).Key Transformations Applied:Temperature Conversion: Converts Kelvin back to Celsius:$$\text{Celsius} = \text{Kelvin} - 273.15$$Wind Speed Conversion: Converts meters/second back to kilometers/hour:$$\text{km/h} = \text{m/s} \times 3.6$$Categorization: Maps AQI numeric codes (1–6) to meaningful human-readable categories (Good, Fair, Moderate, Poor, etc.).SQLCREATE PROCEDURE sp_run_weather_etl
AS
BEGIN
    SET NOCOUNT ON;

    -- 1. Populate dim_city with new cities
    INSERT INTO dim_city (city_name, country)
    SELECT DISTINCT raw.city_name, raw.country
    FROM niazi.dbo.raw_weather_logs raw
    LEFT JOIN dim_city dim 
        ON raw.city_name = dim.city_name AND raw.country = dim.country
    WHERE dim.city_key IS NULL;

    -- 2. Transform and Load Fact Table
    INSERT INTO fact_weather (city_key, date_key, temperature_celsius, humidity, aqi_index, aqi_desc, wind_speed_kmh)
    SELECT 
        c.city_key,
        CAST(FORMAT(raw.fetched_at, 'yyyyMMdd') AS INT) AS date_key,
        ROUND(raw.temperature_kelvin - 273.15, 2) AS temperature_celsius,
        raw.humidity,
        raw.aqi_index,
        CASE raw.aqi_index
            WHEN 1 THEN 'Good'
            WHEN 2 THEN 'Fair'
            WHEN 3 THEN 'Moderate'
            WHEN 4 THEN 'Poor'
            WHEN 5 THEN 'Very Poor'
            ELSE 'Unknown'
        END AS aqi_desc,
        ROUND(raw.wind_speed * 3.6, 2) AS wind_speed_kmh
    FROM niazi.dbo.raw_weather_logs raw
    INNER JOIN dim_city c ON raw.city_name = c.city_name AND raw.country = c.country
    LEFT JOIN fact_weather fact ON c.city_key = fact.city_key AND CAST(FORMAT(raw.fetched_at, 'yyyyMMdd') AS INT) = fact.date_key
    WHERE fact.fact_key IS NULL;

    -- 3. Truncate staging table for next run
    TRUNCATE TABLE niazi.dbo.raw_weather_logs;

    PRINT 'ETL Pipeline successfully completed!';
END;
📊 Power BI VisualizationWe connect Power BI to niazi_dw using the Import Mode to load tables: dim_city, dim_date, and fact_weather.Data Modeling: Established a 1:N (One-to-Many) relationship between Dimension tables (dim_city, dim_date) and the Fact table (fact_weather).Dashboard Visuals:KPI Cards: Showing current temperature and AQI description for selected cities.Gauge Charts: Visualizing temperature ranges.Clustered Column Charts: Comparing wind speeds and humidity levels across cities.# Weather-ETL-Data-Pipeline
End-to-End Weather ETL Pipeline using Python, SQL Server.
