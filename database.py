import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

print("HOST =", os.getenv("DB_HOST"))
print("USER =", os.getenv("DB_USER"))
print("PASSWORD =", os.getenv("DB_PASSWORD"))
print("DATABASE =", os.getenv("DB_NAME"))
print("PORT =", os.getenv("DB_PORT"))

def get_connection():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )
    return connection

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("✅ Database Connected Successfully!")
        conn.close()
    except Exception as e:
        print("❌ Connection Failed")
        print(e)