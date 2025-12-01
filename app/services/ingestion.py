import pandas as pd
import uuid
import os
from datetime import datetime
from pathlib import Path
from app.services.cleaning_service import CleaningService
from database import get_db_connection

class IngestionService:
    def __init__(self):
        self.cleaner_service = CleaningService()

    def process_and_save(self, file_path: Path, file_type: str, case_info: dict) -> int:
        df = self.cleaner_service.clean_file(str(file_path), case_info)
        if df is None or df.empty:
            raise ValueError("文件内容为空或格式无法识别")

        df = self._map_columns(df, case_info)

        if 'amount' in df.columns:
            df['amount'] = df['amount'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
            unit = case_info.get('amount_unit', 'yuan')
            if unit == 'fen':
                df['amount'] = df['amount'] / 100.0
            elif unit == 'jiao':
                df['amount'] = df['amount'] / 10.0
            df = df[df['amount'].abs() >= 0.01]

        df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
        df['import_batch'] = datetime.now().strftime("%Y%m%d%H%M%S")
        df['raw_file_name'] = file_path.name

        self._save_to_duckdb(df)
        return len(df)

    def _map_columns(self, df, case_info):
        mapping = {
            '姓名': 'owner_name', '户名': 'owner_name',
            '身份证': 'owner_id', '身份证号': 'owner_id',
            '微信号': 'owner_account', '账号': 'owner_account', '交易账号': 'owner_account',
            '交易时间': 'trans_time', '时间': 'trans_time', '入账时间': 'trans_time',
            '金额': 'amount', '交易金额': 'amount', '操作金额': 'amount',
            '交易对方': 'counterparty_name', '微信昵称': 'counterparty_name', '对方户名': 'counterparty_name', '收款方': 'counterparty_name',
            '对方账号': 'counterparty_account',
            '交易单号': 'trans_order_id', '流水号': 'trans_order_id',
            '商户单号': 'merchant_order_id',
            '备注': 'remark',
            '账单来源': 'bill_source'
        }
        df = df.rename(columns=mapping)
        df['case_id'] = case_info['case_id']
        df['case_name'] = case_info['case_name']
        df['person_identity'] = case_info['person_type']
        for col in mapping.values():
            if col not in df.columns:
                df[col] = None
        return df

    def _save_to_duckdb(self, df):
        conn = get_db_connection()
        db_cols = [
            'id', 'case_id', 'case_name', 'person_identity', 'bill_source',
            'owner_name', 'owner_id', 'owner_account',
            'trans_time', 'amount', 'counterparty_name', 'counterparty_account',
            'trans_order_id', 'merchant_order_id', 'remark',
            'raw_file_name', 'import_batch'
        ]
        final_df = pd.DataFrame()
        for col in db_cols:
            final_df[col] = df[col] if col in df.columns else None
        conn.register('final_df', final_df)
        conn.execute("INSERT INTO transactions SELECT * FROM final_df")
        conn.close()
