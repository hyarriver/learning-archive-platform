// 采集管理功能
async function loadCollectionSources() {
    const sourcesList = document.getElementById('sources-list');
    sourcesList.innerHTML = '<div class="text-center py-8 text-muted-foreground">加载中...</div>';

    try {
        const sources = await api.getCollectionSources();
        displaySources(sources);
    } catch (error) {
        sourcesList.innerHTML = `<div class="text-center py-8 text-destructive">${error.message}</div>`;
    }
}

function displaySources(sources) {
    const sourcesList = document.getElementById('sources-list');
    
    if (sources.length === 0) {
        sourcesList.innerHTML = '<div class="text-center py-8 text-muted-foreground">暂无采集源，点击"添加采集源"按钮创建</div>';
        return;
    }

    sourcesList.innerHTML = '<div class="grid gap-4">' + sources.map(source => `
        <div class="border border-border rounded-lg p-5 bg-card shadow-sm hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-3 mb-3">
                        <h3 class="text-lg font-semibold">${escapeHtml(source.name)}</h3>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            source.enabled 
                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' 
                                : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
                        }">
                            ${source.enabled ? '✓ 启用' : '✗ 禁用'}
                        </span>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                            ${source.source_type === 'webpage' ? '📄 网页' : '🎥 视频'}
                        </span>
                    </div>
                    <div class="space-y-2 text-sm">
                        <div class="flex items-start gap-2">
                            <span class="text-muted-foreground font-medium min-w-[60px]">URL:</span>
                            <span class="text-foreground break-all">${escapeHtml(source.url_pattern)}</span>
                        </div>
                        ${source.created_at ? `
                            <div class="flex items-center gap-2 text-muted-foreground">
                                <span class="font-medium">创建时间:</span>
                                <span>${formatDate(source.created_at)}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
                <div class="flex flex-col gap-2 shrink-0">
                    <button 
                        onclick="triggerCollection(${source.id})"
                        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4"
                    >
                        触发采集
                    </button>
                    <button 
                        onclick="deleteSource(${source.id})"
                        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-destructive text-destructive-foreground hover:bg-destructive/90 h-9 px-4"
                    >
                        删除
                    </button>
                </div>
            </div>
        </div>
    `).join('') + '</div>';
}

async function triggerCollection(sourceId = null) {
    try {
        await api.triggerCollection(sourceId);
        alert('采集任务已触发');
    } catch (error) {
        alert(`触发失败: ${error.message}`);
    }
}

async function deleteSource(sourceId) {
    if (!confirm('确定要删除这个采集源吗？删除后无法恢复。')) {
        return;
    }
    
    try {
        await api.deleteCollectionSource(sourceId);
        loadCollectionSources();
    } catch (error) {
        alert(`删除失败: ${error.message}`);
    }
}

function showAddSourceModal() {
    const modal = document.getElementById('add-source-modal');
    if (modal) {
        modal.classList.remove('hidden');
        // 清空表单
        document.getElementById('source-name-input').value = '';
        document.getElementById('source-url-input').value = '';
        document.getElementById('source-type-select').value = 'webpage';
    }
}

function hideAddSourceModal() {
    const modal = document.getElementById('add-source-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

async function createSource() {
    const name = document.getElementById('source-name-input').value.trim();
    const url = document.getElementById('source-url-input').value.trim();
    const sourceType = document.getElementById('source-type-select').value;
    
    if (!name || !url) {
        alert('请填写名称和URL');
        return;
    }
    
    const createBtn = document.getElementById('create-source-btn');
    const originalText = createBtn.textContent;
    createBtn.disabled = true;
    createBtn.textContent = '创建中...';
    
    try {
        await api.createCollectionSource({
            name,
            url_pattern: url,
            source_type: sourceType,
            enabled: true
        });
        alert('采集源创建成功！');
        hideAddSourceModal();
        loadCollectionSources();
    } catch (error) {
        alert(`创建失败: ${error.message}`);
    } finally {
        createBtn.disabled = false;
        createBtn.textContent = originalText;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 导出函数
window.loadCollectionSources = loadCollectionSources;
window.triggerCollection = triggerCollection;
window.deleteSource = deleteSource;
window.showAddSourceModal = showAddSourceModal;
window.hideAddSourceModal = hideAddSourceModal;
window.createSource = createSource;
