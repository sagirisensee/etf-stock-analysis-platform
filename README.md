# AI量化投资分析平台

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

基于人工智能的ETF和股票投资分析Web平台，支持用户登录、实时数据分析、技术指标计算和AI驱动投资建议。

## 📋 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [用户登录系统](#用户登录系统)
- [安装指南](#安装指南)
- [使用指南](#使用指南)
- [支持的AI服务](#支持的ai服务)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [更新日志](#更新日志)
- [故障排除](#故障排除)
- [许可证](#许可证)

## 功能特性

### 🤖 智能分析
- **AI驱动分析**: 结合技术指标和大语言模型，提供综合评分和投资建议
- **实时数据**: 获取最新的市场行情和历史数据
- **技术指标**: 支持均线、MACD、布林通道等多种技术指标分析
- **多数据源**: 东方财富、同花顺等数据源，自动切换备用源

### 🔐 用户认证
- **安全登录**: 支持用户注册、登录、登出功能
- **密码加密**: 使用Werkzeug scrypt算法，安全存储密码
- **会话管理**: 自动登录状态保持，安全退出
- **访问控制**: 敏感功能需要登录验证

### 📊 Web界面
- **现代化UI**: 响应式设计，支持桌面和移动设备
- **可视化展示**: 图表和卡片形式展示分析结果
- **实时更新**: 动态加载分析进度和结果
- **用户友好**: 直观的操作界面和清晰的导航

### 🛠 管理功能
- **标的池管理**: 图形化界面添加、删除和管理投资标的（ETF和股票）
- **配置管理**: Web界面配置AI模型参数，无需手动编辑配置文件
- **历史记录**: 保存和查看分析历史，支持导出功能
- **数据导入导出**: 支持JSON格式的标的池导入导出

## 快速开始

### 1. 安装依赖

```bash
# 使用conda (推荐)
conda create -n etf_web python=3.10
conda activate etf_web

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动应用

```bash
python run.py
```

### 3. 访问系统

打开浏览器访问：http://localhost:8888

### 4. 首次使用

1. **登录系统**：使用默认账号 `admin` / `admin123`
2. **配置API**：进入配置页面填写LLM API信息
3. **设置标的池**：添加要分析的ETF或股票
4. **开始分析**：选择分析类型并开始

## 用户登录系统

### 默认管理员账号

- **用户名**: `admin`
- **密码**: `admin123`

> ⚠️ **安全提醒**: 首次登录后请立即修改默认密码！

### 用户注册

1. 访问注册页面：http://localhost:8888/register
2. 填写注册信息：
   - 用户名：3-20个字符，只能包含字母、数字和下划线
   - 密码：至少6个字符
   - 确认密码：必须与密码一致
3. 点击"注册"按钮

### 密码安全

- ✅ 密码使用Werkzeug安全哈希算法加密存储
- ✅ 数据库中不会存储明文密码
- ✅ 支持密码显示/隐藏切换
- ✅ 实时密码强度验证

### 访问控制

**需要登录的功能**：
- 📊 分析功能
- ⚙️ 配置管理  
- 📋 标的池管理
- 📈 历史记录

**公开访问**：
- 🏠 首页
- 🔐 登录/注册页面

## 安装指南

### 环境要求

- Python 3.10+ (推荐 3.10.x)
- pip 或 conda 包管理器

### 安装步骤

#### 方法1：使用conda (推荐)

```bash
# 创建虚拟环境
conda create -n etf_web python=3.10
conda activate etf_web

# 安装依赖
pip install -r requirements.txt
```

#### 方法2：使用venv

```bash
# 创建虚拟环境
python -m venv etf_web
source etf_web/bin/activate  # Linux/Mac
# 或
etf_web\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 依赖说明

#### 核心依赖
- `numpy`: 数值计算
- `pandas`: 数据处理和分析
- `akshare`: 金融数据获取
- `cachetools`: 数据缓存
- `tenacity`: 重试机制
- `openai`: AI接口

#### Web框架
- `Flask`: Web应用框架
- `Jinja2`: 模板引擎
- `Werkzeug`: 密码安全处理

### 验证安装

```bash
# 激活环境
conda activate etf_web

# 测试导入
python -c "
import numpy, pandas, akshare, cachetools, tenacity, flask, openai
from core.data_fetcher import get_all_etf_spot_realtime
print('✅ 所有依赖安装成功！')
"
```

## 使用指南

### 1. 系统配置

首次使用需要配置AI模型参数：

**推荐配置（硅基流动免费）：**
- API基础URL: `https://api.siliconflow.cn/v1`
- 模型名称: `Qwen/Qwen3-8B`
- API密钥: 在[硅基流动官网](https://siliconflow.cn)注册获取

**其他可选配置：**
- Perplexity AI: `https://api.perplexity.ai` (模型: `sonar-pro`)
- OpenAI: `https://api.openai.com/v1` (模型: `gpt-3.5-turbo`)

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
- ✅ 完全兼容OpenAI格式

### Perplexity AI
- API基础URL: `https://api.perplexity.ai`
- 模型: `sonar-pro`
- 性价比高，分析质量好
- ✅ **特殊适配**：自动检测并适配Perplexity响应格式

### OpenAI
- API基础URL: `https://api.openai.com/v1`
- 模型: `gpt-4`, `gpt-3.5-turbo`
- 分析质量最高，成本较高
- ✅ 原生支持OpenAI格式

### 其他兼容服务
- ✅ 支持任何OpenAI兼容的API服务
- ✅ 自动检测API提供商类型
- ✅ 智能适配不同响应格式

## 项目结构

```
my_etf_web/
├── app.py              # Flask主应用
├── run.py              # 启动脚本
├── run_production.py   # 生产环境启动脚本
├── requirements.txt    # 依赖列表
├── etf_analysis.db     # SQLite数据库（自动创建）
├── templates/          # HTML模板
│   ├── base.html       # 基础模板
│   ├── index.html      # 主页
│   ├── login.html      # 登录页面
│   ├── register.html   # 注册页面
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

- **后端**: Flask, SQLite, Werkzeug
- **前端**: Bootstrap 5, Chart.js, Font Awesome
- **数据源**: AKShare (东方财富、同花顺)
- **AI模型**: OpenAI兼容API
- **技术指标**: 基于pandas的自定义实现
- **安全**: Werkzeug密码哈希、Flask会话管理

## 更新日志

### v1.3.0 - API适配优化 (2025-10-06)

#### 🔧 API兼容性
- ✅ **Perplexity AI特殊适配**：解决400错误和响应格式问题
- ✅ **自动API检测**：智能识别API提供商类型
- ✅ **多格式解析**：支持不同API的响应格式
- ✅ **兜底机制**：解析失败时使用默认值，确保系统稳定

#### 🎯 技术改进
- ✅ 移除Perplexity AI的response_format限制
- ✅ 智能JSON提取（支持文本+JSON混合格式）
- ✅ 正则表达式模式匹配
- ✅ 错误处理和日志记录优化

### v1.2.0 - 用户认证系统 (2025-10-06)

#### 🔐 新增功能
- ✅ 用户注册、登录、登出功能
- ✅ 密码安全哈希处理 (Werkzeug scrypt)
- ✅ 会话管理和访问控制
- ✅ 默认管理员账号自动创建
- ✅ 美观的登录/注册界面

#### 🛡️ 安全特性
- ✅ 密码不可逆加密存储
- ✅ 登录装饰器保护敏感路由
- ✅ 自动重定向未登录用户
- ✅ 用户名唯一性验证

### v1.1.0 - 系统优化 (2025-10-05)

#### 🧹 调试日志清理
- ✅ 移除详细调试信息，输出更简洁
- ✅ 保留关键错误和警告日志
- ✅ 优化控制台显示效果

#### 📋 依赖优化
- ✅ 移除pandas_ta依赖（代码中未使用）
- ✅ 优化requirements.txt版本要求
- ✅ 所有技术指标使用pandas内置功能

#### 🔧 数据获取优化
- ✅ 智能数据天数配置 (60-90天)
- ✅ 多数据源自动切换
- ✅ 反爬虫对抗措施
- ✅ 动态日期范围计算

### v1.0.0 - 基础功能 (2025-10-04)

#### 🚀 核心功能
- ✅ ETF和股票实时数据分析
- ✅ 技术指标计算 (SMA、MACD、布林通道)
- ✅ AI驱动投资建议和评分
- ✅ Web界面配置管理
- ✅ 标的池管理
- ✅ 分析历史记录

## 故障排除

### 常见问题

#### 1. 安装问题

**pandas_ta安装失败**
```
ERROR: Could not find a version that satisfies the requirement pandas_ta
```
**解决方案**: 项目已移除pandas_ta依赖，所有技术指标都使用pandas内置功能计算。

**Python版本不兼容**
```
Requires-Python >=3.11
```
**解决方案**: 使用Python 3.10+ (推荐)

#### 2. 启动问题

**启动失败**
- 检查Python版本是否为3.10+
- 确认所有依赖已正确安装
- 检查端口8888是否被占用

#### 3. 分析问题

**分析失败**
- 检查AI模型配置是否正确
- 确认API密钥有效且有足够额度
- 检查网络连接

**数据获取失败**
- 检查网络连接
- 可能是AKShare数据源临时不可用
- 系统会自动使用备用数据源

#### 4. 登录问题

**忘记密码**
- 目前系统不支持密码重置
- 需要联系管理员或重新注册账号

**用户名已存在**
- 选择其他用户名
- 用户名只能包含字母、数字和下划线

### 日志查看

应用运行时会在控制台输出详细日志，有助于诊断问题。

### 验证安装

```bash
# 测试所有功能
python -c "
import sys
sys.path.append('.')
from app import app, init_db
init_db()
print('✅ 系统初始化成功！')
"
```

## 注意事项

1. **API密钥安全**: 请妥善保管您的AI模型API密钥
2. **网络连接**: 需要稳定的网络连接获取市场数据
3. **调用频率**: 注意AI API的调用频率限制
4. **数据准确性**: 分析结果仅供参考，投资有风险
5. **密码安全**: 首次登录后请立即修改默认密码
6. **数据源限制**: 如遇数据获取失败，系统会自动使用备用数据源

## 开发计划

- [ ] 添加更多技术指标
- [ ] 支持自定义分析策略
- [ ] 添加邮件通知功能
- [ ] 支持用户权限管理
- [ ] 添加数据可视化图表
- [ ] 支持密码重置功能
- [ ] 添加用户个人设置

## 🤝 贡献指南

我们欢迎任何形式的贡献！

### 快速开始
1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详细信息。

## 📞 支持

如有问题或建议，请通过以下方式联系：
- 📝 提交Issue
- 📧 发送邮件
- 📖 查看文档

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户！

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！