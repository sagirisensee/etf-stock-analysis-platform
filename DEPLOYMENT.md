# 部署指南

## 🚀 本地启动

### 开发环境
```bash
# 1. 激活conda环境
conda activate etf_web

# 2. 启动项目
python run.py

# 3. 访问应用
# 浏览器打开: http://localhost:8888
```

## 🌐 服务器部署

### 方法一：直接运行（简单部署）

#### 1. 上传项目到服务器
```bash
# 将项目文件夹上传到服务器
scp -r my_etf_web/ user@192.168.1.7:/home/user/
```

#### 2. 在服务器上安装依赖
```bash
# SSH登录服务器
ssh user@192.168.1.7

# 进入项目目录
cd /home/user/my_etf_web

# 创建conda环境（如果还没有）
conda create -n etf_web python=3.10
conda activate etf_web

# 安装依赖
pip install -r requirements.txt
```

#### 3. 启动服务
```bash
# 开发环境启动
python run.py

# 或生产环境启动
python run_production.py
```

#### 4. 访问应用
- 服务器本地访问：`http://localhost:8888`
- 外部访问：`http://192.168.1.7:8888`

### 方法二：使用Gunicorn（生产环境推荐）

#### 1. 安装Gunicorn
```bash
pip install gunicorn
```

#### 2. 创建Gunicorn配置文件
```bash
# 创建配置文件
cat > gunicorn.conf.py << EOF
bind = "0.0.0.0:8888"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
EOF
```

#### 3. 启动Gunicorn
```bash
# 初始化数据库
python -c "from app import init_db; init_db()"

# 启动Gunicorn
gunicorn -c gunicorn.conf.py app:app
```

### 方法三：使用Docker（容器化部署）

#### 1. 创建Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 8888

# 启动命令
CMD ["python", "run_production.py"]
```

#### 2. 构建和运行Docker容器
```bash
# 构建镜像
docker build -t etf-analysis .

# 运行容器
docker run -d \
  --name etf-analysis-app \
  -p 8888:8888 \
  -v $(pwd)/etf_analysis.db:/app/etf_analysis.db \
  -v $(pwd)/logs:/app/logs \
  etf-analysis
```

## 🔧 环境变量配置

可以通过环境变量自定义配置：

```bash
# 设置服务器IP和端口
export SERVER_IP=0.0.0.0
export SERVER_PORT=8888

# 启动应用
python run_production.py
```

## 🔒 安全注意事项

### 1. 防火墙配置
```bash
# 开放端口（以Ubuntu为例）
sudo ufw allow 8888
```

### 2. 反向代理（推荐）
使用Nginx作为反向代理：

```nginx
server {
    listen 80;
    server_name 192.168.1.7;

    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. SSL证书（HTTPS）
```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 📊 监控和日志

### 1. 查看日志
```bash
# 查看应用日志
tail -f logs/access.log
tail -f logs/error.log

# 查看系统日志
journalctl -u your-service-name -f
```

### 2. 进程管理
```bash
# 使用systemd管理服务
sudo systemctl start etf-analysis
sudo systemctl status etf-analysis
sudo systemctl stop etf-analysis
```

## 🚨 故障排除

### 1. 端口被占用
```bash
# 查看端口占用
netstat -tulpn | grep :8888

# 杀死占用进程
sudo kill -9 <PID>
```

### 2. 权限问题
```bash
# 确保有执行权限
chmod +x run.py run_production.py

# 确保数据库文件可写
chmod 666 etf_analysis.db
```

### 3. 网络访问问题
```bash
# 检查防火墙状态
sudo ufw status

# 检查端口监听
ss -tulpn | grep :8888
```

## 📝 常用命令

```bash
# 启动服务
python run_production.py

# 后台运行
nohup python run_production.py > logs/app.log 2>&1 &

# 查看进程
ps aux | grep python

# 停止服务
pkill -f "python run_production.py"
```
