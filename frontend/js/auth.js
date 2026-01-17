// 认证相关功能
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            loginError.classList.remove('show');
            loginError.textContent = '';

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            try {
                await api.login(username, password);
                showMainPage();
            } catch (error) {
                loginError.textContent = error.message;
                loginError.classList.add('show');
            }
        });
    }

    // 检查是否已登录
    if (api.token) {
        api.getCurrentUser()
            .then(() => {
                showMainPage();
            })
            .catch(() => {
                api.setToken(null);
            });
    }
});

function showMainPage() {
    document.getElementById('login-page').classList.remove('active');
    document.getElementById('main-page').classList.add('active');
    
    // 加载用户信息
    loadUserInfo();
    // 加载默认页面
    showPage('files');
}

function loadUserInfo() {
    api.getCurrentUser()
        .then(user => {
            const userElement = document.getElementById('current-user');
            if (userElement) {
                userElement.textContent = user.username;
            }
        })
        .catch(() => {
            api.setToken(null);
            window.location.reload();
        });
}

function logout() {
    api.setToken(null);
    document.getElementById('login-page').classList.add('active');
    document.getElementById('main-page').classList.remove('active');
}

// 导出函数
window.logout = logout;