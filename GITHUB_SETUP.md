# GitHub上传指南

## 🚀 快速上传

### 方法一：使用脚本（推荐）
```bash
# 运行上传脚本
./upload_to_github.sh

# 然后按照脚本提示操作
```

### 方法二：手动上传
```bash
# 1. 初始化Git仓库
git init

# 2. 添加所有文件
git add .

# 3. 提交更改
git commit -m "🎉 初始提交: AI量化投资分析平台 v1.0.0"

# 4. 设置远程仓库
git remote add origin https://github.com/YOUR_USERNAME/etf-stock-analysis-platform.git

# 5. 设置主分支
git branch -M main

# 6. 推送到GitHub
git push -u origin main
```

## 📋 上传前检查清单

### ✅ 必需文件
- [x] `.gitignore` - Git忽略文件
- [x] `LICENSE` - MIT许可证
- [x] `README.md` - 项目说明
- [x] `requirements.txt` - 依赖列表
- [x] `setup.py` - 包配置

### ✅ 文档文件
- [x] `CONTRIBUTING.md` - 贡献指南
- [x] `CHANGELOG.md` - 更新日志
- [x] `SECURITY.md` - 安全政策
- [x] `DEPLOYMENT.md` - 部署指南

### ✅ GitHub配置
- [x] `.github/workflows/ci.yml` - CI/CD工作流
- [x] `.github/workflows/release.yml` - 发布工作流
- [x] `.github/ISSUE_TEMPLATE/` - Issue模板
- [x] `.github/pull_request_template.md` - PR模板

### ✅ 项目文件
- [x] `app.py` - Flask主应用
- [x] `run.py` - 开发环境启动
- [x] `run_production.py` - 生产环境启动
- [x] `core/` - 核心模块
- [x] `templates/` - HTML模板
- [x] `static/` - 静态资源

## 🔧 GitHub仓库设置

### 1. 创建新仓库
1. 登录GitHub
2. 点击右上角的 "+" 号
3. 选择 "New repository"
4. 仓库名称：`etf-stock-analysis-platform`
5. 描述：`AI-powered ETF and stock analysis web platform`
6. 选择 "Public" 或 "Private"
7. 不要勾选 "Initialize with README"（我们已经有了）
8. 点击 "Create repository"

### 2. 配置仓库设置
1. 进入仓库设置页面
2. 在 "Features" 部分启用：
   - Issues
   - Projects
   - Wiki
   - Discussions
3. 在 "Pages" 部分配置（如果需要）
4. 在 "Security" 部分启用：
   - Dependency graph
   - Dependabot alerts
   - Dependabot security updates

### 3. 设置分支保护
1. 进入 "Settings" → "Branches"
2. 添加规则保护 `main` 分支
3. 要求：
   - Pull request reviews
   - Status checks
   - Up-to-date branches

## 📝 更新仓库信息

### 替换占位符
在以下文件中替换 `YOUR_USERNAME` 为你的GitHub用户名：
- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `setup.py`

### 更新联系方式
在以下文件中更新邮箱地址：
- `setup.py`
- `SECURITY.md`
- `README.md`

## 🏷️ 创建第一个Release

```bash
# 1. 创建标签
git tag -a v1.0.0 -m "Release version 1.0.0"

# 2. 推送标签
git push origin v1.0.0

# 3. 在GitHub上创建Release
# 访问: https://github.com/YOUR_USERNAME/etf-stock-analysis-platform/releases
# 点击 "Create a new release"
# 选择标签: v1.0.0
# 标题: Release v1.0.0
# 描述: 初始版本发布
```

## 🔄 日常维护

### 更新代码
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 创建功能分支
git checkout -b feature/new-feature

# 3. 提交更改
git add .
git commit -m "feat: add new feature"

# 4. 推送分支
git push origin feature/new-feature

# 5. 创建Pull Request
```

### 更新文档
```bash
# 更新CHANGELOG.md
# 更新README.md
# 提交更改
git add CHANGELOG.md README.md
git commit -m "docs: update documentation"
git push origin main
```

## 🎉 完成！

上传完成后，你的项目将拥有：
- ✅ 专业的README和文档
- ✅ 完整的CI/CD工作流
- ✅ 贡献指南和Issue模板
- ✅ 安全政策和许可证
- ✅ 规范的代码结构

项目地址：`https://github.com/YOUR_USERNAME/etf-stock-analysis-platform`
