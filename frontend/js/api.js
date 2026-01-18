// API 封装
// 根据环境自动选择API地址
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? window.location.origin 
    : 'http://112.124.2.164:3000';

class API {
    constructor() {
        this.token = localStorage.getItem('token');
    }

    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem('token', token);
        } else {
            localStorage.removeItem('token');
        }
    }

    async request(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${API_BASE_URL}${url}`, {
            ...options,
            headers,
        });

        if (response.status === 401) {
            // Token 过期，清除token并显示登录页（避免立即reload导致循环刷新）
            this.setToken(null);
            // 触发自定义事件，让页面切换到登录状态，而不是立即reload
            window.dispatchEvent(new CustomEvent('auth-required'));
            throw new Error('认证失败，请重新登录');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: '请求失败' }));
            throw new Error(error.detail || '请求失败');
        }

        return response.json();
    }

    async login(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: '登录失败' }));
            throw new Error(error.detail || '登录失败');
        }

        const data = await response.json();
        this.setToken(data.access_token);
        return data;
    }

    async register(username, password) {
        const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: '注册失败' }));
            throw new Error(error.detail || '注册失败');
        }

        return response.json();
    }

    async getCurrentUser() {
        return this.request('/api/auth/me');
    }

    async getFiles(page = 1, pageSize = 20, filters = {}) {
        const params = new URLSearchParams({
            page: page.toString(),
            page_size: pageSize.toString(),
            ...filters,
        });
        return this.request(`/api/files?${params}`);
    }

    async getFile(fileId) {
        return this.request(`/api/files/${fileId}`);
    }

    async downloadFile(fileId) {
        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/files/${fileId}/download`, {
                headers,
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: '下载失败' }));
                throw new Error(error.detail || '下载失败');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            
            // 解析文件名
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'file.md';
            
            if (contentDisposition) {
                // 支持两种格式：filename="xxx.md" 或 filename*=UTF-8''xxx.md
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                    // 处理 URL 编码的文件名
                    if (filename.includes("''")) {
                        const parts = filename.split("''");
                        if (parts.length > 1) {
                            filename = decodeURIComponent(parts[parts.length - 1]);
                        }
                    }
                }
            }

            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            // 显示成功提示
            if (typeof showToast === 'function') {
                showToast('文件下载成功', 'success', 2000);
            }
        } catch (error) {
            // 显示错误提示
            if (typeof showToast === 'function') {
                showToast(error.message || '下载失败', 'error', 3000);
            }
            throw error;
        }
    }

    async uploadFile(file, title = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (title) {
            formData.append('title', title);
        }

        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${API_BASE_URL}/api/files/upload`, {
            method: 'POST',
            headers,
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: '上传失败' }));
            throw new Error(error.detail || '上传失败');
        }

        return response.json();
    }

    async deleteFile(fileId) {
        return this.request(`/api/files/${fileId}`, {
            method: 'DELETE',
        });
    }

    async getCollectionSources() {
        return this.request('/api/collection/sources');
    }

    async createCollectionSource(sourceData) {
        return this.request('/api/collection/sources', {
            method: 'POST',
            body: JSON.stringify(sourceData),
        });
    }

    async updateCollectionSource(sourceId, sourceData) {
        return this.request(`/api/collection/sources/${sourceId}`, {
            method: 'PUT',
            body: JSON.stringify(sourceData),
        });
    }

    async deleteCollectionSource(sourceId) {
        return this.request(`/api/collection/sources/${sourceId}`, {
            method: 'DELETE',
        });
    }

    async triggerCollection(sourceId = null) {
        if (sourceId) {
            return this.request(`/api/collection/sources/${sourceId}/trigger`, {
                method: 'POST',
            });
        } else {
            return this.request('/api/collection/trigger', {
                method: 'POST',
            });
        }
    }

    async getCollectionLogs(filters = {}) {
        const params = new URLSearchParams(filters);
        return this.request(`/api/collection/logs?${params}`);
    }

    // 用户管理API
    async getUsers() {
        return this.request('/api/users');
    }

    async getUser(userId) {
        return this.request(`/api/users/${userId}`);
    }

    async createUser(userData) {
        return this.request('/api/users', {
            method: 'POST',
            body: JSON.stringify(userData),
        });
    }

    async updateUser(userId, userData) {
        return this.request(`/api/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(userData),
        });
    }

    async deleteUser(userId) {
        return this.request(`/api/users/${userId}`, {
            method: 'DELETE',
        });
    }
}

// 全局 API 实例
const api = new API();