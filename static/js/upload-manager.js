class UploadManager {
    constructor() {
        this.filesMap = new Map();
        this.init();
    }

    init() {
        const fileInput = document.getElementById('file-input');
        if (fileInput) fileInput.addEventListener('change', (e) => this.handleSelect(e));

        const startBtn = document.getElementById('start-upload-btn');
        if (startBtn) startBtn.addEventListener('click', () => this.uploadAll());

        const dropZone = document.body;
        dropZone.addEventListener('dragover', (e) => e.preventDefault());
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            if (!document.getElementById('upload-modal').classList.contains('hidden')) {
                this.addFiles(e.dataTransfer.files);
            }
        });
    }

    handleSelect(e) {
        this.addFiles(e.target.files);
        e.target.value = '';
    }

    addFiles(fileList) {
        const listEl = document.getElementById('file-staging-area');
        if (this.filesMap.size === 0) listEl.innerHTML = '';

        Array.from(fileList).forEach(file => {
            let defaultType = '排查人员';
            let defaultUnit = 'yuan';
            if (file.name.toLowerCase().endsWith('.txt')) {
                defaultUnit = 'fen';
            }
            const config = { file, type: defaultType, unit: defaultUnit };
            this.filesMap.set(file.name, config);
            this.renderRow(file.name, config);
        });
        const btn = document.getElementById('start-upload-btn');
        if (btn) btn.disabled = this.filesMap.size === 0;
        const statusEl = document.getElementById('upload-status-msg');
        if (statusEl) {
            statusEl.textContent = `已添加 ${this.filesMap.size} 个文件`;
            statusEl.className = 'mr-auto self-center text-sm text-cyan-400';
        }
    }

    renderRow(filename, config) {
        const oldRow = document.getElementById(`row-${filename}`);
        if (oldRow) oldRow.remove();

        const listEl = document.getElementById('file-staging-area');
        const row = document.createElement('div');
        row.id = `row-${filename}`;
        row.className = 'grid grid-cols-12 gap-2 p-2 bg-slate-700/50 rounded mb-1 text-sm items-center animate-fade-in';
        row.innerHTML = `
            <div class="col-span-4 truncate text-slate-200" title="${filename}">${filename}</div>
            <div class="col-span-2 text-slate-400 text-xs">${(config.file.size/1024).toFixed(1)} KB</div>
            <div class="col-span-3">
                <select onchange="uploadManager.updateConfig('${filename}', 'type', this.value)" class="w-full bg-slate-900 border border-slate-600 text-white text-xs rounded px-2 py-1">
                    <option value="排查人员" ${config.type==='排查人员'?'selected':''}>排查人员</option>
                    <option value="收脏人员" ${config.type==='收脏人员'?'selected':''}>收脏人员</option>
                    <option value="盗窃人员" ${config.type==='盗窃人员'?'selected':''}>盗窃人员</option>
                </select>
            </div>
            <div class="col-span-2">
                <select onchange="uploadManager.updateConfig('${filename}', 'unit', this.value)" class="w-full bg-slate-900 border border-slate-600 text-white text-xs rounded px-2 py-1">
                    <option value="yuan" ${config.unit==='yuan'?'selected':''}>元</option>
                    <option value="fen" ${config.unit==='fen'?'selected':''}>分 (÷100)</option>
                    <option value="jiao" ${config.unit==='jiao'?'selected':''}>角 (÷10)</option>
                </select>
            </div>
            <div class="col-span-1 text-center">
                <button onclick="uploadManager.remove('${filename}')" class="text-red-400 hover:text-red-300">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;
        listEl.appendChild(row);
    }

    updateConfig(filename, key, val) {
        const config = this.filesMap.get(filename);
        if (config) {
            config[key] = val;
            this.filesMap.set(filename, config);
        }
    }

    remove(filename) {
        this.filesMap.delete(filename);
        const row = document.getElementById(`row-${filename}`);
        if (row) row.remove();
        if (this.filesMap.size === 0) {
            document.getElementById('file-staging-area').innerHTML = '<div class="text-center text-gray-500 py-10">请点击上方按钮添加文件</div>';
        }
        const btn = document.getElementById('start-upload-btn');
        if (btn) btn.disabled = this.filesMap.size === 0;
    }

    async uploadAll() {
        const caseName = document.getElementById('upload-case-name').value.trim();
        const caseId = document.getElementById('upload-case-id').value.trim();
        const statusEl = document.getElementById('upload-status-msg');
        const btn = document.getElementById('start-upload-btn');
        if (!caseName || !caseId) { alert('请填写案件名称和编号'); return; }
        if (this.filesMap.size === 0) { alert('请至少添加一个文件'); return; }
        btn.disabled = true;
        btn.textContent = '正在处理...';
        if (statusEl) { statusEl.textContent = `正在上传 ${this.filesMap.size} 个文件，请稍候...`; statusEl.className = 'mr-auto self-center text-sm text-cyan-400'; }
        const formData = new FormData();
        formData.append('case_name', caseName);
        formData.append('case_id', caseId);
        const configs = {};
        this.filesMap.forEach((cfg, name) => { formData.append('files', cfg.file); configs[name] = { type: cfg.type, unit: cfg.unit }; });
        formData.append('file_configs', JSON.stringify(configs));
        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.status === 'success') {
                if (statusEl) { statusEl.textContent = '全部处理完成！正在刷新...'; statusEl.className = 'mr-auto self-center text-sm text-green-400'; }
                setTimeout(() => window.location.reload(), 1000);
            } else { throw new Error(data.message); }
        } catch (e) {
            if (statusEl) { statusEl.textContent = '上传失败: ' + e.message; statusEl.className = 'mr-auto self-center text-sm text-red-400'; }
            btn.disabled = false;
            btn.textContent = '开始处理并入库';
        }
    }
}

window.uploadManager = new UploadManager();
