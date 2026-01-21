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

// 进度轮询间隔器存储 {sourceId: intervalId}
const progressPollers = {};

function displaySources(sources) {
    const sourcesList = document.getElementById('sources-list');
    
    if (sources.length === 0) {
        sourcesList.innerHTML = '<div class="text-center py-8 text-muted-foreground">暂无采集源，点击"添加采集源"按钮创建</div>';
        return;
    }

    sourcesList.innerHTML = '<div class="grid gap-4">' + sources.map(source => `
        <div class="card p-5" id="source-card-${source.id}">
            <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-3 mb-3">
                        <h3 class="text-lg font-semibold">${escapeHtml(source.name)}</h3>
                        <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            source.enabled 
                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' 
                                : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
                        }">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                ${source.enabled ? '<path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />' : '<path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />'}
                            </svg>
                            ${source.enabled ? '启用' : '禁用'}
                        </span>
                        <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                ${source.source_type === 'webpage' ? '<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />' : '<path stroke-linecap="round" stroke-linejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />'}
                            </svg>
                            ${source.source_type === 'webpage' ? '网页' : '视频'}
                        </span>
                    </div>
                    <div class="space-y-2 text-sm">
                        <div class="flex items-start gap-2">
                            <span class="text-muted-foreground font-medium min-w-[60px]">URL:</span>
                            <span class="text-foreground break-all">${escapeHtml(source.url_pattern)}</span>
                        </div>
                        ${source.search_params ? `
                            <div class="flex items-start gap-2">
                                <span class="text-muted-foreground font-medium min-w-[60px]">搜索参数:</span>
                                <span class="text-foreground break-all font-mono text-xs bg-muted px-2 py-1 rounded">${escapeHtml(JSON.stringify(source.search_params))}</span>
                            </div>
                        ` : ''}
                        ${source.created_at ? `
                            <div class="flex items-center gap-2 text-muted-foreground">
                                <span class="font-medium">创建时间:</span>
                                <span>${formatDate(source.created_at)}</span>
                            </div>
                        ` : ''}
                    </div>
                    <!-- 进度条容器 -->
                    <div id="progress-container-${source.id}" class="mt-3 hidden">
                        <div class="flex items-center justify-between text-xs text-muted-foreground mb-1">
                            <span id="progress-message-${source.id}">准备中...</span>
                            <span id="progress-percent-${source.id}">0%</span>
                        </div>
                        <div class="progress">
                            <div id="progress-bar-${source.id}" 
                                class="progress-indicator" 
                                style="width: 0%">
                            </div>
                        </div>
                    </div>
                </div>
                <div class="flex flex-col gap-2 shrink-0">
                    <button 
                        onclick="toggleSourceEnabled(${source.id}, ${source.enabled})"
                        class="inline-flex items-center gap-2 justify-center rounded-lg text-xs font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 ${
                            source.enabled 
                                ? 'bg-orange-500 text-white hover:bg-orange-600 hover:shadow-md hover:scale-105' 
                                : 'bg-green-500 text-white hover:bg-green-600 hover:shadow-md hover:scale-105'
                        } h-9 px-3 cursor-pointer"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            ${source.enabled ? '<path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />' : '<path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />'}
                        </svg>
                        ${source.enabled ? '禁用' : '启用'}
                    </button>
                    <button 
                        id="trigger-btn-${source.id}"
                        onclick="triggerCollection(${source.id})"
                        class="inline-flex items-center gap-2 justify-center rounded-lg text-xs font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow-md hover:scale-105 h-9 px-3 cursor-pointer"
                        ${!source.enabled ? 'disabled="disabled"' : ''}
                        ${!source.enabled ? 'title="采集源已禁用，无法触发采集"' : ''}
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        触发采集
                    </button>
                    <button 
                        onclick="showEditSourceModal(${source.id})"
                        class="inline-flex items-center gap-2 justify-center rounded-lg text-xs font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3 cursor-pointer"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        编辑
                    </button>
                    <button 
                        onclick="deleteSource(${source.id})"
                        class="inline-flex items-center gap-2 justify-center rounded-lg text-xs font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-destructive text-destructive-foreground hover:bg-destructive/90 hover:shadow-md hover:scale-105 h-9 px-3 cursor-pointer"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                        删除
                    </button>
                </div>
            </div>
        </div>
    `).join('') + '</div>';
    
    // 加载每个采集源的进度（如果正在运行）
    // 注意：只在状态为running或pending时才启动轮询
    sources.forEach(source => {
        updateProgress(source.id, false); // 不自动启动轮询，由updateProgress内部判断
    });
}

