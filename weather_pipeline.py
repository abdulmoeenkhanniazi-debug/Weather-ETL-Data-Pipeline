import pyodbc
import requests

# 1. Apni details yahan dalein
API_KEY = "1c343ead8d244c60a5884847261407"
CITIES = ["Lahore", "Karachi", "Islamabad", "London"]

# 2. SQL Server (SSMS) Connection String
# Note: Windows Authentication ke liye 'Trusted_Connection=yes' use hota hai
conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-3NJT5DK\\SQLEXPRESS;"  # Agar server ka naam alag hai to localhost ki jagah wo likhein
    "Database=niazi;"    # Raw database ka naam
    "Trusted_Connection=yes;"
)

try:
    # SQL Server se connect karein
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("Database connection successful!")

    # Har city ke liye loop chalayein aur data fetch karein
    for city in CITIES:
        # API URL (aqi=yes karne se air quality ka data bhi milta hai)
        url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={city}&aqi=yes"
        
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            # API se zaroori fields nikalna
            city_name = data['location']['name']
            country = data['location']['country']
            
            # API temperature Celsius mein deti hai, lekin humare table ko Kelvin mein chahiye (C + 273.15)
            temp_celsius = data['current']['temp_c']
            temp_kelvin = temp_celsius + 273.15
            
            humidity = data['current']['humidity']
            
            # Wind speed m/s mein convert karne ke liye (km/h divided by 3.6)
            wind_kph = data['current']['wind_kph']
            wind_ms = round(wind_kph / 3.6, 2)
            
            # Air Quality Index (US - EPA standard index: 1 se 6 tak hota hai)
            aqi_index = data['current']['air_quality']['us-epa-index']
            
            # 3. SQL Query: Data ko niazi db ki raw table mein INSERT karna
            insert_query = """
                INSERT INTO raw_weather_logs (city_name, country, temperature_kelvin, humidity, wind_speed, aqi_index)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(insert_query, (city_name, country, temp_kelvin, humidity, wind_ms, aqi_index))
            print(f"Successfully fetched and saved raw data for {city_name}!")
            
        else:
            print(f"Failed to fetch data for {city}. Status code: {response.status_code}")
            
    # Sab changes ko save/commit karein aur connection close karein
    conn.commit()
    cursor.close()
    conn.close()
    print("ETL Step 1 (Ingestion) Completed!")

except Exception as e:
    print(f"Error occurred: {e}")