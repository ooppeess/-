import duckdb

DB_PATH = "fund_analysis.duckdb"

def main():
    conn = duckdb.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM transactions")
        count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        print(f"transactions rows after cleanup: {count}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
