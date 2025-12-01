# -*- coding: utf-8 -*-
"""
姓名提取工具
"""
import re
import os
from typing import Optional, Tuple


class NameExtractor:
    """姓名提取器"""
    
    @staticmethod
    def extract_from_filename(file_path: str) -> Optional[str]:
        """
        从文件名中提取姓名
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[str]: 提取的姓名，如果未找到则返回None
        """
        filename = os.path.basename(file_path)
        
        # 微信支付交易明细证明文件名模式
        patterns = [
            r'([\u4e00-\u9fa5]{2,4})（[^）]*）\s*微信支付交易明细证明',
            r'([\u4e00-\u9fa5]{2,4})\([^)]*\)\s*微信支付交易明细证明',
            r'([\u4e00-\u9fa5]{2,4})\d*\s*微信支付交易明细证明',
            r'([\u4e00-\u9fa5]{2,4})\s*微信支付交易明细证明'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def extract_from_content(text: str) -> Optional[str]:
        """
        从PDF内容中提取姓名
        
        Args:
            text: PDF提取的文本内容
            
        Returns:
            Optional[str]: 提取的姓名，如果未找到则返回None
        """
        # 多种姓名提取模式
        patterns = [
            r'兹证明[:：\s]*(.+?)(?:[\s（(]|$)',
            r'姓名[:：\s]*(.+?)(?:[\s（(]|$)',
            r'户名[:：\s]*(.+?)(?:[\s（(]|$)',
            r'客户名称[:：\s]*(.+?)(?:[\s（(]|$)',
            r'账单证明[:：\s]*(.+?)(?:[\s（(]|$)',
            r'微信支付[:：\s]*(.+?)(?:[\s（(]|$)',
            r'交易明细[:：\s]*(.+?)(?:[\s（(]|$)',
            r'([\u4e00-\u9fa5]+)[\s　]*先生|女士|小姐',
            r'([\u4e00-\u9fa5]+)[\s　]*的微信支付',
            r'([\u4e00-\u9fa5]+)[\s　]*的.*证明',
            r'[^\n]*[:：]\s*([\u4e00-\u9fa5]+)(?:\s|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match and match.group(1):
                name = match.group(1).strip()
                # 过滤掉明显不是姓名的内容
                if len(name) >= 2 and len(name) <= 4 and not any(char in name for char in ['交易', '明细', '证明', '支付']):
                    return name
        
        return None
    
    @staticmethod
    def extract_from_pdf(file_path: str, text: str) -> Tuple[Optional[str], str]:
        """
        从PDF文件中提取姓名（优先内容，其次文件名）
        
        Args:
            file_path: PDF文件路径
            text: PDF提取的文本内容
            
        Returns:
            Tuple[Optional[str], str]: (提取的姓名, 提取来源)
        """
        # 首先尝试从内容中提取
        content_name = NameExtractor.extract_from_content(text)
        if content_name:
            return content_name, "PDF内容"
        
        # 然后尝试从文件名中提取
        filename_name = NameExtractor.extract_from_filename(file_path)
        if filename_name:
            return filename_name, "文件名"
        
        return None, "未找到"
    
    @staticmethod
    def extract_from_text_file(file_path: str) -> Tuple[Optional[str], str]:
        """
        从文本文件中提取姓名（优先内容，其次文件名）
        
        Args:
            file_path: 文本文件路径
            
        Returns:
            Tuple[Optional[str], str]: (提取的姓名, 提取来源)
        """
        try:
            # 尝试读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        except UnicodeDecodeError:
            try:
                # 如果UTF-8失败，尝试GBK编码
                with open(file_path, 'r', encoding='gbk') as f:
                    text_content = f.read()
            except Exception:
                # 如果都失败，只从文件名提取
                filename_name = NameExtractor.extract_from_filename(file_path)
                return filename_name, "文件名" if filename_name else "未找到"
        except Exception:
            # 如果读取失败，只从文件名提取
            filename_name = NameExtractor.extract_from_filename(file_path)
            return filename_name, "文件名" if filename_name else "未找到"
        
        # 首先尝试从内容中提取
        content_name = NameExtractor.extract_from_content(text_content)
        if content_name:
            return content_name, "文件内容"
        
        # 然后尝试从文件名中提取
        filename_name = NameExtractor.extract_from_filename(file_path)
        if filename_name:
            return filename_name, "文件名"
        
        return None, "未找到"
    
    @staticmethod
    def extract_id_card(text: str) -> Optional[str]:
        """
        从文本中提取身份证号
        
        Args:
            text: 文本内容
            
        Returns:
            Optional[str]: 提取的身份证号，如果未找到则返回None
        """
        patterns = [
            r"(身份证|身份证号)[:：\s]*([0-9Xx]{15,18})",
            r"证件号码[:：\s]*([0-9Xx]{15,18})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(2) if len(match.groups()) > 1 else match.group(1)
        
        return None
    
    @staticmethod
    def extract_wechat_id(text: str) -> Optional[str]:
        """
        从文本中提取微信号
        
        Args:
            text: 文本内容
            
        Returns:
            Optional[str]: 提取的微信号，如果未找到则返回None
        """
        patterns = [
            r"(微信号|微信号:)[:：\s]*([a-zA-Z0-9_\-]+)",
            r"账户[:：\s]*([a-zA-Z0-9_\-]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(2) if len(match.groups()) > 1 else match.group(1)
        
        return None


