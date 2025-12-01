# FundX/database.py
import duckdb
import os

# 数据库文件会生成在软件运行的目录下
DB_PATH = "fund_analysis.duckdb"

def get_db_connection():
    """获取数据库连接"""
    conn = duckdb.connect(DB_PATH)
    return conn

def init_db():
    """初始化数据库表结构 - 根据《多账单.doc》要求"""
    conn = get_db_connection()
    
    # 创建核心交易表 (单账单/多账单共用此表)
    # 字段对应 cleaning 后的标准字段
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id VARCHAR,                  -- 唯一标识
            case_id VARCHAR,             -- 案件编号 (必填)
            case_name VARCHAR,           -- 案件名称 (必填)
            person_identity VARCHAR,     -- 人员身份 (盗窃/收赃/排查)
            
            bill_source VARCHAR,         -- 账单来源 (微信/支付宝/银行)
            owner_name VARCHAR,          -- 姓名/持卡人
            owner_id VARCHAR,            -- 身份证号
            owner_account VARCHAR,       -- 微信号/账号
            
            trans_time TIMESTAMP,        -- 交易时间
            amount DECIMAL(18,2),        -- 金额 (负数为出，正数为入)
            counterparty_name VARCHAR,   -- 交易对方 (清洗后)
            counterparty_account VARCHAR,-- 对方账号
            trans_order_id VARCHAR,      -- 交易单号 (用于关联)
            merchant_order_id VARCHAR,   -- 商户单号 (用于关联)
            remark VARCHAR,
            
            raw_file_name VARCHAR,       -- 原始文件名
            import_batch VARCHAR         -- 导入批次ID
        );
    """)
    # 索引优化
    try:
        conn.execute("DROP INDEX IF EXISTS idx_transactions_case_id")
        conn.execute("DROP INDEX IF EXISTS idx_transactions_trans_time")
        conn.execute("DROP INDEX IF EXISTS idx_transactions_owner")
        conn.execute("DROP INDEX IF EXISTS idx_transactions_counterparty")
        conn.execute("DROP INDEX IF EXISTS idx_orders")
        conn.execute("CREATE INDEX idx_transactions_case_id ON transactions(case_id)")
        conn.execute("CREATE INDEX idx_transactions_trans_time ON transactions(trans_time)")
        conn.execute("CREATE INDEX idx_transactions_owner ON transactions(owner_name)")
        conn.execute("CREATE INDEX idx_transactions_counterparty ON transactions(counterparty_name)")
        try:
            conn.execute("CREATE INDEX idx_orders ON transactions(trans_order_id, merchant_order_id)")
        except Exception:
            conn.execute("CREATE INDEX idx_trans_order_id ON transactions(trans_order_id)")
            conn.execute("CREATE INDEX idx_merchant_order_id ON transactions(merchant_order_id)")
    except Exception:
        pass
    
    print("数据库初始化完成: transactions 表已就绪")
    conn.close()

if __name__ == "__main__":
    init_db()
