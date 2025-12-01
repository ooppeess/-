# FundX/main.py
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, ORJSONResponse
from starlette.middleware.gzip import GZipMiddleware
from database import init_db, get_db_connection
import shutil
import os
import pathlib
import json

# 导入数据库初始化

# --- 导入您新写的服务模块 ---
# 注意：这里适配了您修改后的类名 IngestionService
from app.services.ingestion import IngestionService 
from app.services.single_analysis import get_trend_analysis, get_statistics_table, get_key_counterparties
from app.services.multi_analysis import analyze_stolen_distribution_known, find_hidden_partners, get_22_interaction

# 初始化应用
app = FastAPI(title="资金分析平台独立版", default_response_class=ORJSONResponse)

# 挂载静态文件与模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 初始化入库服务
service = IngestionService()

# 启动事件
@app.on_event("startup")
def startup_event():
    init_db()

# --- 页面路由 (保持不变) ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/page/single-analysis", response_class=HTMLResponse)
async def page_single_analysis(request: Request):
    return templates.TemplateResponse("single_analysis_dashboard.html", {"request": request})

@app.get("/page/multi-analysis", response_class=HTMLResponse)
async def page_multi_analysis(request: Request):
    return templates.TemplateResponse("multi_analysis_dashboard.html", {"request": request})

@app.get("/case-management", response_class=HTMLResponse)
async def case_management(request: Request):
    return templates.TemplateResponse("case-management.html", {"request": request})

@app.get("/data-visualization", response_class=HTMLResponse)
async def data_visualization(request: Request):
    return templates.TemplateResponse("data-visualization.html", {"request": request})

# --- 核心 API：上传与入库 ---
@app.post("/api/upload")
async def upload_file(
    files: list[UploadFile] = File(None),
    file: UploadFile | None = File(None),
    case_name: str = Form(""),
    case_id: str = Form(""),
    file_configs: str = Form("{}")
):
    # 兼容单文件字段名为 file 的情况
    if (not files or len(files) == 0) and file is not None:
        files = [file]
    if not files:
        return {"status": "error", "message": "未选择文件"}
    if not case_name or not case_id:
        return {"status": "error", "message": "请填写案件名称和编号"}

    try:
        configs = json.loads(file_configs) if file_configs else {}
        if isinstance(configs, list):
            # 兼容列表结构，转换为按文件名的字典
            configs = {c.get('filename', f"file_{i}"): {"type": c.get('type', '排查人员'), "unit": c.get('unit', 'yuan')} for i, c in enumerate(configs)}
    except Exception:
        configs = {}

    success_count = 0
    errors = []

    temp_dir = pathlib.Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)

    for file in files:
        try:
            config = configs.get(file.filename, {})
            person_type = config.get('type', '排查人员')
            amount_unit = config.get('unit', 'yuan')

            temp_path = temp_dir / file.filename
            with temp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            case_info = {
                "case_name": case_name,
                "case_id": case_id,
                "person_type": person_type,
                "amount_unit": amount_unit
            }

            file_ext = os.path.splitext(file.filename)[1].lower()
            service.process_and_save(temp_path, file_ext, case_info)
            success_count += 1
        except Exception as e:
            print(f"文件 {file.filename} 处理失败: {e}")
            errors.append(f"{file.filename}: {str(e)}")
        finally:
            if 'temp_path' in locals() and temp_path.exists():
                os.remove(temp_path)

    if success_count == 0 and errors:
        return {"status": "error", "message": "\n".join(errors)}

    msg = f"成功处理 {success_count} 个文件"
    if errors:
        msg += f"，失败 {len(errors)} 个（请检查格式）"

    return {
        "status": "success",
        "message": msg,
        "case_id": case_id
    }

# --- 单账单分析 API ---

@app.get("/api/analysis/single/trend")
async def api_trend(case_id: str, person: str, min: float = 0, max: float = None):
    """单账单-趋势图"""
    data = get_trend_analysis(case_id, person, min_amount=min, max_amount=max)
    return {"data": data}

@app.get("/api/analysis/single/stats")
async def api_stats(case_id: str, person: str, filter: str = 'all'):
    """单账单-统计表 (支持 income_only, expense_only, high_ratio)"""
    data = get_statistics_table(case_id, person, filter_type=filter)
    return {"data": data}

@app.get("/api/analysis/single/keywords")
async def api_keywords(case_id: str):
    """单账单-重点对端 (烟酒/超市等)"""
    data = get_key_counterparties(case_id)
    return {"data": data}

# --- 多账单分析 API (核心重构) ---

@app.get("/api/analysis/multi/interaction")
async def api_interaction(case_id: str):
    """
    多账单-资金交互情况一览 (22交互)
    """
    data = get_22_interaction(case_id)
    # 转换为前端 Network 图需要的节点和边
    nodes = set()
    links = []
    
    # 这里简单处理数据格式以适配前端
    for row in data:
        # row 是 tuple: (source, source_type, target, target_type, time, amount, order_id)
        # 注意：DuckDB fetchdf() 返回 DataFrame, 这里根据您 multi_analysis 返回类型调整
        # 如果是 DataFrame:
        src = row[0] # source
        tgt = row[2] # target
        amt = row[5] # amount
        
        nodes.add(src)
        nodes.add(tgt)
        links.append({
            "source": src,
            "target": tgt,
            "value": amt,
            "time": str(row[4])
        })
        
    return {
        "nodes": [{"name": n} for n in nodes],
        "links": links
    }

@app.get("/api/analysis/multi/stolen_known")
async def api_stolen_known(case_id: str):
    """多账单-销赃节点判断 (有收赃人账单)"""
    data = analyze_stolen_distribution_known(case_id)
    return {"data": data}

@app.get("/api/analysis/multi/hidden")
async def api_hidden(case_id: str, minutes: int = 30):
    """多账单-挖尚不掌握的同伙 (30分钟内频繁交互)"""
    data = find_hidden_partners(case_id, time_window_minutes=minutes)
    return {"data": data}

# 获取案件列表接口（用于前端下拉框选择）
@app.get("/api/cases")
async def get_cases():
    """获取所有案件列表，用于前端下拉框选择"""
    try:
        conn = get_db_connection()
        df = conn.execute("SELECT DISTINCT case_id, case_name FROM transactions").fetchdf()
        conn.close()
        return {"success": True, "data": df.to_dict(orient='records')}
    except Exception as e:
        return {"success": False, "message": str(e)}
 
if __name__ == "__main__":
    import webbrowser
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(app, host=host, port=port)
