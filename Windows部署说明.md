# Windows 系统部署到服务器指南

## 服务器信息
- **地址**: 112.124.2.164
- **端口**: 3000（SSH默认端口22）

## 方法一：使用 WinSCP（图形界面，推荐）

### 1. 下载安装 WinSCP
- 访问：https://winscp.net/
- 下载并安装 WinSCP

### 2. 连接服务器
1. 打开 WinSCP
2. 新建会话，填写：
   - **主机名**: 112.124.2.164
   - **端口**: 22
   - **用户名**: root
   - **密码**: （输入服务器密码）
   - **协议**: SFTP
3. 点击"登录"

### 3. 上传项目文件
1. 左侧窗口：浏览到项目目录 `d:\codeViews\Learning Archive Platform`
2. 右侧窗口：导航到 `/opt/` 目录
3. 选择整个项目文件夹，右键 → "上传"
4. 等待上传完成

## 方法二：使用 PowerShell scp 命令

### 在 PowerShell 中执行：

```powershell
# 进入项目父目录
cd "d:\codeViews"

# 上传项目（需要输入密码）
scp -r "Learning Archive Platform" root@112.124.2.164:/opt/
```

**注意**：
- 首次连接会提示确认主机密钥，输入 `yes`
- 需要输入服务器 root 密码
- 文件较大时可能需要等待

## 方法三：使用 Git（如果服务器有 Git）

### 在本地：
```powershell
# 如果还没有 Git 仓库，先初始化
cd "d:\codeViews\Learning Archive Platform"
git init
git add .
git commit -m "Initial commit"
```

### 在服务器上：
```bash
# SSH 登录服务器
ssh root@112.124.2.164

# 安装 Git（如果未安装）
yum install -y git  # CentOS
# 或
apt install -y git  # Ubuntu

# 克隆项目（如果使用远程仓库）
cd /opt
git clone <your-repo-url> "Learning Archive Platform"

# 或直接拉取本地仓库（需要先建立 SSH 连接）
```

## 方法四：使用压缩包传输

### 1. 在本地压缩项目

```powershell
# 进入项目目录
cd "d:\codeViews"

# 使用 PowerShell 压缩（排除不必要的文件）
Compress-Archive -Path "Learning Archive Platform" -DestinationPath "Learning Archive Platform.zip" -Force
```

或使用 7-Zip/WinRAR 手动压缩

### 2. 上传压缩包

```powershell
# 使用 scp 上传
scp "Learning Archive Platform.zip" root@112.124.2.164:/opt/
```

### 3. 在服务器上解压

```bash
# SSH 登录服务器
ssh root@112.124.2.164

# 解压文件
cd /opt
unzip "Learning Archive Platform.zip"
# 或
tar -xzf "Learning Archive Platform.tar.gz"
```

## 方法五：使用 rsync（如果安装了）

```powershell
# Windows 上需要安装 Git Bash 或 WSL
rsync -avz --progress "Learning Archive Platform/" root@112.124.2.164:/opt/Learning\ Archive\ Platform/
```

## 上传后的操作

### 1. SSH 登录服务器

```powershell
ssh root@112.124.2.164
```

### 2. 进入项目目录

```bash
cd /opt/Learning\ Archive\ Platform/backend
```

### 3. 设置 Python 环境

```bash
# 安装 Python（如果未安装）
yum install -y python3 python3-pip python3-venv  # CentOS
# 或
apt update && apt install -y python3 python3-pip python3-venv  # Ubuntu

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境变量示例
cp .env.example .env

# 编辑配置
nano .env
# 或
vi .env
```

**重要配置**：
```env
PORT=3000
DEBUG=False
APP_ENV=production
SECRET_KEY=生成的随机密钥
JWT_SECRET_KEY=生成的随机密钥
```

**生成随机密钥**：
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. 初始化数据库

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 初始化数据库
python scripts/init_db.py
```

### 6. 创建管理员用户

```bash
python scripts/create_user.py admin your_password
```

### 7. 启动服务

#### 测试运行：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

#### 使用 systemd 服务（推荐）：

创建服务文件：
```bash
sudo nano /etc/systemd/system/archive-platform.service
```

内容：
```ini
[Unit]
Description=Learning Archive Platform API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Learning Archive Platform/backend
Environment="PATH=/opt/Learning Archive Platform/backend/venv/bin"
ExecStart=/opt/Learning Archive Platform/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 3000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

启用并启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable archive-platform
sudo systemctl start archive-platform
sudo systemctl status archive-platform
```

### 8. 配置防火墙

```bash
# CentOS/RHEL
firewall-cmd --permanent --add-port=3000/tcp
firewall-cmd --reload

# Ubuntu/Debian
ufw allow 3000/tcp
ufw reload
```

## 验证部署

### 1. 检查服务状态
```bash
systemctl status archive-platform
```

### 2. 查看日志
```bash
journalctl -u archive-platform -f
```

### 3. 测试访问
- 健康检查: `http://112.124.2.164:3000/health`
- API 文档: `http://112.124.2.164:3000/docs`
- 前端页面: `http://112.124.2.164:3000/`

## 常见问题

### 1. scp 命令不可用
**解决方案**: 
- 使用 WinSCP（图形界面）
- 或安装 Git for Windows（包含 scp）
- 或使用 WSL（Windows Subsystem for Linux）

### 2. 权限被拒绝
**解决方案**:
```bash
# 检查目录权限
ls -la /opt/

# 修改权限
chmod 755 /opt/Learning\ Archive\ Platform
```

### 3. 端口 3000 无法访问
**解决方案**:
```bash
# 检查服务是否运行
systemctl status archive-platform

# 检查端口占用
netstat -tulpn | grep 3000

# 检查防火墙
firewall-cmd --list-all  # CentOS
ufw status  # Ubuntu
```

### 4. Python 依赖安装失败
**解决方案**:
```bash
# 更新 pip
pip install --upgrade pip setuptools wheel

# 安装系统依赖（如果需要）
# CentOS:
yum install -y python3-devel gcc
# Ubuntu:
apt install -y python3-dev build-essential
```

## 服务管理命令

```bash
# 启动服务
sudo systemctl start archive-platform

# 停止服务
sudo systemctl stop archive-platform

# 重启服务
sudo systemctl restart archive-platform

# 查看状态
sudo systemctl status archive-platform

# 查看日志
sudo journalctl -u archive-platform -f

# 查看最近100行日志
sudo journalctl -u archive-platform -n 100
```

---

**推荐使用方法一（WinSCP）**，操作简单，界面友好，支持断点续传。
