// 文件管理功能
let currentPage = 1;
let currentPageSize = 20;
let currentFilters = {};
let currentUserRole = 'user';
let selectedFiles = new Set(); // 存储选中的文件ID

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
    
    // 清空已选择的文件
    selectedFiles.clear();
    updateBulkActions();
    
    if (files.length === 0) {
        filesList.innerHTML = '<div class="text-center py-8 text-muted-foreground">暂无文件</div>';
        return;
    }

    // 按文件类型分组
    const collectionFiles = files.filter(f => f.file_type === 'collection');
    const uploadFiles = files.filter(f => f.file_type === 'upload');

    let html = '';

    // 显示采集文件（按来源分类，可展开收起）
    if (collectionFiles.length > 0) {
        html += '<div class="mb-6">';
        html += '<h3 class="text-lg font-semibold mb-4 text-muted-foreground">📚 采集文件</h3>';
        
        // 按采集源分组
        const filesBySource = {};
        collectionFiles.forEach(file => {
            const sourceName = file.source_name || '未分类';
            if (!filesBySource[sourceName]) {
                filesBySource[sourceName] = [];
            }
            filesBySource[sourceName].push(file);
        });
        
        // 生成分类列表
        const sources = Object.keys(filesBySource).sort();
        sources.forEach((sourceName, index) => {
            const sourceFiles = filesBySource[sourceName];
            const categoryId = `category-${sourceName.replace(/\s+/g, '-')}-${index}`;
            const isExpanded = index === 0; // 默认展开第一个分类
            
            html += `<div class="mb-4 border border-border rounded-lg overflow-hidden bg-card">`;
            // 分类标题（可点击展开/收起）
            html += `<button 
                class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-accent transition-colors category-toggle-btn" 
                data-category-id="${categoryId}"
                onclick="toggleCategory('${categoryId}')"
            >`;
            html += `<div class="flex items-center gap-2">`;
            html += `<span class="text-base font-semibold">${escapeHtml(sourceName)}</span>`;
            html += `<span class="text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded">${sourceFiles.length} 个文件</span>`;
            html += `</div>`;
            html += `<svg class="category-icon w-5 h-5 text-muted-foreground transition-transform" data-category-id="${categoryId}" ${isExpanded ? '' : 'style="transform: rotate(-90deg)"'} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">`;
            html += `<path d="M6 9l6 6 6-6"/>`;
            html += `</svg>`;
            html += `</button>`;
            
            // 文件列表（默认展开）
            html += `<div class="category-content ${isExpanded ? '' : 'hidden'}" id="${categoryId}">`;
            html += `<div class="px-4 pb-3 space-y-2">`;
            sourceFiles.forEach(file => {
                html += createFileCard(file);
            });
            html += `</div>`;
            html += `</div>`;
            html += `</div>`;
        });
        
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

// 切换分类展开/收起
function toggleCategory(categoryId) {
    const content = document.getElementById(categoryId);
    const icon = document.querySelector(`.category-icon[data-category-id="${categoryId}"]`);
    
    if (!content || !icon) return;
    
    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        icon.style.transform = 'rotate(0deg)';
    } else {
        content.classList.add('hidden');
        icon.style.transform = 'rotate(-90deg)';
    }
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
    
    // 判断是否为视频类型，视频类型不支持预览
    const isVideo = file.source_type === 'video';
    const clickHandler = isVideo ? '' : `onclick="showFileDetail(${file.id})"`;
    const cursorClass = isVideo ? '' : 'cursor-pointer';

    // 是否为管理员（管理员可以使用批量删除）
    const isAdmin = currentUserRole === 'admin';
    const isChecked = selectedFiles.has(file.id);

    return `
        <div class="card p-4 hover:bg-accent transition-colors ${isChecked && isAdmin ? 'ring-2 ring-primary' : ''}">
            <div class="flex items-start justify-between gap-4">
                ${isAdmin ? `
                    <input 
                        type="checkbox" 
                        class="file-checkbox mt-1 h-4 w-4 rounded border-input text-primary focus:ring-2 focus:ring-ring cursor-pointer" 
                        data-file-id="${file.id}"
                        ${isChecked ? 'checked' : ''}
                        onchange="toggleFileSelection(${file.id}, this.checked)"
                        onclick="event.stopPropagation();"
                    />
                ` : ''}
                <div class="flex-1 min-w-0 ${cursorClass}" ${clickHandler}>
                    <h3 class="text-base font-semibold mb-2 truncate">${escapeHtml(file.title)}</h3>
                    ${file.summary ? `<p class="text-sm text-muted-foreground mb-2 line-clamp-2">${escapeHtml(file.summary)}</p>` : ''}
                    <div class="flex flex-wrap items-center gap-3 text-xs text-muted-foreground mt-2">
                        <span class="inline-flex items-center px-2 py-1 rounded-md bg-secondary text-secondary-foreground">
                            ${file.file_type === 'collection' ? '📚 采集' : '📁 上传'}
                        </span>
                        ${isVideo ? '<span class="inline-flex items-center px-2 py-1 rounded-md bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300">🎥 视频</span>' : ''}
                        ${sourceInfo}
                        <span class="text-muted-foreground">${createdAt}</span>
                    </div>
                    ${isVideo ? '<div class="text-xs text-muted-foreground mt-1 italic">视频文件仅支持下载链接，不支持预览</div>' : ''}
                    ${file.tags && file.tags.length > 0 ? `
                        <div class="flex flex-wrap gap-1 mt-2">
                            ${file.tags.map(tag => `<span class="text-xs px-2 py-0.5 rounded bg-accent text-accent-foreground">${escapeHtml(tag)}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
                <div class="flex gap-2 items-start">
                    <button 
                        onclick="event.stopPropagation(); downloadFileHandler(${file.id})"
                        class="btn btn-secondary btn-sm"
                    >
                        下载
                    </button>
                    ${canDelete ? `
                        <button 
                            onclick="event.stopPropagation(); deleteFile(${file.id})"
                            class="btn btn-destructive btn-sm"
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

/**
 * 检测内容类型（代码 vs Markdown）
 */
function detectContentType(content) {
    if (!content || content.trim().length === 0) {
        return 'text';
    }
    
    // 检查是否主要是代码块（以```开头，或者代码块占大部分内容）
    const codeBlockPattern = /```[\s\S]*?```/g;
    const codeBlocks = content.match(codeBlockPattern);
    const codeBlockLength = codeBlocks ? codeBlocks.reduce((sum, block) => sum + block.length, 0) : 0;
    
    // 检查Markdown语法特征
    const markdownPatterns = [
        /^#{1,6}\s+.+$/m,           // 标题
        /^\*\s+.+$/m,               // 列表
        /^-\s+.+$/m,                // 列表
        /^\d+\.\s+.+$/m,            // 有序列表
        /\[.+\]\(.+\)/g,            // 链接
        /!\[.+\]\(.+\)/g,           // 图片
        /^\>\s+.+$/m,              // 引用
        /\|.+\|/g,                  // 表格
    ];
    
    const markdownMatches = markdownPatterns.reduce((count, pattern) => {
        const matches = content.match(pattern);
        return count + (matches ? matches.length : 0);
    }, 0);
    
    // 检查代码特征（关键词且格式整齐）
    const codeKeywords = /\b(function|class|import|export|def|const|let|var|return|if|else|for|while|public|private|static)\b/g;
    const codeMatches = (content.match(codeKeywords) || []).length;
    
    // 如果代码块占比超过30%，或者代码关键词很多且内容结构化，认为是代码
    const codeRatio = codeBlockLength / content.length;
    const isCodeHeavy = codeRatio > 0.3 || (codeMatches > 10 && codeBlockLength > 0);
    
    // 如果有明显的Markdown特征，认为是Markdown
    const isMarkdown = markdownMatches > 3 || (codeBlocks && codeBlocks.length > 0 && markdownMatches > 0);
    
    if (isCodeHeavy && !isMarkdown) {
        return 'code';
    } else if (isMarkdown || codeBlocks) {
        return 'markdown';
    } else {
        return 'text';
    }
}

/**
 * 渲染代码内容（带语法高亮）
 */
function renderCodeContent(content) {
    if (typeof hljs === 'undefined') {
        // 如果没有 highlight.js，返回简单格式
        return `<pre class="whitespace-pre-wrap bg-muted border border-border rounded-lg p-4 overflow-x-auto"><code>${escapeHtml(content)}</code></pre>`;
    }
    
    // 检测代码块中的语言
    const codeBlockPattern = /```(\w+)?\n?([\s\S]*?)```/g;
    const matches = [];
    let match;
    
    // 收集所有代码块
    while ((match = codeBlockPattern.exec(content)) !== null) {
        matches.push(match);
    }
    
    // 如果没有代码块，尝试自动检测语言
    if (matches.length === 0) {
        try {
            const highlighted = hljs.highlightAuto(content).value;
            return `<pre class="bg-[#0d1117] border border-border rounded-lg p-4 overflow-x-auto"><code class="hljs">${highlighted}</code></pre>`;
        } catch (e) {
            return `<pre class="whitespace-pre-wrap bg-muted border border-border rounded-lg p-4 overflow-x-auto"><code>${escapeHtml(content)}</code></pre>`;
        }
    }
    
    // 处理代码块
    let html = content;
    // 从后往前替换，避免索引问题
    for (let i = matches.length - 1; i >= 0; i--) {
        match = matches[i];
        const language = match[1] || '';
        const code = match[2].trim();
        try {
            const highlighted = hljs.highlight(code, { language: language || 'plaintext' }).value;
            const codeBlockHtml = `<pre class="bg-[#0d1117] border border-border rounded-lg p-4 overflow-x-auto mb-4"><code class="hljs language-${language}">${highlighted}</code></pre>`;
            html = html.substring(0, match.index) + codeBlockHtml + html.substring(match.index + match[0].length);
        } catch (e) {
            // 如果高亮失败，使用纯文本
            const codeBlockHtml = `<pre class="bg-muted border border-border rounded-lg p-4 overflow-x-auto mb-4"><code>${escapeHtml(code)}</code></pre>`;
            html = html.substring(0, match.index) + codeBlockHtml + html.substring(match.index + match[0].length);
        }
    }
    
    return html;
}

/**
 * 清理目录内容（TOC）- 移除包含大量锚点链接的冗余目录
 */
function cleanTOCContent(html) {
    // 匹配目录结构：通常是包含大量锚点链接的列表或段落
    
    // 1. 移除"目录"标题后的目录内容块
    // 匹配模式：<h1-6>目录</h1-6> 后面跟着大量锚点链接的内容
    const tocPattern = /(<h[1-6][^>]*>[\s]*目录[\s]*<\/h[1-6]>)([\s\S]{0,2000}?)(?=<h[1-6]|$)/gi;
    html = html.replace(tocPattern, (match, title, content) => {
        // 统计锚点链接数量
        const anchorLinks = (content.match(/href=["']#[^"']*["']/gi) || []).length;
        const totalLinks = (content.match(/<a[^>]*href=["'][^"']*["']/gi) || []).length;
        
        // 如果锚点链接数量多且占比高，认为是目录内容，隐藏
        if (anchorLinks >= 3 && (totalLinks === 0 || anchorLinks / totalLinks > 0.5)) {
            return `<div class="toc-section-hidden" style="display: none;">${title}${content}</div>`;
        }
        return match;
    });
    
    // 2. 移除包含URL编码的冗长锚点链接文本
    html = html.replace(/<a([^>]*)\shref=["']#([^"']+)["']([^>]*)>([^<]*(?:%[0-9A-F]{2}|cursor)[^<]{20,})<\/a>/gi, (match, before, href, after, text) => {
        // 如果链接文本包含URL编码且很长，隐藏
        if (text.includes('%') && text.length > 30) {
            return '<span class="toc-link-hidden" style="display: none;"></span>';
        }
        return match;
    });
    
    // 3. 移除列表项中只包含锚点的重复内容
    html = html.replace(/<li[^>]*>\s*<a[^>]*href=["']#[^"']*["'][^>]*>(.+?)<\/a>\s*<\/li>/gi, (match, text) => {
        // 如果文本是URL编码的长字符串，隐藏
        if (text.includes('%') && text.length > 30) {
            return '<li class="toc-item-hidden" style="display: none;"></li>';
        }
        return match;
    });
    
    return html;
}

/**
 * 渲染Markdown内容
 */
function renderMarkdownContent(content, fileId) {
    // 配置 marked
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(code, { language: lang }).value;
                    } catch (err) {}
                }
                return hljs.highlightAuto(code).value;
            },
            breaks: true,
            gfm: true
        });
        let html = marked.parse(content);
        
        // 清理冗余的目录内容
        html = cleanTOCContent(html);
        
        // 处理图片路径：将相对路径转换为API路径
        if (fileId) {
            // 匹配图片标签：![alt](path) 转换为 <img src="path">
            // 处理Markdown中的图片语法和HTML中的图片标签
            html = html.replace(/<img([^>]*)\ssrc=["']([^"']+)["']([^>]*)>/gi, (match, before, src, after) => {
                // 如果是相对路径（不以http开头），转换为API路径
                if (!src.startsWith('http://') && !src.startsWith('https://') && !src.startsWith('data:')) {
                    // 如果路径已经包含 images/，直接使用；否则添加 images/ 前缀
                    // 后端期望的格式：/api/files/{fileId}/images/images/{filename} 或 /api/files/{fileId}/images/{filename}
                    let imagePath = src;
                    // 移除开头的 ./ 或 /
                    imagePath = imagePath.replace(/^\.\//, '').replace(/^\//, '');
                    // 如果路径已经以 images/ 开头，直接使用
                    // 否则需要根据实际情况判断（如果是不带路径的文件名，需要加 images/）
                    // 但为了兼容性，我们直接使用原始路径，让后端处理
                    const apiPath = `/api/files/${fileId}/images/${encodeURIComponent(imagePath)}`;
                    return `<img${before} src="${apiPath}"${after}>`;
                }
                return match;
            });
            
            // 也处理Markdown语法的图片链接（如果marked没有转换）
            html = html.replace(/\[!\[([^\]]*)\]\(([^)]+)\)\]\([^)]+\)/g, (match, alt, src) => {
                if (!src.startsWith('http://') && !src.startsWith('https://') && !src.startsWith('data:')) {
                    // 移除开头的 ./ 或 /
                    let imagePath = src.replace(/^\.\//, '').replace(/^\//, '');
                    const apiPath = `/api/files/${fileId}/images/${encodeURIComponent(imagePath)}`;
                    return `<img src="${apiPath}" alt="${alt}">`;
                }
                return match;
            });
        }
        
        // 移除所有超链接的可点击功能（保留文本显示）
        html = html.replace(/<a([^>]*)\shref=["']([^"']+)["']([^>]*)>([^<]+)<\/a>/gi, (match, before, href, after, text) => {
            // 移除href属性，添加pointer-events: none样式，保留文本
            return `<span class="text-foreground" style="pointer-events: none; cursor: default;" title="${href}">${text} <span class="text-muted-foreground text-xs font-mono">(${href})</span></span>`;
        });
        
        return html;
    }
    // 如果没有 marked，返回原始内容
    return escapeHtml(content);
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
        
        // 检查是否为视频类型
        if (file.video_url) {
            // 视频类型：显示视频链接
            fileContent.innerHTML = `
                <div class="text-center py-8 space-y-4 max-w-2xl mx-auto">
                    <div class="text-2xl mb-4">🎥</div>
                    <div class="text-lg font-semibold text-foreground mb-2">${escapeHtml(file.title)}</div>
                    <div class="text-muted-foreground mb-4">视频类型文件不支持在线预览，请使用下方链接访问视频。</div>
                    <div class="card p-4 mb-4">
                        <div class="text-sm text-muted-foreground mb-2">视频链接：</div>
                        <a 
                            href="${escapeHtml(file.video_url)}" 
                            target="_blank" 
                            rel="noopener noreferrer"
                            class="text-primary hover:underline break-all inline-block max-w-full"
                        >
                            ${escapeHtml(file.video_url)}
                        </a>
                    </div>
                    <div class="flex gap-3 justify-center">
                        <button 
                            onclick="event.stopPropagation(); downloadFileHandler(${fileId})"
                            class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-6"
                        >
                            下载视频链接
                        </button>
                        <a 
                            href="${escapeHtml(file.video_url)}" 
                            target="_blank" 
                            rel="noopener noreferrer"
                            class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-secondary text-secondary-foreground hover:bg-secondary/80 h-10 px-6"
                        >
                            打开视频
                        </a>
                    </div>
                </div>
            `;
        } else {
            // 非视频类型：正常渲染内容
            // 检测内容类型并渲染
            const contentType = detectContentType(file.content);
            let renderedContent = '';
            
            if (contentType === 'code') {
                // 代码类型：使用代码高亮
                renderedContent = `<div class="code-content-wrapper w-full"><div class="code-content card p-4 sm:p-6 overflow-x-auto">${renderCodeContent(file.content)}</div></div>`;
        } else if (contentType === 'markdown') {
            // Markdown类型：使用Markdown渲染（传递fileId用于图片路径转换）
            // 使用最大宽度限制，改善阅读体验
            renderedContent = `<div class="markdown-wrapper w-full max-w-5xl mx-auto"><div class="markdown-content card p-4 sm:p-6 lg:p-8">${renderMarkdownContent(file.content, fileId)}</div></div>`;
        } else {
            // 普通文本：简单显示
            renderedContent = `<div class="text-content-wrapper w-full max-w-5xl mx-auto"><pre class="whitespace-pre-wrap card p-4 sm:p-6 overflow-x-auto">${escapeHtml(file.content)}</pre></div>`;
        }
            
            fileContent.innerHTML = renderedContent;
        }
        
        // 如果使用 highlight.js，需要初始化
        if (typeof hljs !== 'undefined') {
            fileContent.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }
        
        // 加载图片：使用fetch API携带认证token
        if (fileId) {
            loadImagesWithAuth(fileContent, fileId);
        }
        
        // 设置下载按钮
        document.getElementById('download-btn').onclick = async () => {
            try {
                await api.downloadFile(fileId);
            } catch (error) {
                // 错误已在 downloadFile 方法中处理并显示 Toast
            }
        };
    } catch (error) {
        // 如果是视频类型不支持预览的错误，显示更友好的提示
        if (error.message && error.message.includes('视频类型文件不支持预览')) {
            fileContent.innerHTML = `
                <div class="text-center py-8 space-y-4">
                    <div class="text-lg font-semibold text-foreground">🎥 视频文件</div>
                    <div class="text-muted-foreground">视频类型文件不支持在线预览，请使用下载功能查看文件内容。</div>
                    <button 
                        onclick="event.stopPropagation(); downloadFileHandler(${fileId})"
                        class="btn btn-primary"
                    >
                        下载文件
                    </button>
                </div>
            `;
        } else {
            fileContent.innerHTML = `<div class="text-center py-8 text-destructive">${error.message}</div>`;
        }
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

// 批量选择和删除功能
function toggleFileSelection(fileId, checked) {
    if (checked) {
        selectedFiles.add(fileId);
    } else {
        selectedFiles.delete(fileId);
    }
    updateBulkActions();
}

function selectAllFiles() {
    // 获取当前页面所有文件的checkbox
    const checkboxes = document.querySelectorAll('#files-list input[type="checkbox"].file-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(cb => {
        const fileId = parseInt(cb.getAttribute('data-file-id'));
        if (isNaN(fileId)) return;
        
        cb.checked = !allChecked;
        if (!allChecked) {
            selectedFiles.add(fileId);
        } else {
            selectedFiles.delete(fileId);
        }
    });
    
    updateBulkActions();
}

