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
        item.classList.remove('bg-accent', 'text-accent-foreground');
    });
    
    const navItem = document.querySelector(`[data-page="${pageName}"]`);
    if (navItem) {
        navItem.classList.add('bg-accent', 'text-accent-foreground');
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

document.addEventListener('DOMContentLoaded', () => {
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