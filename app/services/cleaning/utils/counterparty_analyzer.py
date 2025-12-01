# -*- coding: utf-8 -*-
"""
交易主体分析工具
"""
import pandas as pd
from typing import Optional, Dict, Any


class CounterpartyAnalyzer:
    """
    交易主体分析器
    
    交易主体应该是账户持有人（从PDF内容中提取的真实姓名），
    而不是交易对方中出现次数最多的账户。
    """
    
    @staticmethod
    def get_account_holder(df: pd.DataFrame, name_col: str = "姓名") -> str:
        """
        获取账户持有人（交易主体）
        
        Args:
            df: 数据框
            name_col: 姓名列名
            
        Returns:
            str: 账户持有人姓名
        """
        if df.empty or name_col not in df.columns:
            return "未知"
        
        # 获取第一行的姓名作为账户持有人
        account_holder = df[name_col].iloc[0] if not df.empty else "未知"
        return str(account_holder)
    
    @staticmethod
    def analyze_main_counterparty(df: pd.DataFrame, counterparty_col: str = "交易对方") -> str:
        """
        分析主要交易对方（拥有最多交易条目的对手方账户名称）
        
        注意：这不是交易主体，而是交易对方中出现次数最多的账户。
        交易主体应该是账户持有人（从PDF内容中提取的真实姓名）。
        
        Args:
            df: 数据框
            counterparty_col: 交易对方列名
            
        Returns:
            str: 主要交易对方名称（交易条目数量最高的对手方账户）
        """
        if df.empty or counterparty_col not in df.columns:
            return "未知"
        
        # 定义停用词列表，过滤支付方式/系统词
        STOPWORDS = {
            "余额", "余额支付", "零钱", "零钱通", "理财通",
            "信用卡还款", "提现", "充值", "退款", "扫码收款",
            "转账", "转入", "转出", "系统", "商户平台", "对公账户",
            "微信支付", "支付宝", "银行卡", "快捷支付", "网银",
            "自动扣款", "代扣", "批量代收", "批量代付", "批量转账",
            "红包", "群收款", "AA收款", "面对面收款", "二维码收款",
            "信用卡", "借记卡", "储蓄卡", "信用卡还款", "花呗",
            "借呗", "网商银行", "余额宝", "理财", "基金", "保险",
            "生活缴费", "手机充值", "水电费", "燃气费", "宽带费",
            "交通罚款", "违章缴费", "ETC", "加油", "停车费",
            "话费充值", "流量充值", "游戏充值", "会员充值",
            "购物", "消费", "支付", "付款", "收款", "到账",
            "成功", "失败", "处理中", "待处理", "已撤销",
            "未知", "其他", "系统", "平台", "服务", "手续费"
        }
        
        # 获取交易对方数据并过滤停用词
        s = df[counterparty_col].dropna().astype(str).str.strip()
        
        # 过滤停用词
        s = s[~s.isin(STOPWORDS)]
        
        # 使用正则表达式过滤以停用词开头的值
        import re
        pattern = r'^(余额|零钱|零钱通|信用卡|提现|充值|转账|退款|微信|支付宝|银行卡|快捷|网银|自动|代扣|批量|红包|群收|AA|面对面|二维码|借记|储蓄|花呗|借呗|网商|余额宝|理财|基金|保险|生活|手机|水电|燃气|宽带|交通|违章|ETC|加油|停车|话费|流量|游戏|会员|购物|消费|支付|付款|收款|到账|成功|失败|处理|待处理|已撤销|未知|其他|系统|平台|服务|手续费)'
        s = s[~s.str.contains(pattern, na=False, regex=True)]
        
        if s.empty:
            return "未知"
        
        # 统计每个交易对方的交易次数
        counterparty_counts = s.value_counts()
        if counterparty_counts.empty:
            return "未知"
        
        # 找到交易条目数量最高的对手方账户
        max_count = counterparty_counts.max()
        top_counterparties = counterparty_counts[counterparty_counts == max_count]
        
        # 如果有多个账户的交易条目数量相同且都是最高，选择第一个
        main_counterparty = top_counterparties.index[0]  # type: ignore
        return str(main_counterparty)
    
    @staticmethod
    def get_counterparty_stats(df: pd.DataFrame, counterparty_col: str = "交易对方", top_n: int = 5) -> Dict[str, Any]:
        """
        获取交易主体统计信息
        
        Args:
            df: 数据框
            counterparty_col: 交易对方列名
            top_n: 返回前N个交易主体
            
        Returns:
            Dict: 包含统计信息的字典
        """
        if df.empty or counterparty_col not in df.columns:
            return {
                "main_counterparty": "未知",
                "total_transactions": 0,
                "top_counterparties": [],
                "counterparty_counts": {}
            }
        
        counterparty_counts = df[counterparty_col].value_counts()
        if counterparty_counts.empty:
            return {
                "main_counterparty": "未知",
                "total_transactions": 0,
                "top_counterparties": [],
                "counterparty_counts": {}
            }
        
        main_counterparty = counterparty_counts.index[0]
        top_counterparties = [
            {"name": name, "count": count} 
            for name, count in counterparty_counts.head(top_n).items()
        ]
        
        return {
            "main_counterparty": main_counterparty,
            "total_transactions": len(df),
            "top_counterparties": top_counterparties,
            "counterparty_counts": counterparty_counts.to_dict()
        }
    
    @staticmethod
    def print_counterparty_stats(df: pd.DataFrame, counterparty_col: str = "交易对方", top_n: int = 5):
        """
        打印交易对方统计信息
        
        Args:
            df: 数据框
            counterparty_col: 交易对方列名
            top_n: 显示前N个交易对方
        """
        stats = CounterpartyAnalyzer.get_counterparty_stats(df, counterparty_col, top_n)
        
        print(f"主要交易对方: {stats['main_counterparty']} (交易次数: {stats['counterparty_counts'].get(stats['main_counterparty'], 0)})")
        print("交易对方统计:")
        for i, counterparty_info in enumerate(stats['top_counterparties']):
            print(f"  {i+1}. {counterparty_info['name']}: {counterparty_info['count']}次")
    
    @staticmethod
    def update_name_from_counterparty(df: pd.DataFrame, name_col: str = "姓名", 
                                   counterparty_col: str = "交易对方", 
                                   fallback_name: str = "未知") -> pd.DataFrame:
        """
        如果姓名为空或未知，使用主要交易主体作为姓名
        
        Args:
            df: 数据框
            name_col: 姓名列名
            counterparty_col: 交易对方列名
            fallback_name: 默认姓名
            
        Returns:
            pd.DataFrame: 更新后的数据框
        """
        if df.empty:
            return df
        
        # 分析主要交易主体
        main_counterparty = CounterpartyAnalyzer.analyze_main_counterparty(df, counterparty_col)
        
        # 如果姓名列存在
        if name_col in df.columns:
            original_name = df[name_col].iloc[0] if not df.empty else fallback_name
            
            # 检查原始姓名是否为空或未知
            if pd.isna(original_name) or str(original_name).strip() == "" or str(original_name).strip() == fallback_name:
                df[name_col] = main_counterparty
                print(f"使用主要交易主体作为姓名: {main_counterparty}")
            else:
                print(f"保持原始姓名: {original_name}")
        else:
            # 如果姓名列不存在，添加姓名列
            df[name_col] = main_counterparty
            print(f"添加姓名列，使用主要交易主体: {main_counterparty}")
        
        return df


