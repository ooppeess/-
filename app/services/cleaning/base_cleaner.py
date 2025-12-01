# -*- coding: utf-8 -*-
"""
基础清洗器类
"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional
import pandas as pd
from .utils.counterparty_analyzer import CounterpartyAnalyzer


class BaseCleaner(ABC):
    """基础清洗器抽象类"""
    
    def __init__(self):
        self.counterparty_analyzer = CounterpartyAnalyzer()
    
    @abstractmethod
    def clean(self, file_path: str, case_name: str, case_id: str, 
              person_type: str, source_type: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        清洗文件
        
        Args:
            file_path: 文件路径
            case_name: 案件名称
            case_id: 案件编号
            person_type: 人员身份
            source_type: 账单类型
            
        Returns:
            Tuple[Optional[pd.DataFrame], Optional[str]]: (数据框, 错误信息)
        """
        pass
    
    def _add_metadata(self, df: pd.DataFrame, case_name: str, case_id: str, 
                      person_type: str, source_type: str) -> pd.DataFrame:
        """
        添加元数据到数据框
        
        Args:
            df: 数据框
            case_name: 案件名称
            case_id: 案件编号
            person_type: 人员身份
            source_type: 账单类型
            
        Returns:
            pd.DataFrame: 添加元数据后的数据框
        """
        if df.empty:
            return df
        
        # 添加元数据列
        df["案件名称"] = case_name
        df["案件编号"] = case_id
        df["人员身份"] = person_type
        df["账单类型"] = source_type
        
        return df
    
    def _standardize_string_columns(self, df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """
        标准化字符串列（去除空格）
        
        Args:
            df: 数据框
            columns: 需要标准化的列名列表
            
        Returns:
            pd.DataFrame: 标准化后的数据框
        """
        for col in columns:
            if col in df.columns:
                # 确保是Series类型再调用str方法
                series = df[col].astype(str)
                df[col] = series.str.strip()  # type: ignore
        
        return df
    
    def _analyze_and_update_name(self, df: pd.DataFrame, 
                                counterparty_col: str = "交易对方",
                                name_col: str = "姓名") -> pd.DataFrame:
        """
        分析交易主体并更新姓名
        
        Args:
            df: 数据框
            counterparty_col: 交易对方列名
            name_col: 姓名列名
            
        Returns:
            pd.DataFrame: 更新后的数据框
        """
        if df.empty:
            return df
        
        # 获取账户持有人（交易主体）
        account_holder = self.counterparty_analyzer.get_account_holder(df, name_col)
        print(f"交易主体（账户持有人）: {account_holder}")
        
        # 打印交易对方统计
        self.counterparty_analyzer.print_counterparty_stats(df, counterparty_col)
        
        # 只有在姓名为空或未知时才使用主要交易对方作为姓名
        df = self.counterparty_analyzer.update_name_from_counterparty(df, name_col, counterparty_col)
        
        return df
    
    def _update_name_if_empty(self, df: pd.DataFrame, 
                             counterparty_col: str = "交易对方",
                             name_col: str = "姓名") -> pd.DataFrame:
        """
        只有在姓名为空或未知时才使用主要交易主体作为姓名
        
        Args:
            df: 数据框
            counterparty_col: 交易对方列名
            name_col: 姓名列名
            
        Returns:
            pd.DataFrame: 更新后的数据框
        """
        if df.empty:
            return df
        
        # 如果姓名列存在
        if name_col in df.columns:
            # 检查第一行的姓名
            first_name = df[name_col].iloc[0] if not df.empty else ""
            
            # 只有在姓名为空、未知或明显是占位符时才更新
            if (pd.isna(first_name) or 
                str(first_name).strip() in ["", "未知", "未知姓名", "未识别"] or
                len(str(first_name).strip()) < 2):
                
                # 分析主要交易对方
                main_counterparty = self.counterparty_analyzer.analyze_main_counterparty(df, counterparty_col)
                
                # 更新姓名
                df[name_col] = main_counterparty
                print(f"姓名为空，使用主要交易对方作为姓名: {main_counterparty}")
            else:
                print(f"保持原始姓名: {first_name}")
        else:
            # 如果姓名列不存在，添加姓名列
            main_counterparty = self.counterparty_analyzer.analyze_main_counterparty(df, counterparty_col)
            df[name_col] = main_counterparty
            print(f"添加姓名列，使用主要交易对方: {main_counterparty}")
        
        return df
    
    def _validate_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        验证数据有效性
        
        Args:
            df: 数据框
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if df.empty:
            return False, "数据为空"
        
        # 检查必需列
        required_cols = ["交易时间", "金额(元)"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"缺少必需列: {missing_cols}"
        
        return True, ""
