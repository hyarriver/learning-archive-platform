// 主应用逻辑
function showPage(pageName) {
    // 隐藏所有内容页
    document.querySelectorAll('.content-page').forEach(page => {
        page.classList.remove('active');
    });
    
    // 显示指定页
    const targetPage = document.getElementById(`${pageName}-page`);
    if (targetPage) {
        targetPage.classList.add('active');
    }
    
    // 更新导航状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    const navItem = document.querySelector(`[data-page="${pageName}"]`);
    if (navItem) {
        navItem.classList.add('active');
    }
    
    // 加载对应页面数据
    if (pageName === 'files') {
        loadFiles();
    } else if (pageName === 'collection') {
        loadCollectionSources();
    }
}

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
        triggerAllBtn.addEventListener('click', () => {
            if (confirm('确定要触发所有采集源吗？')) {
                triggerCollection();
            }
        });
    }
});