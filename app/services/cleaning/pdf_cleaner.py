import pdfplumber
import pandas as pd
import io
import re
from typing import Tuple, Optional
from .base_cleaner import BaseCleaner

class PDFCleaner(BaseCleaner):
    def clean(self, file_content: bytes = None, filename: str = "", **kwargs) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            if file_content is None:
                file_path = kwargs.get('file_path')
                if not file_path:
                    return None, "缺少PDF内容或文件路径"
                with open(file_path, 'rb') as f:
                    file_content = f.read()

            transactions = []
            user_info = {"name": "", "id_card": "", "wechat_id": ""}

            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                first_page_text = pdf.pages[0].extract_text() or ""
                name_match = re.search(r"兹证明:(.*?)\(", first_page_text)
                id_match = re.search(r"身份证:(.*?)\)", first_page_text)
                if name_match:
                    user_info['name'] = name_match.group(1).strip()
                if id_match:
                    user_info['id_card'] = id_match.group(1).strip()

                for page in pdf.pages:
                    table = page.extract_table()
                    if not table:
                        continue
                    for row in table:
                        if not row or len(row) < 5 or ("交易单号" in str(row[0])):
                            continue
                        try:
                            amt_str = (row[5] if len(row) > 5 else "").replace('¥', '').replace(',', '').strip()
                            amt_val = float(amt_str) if amt_str else 0.0
                            item = {
                                "交易单号": str(row[0]).strip(),
                                "交易时间": str(row[1]).replace('\n', ' '),
                                "交易类型": str(row[2]).strip(),
                                "收/支/其他": str(row[3]).strip(),
                                "交易方式": str(row[4]).strip(),
                                "金额(元)": amt_val,
                                "交易对方": str(row[6]).strip() if len(row) > 6 and row[6] is not None else "",
                                "商户单号": str(row[7]).strip() if len(row) > 7 and row[7] is not None else "",
                                "姓名": user_info['name'],
                                "身份证": user_info['id_card'],
                            }
                            transactions.append(item)
                        except Exception:
                            continue

            df = pd.DataFrame(transactions)
            return df, None
        except Exception as e:
            return None, f"PDF清洗失败: {e}"