function updateBulkActions() {
    const bulkActionsBar = document.getElementById('bulk-actions-bar');
    const selectAllBtn = document.getElementById('select-all-btn');
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
    const selectedCountEl = document.getElementById('selected-count');
    
    if (!bulkActionsBar || currentUserRole !== 'admin') {
        return;
    }
    
    const count = selectedFiles.size;
    
    if (count > 0) {
        bulkActionsBar.classList.remove('hidden');
        if (bulkDeleteBtn) {
            bulkDeleteBtn.textContent = `批量删除 (${count})`;
        }
        if (selectedCountEl) {
            selectedCountEl.textContent = `已选择 ${count} 个文件`;
        }
    } else {
        bulkActionsBar.classList.add('hidden');
    }
}

async function bulkDeleteFiles() {
    if (selectedFiles.size === 0) {
        showToast('请先选择要删除的文件', 'warning', 2000);
        return;
    }
    
    const confirmed = await showConfirm(
        `确定要删除选中的 ${selectedFiles.size} 个文件吗？此操作无法恢复。`,
        '批量删除文件',
        '删除',
        '取消'
    );
    
    if (!confirmed) {
        return;
    }
    
    const fileIds = Array.from(selectedFiles);
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
    const originalText = bulkDeleteBtn ? bulkDeleteBtn.textContent : '批量删除';
    
    if (bulkDeleteBtn) {
        bulkDeleteBtn.disabled = true;
        bulkDeleteBtn.textContent = '删除中...';
    }
    
    try {
        const result = await api.bulkDeleteFiles(fileIds);
        showToast(result.message || `成功删除 ${result.success_count || fileIds.length} 个文件`, 'success', 3000);
        selectedFiles.clear();
        updateBulkActions();
        // 重新加载文件列表
        loadFiles(currentPage, currentFilters);
    } catch (error) {
        showToast(`批量删除失败: ${error.message}`, 'error', 3000);
    } finally {
        if (bulkDeleteBtn) {
            bulkDeleteBtn.disabled = false;
            bulkDeleteBtn.textContent = originalText;
        }
    }
}

