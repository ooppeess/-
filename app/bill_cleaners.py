#!/usr/bin/env python3
"""
账单清洗系统 - 支持多种账单格式的清洗和标准化
包括：Excel、PDF、TXT、财付通、微信、支付宝、银行流水等
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
import io

logger = logging.getLogger(__name__)

class BillCleaningError(Exception):
    """账单清洗异常"""
    pass

class BillCleanerBase:
    """账单清洗器基类"""
    
    # 统一目标字段
    TARGET_COLUMNS = [
        '案件名称', '案件编号', '人员身份', '账单来源', '账单类型',
        '姓名', '身份证', '微信号', '交易单号', '交易时间', 
        '交易类型', '收/支/其他', '交易方式', '金额(元)', 
        '交易对方', '商户单号', '备注'
    ]
    
    # 必需字段
    REQUIRED_COLUMNS = ['交易时间', '金额(元)', '交易对方']
    
    def __init__(self, case_name: str = '', case_id: str = '', 
                 person_type: str = '', source_type: str = ''):
        self.case_name = case_name
        self.case_id = case_id
        self.person_type = person_type
        self.source_type = source_type
    
    def clean(self, file_path: Path) -> pd.DataFrame:
        """清洗账单文件"""
        raise NotImplementedError("子类必须实现clean方法")
    
    def _add_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加元数据"""
        df['案件名称'] = self.case_name
        df['案件编号'] = self.case_id
        df['人员身份'] = self.person_type
        df['账单来源'] = self.source_type
        return df
    
    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证数据完整性"""
        if df.empty:
            raise BillCleaningError("清洗后的数据为空")
        
        # 检查必需字段
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise BillCleaningError(f"缺少必需列: {missing_cols}")
        
        # 删除必需字段为空的行
        df = df.dropna(subset=self.REQUIRED_COLUMNS)
        
        if df.empty:
            raise BillCleaningError("清洗后所有必需字段都为空")
        
        return df
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        # 金额列标准化
        amount_cols = ['金额', '交易金额', '金额(元)', 'amount', 'money']
        for col in amount_cols:
            if col in df.columns:
                df = df.rename(columns={col: '金额(元)'})
                break
        
        # 时间列标准化
        time_cols = ['交易时间', '交易日期', '日期', 'time', 'date']
        for col in time_cols:
            if col in df.columns:
                df = df.rename(columns={col: '交易时间'})
                break
        
        # 交易对方标准化
        counterparty_cols = [
            '交易对方', '对方名称', '微信昵称', '对端', 
            '对手侧账户名称', '第三方账户名称', '对手方ID'
        ]
        for col in counterparty_cols:
            if col in df.columns:
                df = df.rename(columns={col: '交易对方'})
                break
        
        return df

class ExcelCleaner(BillCleanerBase):
    """Excel账单清洗器"""
    
    # Excel列名映射
    COLUMN_MAPPING = {
        # 姓名相关
        '姓名': ['持卡人', '户名', '客户名称', '账户名称', '用户侧账号名称'],
        # 身份证相关
        '身份证': ['身份证号', '证件号码'],
        # 微信号相关
        '微信号': ['微信号', '用户ID', '账户', '账号'],
        # 时间相关
        '交易时间': ['交易日期', '日期', '时间', '交易时间', '记账日期'],
        # 金额相关
        '金额': ['交易金额', '金额(元)', '金额', '发生额', '借方金额', '贷方金额'],
        # 交易对方
        '交易对方': ['交易对方', '对端', '对方名称', '微信昵称', '对手侧账户名称', '对方户名']
    }
    
    def clean(self, file_path: Path) -> pd.DataFrame:
        """清洗Excel账单"""
        logger.info(f"开始清洗Excel文件: {file_path}")
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path, engine="openpyxl")
            logger.info(f"原始数据行数: {len(df)}, 列数: {len(df.columns)}")
            
            # 标准化列名
            df = self._standardize_excel_columns(df)
            
            # 筛选必需列
            df = self._filter_required_columns(df)
            
            # 添加元数据
            df = self._add_metadata(df)
            
            # 标准化字符串列
            df = self._standardize_string_columns(df)
            
            # 处理数据类型
            df = self._process_data_types(df)
            
            # 更新姓名（如果为空）
            df = self._update_name_if_empty(df)
            
            # 验证数据
            df = self._validate_data(df)
            
            logger.info(f"清洗完成，最终数据行数: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"Excel清洗失败: {e}")
            raise BillCleaningError(f"Excel文件清洗失败: {e}")
    
    def _standardize_excel_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化Excel列名"""
        column_mapping = {}
        
        for standard_name, possible_names in self.COLUMN_MAPPING.items():
            for possible_name in possible_names:
                if possible_name in df.columns:
                    column_mapping[possible_name] = standard_name
                    break
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
            logger.info(f"列名映射: {column_mapping}")
        
        return df
    
    def _filter_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """筛选必需列"""
        expected_columns = ['姓名', '身份证号', '微信号', '交易时间', '交易类型', '金额', '微信昵称', '对方账号']
        
        # 检查是否存在期望的列
        existing_columns = [col for col in expected_columns if col in df.columns]
        
        if existing_columns:
            df = df[existing_columns]
            logger.info(f"保留列: {existing_columns}")
        else:
            logger.warning("未找到期望的列，保留所有列")
        
        return df
    
    def _standardize_string_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化字符串列"""
        string_columns = ['姓名', '身份证号', '微信号', '微信昵称', '对方账号']
        
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        
        return df
    
    def _process_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理数据类型"""
        # 处理交易时间
        if '交易时间' in df.columns:
            df['交易时间'] = pd.to_datetime(df['交易时间'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        
        # 处理金额
        if '金额' in df.columns:
            df['金额'] = pd.to_numeric(df['金额'], errors='coerce')
        
        return df
    
    def _update_name_if_empty(self, df: pd.DataFrame) -> pd.DataFrame:
        """如果姓名为空，从交易对方统计中补全"""
        if '姓名' not in df.columns or df['姓名'].isna().all():
            if '微信昵称' in df.columns:
                # 统计主要交易对方
                counterparty_stats = df['微信昵称'].value_counts()
                if not counterparty_stats.empty:
                    main_counterparty = counterparty_stats.index[0]
                    df['姓名'] = main_counterparty
                    logger.info(f"姓名为空，使用主要交易对方补全: {main_counterparty}")
        
        return df

class PDFCleaner(BillCleanerBase):
    """PDF账单清洗器"""
    
    def clean(self, file_path: Path) -> pd.DataFrame:
        """清洗PDF账单"""
        logger.info(f"开始清洗PDF文件: {file_path}")
        
        try:
            import pdfplumber
            
            # 检查文件
            if not file_path.exists() or file_path.stat().st_size == 0:
                raise BillCleaningError("PDF文件不存在或为空")
            
            # 打开PDF文件
            with pdfplumber.open(file_path) as pdf:
                # 提取个人信息
                personal_info = self._extract_personal_info(pdf, file_path)
                
                # 提取表格数据
                table_data = self._extract_table_data(pdf)
                
                if table_data.empty:
                    raise BillCleaningError("未找到有效的表格数据")
                
                # 构建DataFrame
                df = self._create_dataframe(table_data, personal_info)
                
                # 处理数据类型
                df = self._process_data_types(df)
                
                # 添加个人信息
                df = self._add_personal_info(df, personal_info)
                
                # 添加元数据
                df = self._add_metadata(df)
                
                # 验证数据
                df = self._validate_data(df)
                
                logger.info(f"PDF清洗完成，数据行数: {len(df)}")
                return df
                
        except ImportError:
            raise BillCleaningError("缺少pdfplumber库，无法处理PDF文件")
        except Exception as e:
            logger.error(f"PDF清洗失败: {e}")
            raise BillCleaningError(f"PDF文件清洗失败: {e}")
    
    def _extract_personal_info(self, pdf, file_path: Path) -> Dict[str, str]:
        """从PDF中提取个人信息"""
        personal_info = {
            '姓名': '',
            '身份证': '',
            '微信号': ''
        }
        
        # 从文件名提取信息
        filename = file_path.stem
        
        # 尝试从PDF文本中提取
        for page in pdf.pages[:3]:  # 只检查前3页
            text = page.extract_text()
            if text:
                # 提取姓名
                name_match = re.search(r'姓名[:：]\s*([^\n]+)', text)
                if name_match:
                    personal_info['姓名'] = name_match.group(1).strip()
                
                # 提取身份证号
                id_match = re.search(r'身份证[:：]\s*(\d+)', text)
                if id_match:
                    personal_info['身份证'] = id_match.group(1).strip()
                
                # 提取微信号
                wechat_match = re.search(r'微信号[:：]\s*([^\n]+)', text)
                if wechat_match:
                    personal_info['微信号'] = wechat_match.group(1).strip()
        
        # 如果PDF中没有，尝试从文件名提取
        if not personal_info['姓名']:
            # 假设文件名格式包含姓名
            name_parts = filename.split()
            if len(name_parts) > 1:
                personal_info['姓名'] = name_parts[0]
        
        return personal_info
    
    def _extract_table_data(self, pdf) -> pd.DataFrame:
        """从PDF中提取表格数据"""
        all_tables = []
        
        for page in pdf.pages:
            tables = page.extract_tables()
            
            for table in tables:
                if table and len(table) > 1:  # 至少要有表头和一行数据
                    # 检查是否包含关键字段
                    header_row = table[0]
                    key_fields = ['交易时间', '交易单号', '金额', '交易对方']
                    
                    if any(field in str(header_row) for field in key_fields):
                        df = pd.DataFrame(table[1:], columns=table[0])
                        all_tables.append(df)
        
        if all_tables:
            return pd.concat(all_tables, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def _create_dataframe(self, table_data: pd.DataFrame, personal_info: Dict[str, str]) -> pd.DataFrame:
        """构建标准DataFrame"""
        # 重命名列
        column_mapping = {
            '交易单号': '交易单号',
            '交易时间': '交易时间',
            '交易类型': '交易类型',
            '收/支/其他': '收/支/其他',
            '交易方式': '交易方式',
            '金额(元)': '金额(元)',
            '交易对方': '微信昵称',  # 临时名称
            '商户单号': '商户单号'
        }
        
        # 标准化列名
        for col in table_data.columns:
            for standard_name, possible_names in column_mapping.items():
                if isinstance(possible_names, list):
                    if col in possible_names:
                        table_data = table_data.rename(columns={col: standard_name})
                        break
                elif col == possible_names:
                    table_data = table_data.rename(columns={col: standard_name})
                    break
        
        # 确保有必需的列
        required_cols = ['交易单号', '交易时间', '金额(元)', '微信昵称']
        for col in required_cols:
            if col not in table_data.columns:
                table_data[col] = ''
        
        return table_data
    
    def _process_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理PDF数据类型"""
        # 处理交易时间
        if '交易时间' in df.columns:
            df['交易时间'] = pd.to_datetime(df['交易时间'], errors='coerce')
        
        # 处理金额
        if '金额(元)' in df.columns:
            # 根据交易类型确定金额符号
            if '收/支/其他' in df.columns:
                df['收/支/其他'] = df['收/支/其他'].astype(str).str.strip()
                
                # 根据交易类型纠正收/支
                expense_keywords = ['消费', '付款', '支付', '转出', '提现', '扣费']
                income_keywords = ['退款', '入账', '收款', '转入', '充值', '退回']
                
                for i, row in df.iterrows():
                    transaction_type = str(row.get('交易类型', ''))
                    
                    if any(keyword in transaction_type for keyword in expense_keywords):
                        df.at[i, '收/支/其他'] = '支出'
                    elif any(keyword in transaction_type for keyword in income_keywords):
                        df.at[i, '收/支/其他'] = '收入'
                
                # 处理金额符号
                for i, row in df.iterrows():
                    direction = row.get('收/支/其他', '')
                    amount_str = str(row.get('金额(元)', '0'))
                    
                    # 提取数字
                    amount_match = re.search(r'[\d+\-.]+', amount_str)
                    if amount_match:
                        amount = float(amount_match.group())
                        
                        if direction == '支出':
                            amount = -abs(amount)
                        elif direction == '收入':
                            amount = abs(amount)
                        
                        df.at[i, '金额(元)'] = amount
        
        return df
    
    def _add_personal_info(self, df: pd.DataFrame, personal_info: Dict[str, str]) -> pd.DataFrame:
        """添加个人信息"""
        df['姓名'] = personal_info.get('姓名', '')
        df['身份证'] = personal_info.get('身份证', '')
        df['微信号'] = personal_info.get('微信号', '')
        return df

class TXTCleaner(BillCleanerBase):
    """TXT账单清洗器"""
    
    def clean(self, file_path: Path) -> pd.DataFrame:
        """清洗TXT账单"""
        logger.info(f"开始清洗TXT文件: {file_path}")
        
        try:
            # 尝试读取文件
            content = self._read_file_with_encoding(file_path)
            
            if not content:
                raise BillCleaningError("无法读取TXT文件内容")
            
            # 判断文件格式
            if self._is_wechat_format(content):
                logger.info("识别为微信/财付通格式")
                df = self._clean_wechat_format(content)
            elif self._is_tenpay_format(content):
                logger.info("识别为财付通格式")
                df = self._clean_tenpay_format(content)
            else:
                logger.info("使用通用TXT格式")
                df = self._clean_generic_format(content)
            
            # 标准化列名
            df = self._standardize_columns(df)
            
            # 处理数据类型
            df = self._process_data_types(df)
            
            # 添加元数据
            df = self._add_metadata(df)
            
            # 验证数据
            df = self._validate_data(df)
            
            logger.info(f"TXT清洗完成，数据行数: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"TXT清洗失败: {e}")
            raise BillCleaningError(f"TXT文件清洗失败: {e}")
    
    def _read_file_with_encoding(self, file_path: Path) -> Optional[str]:
        """使用多种编码尝试读取文件"""
        encodings = [
            'utf-8', 'utf-8-sig', 'gb18030', 'gbk', 'cp936',
            'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'big5'
        ]
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"成功使用 {encoding} 编码读取文件")
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"使用 {encoding} 编码读取失败: {e}")
                continue
        
        return None
    
    def _is_wechat_format(self, content: str) -> bool:
        """判断是否为微信格式"""
        lines = content.split('\n')
        if len(lines) < 2:
            return False
        
        header = lines[0]
        wechat_keywords = ['用户ID', '交易单号', '借贷类型', '交易金额(分)', '交易时间']
        
        return any(keyword in header for keyword in wechat_keywords)
    
    def _is_tenpay_format(self, content: str) -> bool:
        """判断是否为财付通格式"""
        tenpay_keywords = [
            '用户ID', '交易单号', '大单号', '用户侧账号名称',
            '借贷类型', '交易业务类型', '交易用途类型'
        ]
        
        return sum(1 for keyword in tenpay_keywords if keyword in content) >= 3
    
    def _clean_wechat_format(self, content: str) -> pd.DataFrame:
        """清洗微信格式"""
        lines = content.strip().split('\n')
        
        if len(lines) < 2:
            return pd.DataFrame()
        
        # 读取为DataFrame
        from io import StringIO
        df = pd.read_csv(StringIO(content), sep='\t')
        
        # 字段映射
        column_mapping = {
            '用户侧账号名称': '姓名',
            '用户ID': '微信号',
            '交易单号': '交易单号',
            '交易时间': '交易时间',
            '交易用途类型': '交易类型',
            '交易业务类型': '交易方式',
            '交易金额(分)': '金额_分',
            '借贷类型': '借贷类型',
            '对手侧账户名称': '交易对方',
            '大单号': '商户单号',
            '备注1': '备注'
        }
        
        # 重命名存在的列
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 处理金额
        if '金额_分' in df.columns and '借贷类型' in df.columns:
            df['金额_分'] = pd.to_numeric(df['金额_分'], errors='coerce')
            
            # 根据借贷类型确定符号
            sign_map = {'入': 1, '出': -1}
            df['符号'] = df['借贷类型'].map(sign_map).fillna(1)
            
            df['金额(元)'] = df['金额_分'] * df['符号']
        
        # 处理交易时间
        if '交易时间' in df.columns:
            df['交易时间'] = pd.to_datetime(df['交易时间'], errors='coerce')
        
        # 处理交易对方
        if '交易对方' not in df.columns:
            # 从备选字段中选择
            counterparty_fields = ['第三方账户名称', '对手方ID']
            for field in counterparty_fields:
                if field in df.columns:
                    df['交易对方'] = df[field]
                    break
            else:
                df['交易对方'] = '未知'
        
        return df
    
    def _clean_tenpay_format(self, content: str) -> pd.DataFrame:
        """清洗财付通格式"""
        # 财付通格式与微信格式类似，可以复用逻辑
        return self._clean_wechat_format(content)
    
    def _clean_generic_format(self, content: str) -> pd.DataFrame:
        """清洗通用TXT格式"""
        lines = content.strip().split('\n')
        
        if len(lines) < 2:
            return pd.DataFrame()
        
        # 尝试读取为制表符分隔的文件
        try:
            from io import StringIO
            df = pd.read_csv(StringIO(content), sep='\t')
            
            # 通用字段映射
            self._apply_generic_mapping(df)
            
            return df
        except:
            # 如果失败，尝试其他分隔符
            try:
                df = pd.read_csv(StringIO(content), sep=',')
                self._apply_generic_mapping(df)
                return df
            except:
                return pd.DataFrame()
    
    def _apply_generic_mapping(self, df: pd.DataFrame) -> None:
        """应用通用字段映射"""
        # 姓名映射
        name_fields = ['姓名', '持卡人', '户名', '客户名称', '账户名称', '用户侧账号名称']
        for field in name_fields:
            if field in df.columns:
                df['姓名'] = df[field]
                break
        
        # 身份证映射
        id_fields = ['身份证', '身份证号', '证件号码']
        for field in id_fields:
            if field in df.columns:
                df['身份证'] = df[field]
                break
        
        # 微信号映射
        wechat_fields = ['微信号', '用户ID', '账户', '账号']
        for field in wechat_fields:
            if field in df.columns:
                df['微信号'] = df[field]
                break
        
        # 交易时间映射
        time_fields = ['交易时间', '交易日期', '日期', '时间', 'time', 'date']
        for field in time_fields:
            if field in df.columns:
                df['交易时间'] = pd.to_datetime(df[field], errors='coerce')
                break
        
        # 金额映射
        amount_fields = ['金额', '交易金额', '金额(元)', 'amount', 'money']
        for field in amount_fields:
            if field in df.columns:
                df['金额(元)'] = pd.to_numeric(df[field], errors='coerce')
                break
        
        # 交易对方映射
        counterparty_fields = ['交易对方', '对方名称', '微信昵称', '对端', '对手侧账户名称']
        for field in counterparty_fields:
            if field in df.columns:
                df['交易对方'] = df[field]
                break

class TenpayCleaner(BillCleanerBase):
    """财付通专用清洗器"""
    
    # 财付通标准字段
    TENPAY_COLUMNS = [
        '用户ID', '交易单号', '大单号', '用户侧账号名称', '借贷类型',
        '交易业务类型', '交易用途类型', '交易时间', '交易金额(分)',
        '账户余额(分)', '用户银行卡号', '用户侧网银联单号', '网联/银联',
        '第三方账户名称', '对手方ID', '对手侧账户名称', '对手方银行卡号',
        '对手方银行名称', '对手侧网银联单号', '网联/银联', '基金公司信息',
        '间联/非间联交易', '第三方账户名称', '对手方接收时间', '对手方接收金额(分)',
        '备注1', '备注2'
    ]
    
    def clean(self, file_path: Path) -> pd.DataFrame:
        """清洗财付通账单"""
        logger.info(f"开始清洗财付通文件: {file_path}")
        
        try:
            content = self._read_tenpay_file(file_path)
            df = self._clean_tenpay_data(content)
            
            # 标准化列名
            df = self._standardize_columns(df)
            
            # 处理数据类型
            df = self._process_data_types(df)
            
            # 添加元数据
            df = self._add_metadata(df)
            
            # 验证数据
            df = self._validate_data(df)
            
            logger.info(f"财付通清洗完成，数据行数: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"财付通清洗失败: {e}")
            raise BillCleaningError(f"财付通文件清洗失败: {e}")
    
    def _read_tenpay_file(self, file_path: Path) -> str:
        """读取财付通文件"""
        encodings = ['gb18030', 'gbk', 'utf-8', 'utf-8-sig']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        raise BillCleaningError("无法使用任何编码读取财付通文件")
    
    def _clean_tenpay_data(self, content: str) -> pd.DataFrame:
        """清洗财付通数据"""
        lines = content.strip().split('\n')
        
        if len(lines) < 2:
            return pd.DataFrame()
        
        # 读取为DataFrame
        from io import StringIO
        df = pd.read_csv(StringIO(content), sep='\t')
        
        # 字段映射
        column_mapping = {
            '用户侧账号名称': '姓名',
            '用户ID': '微信号',
            '交易单号': '交易单号',
            '交易时间': '交易时间',
            '交易用途类型': '交易类型',
            '交易业务类型': '交易方式',
            '交易金额(分)': '金额_分',
            '借贷类型': '借贷类型',
            '对手侧账户名称': '交易对方',
            '大单号': '商户单号',
            '备注1': '备注'
        }
        
        # 重命名存在的列
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 处理金额
        if '金额_分' in df.columns and '借贷类型' in df.columns:
            df['金额_分'] = pd.to_numeric(df['金额_分'], errors='coerce')
            
            # 根据借贷类型确定符号
            sign_map = {'入': 1, '出': -1}
            df['符号'] = df['借贷类型'].map(sign_map).fillna(1)
            
            df['金额(元)'] = df['金额_分'] * df['符号']
        
        # 处理交易时间
        if '交易时间' in df.columns:
            df['交易时间'] = pd.to_datetime(df['交易时间'], errors='coerce')
        
        # 处理备注
        if '备注' in df.columns and '备注2' in df.columns:
            df['备注'] = df['备注'].fillna('') + df['备注2'].fillna('')
        
        return df
    
    def _process_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理财付通数据类型"""
        # 处理乱码的借贷类型
        if '借贷类型' in df.columns:
            df['借贷类型'] = df['借贷类型'].astype(str)
            
            # 处理乱码
            df.loc[df['借贷类型'].str.contains('³ö', na=False), '借贷类型'] = '出'
            df.loc[df['借贷类型'].str.contains('Èë', na=False), '借贷类型'] = '入'
        
        # 处理收/支/其他
        if '借贷类型' in df.columns:
            df['收/支/其他'] = df['借贷类型'].map({'入': '收', '出': '支'}).fillna('其他')
        
        # 处理交易对方
        if '交易对方' not in df.columns or df['交易对方'].isna().all():
            # 从备选字段中选择
            counterparty_fields = ['第三方账户名称.1', '第三方账户名称', '对手方ID']
            for field in counterparty_fields:
                if field in df.columns:
                    df['交易对方'] = df[field]
                    break
        
        return df

class CleaningService:
    """数据清洗服务"""
    
    def __init__(self):
        self.cleaners = {
            '.xlsx': ExcelCleaner(),
            '.xls': ExcelCleaner(),
            '.pdf': PDFCleaner(),
            '.txt': TXTCleaner()
        }
    
    def clean_file(self, file_path: Path, file_type: str, 
                   case_name: str = '', case_id: str = '',
                   person_type: str = '', source_type: str = '') -> pd.DataFrame:
        """清洗文件"""
        logger.info(f"开始清洗文件: {file_path}, 类型: {file_type}")
        allowed_identities = {"盗窃人员", "收脏人员", "排查人员"}
        if person_type not in allowed_identities:
            raise BillCleaningError("人员身份必须为：盗窃人员/收脏人员/排查人员 之一")
        
        # 创建清洗器
        if file_type in self.cleaners:
            cleaner = self.cleaners[file_type]
            cleaner.case_name = case_name
            cleaner.case_id = case_id
            cleaner.person_type = person_type
            cleaner.source_type = source_type
            
            df = cleaner.clean(file_path)
        else:
            raise BillCleaningError(f"不支持的文件类型: {file_type}")
        
        # 标准化列名
        df = self._standardize_columns(df)
        
        # 处理金额单位
        df = self._convert_amount_unit(df, '元')  # 默认元

        # 去噪处理：交易对方严格去空格及特殊符号
        if '交易对方' in df.columns:
            df['交易对方'] = df['交易对方'].astype(str)
            df['交易对方'] = df['交易对方'].str.replace(r'[^\w\u4e00-\u9fa5]', '', regex=True)
            df['交易对方'] = df['交易对方'].str.strip()

        # 金额过滤：删除 |金额| < 100 的记录（绝对值）
        if '金额(元)' in df.columns:
            df['金额(元)'] = pd.to_numeric(df['金额(元)'], errors='coerce').fillna(0)
            df = df[df['金额(元)'].abs() >= 100].copy()
            if df.empty:
                raise BillCleaningError("过滤金额后数据为空（所有记录金额绝对值均小于100）")
        
        # 验证必需列
        df = self._validate_required_columns(df)
        
        # 排序
        if '交易时间' in df.columns:
            df = df.sort_values('交易时间')
        
        logger.info(f"数据清洗完成，最终行数: {len(df)}")
        return df
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        return BillCleanerBase._standardize_columns(self, df)
    
    def _convert_amount_unit(self, df: pd.DataFrame, unit: str) -> pd.DataFrame:
        """转换金额单位"""
        if '金额(元)' not in df.columns:
            return df
        
        df['金额(元)'] = pd.to_numeric(df['金额(元)'], errors='coerce')
        
        if unit == '角':
            df['金额(元)'] = df['金额(元)'] / 10
        elif unit == '分':
            df['金额(元)'] = df['金额(元)'] / 100
        
        return df
    
    def _validate_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证必需列"""
        return BillCleanerBase._validate_required_columns(self, df)

# 使用示例
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建清洗服务
    cleaning_service = CleaningService()
    
    # 测试文件路径
    test_files = [
        ("/path/to/test.xlsx", ".xlsx"),
        ("/path/to/test.pdf", ".pdf"),
        ("/path/to/test.txt", ".txt")
    ]
    
    for file_path, file_type in test_files:
        try:
            if Path(file_path).exists():
                df = cleaning_service.clean_file(
                    Path(file_path), file_type,
                    case_name="测试案件",
                    case_id="CASE-001",
                    person_type="嫌疑人",
                    source_type="微信"
                )
                print(f"{file_type} 文件清洗成功，数据行数: {len(df)}")
                print(df.head())
        except Exception as e:
            print(f"{file_type} 文件清洗失败: {e}")
