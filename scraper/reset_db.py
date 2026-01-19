"""
WorldCup Alpha - Database Reset Script
每次运行会清空并重建 market_odds 表
支持多赛事：World Cup, EPL, NBA
"""
import os
import psycopg2
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DATABASE_URL = os.getenv('DATABASE_URL')


def reset_database():
    """重置数据库：删除并重建 market_odds 表"""
    if not DATABASE_URL:
        print("错误: DATABASE_URL 未设置，请检查 .env 文件")
        return False

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # 1. 删除旧表
        print("正在删除旧表...")
        cursor.execute("DROP TABLE IF EXISTS market_odds;")

        # 2. 创建新表 (包含 sport_type 字段)
        print("正在创建新表...")
        create_table_sql = """
        CREATE TABLE market_odds (
            id SERIAL PRIMARY KEY,
            sport_type VARCHAR(20) NOT NULL,
            team_name VARCHAR(100) NOT NULL,
            web2_odds FLOAT,
            polymarket_price FLOAT,
            polymarket_url TEXT,
            kalshi_price FLOAT,
            kalshi_url TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_sql)

        # 3. 创建索引以加速查询
        print("正在创建索引...")
        cursor.execute("CREATE INDEX idx_sport_type ON market_odds(sport_type);")
        cursor.execute("CREATE INDEX idx_team_name ON market_odds(team_name);")
        cursor.execute("CREATE INDEX idx_sport_team ON market_odds(sport_type, team_name);")

        conn.commit()
        print("market_odds 表重置成功！")

        # 显示表结构
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'market_odds'
            ORDER BY ordinal_position;
        """)

        print("\n表结构:")
        print("-" * 50)
        for row in cursor.fetchall():
            print(f"  {row[0]:20} | {row[1]:15} | nullable: {row[2]}")
        print("-" * 50)

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"数据库错误: {e}")
        return False
    except Exception as e:
        print(f"未知错误: {e}")
        return False


if __name__ == '__main__':
    print("=" * 50)
    print("WorldCup Alpha - 数据库重置脚本")
    print("=" * 50)
    reset_database()
