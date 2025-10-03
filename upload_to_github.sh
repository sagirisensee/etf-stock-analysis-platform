#!/bin/bash

# GitHub上传脚本
# 使用方法: ./upload_to_github.sh

echo "🚀 准备上传到GitHub..."

# 检查是否已初始化git仓库
if [ ! -d ".git" ]; then
    echo "📦 初始化Git仓库..."
    git init
fi

# 添加所有文件
echo "📁 添加文件到Git..."
git add .

# 提交更改
echo "💾 提交更改..."
git commit -m "🎉 初始提交: AI量化投资分析平台 v1.0.0

✨ 功能特性:
- AI驱动的ETF和股票分析
- 现代化Web界面
- 图形化标的池管理
- 技术指标分析
- 分析历史记录
- JSON导入导出
- 多种AI服务支持

🛠 技术栈:
- Flask Web框架
- SQLite数据库
- AKShare数据源
- OpenAI兼容API
- 自定义技术指标

📚 文档:
- 完整的README
- 部署指南
- 贡献指南
- 安全政策
- 更新日志"

# 设置远程仓库（需要用户手动替换用户名）
echo "🔗 设置远程仓库..."
echo "请手动执行以下命令："
echo "git remote add origin https://github.com/YOUR_USERNAME/etf-stock-analysis-platform.git"
echo "git branch -M main"
echo "git push -u origin main"

echo ""
echo "✅ 本地Git设置完成！"
echo ""
echo "📋 下一步操作："
echo "1. 在GitHub上创建新仓库: etf-stock-analysis-platform"
echo "2. 复制仓库URL"
echo "3. 运行以下命令："
echo "   git remote add origin https://github.com/YOUR_USERNAME/etf-stock-analysis-platform.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "🎉 上传完成！"
