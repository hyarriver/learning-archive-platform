# GitHub 上传指南

## 步骤 1: 创建 GitHub 仓库

1. 访问 https://github.com
2. 登录你的账号
3. 点击右上角的 "+" → "New repository"
4. 填写仓库信息：
   - **Repository name**: `learning-archive-platform` (或你喜欢的名字)
   - **Description**: 学习资料聚合平台
   - **Visibility**: 选择 Public（公开）或 Private（私有）
   - **不要**勾选 "Initialize this repository with a README"（因为我们已经有了）
5. 点击 "Create repository"

## 步骤 2: 在本地提交代码

### 2.1 初始化 Git 仓库（如果还没有）

```bash
cd "d:\codeViews\Learning Archive Platform"
git init
```

### 2.2 配置 Git 用户信息（如果还没有配置）

```bash
git config --global user.name "你的名字"
git config --global user.email "your.email@example.com"
```

### 2.3 添加文件到 Git

```bash
# 添加所有文件
git add .

# 或者只添加特定文件
# git add backend/ frontend/ docs/ README.md .gitignore
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
- 完整的部署文档"
```

## 步骤 3: 连接到 GitHub 并推送

### 3.1 添加远程仓库

在 GitHub 创建仓库后，复制仓库地址（HTTPS 或 SSH），然后执行：

```bash
# 使用 HTTPS（推荐，简单）
git remote add origin https://github.com/你的用户名/learning-archive-platform.git

# 或使用 SSH（需要配置SSH密钥）
# git remote add origin git@github.com:你的用户名/learning-archive-platform.git
```

### 3.2 推送代码到 GitHub

```bash
# 推送到 main 分支
git branch -M main
git push -u origin main

# 如果遇到错误，可能需要先 pull
# git pull origin main --allow-unrelated-histories
```

### 3.3 如果需要输入用户名和密码

- **用户名**: 你的 GitHub 用户名
- **密码**: 使用 Personal Access Token（不是GitHub密码）
  - 获取 Token: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
  - 权限选择: `repo` 权限

## 步骤 4: 验证上传

访问你的 GitHub 仓库，应该能看到所有文件都已上传。

## 常用 Git 命令

```bash
# 查看状态
git status

# 查看提交历史
git log --oneline

# 添加文件
git add 文件名

# 提交更改
git commit -m "提交说明"

# 推送到远程
git push

# 拉取远程更新
git pull

# 查看远程仓库
git remote -v
```

## 注意事项

⚠️ **重要**：
- `.env` 文件已添加到 `.gitignore`，不会上传敏感信息
- `data/` 目录和 `logs/` 目录不会上传（这些是运行时生成的文件）
- `venv/` 虚拟环境不会上传（太大了）
- 确保 `.env.example` 文件已上传（作为配置模板）

## 后续更新代码

当你修改代码后，需要更新到 GitHub：

```bash
# 1. 查看更改
git status

# 2. 添加更改
git add .

# 3. 提交更改
git commit -m "描述你的更改"

# 4. 推送到 GitHub
git push
```

## 如果有冲突

如果多人协作或在不同地方修改了代码：

```bash
# 1. 先拉取远程更改
git pull origin main

# 2. 解决冲突（如果有）

# 3. 再次推送
git push
```

---

**代码上传到 GitHub 完成！**
