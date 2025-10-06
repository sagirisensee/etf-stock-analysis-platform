# 安装指南

## 系统要求

- Python 3.10+ (推荐 3.10.x)
- pip 或 conda 包管理器

## 快速安装

### 方法1：使用conda (推荐)

```bash
# 创建虚拟环境
conda create -n etf_web python=3.10
conda activate etf_web

# 安装依赖
pip install -r requirements.txt

# 或者使用兼容性版本
pip install -r requirements-compatible.txt
```

### 方法2：使用venv

```bash
# 创建虚拟环境
python -m venv etf_web
source etf_web/bin/activate  # Linux/Mac
# 或
etf_web\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 依赖说明

### 核心依赖
- `numpy`: 数值计算
- `pandas`: 数据处理和分析
- `akshare`: 金融数据获取
- `cachetools`: 数据缓存
- `tenacity`: 重试机制
- `openai`: AI接口

### Web框架
- `Flask`: Web应用框架
- `Jinja2`: 模板引擎
- 其他Flask相关依赖

## 常见问题

### 1. pandas_ta安装失败
**问题**: `ERROR: Could not find a version that satisfies the requirement pandas_ta`

**解决方案**: 项目已移除pandas_ta依赖，所有技术指标都使用pandas内置功能计算。

### 2. Python版本不兼容
**问题**: `Requires-Python >=3.11` 或 `>=3.12`

**解决方案**: 
- 使用Python 3.10+ (推荐)
- 如果必须使用旧版本，使用 `requirements-compatible.txt`

### 3. 依赖冲突
**问题**: 包版本冲突

**解决方案**:
```bash
# 清理环境
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

## 验证安装

```bash
# 激活环境
conda activate etf_web  # 或 source etf_web/bin/activate

# 测试导入
python -c "
import numpy, pandas, akshare, cachetools, tenacity, flask, openai
from core.data_fetcher import get_all_etf_spot_realtime
print('✅ 所有依赖安装成功！')
"
```

## 运行应用

```bash
# 启动Web应用
python run.py

# 或生产模式
python run_production.py
```

## 注意事项

1. **不要安装pandas_ta**: 项目代码中未使用此包
2. **使用Python 3.10+**: 确保最佳兼容性
3. **网络问题**: 首次运行可能需要下载数据，请确保网络连接正常
4. **数据源限制**: 如遇数据获取失败，系统会自动使用备用数据源
