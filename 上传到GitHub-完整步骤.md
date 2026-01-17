# 上传代码到 GitHub - 完整步骤

## 步骤 1: 创建 GitHub 仓库

1. 访问 https://github.com 并登录
2. 点击右上角的 "+" → "New repository"
3. 填写信息：
   - **Repository name**: `learning-archive-platform` (或你喜欢的名字)
   - **Description**: 学习资料聚合平台 - 私域学习资料聚合平台，通过自动化采集将网页和视频内容转换为 Markdown 格式
   - **Visibility**: Public（公开）或 Private（私有）
   - **不要**勾选 "Add a README file"（我们已经有了）
4. 点击 "Create repository"

## 步骤 2: 在本地准备代码

### 2.1 进入项目目录

```bash
cd "d:\codeViews\Learning Archive Platform"
```

### 2.2 初始化 Git 仓库（如果还没有）

```bash
git init
```

### 2.3 添加所有文件

```bash
git add .
```

### 2.4 创建提交

```bash
git commit -m "Initial commit: Learning Archive Platform

- 完整的后端API（FastAPI）
- 爬虫模块（网页和视频）
- Markdown转换模块
- 文件管理和版本控制
- 任务调度系统
- 前端界面
- 完整的部署文档和脚本"
```

## 步骤 3: 连接到 GitHub

### 3.1 添加远程仓库

在 GitHub 创建仓库后，复制仓库地址（HTTPS），然后执行：

```bash
# 替换 YOUR_USERNAME 为你的 GitHub 用户名
# 替换 REPO_NAME 为你的仓库名
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# 例如：
# git remote add origin https://github.com/yourusername/learning-archive-platform.git
```

### 3.2 重命名分支为 main（如果使用的是 master）

```bash
git branch -M main
```

### 3.3 推送到 GitHub

```bash
git push -u origin main
```

如果提示输入用户名和密码：
- **用户名**: 你的 GitHub 用户名
- **密码**: 使用 **Personal Access Token**（不是 GitHub 密码）
  - 获取 Token: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
  - 权限选择: 勾选 `repo` 权限
  - 复制生成的 Token（只显示一次，注意保存）

## 步骤 4: 验证上传

访问你的 GitHub 仓库地址，应该能看到所有文件都已上传成功。

## 完整命令序列（复制粘贴）

```bash
# 1. 进入项目目录
cd "d:\codeViews\Learning Archive Platform"

# 2. 初始化 Git（如果还没有）
git init

# 3. 添加所有文件
git add .

# 4. 创建提交
git commit -m "Initial commit: Learning Archive Platform - Complete project with backend API, crawler, converter, file management, scheduler, frontend and deployment docs"

# 5. 添加远程仓库（替换 YOUR_USERNAME 和 REPO_NAME）
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# 6. 推送到 GitHub
git branch -M main
git push -u origin main
```

## 后续更新代码

当你修改代码后，需要更新到 GitHub：

```bash
# 1. 查看更改
git status

# 2. 添加更改的文件
git add .

# 3. 提交更改
git commit -m "描述你的更改内容"

# 4. 推送到 GitHub
git push
```

## 常见问题

### 1. 如果提示 "remote origin already exists"

```bash
# 删除现有的远程仓库
git remote remove origin

# 重新添加
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
```

### 2. 如果推送失败，需要先拉取

```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### 3. 如果遇到认证问题

确保使用 Personal Access Token 而不是密码：
- GitHub → Settings → Developer settings → Personal access tokens
- 创建新 token，选择 `repo` 权限

---

**代码已准备好上传到 GitHub！**
