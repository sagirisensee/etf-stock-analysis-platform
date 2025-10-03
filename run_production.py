#!/usr/bin/env python3
"""
AI量化投资分析平台 - 生产环境启动脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置工作目录
os.chdir(project_root)

if __name__ == '__main__':
    try:
        from app import app, init_db
        
        print("=== AI量化投资分析平台 (生产环境) ===")
        print(f"项目目录: {project_root}")
        
        # 初始化数据库
        print("正在初始化数据库...")
        init_db()
        print("数据库初始化完成")
        
        # 获取服务器IP和端口
        server_ip = os.getenv('SERVER_IP', '0.0.0.0')
        server_port = int(os.getenv('SERVER_PORT', '8888'))
        
        print(f"启动Web服务...")
        print(f"访问地址: http://{server_ip}:{server_port}")
        print(f"外部访问: http://192.168.1.7:{server_port}")
        print("按 Ctrl+C 停止服务")
        
        app.run(
            debug=False,  # 生产环境关闭debug
            host=server_ip,
            port=server_port,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)
