// 文件管理功能
let currentPage = 1;
let currentPageSize = 20;
let currentFilters = {};

async function loadFiles(page = 1, filters = {}) {
    currentPage = page;
    currentFilters = filters;
    
    const filesList = document.getElementById('files-list');
    filesList.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const data = await api.getFiles(page, currentPageSize, filters);
        displayFiles(data.items);
        displayPagination(data.total, data.page, data.page_size);
    } catch (error) {
        filesList.innerHTML = `<div class="error-message show">${error.message}</div>`;
    }
}

function displayFiles(files) {
    const filesList = document.getElementById('files-list');
    
    if (files.length === 0) {
        filesList.innerHTML = '<div class="loading">暂无文件</div>';
        return;
    }

    filesList.innerHTML = files.map(file => `
        <div class="file-card" onclick="showFileDetail(${file.id})">
            <h3>${escapeHtml(file.title)}</h3>
            ${file.summary ? `<p class="file-meta">${escapeHtml(file.summary)}</p>` : ''}
            ${file.tags && file.tags.length > 0 ? `
                <div class="file-tags">
                    ${file.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                </div>
            ` : ''}
            <p class="file-meta">创建时间: ${formatDate(file.created_at)}</p>
        </div>
    `).join('');
}

function displayPagination(total, page, pageSize) {
    const pagination = document.getElementById('pagination');
    const totalPages = Math.ceil(total / pageSize);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    
    // 上一页
    if (page > 1) {
        html += `<button onclick="loadFiles(${page - 1}, currentFilters)">上一页</button>`;
    }
    
    // 页码
    for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {
        html += `<button class="${i === page ? 'active' : ''}" onclick="loadFiles(${i}, currentFilters)">${i}</button>`;
    }
    
    // 下一页
    if (page < totalPages) {
        html += `<button onclick="loadFiles(${page + 1}, currentFilters)">下一页</button>`;
    }
    
    pagination.innerHTML = html;
}

async function showFileDetail(fileId) {
    // 隐藏文件列表页，显示详情页
    document.getElementById('files-page').classList.remove('active');
    document.getElementById('file-detail-page').classList.add('active');

    const fileContent = document.getElementById('file-content');
    fileContent.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const file = await api.getFile(fileId);
        document.getElementById('file-title').textContent = file.title;
        
        // 简单的 Markdown 渲染（可以替换为更强大的库）
        fileContent.innerHTML = `<pre>${escapeHtml(file.content)}</pre>`;
        
        // 设置下载按钮
        document.getElementById('download-btn').onclick = () => {
            api.downloadFile(fileId);
        };
    } catch (error) {
        fileContent.innerHTML = `<div class="error-message show">${error.message}</div>`;
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
    return date.toLocaleString('zh-CN');
}

// 搜索功能
document.addEventListener('DOMContentLoaded', () => {
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
    
    const backBtn = document.getElementById('back-btn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            document.getElementById('file-detail-page').classList.remove('active');
            document.getElementById('files-page').classList.add('active');
        });
    }
});

// 导出函数
window.loadFiles = loadFiles;
window.showFileDetail = showFileDetail;