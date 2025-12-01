# app/single_analysis.py
from database import get_db_connection

# 1. 趋势图（带金额筛选）
def get_trend_analysis(case_id, person_name, min_amount=0, max_amount=None):
    conn = get_db_connection()
    
    # 构建金额筛选条件
    amount_filter = f"AND ABS(amount) >= {min_amount}"
    if max_amount:
        amount_filter += f" AND ABS(amount) <= {max_amount}"
        
    if person_name and str(person_name).strip():
        sql = f"""
            SELECT 
                strftime(trans_time, '%Y-%m') as month,
                SUM(CASE WHEN COALESCE(amount,0) > 0 THEN COALESCE(amount,0) ELSE 0 END) as total_in,
                SUM(CASE WHEN COALESCE(amount,0) < 0 THEN ABS(COALESCE(amount,0)) ELSE 0 END) as total_out
            FROM transactions
            WHERE case_id = ? AND owner_name = ? {amount_filter}
            GROUP BY month
            ORDER BY month
        """
        df = conn.execute(sql, [case_id, person_name]).fetchdf()
    else:
        sql = f"""
            SELECT 
                strftime(trans_time, '%Y-%m') as month,
                SUM(CASE WHEN COALESCE(amount,0) > 0 THEN COALESCE(amount,0) ELSE 0 END) as total_in,
                SUM(CASE WHEN COALESCE(amount,0) < 0 THEN ABS(COALESCE(amount,0)) ELSE 0 END) as total_out
            FROM transactions
            WHERE case_id = ? {amount_filter}
            GROUP BY month
            ORDER BY month
        """
        df = conn.execute(sql, [case_id]).fetchdf()
    conn.close()
    return df.to_dict(orient='records')

# 2. 统计表（三种特殊逻辑）
def get_statistics_table(case_id, person_name, filter_type='all'):
    conn = get_db_connection()
    
    # 基础聚合查询
    if person_name and str(person_name).strip():
        sql = """
            SELECT 
                counterparty_name,
                COUNT(*) as total_count,
                SUM(COALESCE(amount,0)) as net_amount,
                SUM(CASE WHEN COALESCE(amount,0) > 0 THEN 1 ELSE 0 END) as in_count,
                SUM(CASE WHEN COALESCE(amount,0) > 0 THEN COALESCE(amount,0) ELSE 0 END) as in_amount,
                SUM(CASE WHEN COALESCE(amount,0) < 0 THEN 1 ELSE 0 END) as out_count,
                SUM(CASE WHEN COALESCE(amount,0) < 0 THEN ABS(COALESCE(amount,0)) ELSE 0 END) as out_amount
            FROM transactions
            WHERE case_id = ? AND owner_name = ?
            GROUP BY counterparty_name
        """
        params = [case_id, person_name]
    else:
        sql = """
            SELECT 
                counterparty_name,
                COUNT(*) as total_count,
                SUM(COALESCE(amount,0)) as net_amount,
                SUM(CASE WHEN COALESCE(amount,0) > 0 THEN 1 ELSE 0 END) as in_count,
                SUM(CASE WHEN COALESCE(amount,0) > 0 THEN COALESCE(amount,0) ELSE 0 END) as in_amount,
                SUM(CASE WHEN COALESCE(amount,0) < 0 THEN 1 ELSE 0 END) as out_count,
                SUM(CASE WHEN COALESCE(amount,0) < 0 THEN ABS(COALESCE(amount,0)) ELSE 0 END) as out_amount
            FROM transactions
            WHERE case_id = ?
            GROUP BY counterparty_name
        """
        params = [case_id]
    
    # 根据 filter_type 添加 HAVING 筛选
    if filter_type == 'income_only': # 有收无支
        sql += " HAVING in_count > 0 AND out_count = 0"
    elif filter_type == 'expense_only': # 有支无收
        sql += " HAVING out_count > 0 AND in_count = 0"
    elif filter_type == 'high_ratio': # 收支比例悬殊 > 3:1
        # 避免除以零，使用逻辑判断
        sql += """ HAVING 
            (out_amount > 0 AND in_amount / out_amount > 3) 
            OR 
            (in_amount > 0 AND out_amount / in_amount > 3)
        """
        
    sql += " ORDER BY ABS(net_amount) DESC"
    
    df = conn.execute(sql, params).fetchdf()
    conn.close()
    return df.to_dict(orient='records')

# 3. 重点对端（特定关键词）
def get_key_counterparties(case_id):
    conn = get_db_connection()
    
    keywords = ["烟酒", "副食", "小卖", "回收", "维修", "摩托车", "汽修", "手机", "废旧", "金属", "超市"]
    # 构造 SQL 的 OR LIKE 语句
    like_clauses = " OR ".join([f"counterparty_name LIKE '%{k}%'" for k in keywords])
    
    sql = f"""
        SELECT 
            counterparty_name,
            COUNT(*) as count,
            SUM(CASE WHEN COALESCE(amount,0) > 0 THEN COALESCE(amount,0) ELSE 0 END) as in_amount,
            SUM(CASE WHEN COALESCE(amount,0) < 0 THEN ABS(COALESCE(amount,0)) ELSE 0 END) as out_amount
        FROM transactions
        WHERE case_id = ? AND ({like_clauses})
        GROUP BY counterparty_name
        ORDER BY count DESC
    """
    df = conn.execute(sql, [case_id]).fetchdf()
    conn.close()
    return df.to_dict(orient='records')
