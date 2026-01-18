// 文件管理功能
let currentPage = 1;
let currentPageSize = 20;
let currentFilters = {};
let currentUserRole = 'user';

async function loadFiles(page = 1, filters = {}) {
    currentPage = page;
    currentFilters = filters;
    
    const filesList = document.getElementById('files-list');
    filesList.innerHTML = '<div class="text-center py-8 text-muted-foreground">加载中...</div>';

    try {
        const data = await api.getFiles(page, currentPageSize, filters);
        displayFiles(data.items);
        displayPagination(data.total, data.page, data.page_size);
    } catch (error) {
        filesList.innerHTML = `<div class="text-center py-8 text-destructive">${error.message}</div>`;
    }
}

function displayFiles(files) {
    const filesList = document.getElementById('files-list');
    
    if (files.length === 0) {
        filesList.innerHTML = '<div class="text-center py-8 text-muted-foreground">暂无文件</div>';
        return;
    }

    // 按文件类型分组
    const collectionFiles = files.filter(f => f.file_type === 'collection');
    const uploadFiles = files.filter(f => f.file_type === 'upload');

    let html = '';

    // 显示采集文件
    if (collectionFiles.length > 0) {
        html += '<div class="mb-6">';
        html += '<h3 class="text-lg font-semibold mb-3 text-muted-foreground">📚 采集文件</h3>';
        html += '<div class="grid gap-3">';
        collectionFiles.forEach(file => {
            html += createFileCard(file);
        });
        html += '</div>';
        html += '</div>';
    }

    // 显示用户上传文件
    if (uploadFiles.length > 0) {
        html += '<div class="mb-6">';
        html += '<h3 class="text-lg font-semibold mb-3 text-muted-foreground">📁 用户上传</h3>';
        html += '<div class="grid gap-3">';
        uploadFiles.forEach(file => {
            html += createFileCard(file);
        });
        html += '</div>';
        html += '</div>';
    }

    filesList.innerHTML = html;
}

