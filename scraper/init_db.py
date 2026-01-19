import os
import psycopg2
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DATABASE_URL = os.getenv('DATABASE_URL')

def init_database():
    """初始化数据库，创建 market_odds 表"""
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS market_odds (
        id SERIAL PRIMARY KEY,
        team_name VARCHAR(50),
        polymarket_price FLOAT,
        web2_odds FLOAT,
        source_web2 VARCHAR(50),
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ev_percentage FLOAT
    );
    """

    cursor.execute(create_table_sql)
    conn.commit()

    print("market_odds 表创建成功！")

    cursor.close()
    conn.close()

if __name__ == '__main__':
    init_database()
