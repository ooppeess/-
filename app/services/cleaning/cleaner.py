import pandas as pd
import pdfplumber
import re


class BillStandardizer:
    def __init__(self):
        self.standard_columns = [
            "姓名", "身份证", "微信号", "交易单号", "交易时间",
            "交易类型", "收/支/其他", "交易方式", "金额(元)", "交易对方", "商户单号",
        ]

    def clean_tenpay_txt(self, file_path: str, user_info: dict | None = None) -> pd.DataFrame:
        try:
            df = pd.read_csv(file_path, sep="\t", encoding="utf-8", on_bad_lines="skip")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, sep="\t", encoding="gb18030", on_bad_lines="skip")

        df_std = pd.DataFrame(columns=self.standard_columns)

        if "交易单号" in df.columns:
            df_std["交易单号"] = (
                df["交易单号"].astype(str).str.replace("\t", "")
            )
        if "交易时间" in df.columns:
            df_std["交易时间"] = pd.to_datetime(df["交易时间"], errors="coerce").dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        if "交易业务类型" in df.columns:
            df_std["交易类型"] = df["交易业务类型"]
        if "借贷类型" in df.columns:
            df_std["收/支/其他"] = df["借贷类型"]
        if "交易用途类型" in df.columns:
            df_std["交易方式"] = df["交易用途类型"]
        if "对手侧账户名称" in df.columns:
            df_std["交易对方"] = df["对手侧账户名称"]

        df_std["商户单号"] = df["商户单号"] if "商户单号" in df.columns else ""

        if "交易金额(分)" in df.columns:
            df_std["金额(元)"] = df["交易金额(分)"].apply(
                lambda x: float(str(x).replace(",", "")) / 100 if pd.notna(x) else 0.0
            )

        if user_info:
            df_std["姓名"] = user_info.get("name", "")
            df_std["身份证"] = user_info.get("id_card", "")
            df_std["微信号"] = user_info.get("wechat_id", "")
        else:
            if "用户侧账号名称" in df.columns:
                df_std["姓名"] = df["用户侧账号名称"]

        return df_std

    def clean_wechat_pdf(self, file_path: str) -> pd.DataFrame:
        transactions: list[dict] = []
        user_info = {"name": "", "id_card": "", "wechat_id": ""}

        with pdfplumber.open(file_path) as pdf:
            first_page_text = pdf.pages[0].extract_text() or ""

            name_match = re.search(r"兹证明:(.*?)\(", first_page_text)
            id_match = re.search(r"身份证:(.*?)\)", first_page_text)
            wx_match = re.search(r"微信号:(.*?)中", first_page_text)

            if name_match:
                user_info["name"] = name_match.group(1).strip()
            if id_match:
                user_info["id_card"] = id_match.group(1).strip()
            if wx_match:
                user_info["wechat_id"] = wx_match.group(1).strip()

            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = table[0]
                    for row in table[1:]:
                        if not row or len(row) < 5:
                            continue
                        if "交易单号" in str(row[0]):
                            continue
                        try:
                            amount_str = (row[5] if len(row) > 5 else "").replace(",", "")
                            amount_str = amount_str.replace("¥", "").strip()
                            amount_val = float(amount_str) if amount_str else 0.0

                            item = {
                                "姓名": user_info["name"],
                                "身份证": user_info["id_card"],
                                "微信号": user_info["wechat_id"],
                                "交易单号": (row[0] or "").replace("\n", ""),
                                "交易时间": (row[1] or "").replace("\n", " "),
                                "交易类型": (row[2] or "").replace("\n", ""),
                                "收/支/其他": (row[3] or "").replace("\n", ""),
                                "交易方式": (row[4] or "").replace("\n", ""),
                                "金额(元)": amount_val,
                                "交易对方": (row[6] if len(row) > 6 else "").replace("\n", ""),
                                "商户单号": (row[7] if len(row) > 7 else "").replace("\n", ""),
                            }
                            transactions.append(item)
                        except Exception:
                            continue

        return pd.DataFrame(transactions, columns=self.standard_columns)


if __name__ == "__main__":
    cleaner = BillStandardizer()
    print("BillStandardizer 已就绪")
