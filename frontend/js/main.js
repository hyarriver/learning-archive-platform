// 主应用逻辑
function showPage(pageName) {
    // 隐藏所有内容页
    document.querySelectorAll('.content-page').forEach(page => {
        page.classList.add('hidden');
    });
    
    // 显示指定页
    const targetPage = document.getElementById(`${pageName}-page`);
    if (targetPage) {
        targetPage.classList.remove('hidden');
    }
    
    // 更新导航状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('bg-primary', 'text-primary-foreground', 'shadow-md');
    });
    
    const navItem = document.querySelector(`[data-page="${pageName}"]`);
    if (navItem) {
        navItem.classList.add('bg-primary', 'text-primary-foreground', 'shadow-md');
    }
    
    // 加载对应页面数据
    if (pageName === 'files') {
        if (typeof loadFiles === 'function') {
            loadFiles();
        }
    } else if (pageName === 'collection') {
        if (typeof loadCollectionSources === 'function') {
            loadCollectionSources();
        }
    } else if (pageName === 'users') {
        if (typeof loadUsers === 'function') {
            loadUsers();
        }
    }
}

// 导出函数供全局使用
window.showPage = showPage;

// 暗夜模式切换功能
function initTheme() {
    // 读取本地存储的主题设置，默认跟随系统
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = savedTheme === 'dark' || (!savedTheme && prefersDark);
    
    applyTheme(isDark);
    updateThemeIcon(isDark);
}

function applyTheme(isDark) {
    const html = document.documentElement;
    if (isDark) {
        html.classList.add('dark');
    } else {
        html.classList.remove('dark');
    }
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

function updateThemeIcon(isDark) {
    const sunIcon = document.getElementById('theme-icon-sun');
    const moonIcon = document.getElementById('theme-icon-moon');
    
    if (sunIcon && moonIcon) {
        if (isDark) {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        } else {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        }
    }
}

function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    applyTheme(!isDark);
    updateThemeIcon(!isDark);
}

// 监听系统主题变化
if (window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', (e) => {
        // 如果用户没有手动设置主题，则跟随系统
        if (!localStorage.getItem('theme')) {
            applyTheme(e.matches);
            updateThemeIcon(e.matches);
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // 初始化主题
    initTheme();
    
    // 主题切换按钮
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }
    
    // 导航切换
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const pageName = item.getAttribute('data-page');
            showPage(pageName);
        });
    });
    
    // 退出按钮
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            logout();
        });
    }
    
    // 触发全部采集按钮
    const triggerAllBtn = document.getElementById('trigger-all-btn');
    if (triggerAllBtn) {
        triggerAllBtn.addEventListener('click', async () => {
            const confirmed = await showConfirm('确定要触发所有采集源吗？', '触发全部采集', '确定', '取消');
            if (confirmed) {
                triggerCollection();
            }
        });
    }
    
    // 添加采集源按钮
    const addSourceBtn = document.getElementById('add-source-btn');
    if (addSourceBtn) {
        addSourceBtn.addEventListener('click', () => {
            showAddSourceModal();
        });
    }
    
    // 关闭添加采集源对话框
    const closeAddSourceModal = document.getElementById('close-add-source-modal');
    const closeAddSourceModal2 = document.getElementById('close-add-source-modal-2');
    if (closeAddSourceModal) {
        closeAddSourceModal.addEventListener('click', () => {
            hideAddSourceModal();
        });
    }
    if (closeAddSourceModal2) {
        closeAddSourceModal2.addEventListener('click', () => {
            hideAddSourceModal();
        });
    }
});