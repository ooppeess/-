# -*- coding: utf-8 -*-
"""
财付通清洗器（整合TT/cleaner.py的完整逻辑）
"""
import io
import pandas as pd
import numpy as np
from io import BytesIO
from typing import Tuple, Optional, cast
from .base_cleaner import BaseCleaner


class TenpayCleaner(BaseCleaner):
    def clean(self, file_content: bytes = None, filename: str = "", **kwargs) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            if file_content is None and "file_path" in kwargs:
                with open(kwargs["file_path"], "rb") as f:
                    file_content = f.read()
            if file_content is None:
                return None, "缺少文件内容"
            try:
                df = pd.read_csv(BytesIO(file_content), sep='\t', encoding='utf-8', on_bad_lines='skip')
            except UnicodeDecodeError:
                df = pd.read_csv(BytesIO(file_content), sep='\t', encoding='gb18030', on_bad_lines='skip')
            df.columns = [str(c).strip() for c in df.columns]
            standard_df = pd.DataFrame()
            if '交易金额(分)' in df.columns:
                standard_df['金额(元)'] = df['交易金额(分)'].astype(str).str.replace(',', '').astype(float) / 100
            else:
                standard_df['金额(元)'] = 0.0
            if '交易时间' in df.columns:
                standard_df['交易时间'] = pd.to_datetime(df['交易时间'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                standard_df['交易时间'] = ''
            if '交易单号' in df.columns:
                standard_df['交易单号'] = df['交易单号'].astype(str).str.strip()
            else:
                standard_df['交易单号'] = ''
            standard_df['收/支/其他'] = df['借贷类型'] if '借贷类型' in df.columns else ''
            if '对手侧账户名称' in df.columns:
                standard_df['交易对方'] = df['对手侧账户名称']
            elif '第三方账户名称' in df.columns:
                standard_df['交易对方'] = df['第三方账户名称']
            elif '对手方ID' in df.columns:
                standard_df['交易对方'] = df['对手方ID']
            else:
                standard_df['交易对方'] = ''
            if '交易业务类型' in df.columns:
                standard_df['交易类型'] = df['交易业务类型']
            else:
                standard_df['交易类型'] = ''
            if '交易用途类型' in df.columns:
                standard_df['交易方式'] = df['交易用途类型']
            else:
                standard_df['交易方式'] = ''
            if '大单号' in df.columns:
                standard_df['商户单号'] = df['大单号']
            elif '商户单号' in df.columns:
                standard_df['商户单号'] = df['商户单号']
            else:
                standard_df['商户单号'] = ''
            owner_name = kwargs.get('owner_name', None)
            if owner_name is None:
                owner_name = (df['用户侧账号名称'].iloc[0] if '用户侧账号名称' in df.columns and not df.empty else '未知')
            standard_df['姓名'] = owner_name
            standard_df['身份证'] = kwargs.get('id_card', '')
            standard_df['微信号'] = kwargs.get('wechat_id', '')
            cols = ["姓名", "身份证", "微信号", "交易单号", "交易时间", "交易类型", "收/支/其他", "交易方式", "金额(元)", "交易对方", "商户单号"]
            for c in cols:
                if c not in standard_df.columns:
                    standard_df[c] = ''
            standard_df = standard_df[cols]
            return standard_df, None
        except Exception as e:
            return None, f"财付通清洗失败：{e}"
    
    def _read_tenpay_table(self, path: str) -> pd.DataFrame:
        """
        读取财付通 .txt（制表符分隔），自动识别多编码并定位表头
        支持财付通TXT文件的27个字段表头格式
        """
        with open(path, 'rb') as f:
            raw = f.read()

        # 完整的编码支持列表（整合TT/cleaner.py）
        enc_candidates = ['utf-8', 'utf-8-sig', 'gb18030', 'gbk', 'cp936', 'utf-16', 'utf-16le', 'utf-16be', 'latin-1']
        
        text = None
        for enc in enc_candidates:
            try:
                text = raw.decode(enc)
                break
            except Exception:
                continue
        
        if text is None:
            text = raw.decode('gb18030', errors='ignore')  # 兜底

        # 定位标题行（财付通TXT文件的标准表头）
        lines = [ln.strip('\r\n') for ln in text.splitlines()]
        header_idx = 0
        
        # 财付通TXT文件的标准表头字段
        tenpay_header_keys = [
            "用户ID", "交易单号", "大单号", "用户侧账号名称", "借贷类型", "交易业务类型", 
            "交易用途类型", "交易时间", "交易金额(分)", "账户余额(分)", "用户银行卡号", 
            "用户侧网银联单号", "网联/银联", "第三方账户名称", "对手方ID", "对手侧账户名称", 
            "对手方银行卡号", "对手侧银行名称", "对手侧网银联单号", "网联/银联", "基金公司信息", 
            "间联/非间联交易", "第三方账户名称", "对手方接收时间", "对手方接收金额(分)", "备注1", "备注2"
        ]
        
        def is_tenpay_header(s: str) -> bool:
            """检查是否为财付通TXT文件的表头行"""
            if "\t" not in s:
                return False
            # 检查是否包含财付通特有的关键字段
            key_fields = ["用户ID", "交易单号", "大单号", "用户侧账号名称", "借贷类型", "交易业务类型"]
            return sum(1 for k in key_fields if k in s) >= 3
        
        for i, ln in enumerate(lines):
            if is_tenpay_header(ln):
                header_idx = i
                break
        
        data_text = "\n".join(lines[header_idx:])
        df = pd.read_csv(io.StringIO(data_text), sep="\t", dtype=str, engine="python", on_bad_lines="skip")
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        return df

    def _clean_tenpay_data(self, df: pd.DataFrame, case_name: str, case_id: str, role: str, source: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        清洗财付通数据（支持财付通TXT文件的27个字段表头格式）
        """
        try:
            def get_col(name: str):
                """获取列数据，支持列名匹配"""
                if name in df.columns:
                    return df[name]
                # 处理重复列名的情况（如"第三方账户名称"出现两次）
                for c in df.columns:
                    if c.startswith(name + "."):
                        return df[c]
                return pd.Series([np.nan] * len(df))

            out = pd.DataFrame()
            
            # 根据用户要求的字段映射
            # 案件名称: 用户侧账号名称
            out["案件名称"] = case_name
            
            # 案件编号: 大单号
            out["案件编号"] = case_id
            
            # 账单类型: 交易业务类型（例如消费、转账等）
            out["账单类型"] = get_col("交易业务类型")
            
            # 姓名: 用户侧账号名称
            out["姓名"] = get_col("用户侧账号名称")
            
            # 身份证: 文件中没有直接对应的字段，空着
            out["身份证"] = pd.Series([""] * len(df))
            
            # 微信号: 用户侧网银联单号 或 wxid（微信ID）
            out["微信号"] = get_col("用户侧网银联单号")
            
            # 交易单号: 交易单号
            out["交易单号"] = get_col("交易单号")
            
            # 交易时间: 交易时间
            out["交易时间"] = pd.to_datetime(get_col("交易时间"), errors="coerce")
            
            # 交易类型: 交易用途类型
            out["交易类型"] = get_col("交易用途类型")
            
            # 收/支/其他: 借贷类型（出/入）
            jl = get_col("借贷类型").fillna("")
            out["收/支/其他"] = jl.map(lambda v: "收" if str(v).strip()=="入" else ("支" if str(v).strip()=="出" else "其他"))
            
            # 交易方式: 交易方式（例如余额支付、快捷支付）
            out["交易方式"] = get_col("交易业务类型")
            
            # 金额：交易金额（分）转为元，并按借贷类型设置正负号
            amount_fen = pd.to_numeric(get_col("交易金额(分)"), errors="coerce")
            sign = jl.map(lambda v: 1 if str(v).strip()=="入" else (-1 if str(v).strip()=="出" else np.nan)).fillna(1)
            if not isinstance(amount_fen, pd.Series):
                amount_fen = pd.Series(amount_fen)
            amount_fen = amount_fen.fillna(0)
            # 转换为元
            amount_yuan = amount_fen / 100.0
            out["金额"] = amount_yuan * sign
            
            # 交易对方: 对手方账户名称
            out["交易对方"] = get_col("对手侧账户名称")
            
            # 商户单号: 网联清算有限公司 或相关的商户标识信息
            out["商户单号"] = get_col("大单号")
            
            # 备注
            note1, note2 = get_col("备注1"), get_col("备注2")
            out["备注"] = (note1 if note1 is not None else pd.Series([""]*len(df))).fillna("")
            if note2 is not None:
                mask = out["备注"].fillna("") == ""
                out.loc[mask, "备注"] = note2

            # 丢弃无效行
            out = out[(out["交易时间"].notna()) & (out["金额(元)"].notna())]
            if out.empty:
                return None, "解析后为空：缺少有效的交易时间或金额"

            # 附加元字段
            out["案件名称"] = case_name
            out["案件编号"] = case_id
            out["人员身份"] = role
            out["账单来源"] = source or "财付通"

            # 检查是否需要更新姓名（只有在姓名为空或未知时才使用交易主体）
            if not out.empty:
                # 确保 out 是 DataFrame 类型
                if isinstance(out, pd.DataFrame):
                    out = self._update_name_if_empty(out, "交易对方", "姓名")
                
                # 提取交易主体（从姓名字段获取）
                if isinstance(out, pd.DataFrame) and not out.empty and "姓名" in out.columns:
                    transaction_subject = out["姓名"].iloc[0]
                else:
                    transaction_subject = "未知"
                print(f"财付通文件交易主体: {transaction_subject}")

            # 字段顺序统一（标准15个字段）
            standard_fields = [
                "案件名称", "案件编号", "账单类型", "姓名", "身份证", "微信号", 
                "交易单号", "交易时间", "交易类型", "收/支/其他", "交易方式", 
                "金额(元)", "交易对方", "商户单号", "备注"
            ]
            
            # 确保所有标准字段都存在
            for field in standard_fields:
                if field not in out.columns:
                    if field == "账单类型":
                        out[field] = source or "财付通"
                    else:
                        out[field] = ""
            
            # 按标准字段顺序排列
            if isinstance(out, pd.DataFrame) and not out.empty:
                # 确保所有标准字段都存在
                for field in standard_fields:
                    if field not in out.columns:
                        out[field] = ""
                out = out[standard_fields]
                if "交易时间" in out.columns:
                    out = out.sort_values(by="交易时间")  # type: ignore
                out = out.reset_index(drop=True)
            else:
                out = pd.DataFrame(columns=standard_fields)  # type: ignore
            
            # 确保返回的是 DataFrame
            if not isinstance(out, pd.DataFrame):
                out = pd.DataFrame(columns=standard_fields)  # type: ignore
            
            return out, ""
        except Exception as e:
            return None, f"财付通数据清洗失败：{e}"
