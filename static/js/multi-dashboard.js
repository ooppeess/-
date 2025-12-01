async function fetchJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
}

// --- 渲染函数 ---

function renderInteraction(data) {
    const el = document.getElementById('interaction-graph');
    if (!data || !data.nodes || data.nodes.length === 0) {
        el.innerHTML = '<div class="flex flex-col items-center text-slate-500"><i class="fa-solid fa-circle-nodes text-3xl mb-2 opacity-50"></i><span>暂无交互数据</span></div>';
        return;
    }
    // 简易展示，实际建议接入 ECharts Graph
    const bigTrans = data.links.filter(l => l.value > 10000).length;
    el.innerHTML = `
        <div class="flex flex-col items-center justify-center h-full gap-6">
            <div class="grid grid-cols-2 gap-8 w-full max-w-[200px]">
                <div class="text-center">
                    <div class="text-3xl font-bold text-white">${data.nodes.length}</div>
                    <div class="text-xs text-orange-400 uppercase tracking-wider mt-1">涉案人员</div>
                </div>
                <div class="text-center">
                    <div class="text-3xl font-bold text-white">${data.links.length}</div>
                    <div class="text-xs text-blue-400 uppercase tracking-wider mt-1">资金连线</div>
                </div>
            </div>
            <div class="w-full px-6">
                <div class="flex justify-between text-xs text-slate-400 mb-1">
                    <span>大额交易占比</span>
                    <span>${bigTrans} 笔</span>
                </div>
                <div class="w-full bg-slate-700 h-1.5 rounded-full overflow-hidden">
                    <div class="bg-orange-500 h-full" style="width: ${(bigTrans/data.links.length)*100}%"></div>
                </div>
            </div>
            <button class="text-xs border border-slate-600 text-slate-300 px-3 py-1.5 rounded hover:bg-slate-700 transition-colors">
                查看全图谱
            </button>
        </div>
    `;
}

function renderStolen(data) {
    const el = document.getElementById('stolen-table');
    if (!data || !data.data || data.data.length === 0) {
        el.innerHTML = '<div class="h-full flex flex-col items-center justify-center text-slate-500 gap-2"><i class="fa-solid fa-check-circle text-2xl opacity-30"></i><span>未发现明显销赃特征</span></div>';
        return;
    }
    const rows = data.data.slice(0, 50).map(x => `
        <tr class="group border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors cursor-default">
            <td class="px-3 py-2.5">
                <div class="flex items-center gap-2">
                    <div class="w-6 h-6 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center text-xs"><i class="fa-solid fa-user-tag"></i></div>
                    <span class="text-slate-200">${x.source}</span>
                </div>
            </td>
            <td class="px-1 text-slate-600"><i class="fa-solid fa-arrow-right text-xs"></i></td>
            <td class="px-3 py-2.5">
                <div class="flex items-center gap-2">
                    <span class="text-slate-200">${x.target}</span>
                    <div class="w-6 h-6 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center text-xs"><i class="fa-solid fa-user-ninja"></i></div>
                </div>
            </td>
            <td class="px-3 py-2.5 text-right font-mono text-orange-400 font-bold">¥${(x.amount||0).toLocaleString()}</td>
        </tr>
    `).join('');
    
    el.innerHTML = `
        <table class="w-full text-sm border-separate border-spacing-0">
            <thead class="sticky top-0 bg-slate-800 z-10">
                <tr class="text-slate-500 text-xs uppercase tracking-wider">
                    <th class="text-left px-3 py-2 bg-slate-800">资金来源 (收赃)</th>
                    <th class="bg-slate-800"></th>
                    <th class="text-left px-3 py-2 bg-slate-800">资金去向 (盗窃)</th>
                    <th class="text-right px-3 py-2 bg-slate-800">金额</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>`;
}

