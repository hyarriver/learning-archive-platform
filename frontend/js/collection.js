// 采集管理功能
async function loadCollectionSources() {
    const sourcesList = document.getElementById('sources-list');
    sourcesList.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const sources = await api.getCollectionSources();
        displaySources(sources);
    } catch (error) {
        sourcesList.innerHTML = `<div class="error-message show">${error.message}</div>`;
    }
}

function displaySources(sources) {
    const sourcesList = document.getElementById('sources-list');
    
    if (sources.length === 0) {
        sourcesList.innerHTML = '<div class="loading">暂无采集源</div>';
        return;
    }

    sourcesList.innerHTML = sources.map(source => `
        <div class="source-card">
            <div class="source-info">
                <h3>${escapeHtml(source.name)}</h3>
                <p>类型: ${source.source_type}</p>
                <p>URL: ${escapeHtml(source.url_pattern)}</p>
                <p>状态: ${source.enabled ? '<span style="color: green;">启用</span>' : '<span style="color: red;">禁用</span>'}</p>
            </div>
            <div class="source-actions">
                <button class="btn btn-primary" onclick="triggerCollection(${source.id})">触发采集</button>
                <button class="btn btn-secondary" onclick="deleteSource(${source.id})">删除</button>
            </div>
        </div>
    `).join('');
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
    if (!confirm('确定要删除这个采集源吗？')) {
        return;
    }
    
    try {
        await api.deleteCollectionSource(sourceId);
        loadCollectionSources();
    } catch (error) {
        alert(`删除失败: ${error.message}`);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 导出函数
window.loadCollectionSources = loadCollectionSources;
window.triggerCollection = triggerCollection;
window.deleteSource = deleteSource;