// 加载图片（带认证）
async function loadImagesWithAuth(container, fileId) {
    const images = container.querySelectorAll('img');
    
    // 获取API基础URL
    const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? window.location.origin 
        : 'http://112.124.2.164:3000';
    
    images.forEach(async (img) => {
        const src = img.getAttribute('src');
        
        // 只处理API路径的图片（/api/files/...）
        if (src && src.startsWith('/api/files/') && src.includes('/images/')) {
            try {
                // 使用fetch API携带认证token获取图片
                const fullUrl = src.startsWith('http') ? src : `${API_BASE_URL}${src}`;
                const headers = {};
                if (api.token) {
                    headers['Authorization'] = `Bearer ${api.token}`;
                }
                
                const response = await fetch(fullUrl, { headers });
                
                if (!response.ok) {
                    console.error(`Failed to load image: ${src}`, response.status);
                    img.alt = '图片加载失败';
                    img.style.opacity = '0.5';
                    return;
                }
                
                const blob = await response.blob();
                const blobUrl = window.URL.createObjectURL(blob);
                
                // 更新图片src为blob URL
                img.src = blobUrl;
                
                // 当图片加载完成后，清理blob URL（可选，但会导致缓存失效）
                // img.onload = () => {
                //     window.URL.revokeObjectURL(blobUrl);
                // };
            } catch (error) {
                console.error(`Error loading image: ${src}`, error);
                img.alt = '图片加载失败';
                img.style.opacity = '0.5';
            }
        }
    });
}

// 导出函数
window.loadFiles = loadFiles;
window.showFileDetail = showFileDetail;
window.deleteFile = deleteFile;
window.downloadFileHandler = downloadFileHandler;
window.toggleFileSelection = toggleFileSelection;
window.selectAllFiles = selectAllFiles;
window.bulkDeleteFiles = bulkDeleteFiles;
window.toggleCategory = toggleCategory;