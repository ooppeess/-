async function fetchJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
}

// --- 渲染函数 ---
function renderTrend(data) {
    const el = document.getElementById('trend-chart');
    if (!data || !data.data || data.data.length === 0) {
        el.innerHTML = '<div class="text-slate-500 flex flex-col items-center"><i class="fa-regular fa-folder-open text-2xl mb-2"></i>暂无数据</div>';
        return;
    }
    const inSum = data.data.reduce((s, x) => s + (x.total_in || 0), 0);
    const outSum = data.data.reduce((s, x) => s + (x.total_out || 0), 0);
    el.innerHTML = `
        <div class="flex flex-col justify-center h-full gap-4 p-4">
            <div class="flex items-center justify-between bg-green-500/10 p-3 rounded-lg border border-green-500/20">
                <div class="text-sm text-green-400">总收入</div>
                <div class="text-xl font-bold text-white font-mono">¥${inSum.toLocaleString()}</div>
            </div>
            <div class="flex items-center justify-between bg-red-500/10 p-3 rounded-lg border border-red-500/20">
                <div class="text-sm text-red-400">总支出</div>
                <div class="text-xl font-bold text-white font-mono">¥${outSum.toLocaleString()}</div>
            </div>
            <div class="text-xs text-center text-slate-500 mt-2">详细图表建议接入 ECharts</div>
        </div>
    `;
}

function renderStats(data) {
    const el = document.getElementById('stats-table');
    if (!data || !data.data || data.data.length === 0) {
        el.innerHTML = '<div class="h-full flex items-center justify-center text-slate-500">暂无相关统计</div>';
        return;
    }
    const rows = data.data.slice(0, 50).map(x => `
        <tr class="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
            <td class="px-3 py-2 text-slate-300 truncate max-w-[100px]" title="${x.counterparty_name}">${x.counterparty_name}</td>
            <td class="px-3 py-2 text-right font-mono text-cyan-400">¥${Math.abs(x.net_amount||0).toLocaleString()}</td>
        </tr>
    `).join('');
    el.innerHTML = `
        <table class="w-full text-sm border-collapse">
            <thead class="sticky top-0 bg-slate-800 z-10 shadow-sm">
                <tr class="text-slate-400 text-xs uppercase">
                    <th class="text-left px-3 py-2 font-medium">交易对象</th>
                    <th class="text-right px-3 py-2 font-medium">净额</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-700/50">${rows}</tbody>
        </table>`;
}

function renderKeywords(data) {
    const el = document.getElementById('keywords-list');
    if (!data || !data.data || data.data.length === 0) {
        el.innerHTML = '<div class="h-full flex items-center justify-center text-slate-500">未发现重点行业交易</div>';
        return;
    }
    const items = data.data.map(x => `
        <div class="flex justify-between items-center bg-slate-800 border border-slate-700 p-2 rounded mb-2 hover:border-cyan-500/50 transition-colors">
            <span class="text-slate-200 text-sm font-medium">${x.counterparty_name}</span>
            <span class="text-orange-400 font-mono text-xs">¥${((x.in_amount||0)+(x.out_amount||0)).toLocaleString()}</span>
        </div>
    `).join('');
    el.innerHTML = `<div class="space-y-1">${items}</div>`;
}

// --- 核心逻辑 ---
async function initSingleDashboard() {
    const setupSection = document.getElementById('setup-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const setupCaseSelect = document.getElementById('setup-case-select');
    const setupConfirmBtn = document.getElementById('setup-confirm-btn');
    const switchCaseBtn = document.getElementById('switch-case-btn');
    const globalRefreshBtn = document.getElementById('global-refresh');
    const statsFilter = document.getElementById('stats-filter');

    // 1. 检查 URL 参数
    const urlParams = new URLSearchParams(window.location.search);
    const urlCaseId = urlParams.get('case_id');

    // 获取案件列表并填充下拉框
    try {
        const res = await fetchJSON('/api/cases');
        if (res.success && res.data.length > 0) {
            setupCaseSelect.innerHTML = '<option value="">-- 请选择案件 --</option>' + 
                res.data.map(c => `<option value="${c.case_id}">${c.case_name} (${c.case_id})</option>`).join('');
            setupConfirmBtn.disabled = false;
        } else {
            setupCaseSelect.innerHTML = '<option>暂无案件，请先去上传</option>';
            setupConfirmBtn.disabled = true;
            setupConfirmBtn.textContent = "无可用案件";
        }
    } catch (e) {
        console.error(e);
        setupCaseSelect.innerHTML = '<option>加载失败</option>';
    }

    // 2. 路由逻辑
    if (urlCaseId) {
        // -> 进入看板模式
        setupSection.classList.add('hidden');
        dashboardSection.classList.remove('hidden');
        document.getElementById('current-case-id').value = urlCaseId;
        
        // 尝试设置标题
        const currentOption = Array.from(setupCaseSelect.options).find(o => o.value === urlCaseId);
        document.getElementById('current-case-name').textContent = currentOption ? currentOption.text : urlCaseId;

        // 加载数据
        loadAllData(urlCaseId);
    } else {
        // -> 留在引导模式 (默认状态)
        setupSection.classList.remove('hidden');
        dashboardSection.classList.add('hidden');
    }

    // 3. 事件绑定
    
    // "进入分析" 按钮
    setupConfirmBtn.addEventListener('click', () => {
        const selectedId = setupCaseSelect.value;
        if (selectedId) {
            window.location.href = `/page/single-analysis?case_id=${selectedId}`;
        }
    });

    // "切换案件" 按钮
    switchCaseBtn.addEventListener('click', () => {
        window.location.href = '/page/single-analysis'; // 回到无参数状态，显示引导页
    });

    // "刷新" 按钮
    globalRefreshBtn.addEventListener('click', () => {
        loadAllData(document.getElementById('current-case-id').value);
    });

    // 统计筛选变化
    statsFilter.addEventListener('change', () => {
        const caseId = document.getElementById('current-case-id').value;
        const person = document.getElementById('trend-person').value.trim();
        const filter = statsFilter.value;
        
        document.getElementById('stats-table').innerHTML = '<div class="text-slate-500 p-2"><i class="fa-solid fa-spinner fa-spin"></i></div>';
        
        fetchJSON(`/api/analysis/single/stats?case_id=${encodeURIComponent(caseId)}&person=${encodeURIComponent(person)}&filter=${encodeURIComponent(filter)}`)
            .then(renderStats).catch(e => console.error(e));
    });
}

// 加载所有模块
function loadAllData(caseId) {
    if (!caseId) return;
    const person = document.getElementById('trend-person').value.trim();
    const filter = document.getElementById('stats-filter').value;

    // 并发请求
    Promise.all([
        fetchJSON(`/api/analysis/single/trend?case_id=${encodeURIComponent(caseId)}&person=${encodeURIComponent(person)}`).then(renderTrend),
        fetchJSON(`/api/analysis/single/stats?case_id=${encodeURIComponent(caseId)}&person=${encodeURIComponent(person)}&filter=${encodeURIComponent(filter)}`).then(renderStats),
        fetchJSON(`/api/analysis/single/keywords?case_id=${encodeURIComponent(caseId)}`).then(renderKeywords)
    ]).catch(e => console.error("Data Load Error:", e));
}

document.addEventListener('DOMContentLoaded', initSingleDashboard);