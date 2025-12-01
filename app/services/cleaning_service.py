import os
import pandas as pd
from app.services.cleaning.excel_cleaner import ExcelCleaner
from app.services.cleaning.txt_cleaner import TXTCleaner
from app.services.cleaning.pdf_cleaner import PDFCleaner

class CleaningService:
    def __init__(self):
        self.cleaners = {
            '.xlsx': ExcelCleaner(),
            '.xls': ExcelCleaner(),
            '.pdf': PDFCleaner(),
            '.txt': TXTCleaner(),
            '.csv': TXTCleaner() # CSV也用TXT清洗器处理（兼容性更好）
        }
    
    def clean_file(self, file_path: str, case_info: dict) -> pd.DataFrame:
        """
        统一清洗入口
        :param file_path: 文件绝对路径
        :param case_info: 包含 case_id, case_name, person_type, amount_unit 的字典
        """
        # 获取文件后缀
        ext = os.path.splitext(file_path)[1].lower()
        
        # 找到对应的清洗器
        cleaner = self.cleaners.get(ext)
        if not cleaner:
            raise ValueError(f"不支持的文件类型: {ext}")
            
        # 提取参数
        case_name = case_info.get('case_name', '')
        case_id = case_info.get('case_id', '')
        person_type = case_info.get('person_type', '排查人员')
        source_type = 'unknown' # 默认为未知，清洗器内部会尝试识别
        
        # --- 关键修复：统一调用签名 ---
        # 所有 cleaner 的 clean 方法都必须支持这些参数
        df, error = cleaner.clean(
            file_path=str(file_path),
            case_name=case_name,
            case_id=case_id,
            person_type=person_type,
            source_type=source_type
        )
        
        if error:
            raise ValueError(error)
            
        return df
import os
import pandas as pd
from app.services.cleaning.excel_cleaner import ExcelCleaner
from app.services.cleaning.txt_cleaner import TXTCleaner
from app.services.cleaning.pdf_cleaner import PDFCleaner

class CleaningService:
    def __init__(self):
        self.cleaners = {
            '.xlsx': ExcelCleaner(),
            '.xls': ExcelCleaner(),
            '.pdf': PDFCleaner(),
            '.txt': TXTCleaner(),
            '.csv': TXTCleaner() # CSV也用TXT清洗器处理（兼容性更好）
        }
    
    def clean_file(self, file_path: str, case_info: dict) -> pd.DataFrame:
        """
        统一清洗入口
        :param file_path: 文件绝对路径
        :param case_info: 包含 case_id, case_name, person_type, amount_unit 的字典
        """
        # 获取文件后缀
        ext = os.path.splitext(file_path)[1].lower()
        
        # 找到对应的清洗器
        cleaner = self.cleaners.get(ext)
        if not cleaner:
            raise ValueError(f"不支持的文件类型: {ext}")
            
        # 提取参数
        case_name = case_info.get('case_name', '')
        case_id = case_info.get('case_id', '')
        person_type = case_info.get('person_type', '排查人员')
        source_type = 'unknown' # 默认为未知，清洗器内部会尝试识别
        
        # --- 关键修复：统一调用签名 ---
        # 所有 cleaner 的 clean 方法都必须支持这些参数
        df, error = cleaner.clean(
            file_path=str(file_path),
            case_name=case_name,
            case_id=case_id,
            person_type=person_type,
            source_type=source_type
        )
        
        if error:
            raise ValueError(error)
            
        return df
