# FundX 资金分析平台

## 简介
FundX 是一个基于 FastAPI + DuckDB 的资金分析平台，支持账单上传、数据清洗、单账单分析与多账单关联分析。平台内置页面与静态资源，默认开启 GZip 压缩与 ORJSON 高性能序列化，并对静态资源启用强缓存。

## 技术栈
- 后端：FastAPI、Starlette、Pydantic
- 数据：DuckDB、Pandas
- 前端：Tailwind CSS、ECharts、Anime.js

## 目录结构
```
FF/
├─ start_fundx.bat                 # Windows 启动脚本
├─ main.py                         # 应用入口，注册页面与 API 路由
├─ database.py                     # DuckDB 初始化与索引创建
├─ app/
│  ├─ bill_cleaners.py             # 多格式账单清洗器
│  ├─ cache.py                     # 分析接口 LRU+TTL 缓存
│  └─ services/                    # 核心业务逻辑目录
│     ├─ ingestion.py              # 上传、清洗、入库服务
│     ├─ single_analysis.py        # 单账单分析函数
│     └─ multi_analysis.py         # 多账单分析函数
├─ templates/                      # Jinja2 页面模板
│  ├─ index.html                   # 首页（双入口分流）
│  ├─ single_analysis_dashboard.html
│  └─ multi_analysis_dashboard.html
├─ static/                         # 静态资源（JS/CSS/图片）
│  └─ js/
│     ├─ single-dashboard.js       # 单账单页面交互脚本
│     └─ multi-dashboard.js        # 多账单页面交互脚本
├─ scripts/                        # 辅助脚本
└─ requirements.txt                # 依赖清单
```

## 环境要求
- Python 3.10+
- pip 可用

## 安装依赖
```
python -m pip install -r requirements.txt
```

## 启动服务
- Windows（推荐）
```
./start_fundx.bat
```
- Python 直接运行
```
python main.py
```
- 开发模式（热重载）
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
访问 `http://localhost:8000/`

## 页面路由
- `/` 首页（双入口分流）
- `/page/single-analysis` 单账单分析聚合页
- `/page/multi-analysis` 多账单分析聚合页
- `/case-management` 案件管理
- `/data-visualization` 数据可视化

## API 分组
- 上传
  - `POST /api/upload`
  - 表单字段：`file`、`case_name`、`case_id`、`person_type`（必须为：盗窃人员/收脏人员/排查人员）

- 单账单
  - `GET /api/analysis/single/trend?case_id=...&person=...&min=...` 月度入/出趋势
  - `GET /api/analysis/single/stats?case_id=...&person=...&filter=...` 统计汇总
  - `GET /api/analysis/single/keywords?case_id=...` 关键交易对方 Top 列表

- 多账单
  - `GET /api/analysis/multi/interaction?case_id=...` 22 交互网络
  - `GET /api/analysis/multi/stolen_known?case_id=...` 销赃/分赃研判（已知收赃人）
  - `GET /api/analysis/multi/hidden?case_id=...&minutes=30` 隐形同伙候选（同日、时间窗内）

## 示例请求
```
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "file=@path/to/bill.xlsx" \
  -F "case_name=案件A" \
  -F "case_id=CASE-001" \
  -F "person_type=盗窃人员"

http://127.0.0.1:8000/api/analysis/single/trend?case_id=CASE-001&person=&min=100
http://127.0.0.1:8000/api/analysis/multi/hidden?case_id=CASE-001
```

## 数据库
- DuckDB 文件：`fund_analysis.duckdb`
- 表：`transactions` 含关键字段：
  - `case_id`、`case_name`、`person_identity`
  - `owner_name`、`owner_id`、`owner_account`
  - `trans_time`、`amount`、`counterparty_name`、`counterparty_account`
  - `trans_order_id`、`merchant_order_id`、`remark`
  - `raw_file_name`、`import_batch`
- 索引：
  - `case_id`、`trans_time`、`owner_name`、`counterparty_name`
  - 组合索引 `idx_orders(trans_order_id, merchant_order_id)`

## 清洗与规则
- 人员身份强校验：仅允许 `盗窃人员/收脏人员/排查人员`
- 去噪：`交易对方` 移除空格与特殊符号，仅保留中英文与数字
- 金额过滤：删除绝对值 `< 100` 的记录
- 字段映射：识别 Excel/PDF/TXT 常见列并映射为统一字段

## 性能优化
- 默认启用 GZip 压缩与 ORJSON 响应
- 趋势与交互接口使用 LRU+TTL 内存缓存，上传成功后按 `case_id` 失效
- 静态资源添加强缓存头，提升前端加载性能

## 迁移与注意事项
- 若升级 Schema（新增列等），请删除旧的 `fund_analysis.duckdb` 以重建新结构
- 上传接口返回导入条数 `imported` 字段，便于前端提示

## 清理测试数据
```
python scripts/cleanup_db.py
```
## 首页导航重构（双入口 + 卡片式）
- 首页仅保留两个大卡片入口：`单账单分析`（蓝色系）与 `多账单分析`（橙色系）
- 每个聚合页采用 Card 设计（白底、圆角、阴影），头部为标题与筛选控件，主体为图表/表格
- 布局使用 `grid-cols-1 md:grid-cols-3`，移动端竖向堆叠，桌面端三列排布
- 悬停交互：`hover:translate-y-1` 与 `hover:shadow-md` 提示可点击

## 重要清理步骤（避免旧文件导致环境混乱）
- 删除旧数据库文件：项目根目录 `fund_analysis.duckdb`，运行后会自动生成新结构
- 删除冗余旧代码文件，仅保留 `app/services/` 下的新文件
  - 删除 `app/single_analysis.py`
  - 删除 `app/multi_analysis.py`
- 删除 `api/routers/` 目录（当前入口直接调用 services，不再依赖旧 routers）