function createFileCard(file) {
    // 格式化日期
    const createdAt = formatDate(file.created_at);
    
    // 获取来源信息
    let sourceInfo = '';
    if (file.file_type === 'collection' && file.source_name) {
        sourceInfo = `<span class="text-sm text-muted-foreground">来源: ${escapeHtml(file.source_name)}</span>`;
    } else if (file.file_type === 'upload' && file.upload_username) {
        sourceInfo = `<span class="text-sm text-muted-foreground">上传者: ${escapeHtml(file.upload_username)}</span>`;
    }

    // 判断是否显示删除按钮
    const canDelete = currentUserRole === 'admin' || 
                     (file.file_type === 'upload' && file.upload_user_id);

    return `
        <div class="border border-border rounded-lg p-4 hover:bg-accent transition-colors">
            <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0 cursor-pointer" onclick="showFileDetail(${file.id})">
                    <h3 class="text-base font-semibold mb-2 truncate">${escapeHtml(file.title)}</h3>
                    ${file.summary ? `<p class="text-sm text-muted-foreground mb-2 line-clamp-2">${escapeHtml(file.summary)}</p>` : ''}
                    <div class="flex flex-wrap items-center gap-3 text-xs text-muted-foreground mt-2">
                        <span class="inline-flex items-center px-2 py-1 rounded-md bg-secondary text-secondary-foreground">
                            ${file.file_type === 'collection' ? '📚 采集' : '📁 上传'}
                        </span>
                        ${sourceInfo}
                        <span class="text-muted-foreground">${createdAt}</span>
                    </div>
                    ${file.tags && file.tags.length > 0 ? `
                        <div class="flex flex-wrap gap-1 mt-2">
                            ${file.tags.map(tag => `<span class="text-xs px-2 py-0.5 rounded bg-accent text-accent-foreground">${escapeHtml(tag)}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
                <div class="flex gap-2 items-start">
                    <button 
                        onclick="event.stopPropagation(); downloadFileHandler(${file.id})"
                        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-secondary text-secondary-foreground hover:bg-secondary/80 h-9 px-3"
                    >
                        下载
                    </button>
                    ${canDelete ? `
                        <button 
                            onclick="event.stopPropagation(); deleteFile(${file.id})"
                            class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-destructive text-destructive-foreground hover:bg-destructive/90 h-9 px-3"
                        >
                            删除
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}

function displayPagination(total, page, pageSize) {
    const pagination = document.getElementById('pagination');
    const totalPages = Math.ceil(total / pageSize);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '<div class="flex items-center justify-center gap-2 mt-4">';
    
    // 上一页
    if (page > 1) {
        html += `<button onclick="loadFiles(${page - 1}, currentFilters)" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-secondary text-secondary-foreground hover:bg-secondary/80 h-9 px-4">上一页</button>`;
    }
    
    // 页码
    for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {
        const activeClass = i === page ? 'bg-primary text-primary-foreground hover:bg-primary/90' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80';
        html += `<button onclick="loadFiles(${i}, currentFilters)" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 ${activeClass} h-9 w-9">${i}</button>`;
    }
    
    // 下一页
    if (page < totalPages) {
        html += `<button onclick="loadFiles(${page + 1}, currentFilters)" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-secondary text-secondary-foreground hover:bg-secondary/80 h-9 px-4">下一页</button>`;
    }
    
    html += '</div>';
    pagination.innerHTML = html;
}

async function showFileDetail(fileId) {
    // 隐藏文件列表页，显示详情页
    document.getElementById('files-page').classList.add('hidden');
    document.getElementById('file-detail-page').classList.remove('hidden');

    const fileContent = document.getElementById('file-content');
    fileContent.innerHTML = '<div class="text-center py-8 text-muted-foreground">加载中...</div>';

    try {
        const file = await api.getFile(fileId);
        document.getElementById('file-title').textContent = file.title;
        
        // 简单的 Markdown 渲染（可以替换为更强大的库）
        fileContent.innerHTML = `<pre class="whitespace-pre-wrap bg-card border border-border rounded-lg p-4 overflow-x-auto">${escapeHtml(file.content)}</pre>`;
        
        // 设置下载按钮
        document.getElementById('download-btn').onclick = async () => {
            try {
                await api.downloadFile(fileId);
            } catch (error) {
                // 错误已在 downloadFile 方法中处理并显示 Toast
            }
        };
    } catch (error) {
        fileContent.innerHTML = `<div class="text-center py-8 text-destructive">${error.message}</div>`;
    }
}

async function deleteFile(fileId) {
    const confirmed = await showConfirm('确定要删除这个文件吗？删除后无法恢复。', '删除文件', '删除', '取消');
    if (!confirmed) {
        return;
    }

    try {
        await api.deleteFile(fileId);
        // 重新加载文件列表
        loadFiles(currentPage, currentFilters);
        showToast('文件删除成功', 'success', 2000);
    } catch (error) {
        showToast(`删除失败: ${error.message}`, 'error', 3000);
    }
}

async function uploadFile() {
    const fileInput = document.getElementById('upload-file-input');
    const titleInput = document.getElementById('upload-title-input');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showToast('请选择要上传的文件', 'warning', 3000);
        return;
    }

    const file = fileInput.files[0];
    const title = titleInput.value.trim() || null;

    // 检查文件类型（只允许文本文件）
    if (!file.type.startsWith('text/') && !file.name.endsWith('.md') && !file.name.endsWith('.txt')) {
        const confirmed = await showConfirm('文件可能不是文本文件，是否继续上传？', '确认上传', '继续上传', '取消');
        if (!confirmed) {
            return;
        }
    }

    const uploadBtn = document.getElementById('upload-file-btn');
    const originalText = uploadBtn.textContent;
    uploadBtn.disabled = true;
    uploadBtn.textContent = '上传中...';

    try {
        await api.uploadFile(file, title);
        showToast('文件上传成功！', 'success', 3000);
        // 清空表单
        fileInput.value = '';
        titleInput.value = '';
        // 关闭上传对话框
        document.getElementById('upload-modal').classList.add('hidden');
        // 重新加载文件列表
        loadFiles(1, currentFilters);
    } catch (error) {
        showToast(`上传失败: ${error.message}`, 'error', 3000);
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = originalText;
    }
}

function escapeHtml(text) {
    if (!text) return '';
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

// 搜索功能和上传功能
document.addEventListener('DOMContentLoaded', () => {
    // 更新当前用户角色（只在已登录状态下获取）
    if (api.token) {
        api.getCurrentUser().then(user => {
            currentUserRole = user.role || 'user';
        }).catch(() => {
            // 如果获取失败，不抛出错误，只设置默认角色
            currentUserRole = 'user';
        });
    } else {
        currentUserRole = 'user';
    }

    // 搜索功能
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            const search = searchInput.value.trim();
            loadFiles(1, search ? { search } : {});
        });
    }
    
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const search = searchInput.value.trim();
                loadFiles(1, search ? { search } : {});
            }
        });
    }
    
    // 返回按钮
    const backBtn = document.getElementById('back-btn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            document.getElementById('file-detail-page').classList.add('hidden');
            document.getElementById('files-page').classList.remove('hidden');
        });
    }

    // 上传文件按钮
    const uploadFileBtn = document.getElementById('upload-file-page-btn');
    if (uploadFileBtn) {
        uploadFileBtn.addEventListener('click', () => {
            document.getElementById('upload-modal').classList.remove('hidden');
        });
    }

    // 关闭上传对话框
    const closeUploadModal = document.getElementById('close-upload-modal');
    const closeUploadModal2 = document.getElementById('close-upload-modal-2');
    if (closeUploadModal) {
        closeUploadModal.addEventListener('click', () => {
            document.getElementById('upload-modal').classList.add('hidden');
        });
    }
    if (closeUploadModal2) {
        closeUploadModal2.addEventListener('click', () => {
            document.getElementById('upload-modal').classList.add('hidden');
        });
    }

    // 上传按钮
    const uploadBtn = document.getElementById('upload-file-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', uploadFile);
    }
});

// 下载文件处理函数
async function downloadFileHandler(fileId) {
    try {
        await api.downloadFile(fileId);
    } catch (error) {
        // 错误已在 downloadFile 方法中处理并显示 Toast
    }
}

// 导出函数
window.loadFiles = loadFiles;
window.showFileDetail = showFileDetail;
window.deleteFile = deleteFile;
window.downloadFileHandler = downloadFileHandler;