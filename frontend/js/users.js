// 用户管理功能
async function loadUsers() {
    const usersList = document.getElementById('users-list');
    usersList.innerHTML = '<div class="text-center py-8 text-muted-foreground">加载中...</div>';

    try {
        const users = await api.getUsers();
        displayUsers(users);
    } catch (error) {
        usersList.innerHTML = `<div class="text-center py-8 text-destructive">加载失败: ${error.message}</div>`;
    }
}

function displayUsers(users) {
    const usersList = document.getElementById('users-list');
    
    if (users.length === 0) {
        usersList.innerHTML = '<div class="text-center py-8 text-muted-foreground">暂无用户</div>';
        return;
    }

    usersList.innerHTML = '<div class="grid gap-4">' + users.map(user => `
        <div class="border border-border rounded-lg p-5 bg-card shadow-sm hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-3 mb-3">
                        <h3 class="text-lg font-semibold">${escapeHtml(user.username)}</h3>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            user.role === 'admin' 
                                ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300' 
                                : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
                        }">
                            ${user.role === 'admin' ? '👑 管理员' : '👤 普通用户'}
                        </span>
                    </div>
                    <div class="space-y-2 text-sm">
                        <div class="flex items-center gap-2 text-muted-foreground">
                            <span class="font-medium">ID:</span>
                            <span>${user.id}</span>
                        </div>
                        ${user.created_at ? `
                            <div class="flex items-center gap-2 text-muted-foreground">
                                <span class="font-medium">创建时间:</span>
                                <span>${formatDate(user.created_at)}</span>
                            </div>
                        ` : ''}
                        ${user.last_login ? `
                            <div class="flex items-center gap-2 text-muted-foreground">
                                <span class="font-medium">最后登录:</span>
                                <span>${formatDate(user.last_login)}</span>
                            </div>
                        ` : '<div class="flex items-center gap-2 text-muted-foreground"><span>从未登录</span></div>'}
                        <div class="flex items-center gap-2 text-muted-foreground">
                            <span class="font-medium">上传文件数:</span>
                            <span>${user.file_count || 0}</span>
                        </div>
                    </div>
                </div>
                <div class="flex flex-col gap-2 shrink-0">
                    <button 
                        onclick="toggleUserRole(${user.id}, '${user.role}')"
                        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 ${
                            user.role === 'admin' 
                                ? 'bg-yellow-500 text-white hover:bg-yellow-600' 
                                : 'bg-primary text-primary-foreground hover:bg-primary/90'
                        } h-9 px-4"
                        id="role-btn-${user.id}"
                    >
                        ${user.role === 'admin' ? '降为普通用户' : '提升为管理员'}
                    </button>
                    <button 
                        onclick="deleteUserHandler(${user.id}, '${escapeHtml(user.username)}')"
                        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-destructive text-destructive-foreground hover:bg-destructive/90 h-9 px-4"
                    >
                        删除
                    </button>
                </div>
            </div>
        </div>
    `).join('') + '</div>';
}

async function toggleUserRole(userId, currentRole) {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';
    const action = newRole === 'admin' ? '提升为管理员' : '降为普通用户';
    
    const confirmed = await showConfirm(
        `确定要将用户${action}吗？`,
        '修改用户权限',
        '确定',
        '取消'
    );
    
    if (!confirmed) {
        return;
    }

    try {
        await api.updateUser(userId, { role: newRole });
        showToast(`用户权限已${action}`, 'success', 3000);
        loadUsers();
    } catch (error) {
        showToast(`修改权限失败: ${error.message}`, 'error', 3000);
    }
}

async function deleteUserHandler(userId, username) {
    const confirmed = await showConfirm(
        `确定要删除用户 "${username}" 吗？此操作无法恢复，该用户上传的文件将保留但不再关联到用户。`,
        '删除用户',
        '删除',
        '取消'
    );
    
    if (!confirmed) {
        return;
    }

    try {
        await api.deleteUser(userId);
        showToast('用户删除成功', 'success', 3000);
        loadUsers();
    } catch (error) {
        showToast(`删除失败: ${error.message}`, 'error', 3000);
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

// 导出函数
window.loadUsers = loadUsers;
window.toggleUserRole = toggleUserRole;
window.deleteUserHandler = deleteUserHandler;