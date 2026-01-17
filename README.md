# 学习资料聚合平台 (Learning Archive Platform)

## 项目简介

一个私域学习资料聚合平台，通过自动化采集将网页和视频内容转换为 Markdown 格式，实现学习资料的长期沉淀和统一管理。

## 核心功能

- 🔄 **自动化采集**：每日定时采集指定网站的学习内容
- 📝 **Markdown转换**：将网页和视频字幕转换为标准Markdown格式
- 📂 **文件管理**：按来源、主题组织，支持版本管理
- 🔐 **权限控制**：登录用户才能访问和下载
- 📱 **多端访问**：PC和移动端浏览器响应式支持

## 技术栈

- **后端**: Python + FastAPI
- **数据库**: SQLite
- **爬虫**: requests + BeautifulSoup / yt-dlp
- **转换**: pandoc / html2text
- **任务调度**: APScheduler
- **前端**: 响应式Web（HTML/CSS/JS 或 React/Vue）

## 项目结构

```
Learning Archive Platform/
├── docs/                    # 文档
│   ├── 01-技术架构设计.md
│   ├── 02-开发计划.md
│   └── 03-痛点分析与解决方案.md
├── backend/                 # 后端代码
│   ├── app/
│   ├── tests/
│   └── scripts/
├── frontend/                # 前端代码
├── data/                    # 数据存储（运行时生成）
│   ├── collections/
│   └── uploads/
└── README.md
```

## 快速开始

### 环境要求

- Python 3.9+
- 40GB 存储空间（用于存放采集内容）

### 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd "Learning Archive Platform"

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
cd backend
pip install -r requirements.txt

# 4. 初始化数据库
python scripts/init_db.py

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置必要参数

# 6. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 访问应用

- 前端: `http://localhost:8000`（如前端独立部署）
- API文档: `http://localhost:8000/docs`（FastAPI自动生成）

## 配置说明

### 采集源配置

在数据库中配置 `collection_sources` 表，或通过管理界面添加。

示例配置：
```json
{
  "name": "技术博客",
  "url_pattern": "https://example.com/blog/*",
  "source_type": "webpage",
  "crawler_config": {
    "selectors": {
      "title": "h1",
      "content": ".article-content"
    }
  }
}
```

## 开发计划

详见 [docs/02-开发计划.md](./docs/02-开发计划.md)

### MVP 阶段（16-25天）
- [x] 项目结构搭建
- [ ] 爬虫模块
- [ ] Markdown转换
- [ ] 文件存储与版本管理
- [ ] 用户认证
- [ ] 基础前端

## 重要说明

### 使用边界

- ⚠️ **私域使用**：仅限个人和小规模群体（<50人）
- ⚠️ **不公开传播**：不支持公开分享链接
- ⚠️ **版权尊重**：用于个人学习，不用于商业用途

### 不做功能

- ❌ 内容搜索引擎
- ❌ AI自动总结
- ❌ 公开分享功能
- ❌ 商业化功能

## 常见问题

### Q: 采集失败怎么办？
A: 系统会记录失败日志，支持手动补采。单URL失败不影响整体任务。

### Q: 存储空间不够怎么办？
A: 可以配置归档策略，定期清理旧版本，或只保留差异版本。

### Q: 支持哪些视频平台？
A: 优先支持 yt-dlp 支持的平台（YouTube、B站等），具体取决于yt-dlp更新。

## 许可证

本项目仅供个人学习使用。

## 贡献

欢迎提交Issue和Pull Request。

---

**注意**: 本项目仍处于开发阶段，功能可能不完整。请参考 [开发计划](./docs/02-开发计划.md) 了解当前进度。