async function updateProgress(sourceId, autoStartPolling = true) {
    try {
        const progress = await api.getCollectionProgress(sourceId);
        
        const container = document.getElementById(`progress-container-${sourceId}`);
        const messageEl = document.getElementById(`progress-message-${sourceId}`);
        const percentEl = document.getElementById(`progress-percent-${sourceId}`);
        const barEl = document.getElementById(`progress-bar-${sourceId}`);
        const triggerBtn = document.getElementById(`trigger-btn-${sourceId}`);
        
        if (!container || !messageEl || !percentEl || !barEl) {
            return;
        }
        
        const status = progress.status || 'idle';
        const progressValue = progress.progress || 0;
        const message = progress.message || '';
        
        // 如果是完成或失败状态，立即停止轮询
        if (status === 'completed' || status === 'failed') {
            stopProgressPolling(sourceId);
        }
        
        if (status === 'idle') {
            // 空闲状态，隐藏进度条
            container.classList.add('hidden');
            if (triggerBtn) {
                triggerBtn.disabled = false;
                triggerBtn.textContent = '触发采集';
            }
            // 停止轮询（确保已停止）
            stopProgressPolling(sourceId);
        } else {
            // 显示进度条
            container.classList.remove('hidden');
            messageEl.textContent = message;
            percentEl.textContent = `${progressValue}%`;
            barEl.style.width = `${progressValue}%`;
            
            // 根据状态设置进度条颜色
            if (status === 'completed') {
                barEl.classList.remove('bg-blue-600');
                barEl.classList.add('bg-green-600');
                if (triggerBtn) {
                    triggerBtn.disabled = false;
                    triggerBtn.textContent = '触发采集';
                }
                // 完成后停止轮询（确保已停止）
                stopProgressPolling(sourceId);
                // 3秒后自动隐藏进度条并清理进度状态
                setTimeout(() => {
                    container.classList.add('hidden');
                    // 不刷新列表，避免重新启动轮询
                    // loadCollectionSources(); // 注释掉，避免无限循环
                }, 3000);
            } else if (status === 'failed') {
                barEl.classList.remove('bg-blue-600');
                barEl.classList.add('bg-red-600');
                if (triggerBtn) {
                    triggerBtn.disabled = false;
                    triggerBtn.textContent = '触发采集';
                }
                // 失败后停止轮询（确保已停止）
                stopProgressPolling(sourceId);
                // 5秒后自动隐藏进度条
                setTimeout(() => {
                    container.classList.add('hidden');
                }, 5000);
            } else {
                // running 或 pending 状态
                barEl.classList.remove('bg-green-600', 'bg-red-600');
                barEl.classList.add('bg-blue-600');
                if (triggerBtn) {
                    triggerBtn.disabled = true;
                    triggerBtn.textContent = '采集中...';
                }
                // 只在需要时启动轮询（如果autoStartPolling为true）
                if (autoStartPolling) {
                    startProgressPolling(sourceId);
                }
            }
        }
    } catch (error) {
        console.error(`获取进度失败 (sourceId: ${sourceId}):`, error);
        // 出错时停止轮询
        stopProgressPolling(sourceId);
    }
}

function startProgressPolling(sourceId) {
    // 如果已经在轮询，不重复启动
    if (progressPollers[sourceId]) {
        return;
    }
    
    // 每1秒轮询一次进度
    progressPollers[sourceId] = setInterval(() => {
        updateProgress(sourceId);
    }, 1000);
}

function stopProgressPolling(sourceId) {
    if (progressPollers[sourceId]) {
        clearInterval(progressPollers[sourceId]);
        delete progressPollers[sourceId];
    }
}

async function triggerCollection(sourceId = null) {
    try {
        await api.triggerCollection(sourceId);
        showToast('采集任务已触发', 'success', 2000);
        
        // 如果是单个采集源，开始轮询进度
        if (sourceId) {
            // 等待一小段时间让后端初始化进度
            setTimeout(() => {
                updateProgress(sourceId);
                startProgressPolling(sourceId);
            }, 500);
        }
    } catch (error) {
        showToast(`触发失败: ${error.message}`, 'error', 3000);
    }
}

async function toggleSourceEnabled(sourceId, currentEnabled) {
    const newEnabled = !currentEnabled;
    const action = newEnabled ? '启用' : '禁用';
    
    const confirmed = await showConfirm(
        `确定要${action}这个采集源吗？${newEnabled ? '启用后将可以自动采集和手动触发。' : '禁用后将不会自动采集，也无法手动触发。'}`,
        `${action}采集源`,
        action,
        '取消'
    );
    
    if (!confirmed) {
        return;
    }

    try {
        await api.updateCollectionSource(sourceId, { enabled: newEnabled });
        showToast(`采集源已${action}`, 'success', 3000);
        loadCollectionSources();
    } catch (error) {
        showToast(`${action}失败: ${error.message}`, 'error', 3000);
    }
}

async function deleteSource(sourceId) {
    const confirmed = await showConfirm('确定要删除这个采集源吗？删除后无法恢复。', '删除采集源', '删除', '取消');
    if (!confirmed) {
        return;
    }
    
    try {
        await api.deleteCollectionSource(sourceId);
        showToast('采集源删除成功', 'success', 2000);
        loadCollectionSources();
    } catch (error) {
        showToast(`删除失败: ${error.message}`, 'error', 3000);
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
        document.getElementById('source-search-params-input').value = '';
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
    const searchParamsText = document.getElementById('source-search-params-input').value.trim();
    
    if (!name || !url) {
        showToast('请填写名称和URL', 'warning', 3000);
        return;
    }
    
    // 解析搜索参数
    let searchParams = null;
    if (searchParamsText) {
        try {
            searchParams = JSON.parse(searchParamsText);
        } catch (e) {
            showToast('搜索参数格式错误，请使用有效的JSON格式', 'error', 3000);
            return;
        }
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
            search_params: searchParams,
            enabled: true
        });
        showToast('采集源创建成功！', 'success', 3000);
        hideAddSourceModal();
        loadCollectionSources();
    } catch (error) {
        showToast(`创建失败: ${error.message}`, 'error', 3000);
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
window.toggleSourceEnabled = toggleSourceEnabled;
window.deleteSource = deleteSource;
window.showAddSourceModal = showAddSourceModal;
window.hideAddSourceModal = hideAddSourceModal;
window.createSource = createSource;
