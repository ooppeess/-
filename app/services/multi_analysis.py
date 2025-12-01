# app/multi_analysis.py
from database import get_db_connection

# --- 核心：构建资金交互（22交互） ---
# 逻辑：A的商户单号 = B的交易单号 (或反之)，且都在同一个案件里
def get_22_interaction(case_id):
    conn = get_db_connection()
    
    sql = """
        SELECT 
            t1.owner_name as source,          -- 资金转出方
            t1.person_identity as source_type,
            t2.owner_name as target,          -- 资金接收方
            t2.person_identity as target_type,
            t1.trans_time as time,
            ABS(t1.amount) as amount,
            t1.trans_order_id
        FROM transactions t1
        JOIN transactions t2 ON t1.case_id = t2.case_id
        WHERE t1.case_id = ?
          -- 金额为负代表支出，作为源头
          AND t1.amount < 0
          -- 核心关联逻辑：单号对碰
          AND (
              (t1.merchant_order_id = t2.trans_order_id AND t1.merchant_order_id != '') 
              OR 
              (t1.trans_order_id = t2.merchant_order_id AND t1.trans_order_id != '')
          )
          -- 排除自己转自己
          AND t1.owner_name != t2.owner_name
    """
    df = conn.execute(sql, [case_id]).fetchdf()
    conn.close()
    return df

# 1. 销赃/分赃节点判断 - 场景A：有收赃人账单
# 逻辑：直接查上面的交互表，看谁（收赃）给谁（盗窃）转了钱
def analyze_stolen_distribution_known(case_id):
    df = get_22_interaction(case_id)
    # 筛选：源头是收赃，目标是盗窃
    result = df[
        (df['source_type'] == '收脏人员') & 
        (df['target_type'] == '盗窃人员')
    ]
    return result.to_dict(orient='records')

# 2. 销赃/分赃节点判断 - 场景B：无收赃人账单/现金（推断模式）
# 逻辑：同一天，盗窃人员，多笔支出，金额接近，时间接近
def analyze_stolen_distribution_infer(case_id):
    conn = get_db_connection()
    
    # 找盗窃人员的支出
    sql = """
        SELECT owner_name, trans_time, ABS(amount) as amount
        FROM transactions
        WHERE case_id = ? AND person_identity = '盗窃人员' AND amount < 0
        ORDER BY trans_time
    """
    df = conn.execute(sql, [case_id]).fetchdf()
    conn.close()
    
    # 简单的 Python 逻辑推断（DuckDB 写复杂窗口函数太难调试，用 Python 循环）
    suspicious_groups = []
    # 这里需要写一个滑动窗口算法，简单起见，我写个伪代码逻辑供参考
    # 实际部署建议：先按天分组，然后看每组内是否有 3 人以上金额相差 < 10%
    
    return [{"date": "2024-01-01", "desc": "示例推断数据"}] # 占位

# 3. 挖尚不掌握的同伙
# 逻辑：在已掌握的交互时间点前后 30 分钟内，有频繁交易的陌生人
def find_hidden_partners(case_id, time_window_minutes=30):
    conn = get_db_connection()
    
    # 1. 获取所有已知“盗窃/收赃”人员的交易时间点
    known_sql = "SELECT trans_time FROM transactions WHERE case_id = ? AND person_identity IN ('盗窃人员', '收脏人员')"
    known_times = conn.execute(known_sql, [case_id]).fetchdf()['trans_time'].tolist()
    
    if not known_times:
        return []

    # 2. 这步如果数据量大，直接 SQL 会很慢。
    # 优化逻辑：查找同一天内，跟已知人员交易时间差 < 30分钟 的记录
    # 且 对端名字 不在 已知人员列表中
    
    sql = f"""
        WITH known_persons AS (
            SELECT DISTINCT owner_name FROM transactions WHERE case_id = ?
        )
        SELECT 
            t.counterparty_name,
            COUNT(*) as freq,
            SUM(ABS(t.amount)) as total_amount
        FROM transactions t
        JOIN transactions t_known 
            ON t.case_id = t_known.case_id 
            -- 同一天
            AND strftime(t.trans_time, '%Y-%m-%d') = strftime(t_known.trans_time, '%Y-%m-%d')
        WHERE t.case_id = ?
          -- t_known 是已知人员
          AND t_known.person_identity IN ('盗窃人员', '收脏人员')
          -- 时间差 30 分钟 (1800秒)
          AND ABS(date_diff('second', t.trans_time, t_known.trans_time)) <= {time_window_minutes * 60}
          -- t 的对端不是已知人员
          AND t.counterparty_name NOT IN (SELECT owner_name FROM known_persons)
        GROUP BY t.counterparty_name
        ORDER BY freq DESC
        LIMIT 20
    """
    
    df = conn.execute(sql, [case_id, case_id]).fetchdf()
    conn.close()
    return df.to_dict(orient='records')