function renderHidden(data) {
    const el = document.getElementById('hidden-list');
    if (!data || !data.data || data.data.length === 0) {
        el.innerHTML = '<div class="h-full flex flex-col items-center justify-center text-slate-500 gap-2"><i class="fa-solid fa-user-slash text-2xl opacity-30"></i><span>未挖掘到隐形同伙</span></div>';
        return;
    }
    const items = data.data.map((x, i) => `
        <div class="flex items-center justify-between bg-slate-800 border border-slate-700/50 p-3 rounded-lg mb-2 hover:border-purple-500/50 hover:bg-slate-700/30 transition-all">
            <div class="flex items-center gap-3">
                <div class="text-lg font-bold text-slate-600 w-4 text-center">${i + 1}</div>
                <div>
                    <div class="text-slate-200 font-bold">${x.counterparty_name}</div>
                    <div class="text-xs text-slate-400 flex items-center gap-1">
                        <i class="fa-regular fa-clock"></i> 频繁交互 ${x.freq} 次
                    </div>
                </div>
            </div>
            <div class="text-right">
                <div class="text-purple-400 font-mono font-bold">¥${(x.total_amount||0).toLocaleString()}</div>
                <div class="text-[10px] text-slate-500 uppercase">涉案总额</div>
            </div>
        </div>
    `).join('');
    el.innerHTML = `<div class="space-y-1">${items}</div>`;
}

// --- 核心逻辑 ---
async function initMultiDashboard() {
    const setupSection = document.getElementById('setup-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const setupCaseSelect = document.getElementById('setup-case-select');
    const setupConfirmBtn = document.getElementById('setup-confirm-btn');
    const switchCaseBtn = document.getElementById('switch-case-btn');
    const globalRefreshBtn = document.getElementById('global-refresh');
    const hiddenMinutesInput = document.getElementById('hidden-minutes');
    const hiddenReloadBtn = document.getElementById('hidden-reload-btn');

    // 1. 检查 URL
    const urlParams = new URLSearchParams(window.location.search);
    const urlCaseId = urlParams.get('case_id');

    // 初始化案件列表
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
        setupSection.classList.add('hidden');
        dashboardSection.classList.remove('hidden');
        document.getElementById('current-case-id').value = urlCaseId;
        
        const currentOption = Array.from(setupCaseSelect.options).find(o => o.value === urlCaseId);
        document.getElementById('current-case-name').textContent = currentOption ? currentOption.text : urlCaseId;

        loadAllData(urlCaseId);
    } else {
        setupSection.classList.remove('hidden');
        dashboardSection.classList.add('hidden');
    }

    // 3. 事件绑定
    setupConfirmBtn.addEventListener('click', () => {
        const selectedId = setupCaseSelect.value;
        if (selectedId) {
            window.location.href = `/page/multi-analysis?case_id=${selectedId}`;
        }
    });

    switchCaseBtn.addEventListener('click', () => {
        window.location.href = '/page/multi-analysis';
    });

    globalRefreshBtn.addEventListener('click', () => {
        loadAllData(document.getElementById('current-case-id').value);
    });

    // 隐形同伙单独刷新
    hiddenReloadBtn.addEventListener('click', () => {
        const caseId = document.getElementById('current-case-id').value;
        const minutes = parseInt(hiddenMinutesInput.value || '30', 10);
        document.getElementById('hidden-list').innerHTML = '<div class="text-center p-4 text-slate-500"><i class="fa-solid fa-spinner fa-spin"></i></div>';
        fetchJSON(`/api/analysis/multi/hidden?case_id=${encodeURIComponent(caseId)}&minutes=${minutes}`)
            .then(renderHidden).catch(e => console.error(e));
    });
}

function loadAllData(caseId) {
    if (!caseId) return;
    const minutes = parseInt(document.getElementById('hidden-minutes').value || '30', 10);

    Promise.all([
        fetchJSON(`/api/analysis/multi/interaction?case_id=${encodeURIComponent(caseId)}`).then(renderInteraction),
        fetchJSON(`/api/analysis/multi/stolen_known?case_id=${encodeURIComponent(caseId)}`).then(renderStolen),
        fetchJSON(`/api/analysis/multi/hidden?case_id=${encodeURIComponent(caseId)}&minutes=${minutes}`).then(renderHidden)
    ]).catch(e => console.error("Multi Data Error:", e));
}

document.addEventListener('DOMContentLoaded', initMultiDashboard);