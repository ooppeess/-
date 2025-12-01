# -*- coding: utf-8 -*-
import pandas as pd
from typing import Tuple, Optional
from .base_cleaner import BaseCleaner
from pathlib import Path
import json
import os

class ExcelCleaner(BaseCleaner):
    def clean(self, file_path: str, case_name: str, case_id: str, 
              person_type: str, source_type: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            # 1. 尝试读取 (自动寻找表头)
            df = self._smart_read_excel(file_path)
            if df is None or df.empty:
                return None, "Excel读取为空或无法定位表头"

            # 2. 强制字段映射 (依赖 config/column_mapping.json)
            df = self._apply_mapping(df)

            # 3. 补充缺失的关键列 (防止后续报错)
            for col in ["姓名", "身份证号", "微信号", "交易单号", "商户单号", "对方账号", "备注"]:
                if col not in df.columns:
                    df[col] = ""

            # 4. 补充元数据
            df["案件名称"] = case_name
            df["案件编号"] = case_id
            df["人员身份"] = person_type
            df["账单来源"] = source_type

            # 5. 类型清洗
            if "交易时间" in df.columns:
                df["交易时间"] = pd.to_datetime(df["交易时间"], errors='coerce')
            
            if "金额" in df.columns:
                # 清理千分位逗号等非数字字符
                df["金额"] = df["金额"].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                df["金额"] = pd.to_numeric(df["金额"], errors='coerce').fillna(0)

            # 6. 过滤无效行
            if "交易时间" in df.columns:
                df = df.dropna(subset=["交易时间"])

            return df, None
            
        except Exception as e:
            return None, f"Excel处理异常: {str(e)}"

    def _smart_read_excel(self, path):
        """尝试读取Excel，跳过前面的非表格行；失败则回退至CSV/表格解析"""
        try:
            engine = "openpyxl" if path.endswith(".xlsx") else None
            preview = pd.read_excel(path, engine=engine, nrows=20)
            for i, row in preview.iterrows():
                row_str = str(row.values)
                if ("时间" in row_str or "日期" in row_str) and ("金额" in row_str or "交易金额" in row_str):
                    return pd.read_excel(path, engine=engine, header=i)
            return pd.read_excel(path, engine=engine)
        except Exception:
            try:
                # CSV/表格回退读取，自动推断分隔符
                return pd.read_csv(path, sep=None, engine="python", dtype=str, on_bad_lines="skip")
            except Exception:
                try:
                    # 常见分隔符再次尝试
                    for sep in [",", "\t", ";", "|"]:
                        try:
                            return pd.read_csv(path, sep=sep, dtype=str, on_bad_lines="skip")
                        except Exception:
                            continue
                except Exception:
                    pass
            return None

    def _apply_mapping(self, df):
        # 读取映射配置
        try:
            mapping_path = Path("config/column_mapping.json")
            if mapping_path.exists():
                with open(mapping_path, "r", encoding="utf-8") as f:
                    rename_map = json.load(f)
                # 清理列名空格
                df.columns = df.columns.astype(str).str.strip().str.replace(r'\s+', '', regex=True)
                df.rename(columns=rename_map, inplace=True)
        except:
            pass
        return df
