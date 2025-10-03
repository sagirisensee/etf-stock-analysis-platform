# AI量化投资分析平台

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

基于人工智能的ETF和股票投资分析Web平台，从原有的Telegram机器人项目升级而来。

## 📋 目录

- [功能特性](#功能特性)
- [安装指南](#安装指南)
- [使用指南](#使用指南)
- [支持的AI服务](#支持的ai服务)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 功能特性

### 🤖 智能分析
- **AI驱动分析**: 结合技术指标和大语言模型，提供综合评分和投资建议
- **实时数据**: 获取最新的市场行情和历史数据
- **技术指标**: 支持均线、MACD、布林通道等多种技术指标分析

### 📊 Web界面
- **现代化UI**: 响应式设计，支持桌面和移动设备
- **可视化展示**: 图表和卡片形式展示分析结果
- **实时更新**: 动态加载分析进度和结果

### 🛠 管理功能
- **标的池管理**: 图形化界面添加、删除和管理投资标的（ETF和股票）
- **配置管理**: Web界面配置AI模型参数，无需手动编辑配置文件
- **历史记录**: 保存和查看分析历史，支持导出功能

## 安装指南

### 环境要求
- Python 3.10+
- 支持OpenAI兼容API的大语言模型服务

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/sagirisensee/etf-stock-analysis-platform.git
   cd etf-stock-analysis-platform
   ```

2. **创建虚拟环境**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # 或 venv\Scripts\activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **启动应用**
   ```bash
   python run.py
   ```

5. **访问应用**
   打开浏览器访问: http://localhost:8888

## 🚀 快速开始（硅基流动免费版）

### 1. 获取免费API密钥
1. 访问 [硅基流动官网](https://siliconflow.cn)
2. 注册账号并登录
3. 在控制台获取API密钥

### 2. 配置AI模型
1. 启动应用后访问: http://localhost:8888
2. 点击"系统配置"
3. 填写以下信息：
   - **API基础URL**: `https://api.siliconflow.cn/v1`
   - **模型名称**: `Qwen/Qwen3-8B`
   - **API密钥**: 从硅基流动获取的密钥
4. 点击"保存配置"

### 3. 开始分析
1. 添加您关注的ETF和股票代码
2. 点击"开始分析"
3. 等待AI分析完成，查看评分和建议

## 使用指南

### 1. 系统配置
首次使用需要配置AI模型参数：
- 访问"系统配置"页面
- 填写AI模型API基础URL和密钥
- 选择合适的模型名称
- 设置数据缓存时间

**推荐配置（硅基流动免费）：**
- API基础URL: `https://api.siliconflow.cn/v1`
- 模型名称: `Qwen/Qwen3-8B`
- API密钥: 在[硅基流动官网](https://siliconflow.cn)注册获取

### 2. 管理标的池
- 访问"标的池管理"页面
- 添加您关注的ETF和股票代码
- 支持删除和修改投资标的
- 支持JSON格式导入导出

### 3. 开始分析
- 访问"智能分析"页面
- 选择ETF分析或股票分析
- 等待AI分析完成
- 查看评分和投资建议

### 4. 查看历史
- 访问"分析历史"页面
- 查看过往分析记录
- 支持搜索和筛选功能
- 可导出分析结果

## 支持的AI服务

### 硅基流动 (免费推荐) ⭐
- API基础URL: `https://api.siliconflow.cn/v1`
- 模型: `Qwen/Qwen3-8B`
- **完全免费**，分析质量优秀，推荐新手使用

### Perplexity AI
- API基础URL: `https://api.perplexity.ai`
- 模型: `sonar-pro`
- 性价比高，分析质量好

### OpenAI
- API基础URL: `https://api.openai.com/v1`
- 模型: `gpt-4`, `gpt-3.5-turbo`
- 分析质量最高，成本较高

### 其他兼容服务
支持任何OpenAI兼容的API服务

## 项目结构

```
my_etf_web/
├── app.py              # Flask主应用
├── run.py              # 启动脚本
├── requirements.txt    # 依赖列表
├── etf_analysis.db     # SQLite数据库（自动创建）
├── templates/          # HTML模板
│   ├── base.html       # 基础模板
│   ├── index.html      # 主页
│   ├── config.html     # 配置页面
│   ├── pools.html      # 标的池管理
│   ├── analysis.html   # 分析页面
│   └── history.html    # 历史记录
├── static/             # 静态资源
│   ├── css/            # 样式文件
│   ├── js/             # JavaScript文件
│   └── images/         # 图片资源
├── logs/               # 日志文件
├── config/             # 配置文件
└── core/               # 核心分析模块
    ├── __init__.py     # 包初始化
    ├── analysis.py     # 分析引擎
    ├── data_fetcher.py # 数据获取
    ├── llm_analyzer.py # AI分析器
    └── indicators.py   # 技术指标
```

## 技术栈

- **后端**: Flask, SQLite
- **前端**: Bootstrap 5, Chart.js, Font Awesome
- **数据源**: AKShare
- **AI模型**: OpenAI兼容API
- **技术指标**: 基于pandas的自定义实现

## 注意事项

1. **API密钥安全**: 请妥善保管您的AI模型API密钥
2. **网络连接**: 需要稳定的网络连接获取市场数据
3. **调用频率**: 注意AI API的调用频率限制
4. **数据准确性**: 分析结果仅供参考，投资有风险

## 从Telegram机器人迁移

如果您之前使用的是Telegram机器人版本：

1. 原有的`.env`配置文件不再需要
2. 标的池配置已迁移到Web界面管理
3. 所有分析功能保持不变，只是界面从Telegram转为Web
4. 支持更丰富的可视化展示
5. 已清理不需要的Telegram机器人相关代码

## 故障排除

### 常见问题

1. **启动失败**
   - 检查Python版本是否为3.10+
   - 确认所有依赖已正确安装

2. **分析失败**
   - 检查AI模型配置是否正确
   - 确认API密钥有效且有足够额度
   - 检查网络连接

3. **数据获取失败**
   - 检查网络连接
   - 可能是AKShare数据源临时不可用

### 日志查看
应用运行时会在控制台输出详细日志，有助于诊断问题。

## 开发计划

- [ ] 添加更多技术指标
- [ ] 支持自定义分析策略
- [ ] 添加邮件通知功能
- [ ] 支持多用户管理
- [ ] 添加数据可视化图表

## 🤝 贡献指南

我们欢迎任何形式的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

### 快速开始
1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详细信息。

## 🛡️ 安全

如果您发现了安全漏洞，请查看 [SECURITY.md](SECURITY.md) 了解如何报告。

## 📞 支持

如有问题或建议，请通过以下方式联系：
- 📝 [提交Issue](https://github.com/sagirisensee/etf-stock-analysis-platformt/issues)
- 📧 发送邮件到：[your-email@example.com]
- 📖 查看[文档](https://github.com/sagirisensee/etf-stock-analysis-platform/wiki)

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户！

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！
