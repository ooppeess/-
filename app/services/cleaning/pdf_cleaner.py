import pdfplumber
import pandas as pd
import re
from typing import Tuple, Optional
from .base_cleaner import BaseCleaner

class PDFCleaner(BaseCleaner):
    def clean(self, file_path: str, case_name: str, case_id: str, 
              person_type: str, source_type: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            all_tables = []
            
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # 提取表格
                    tables = page.extract_tables()
                    for table in tables:
                        # 简单的有效性判断：列数大于3且不是纯空
                        if table and len(table) > 1 and len(table[0]) > 3:
                            # 将第一行设为表头
                            df_page = pd.DataFrame(table[1:], columns=table[0])
                            all_tables.append(df_page)

            if not all_tables:
                return None, "未在PDF中识别到有效表格"

            # 合并所有页的表格
            df = pd.concat(all_tables, ignore_index=True)
            
            # --- 标准化处理 ---
            # 1. 去除换行符
            df = df.replace(r'\n', '', regex=True)
            
            # 2. 补充案件信息
            df['案件名称'] = case_name
            df['案件编号'] = case_id
            df['人员身份'] = person_type
            df['账单来源'] = "PDF导入"

            # 3. 简单的列名清洗 (去除空格)
            df.columns = [c.replace(" ", "").replace("\n", "") if c else f"col_{i}" for i, c in enumerate(df.columns)]

            return df, None

        except Exception as e:
            return None, f"PDF解析失败: {str(e)}"