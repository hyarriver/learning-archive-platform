// 美观的通知组件库
// Toast 通知和确认对话框

class NotificationManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // 创建通知容器
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'fixed top-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-none';
        document.body.appendChild(this.container);
    }

    // 显示 Toast 通知
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        const id = `toast-${Date.now()}-${Math.random()}`;
        toast.id = id;
        
        // 根据类型设置图标和颜色
        const configs = {
            success: {
                icon: '✓',
                bg: 'bg-green-500',
                text: 'text-white',
                border: 'border-green-600'
            },
            error: {
                icon: '✕',
                bg: 'bg-red-500',
                text: 'text-white',
                border: 'border-red-600'
            },
            warning: {
                icon: '⚠',
                bg: 'bg-yellow-500',
                text: 'text-white',
                border: 'border-yellow-600'
            },
            info: {
                icon: 'ℹ',
                bg: 'bg-blue-500',
                text: 'text-white',
                border: 'border-blue-600'
            }
        };

        const config = configs[type] || configs.info;

        toast.className = `${config.bg} ${config.text} border-2 ${config.border} rounded-lg shadow-xl px-4 py-3 min-w-[300px] max-w-[500px] pointer-events-auto transform transition-all duration-300 translate-x-full opacity-0 flex items-center gap-3`;
        toast.innerHTML = `
            <div class="flex-shrink-0 text-xl font-bold">${config.icon}</div>
            <div class="flex-1 text-sm font-medium">${this.escapeHtml(message)}</div>
            <button onclick="notificationManager.closeToast('${id}')" class="flex-shrink-0 text-white/80 hover:text-white transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;

        this.container.appendChild(toast);

        // 触发动画
        setTimeout(() => {
            toast.classList.remove('translate-x-full', 'opacity-0');
            toast.classList.add('translate-x-0', 'opacity-100');
        }, 10);

        // 自动关闭
        if (duration > 0) {
            setTimeout(() => {
                this.closeToast(id);
            }, duration);
        }

        return id;
    }

    // 关闭 Toast
    closeToast(id) {
        const toast = document.getElementById(id);
        if (!toast) return;

        toast.classList.remove('translate-x-0', 'opacity-100');
        toast.classList.add('translate-x-full', 'opacity-0');

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    // 显示确认对话框
    showConfirm(message, title = '确认操作', confirmText = '确定', cancelText = '取消') {
        return new Promise((resolve) => {
            // 创建遮罩层
            const overlay = document.createElement('div');
            overlay.className = 'fixed inset-0 bg-black/50 backdrop-blur-sm z-[9998] flex items-center justify-center p-4';
            overlay.style.animation = 'fadeIn 0.2s ease-out';

            // 创建对话框
            const dialog = document.createElement('div');
            dialog.className = 'bg-white dark:bg-gray-800 rounded-lg shadow-2xl border-2 border-gray-200 dark:border-gray-700 w-full max-w-md transform transition-all';
            dialog.style.animation = 'slideUp 0.3s ease-out';

            dialog.innerHTML = `
                <div class="p-6 space-y-4">
                    <div class="flex items-start gap-4">
                        <div class="flex-shrink-0 w-12 h-12 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-yellow-600 dark:text-yellow-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                                <line x1="12" y1="9" x2="12" y2="13"></line>
                                <line x1="12" y1="17" x2="12.01" y2="17"></line>
                            </svg>
                        </div>
                        <div class="flex-1">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">${this.escapeHtml(title)}</h3>
                            <p class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">${this.escapeHtml(message)}</p>
                        </div>
                    </div>
                    <div class="flex gap-3 justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
                        <button 
                            class="confirm-cancel-btn inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-secondary text-secondary-foreground hover:bg-secondary/80 h-10 px-4"
                        >
                            ${this.escapeHtml(cancelText)}
                        </button>
                        <button 
                            class="confirm-ok-btn inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4"
                        >
                            ${this.escapeHtml(confirmText)}
                        </button>
                    </div>
                </div>
            `;

            overlay.appendChild(dialog);
            document.body.appendChild(overlay);

            // 关闭函数
            const close = (result) => {
                overlay.style.animation = 'fadeOut 0.2s ease-out';
                dialog.style.animation = 'slideDown 0.3s ease-out';
                setTimeout(() => {
                    if (overlay.parentNode) {
                        overlay.parentNode.removeChild(overlay);
                    }
                }, 300);
                resolve(result);
            };

            // 绑定按钮事件
            dialog.querySelector('.confirm-ok-btn').addEventListener('click', () => close(true));
            dialog.querySelector('.confirm-cancel-btn').addEventListener('click', () => close(false));

            // 点击遮罩层关闭
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    close(false);
                }
            });

            // ESC 键关闭
            const handleEsc = (e) => {
                if (e.key === 'Escape') {
                    close(false);
                    document.removeEventListener('keydown', handleEsc);
                }
            };
            document.addEventListener('keydown', handleEsc);
        });
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 全局实例
const notificationManager = new NotificationManager();

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    @keyframes fadeOut {
        from {
            opacity: 1;
        }
        to {
            opacity: 0;
        }
    }

    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(20px) scale(0.95);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }

    @keyframes slideDown {
        from {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
        to {
            opacity: 0;
            transform: translateY(20px) scale(0.95);
        }
    }
`;
document.head.appendChild(style);

// 导出便捷方法
window.showToast = (message, type = 'info', duration = 3000) => {
    return notificationManager.showToast(message, type, duration);
};

window.showConfirm = (message, title, confirmText, cancelText) => {
    return notificationManager.showConfirm(message, title, confirmText, cancelText);
};

// 兼容旧的 alert/confirm 函数（可选，用于逐步迁移）
window.customAlert = (message, type = 'info') => {
    notificationManager.showToast(message, type, 4000);
};

window.customConfirm = (message, title) => {
    return notificationManager.showConfirm(message, title || '确认操作');
};