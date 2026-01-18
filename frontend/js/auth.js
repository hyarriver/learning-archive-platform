// 认证相关功能
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const loginError = document.getElementById('login-error');
    const registerError = document.getElementById('register-error');
    const showRegisterBtn = document.getElementById('show-register');
    const showLoginBtn = document.getElementById('show-login');
    const loginContainer = document.getElementById('login-form-container');
    const registerContainer = document.getElementById('register-form-container');

    // 切换登录/注册表单
    if (showRegisterBtn) {
        showRegisterBtn.addEventListener('click', () => {
            loginContainer.classList.add('hidden');
            registerContainer.classList.remove('hidden');
            loginError.classList.add('hidden');
            registerError.classList.add('hidden');
        });
    }

    if (showLoginBtn) {
        showLoginBtn.addEventListener('click', () => {
            registerContainer.classList.add('hidden');
            loginContainer.classList.remove('hidden');
            loginError.classList.add('hidden');
            registerError.classList.add('hidden');
        });
    }

    // 登录表单
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            loginError.classList.add('hidden');
            loginError.textContent = '';

            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;

            try {
                await api.login(username, password);
                showMainPage();
            } catch (error) {
                loginError.textContent = error.message;
                loginError.classList.remove('hidden');
            }
        });
    }

    // 注册表单
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            registerError.classList.add('hidden');
            registerError.textContent = '';

            const username = document.getElementById('register-username').value;
            const password = document.getElementById('register-password').value;

            try {
                await api.register(username, password);
                // 注册成功后自动登录
                await api.login(username, password);
                showMainPage();
            } catch (error) {
                registerError.textContent = error.message;
                registerError.classList.remove('hidden');
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
                // 显示登录页，不reload
                showLoginPage();
            });
    }
    
    // 监听认证失败事件
    window.addEventListener('auth-required', () => {
        showLoginPage();
    });
});

function showMainPage() {
    document.getElementById('auth-page').classList.add('hidden');
    document.getElementById('main-page').classList.remove('hidden');
    
    // 加载用户信息
    loadUserInfo();
    // 加载默认页面
    showPage('files');
}

function loadUserInfo() {
    api.getCurrentUser()
        .then(user => {
            const userElement = document.getElementById('current-user');
            const roleElement = document.getElementById('user-role');
            
            if (userElement) {
                userElement.textContent = user.username;
            }
            
            if (roleElement) {
                roleElement.textContent = user.role === 'admin' ? '管理员' : '普通用户';
                if (user.role === 'admin') {
                    // 显示管理员专用菜单
                    document.querySelectorAll('.admin-only').forEach(el => {
                        el.classList.remove('hidden');
                    });
                }
            }
        })
        .catch(() => {
            api.setToken(null);
            // 显示登录页，避免reload导致循环刷新
            showLoginPage();
        });
}

function showLoginPage() {
    document.getElementById('auth-page').classList.remove('hidden');
    document.getElementById('main-page').classList.add('hidden');
    // 重置表单
    document.getElementById('login-username').value = '';
    document.getElementById('login-password').value = '';
    document.getElementById('login-error').classList.add('hidden');
}

function logout() {
    api.setToken(null);
    showLoginPage();
}

// 导出函数
window.logout = logout;
