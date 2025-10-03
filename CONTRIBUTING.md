# 贡献指南 (Contributing Guide)

感谢您对ETF股票分析平台的关注！我们欢迎任何形式的贡献。

## 🤝 如何贡献

### 报告问题 (Bug Reports)
如果您发现了bug或有功能建议，请：
1. 检查[Issues](https://github.com/your-username/etf-stock-analysis-platform/issues)中是否已有相关问题
2. 创建新的Issue，详细描述问题
3. 提供复现步骤和环境信息

### 提交代码 (Code Contributions)
1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建Pull Request

### 代码规范
- 使用Python PEP 8代码风格
- 添加适当的注释和文档字符串
- 确保代码通过所有测试
- 更新相关文档

## 🛠 开发环境设置

### 1. 克隆仓库
```bash
git clone https://github.com/your-username/etf-stock-analysis-platform.git
cd etf-stock-analysis-platform
```

### 2. 创建虚拟环境
```bash
conda create -n etf_web python=3.10
conda activate etf_web
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 运行项目
```bash
python run.py
```

## 📝 提交信息规范

使用以下格式提交信息：
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

类型包括：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

## 🐛 问题模板

### Bug报告
```markdown
**描述问题**
简要描述问题

**复现步骤**
1. 进入页面 '...'
2. 点击 '...'
3. 滚动到 '...'
4. 看到错误

**预期行为**
描述您期望的行为

**截图**
如果适用，添加截图

**环境信息**
- OS: [e.g. macOS, Windows, Linux]
- Python版本: [e.g. 3.10]
- 浏览器: [e.g. Chrome, Safari]

**附加信息**
添加任何其他相关信息
```

### 功能请求
```markdown
**功能描述**
简要描述您想要的功能

**使用场景**
描述这个功能将如何被使用

**替代方案**
描述您考虑过的其他解决方案

**附加信息**
添加任何其他相关信息
```

## 📞 联系方式

如果您有任何问题，请通过以下方式联系：
- 创建Issue
- 发送邮件到 [your-email@example.com]

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

再次感谢您的贡献！🎉
