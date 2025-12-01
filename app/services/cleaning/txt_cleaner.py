# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import io
from typing import Tuple, Optional
from .base_cleaner import BaseCleaner
import json
from pathlib import Path

class TXTCleaner(BaseCleaner):
    def clean(self, file_path: str, case_name: str, case_id: str, 
              person_type: str, source_type: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            # 1. 读取文件内容
            content = self._read_content(file_path)
            if not content:
                return None, "无法读取TXT文件(编码识别失败)"

            # 2. 转换为 DataFrame
            df = self._parse_content(content)
            if df is None or df.empty:
                return None, "TXT解析为空，未找到有效表格数据"

            # 3. 强制映射（记录原始列名用于单位判断）
            original_cols = list(df.columns)
            df = self._apply_mapping(df)
            df.attrs['original_columns'] = original_cols

            # 4. 特殊处理：微信/财付通的分转元
            self._handle_wechat_amount(df)

            # 5. 补充字段
            for col in ["姓名", "身份证号", "微信号", "交易单号", "商户单号", "对方账号", "备注"]:
                if col not in df.columns:
                    df[col] = ""
            
            df["案件名称"] = case_name
            df["案件编号"] = case_id
            df["人员身份"] = person_type
            df["账单来源"] = source_type or "TXT导入"

            # 6. 类型转换
            if "交易时间" in df.columns:
                df["交易时间"] = pd.to_datetime(df["交易时间"], errors='coerce')
                df = df.dropna(subset=["交易时间"])

            return df, None

        except Exception as e:
            return None, f"TXT处理异常: {str(e)}"

    def _read_content(self, path):
        with open(path, 'rb') as f:
            raw = f.read()
        # 常见编码尝试
        for enc in ['utf-8', 'gb18030', 'gbk', 'cp936', 'latin-1']:
            try:
                return raw.decode(enc)
            except:
                continue
        return None

    def _parse_content(self, text):
        lines = text.splitlines()
        header_idx = -1
        
        # 寻找表头行
        for i, line in enumerate(lines[:50]):
            if "交易时间" in line and ("金额" in line or "交易金额" in line):
                header_idx = i
                break
        
        if header_idx == -1:
            return None # 没找到表头

        # 截取数据部分
        data_lines = lines[header_idx:]
        data_str = "\n".join(data_lines)
        
        # 尝试 CSV 解析
        try:
            # 很多TXT其实是逗号分隔
            return pd.read_csv(io.StringIO(data_str), on_bad_lines='skip')
        except:
            try:
                # 或者是制表符
                return pd.read_csv(io.StringIO(data_str), sep='\t', on_bad_lines='skip')
            except:
                return None

    def _apply_mapping(self, df):
        try:
            mapping_path = Path("config/column_mapping.json")
            if mapping_path.exists():
                with open(mapping_path, "r", encoding="utf-8") as f:
                    rename_map = json.load(f)
                df.columns = df.columns.astype(str).str.strip()
                df.rename(columns=rename_map, inplace=True)
        except:
            pass
        return df

    def _handle_wechat_amount(self, df):
        # 如果之前列名里有 "交易金额(分)"，它现在应该已经被映射为 "金额" 了
        # 我们需要检查原始列名或者判断数值大小
        # 简单粗暴逻辑：如果从 Mapping 中得知来源是分，或者数值普遍巨大且没有小数
        
        if "金额" in df.columns:
            df["金额"] = pd.to_numeric(df["金额"], errors='coerce').fillna(0)
            orig = df.attrs.get('original_columns', [])
            has_fen_header = any("交易金额(分)" in str(c) for c in orig)
            need_div_100 = False
            if has_fen_header:
                need_div_100 = True
            else:
                if "借贷类型" in df.columns or "收/支/其他" in df.columns:
                    series = df["金额"]
                    all_integer = (series.round(0) == series).all()
                    median_val = float(series.median()) if len(series) else 0.0
                    need_div_100 = all_integer and median_val > 1000
            if need_div_100:
                df["金额"] = df["金额"] / 100.0
                 
            # 处理收支符号
            # 如果有"借贷类型"或"收/支/其他"
            col_dir = "借贷类型" if "借贷类型" in df.columns else ("收/支/其他" if "收/支/其他" in df.columns else None)
            if col_dir:
                # 支出/出 -> 负数
                mask_out = df[col_dir].astype(str).str.contains("出|支出")
                df.loc[mask_out, "金额"] = -df.loc[mask_out, "金额"].abs()
                # 收入/入 -> 正数
                mask_in = df[col_dir].astype(str).str.contains("入|收入")
                df.loc[mask_in, "金额"] = df.loc[mask_in, "金额"].abs()
