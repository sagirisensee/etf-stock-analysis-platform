from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import json
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

# 导入原有的分析模块
from core.analysis import generate_ai_driven_report, get_detailed_analysis_report_for_debug
from core.data_fetcher import (
    get_all_etf_spot_realtime, get_etf_daily_history, 
    get_all_stock_spot_realtime, get_stock_daily_history
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# 添加自定义Jinja2过滤器
@app.template_filter('from_json')
def from_json_filter(json_string):
    """将JSON字符串转换为Python对象"""
    try:
        return json.loads(json_string) if json_string else []
    except (json.JSONDecodeError, TypeError):
        return []

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库初始化
DB_PATH = 'etf_analysis.db'

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# 认证相关辅助函数
def create_user(username, password):
    """创建新用户"""
    password_hash = generate_password_hash(password)
    with get_db() as conn:
        try:
            conn.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # 用户名已存在

def verify_user(username, password):
    """验证用户登录"""
    with get_db() as conn:
        user = conn.execute(
            'SELECT id, username, password_hash FROM users WHERE username = ? AND is_active = 1',
            (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            # 更新最后登录时间
            conn.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user['id'],)
            )
            conn.commit()
            return user
        return None

def login_required(f):
    """登录装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_config(user_id, key, default=None):
    """获取用户个人配置"""
    with get_db() as conn:
        result = conn.execute(
            'SELECT config_value FROM user_configs WHERE user_id = ? AND config_key = ?', 
            (user_id, key)
        ).fetchone()
        return result['config_value'] if result else default

def set_user_config(user_id, key, value):
    """设置用户个人配置"""
    with get_db() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO user_configs (user_id, config_key, config_value, updated_at) VALUES (?, ?, ?, ?)',
            (user_id, key, value, datetime.now())
        )
        conn.commit()

def get_user_stock_pools(user_id, pool_type=None):
    """获取用户个人标的池"""
    with get_db() as conn:
        if pool_type:
            results = conn.execute(
                'SELECT * FROM stock_pools WHERE user_id = ? AND type = ? ORDER BY created_at DESC',
                (user_id, pool_type)
            ).fetchall()
        else:
            results = conn.execute(
                'SELECT * FROM stock_pools WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            ).fetchall()
        return [dict(row) for row in results]

def add_to_user_pool(user_id, name, pool_type, code):
    """添加标的到用户个人池中"""
    with get_db() as conn:
        conn.execute(
            'INSERT INTO stock_pools (user_id, name, type, code) VALUES (?, ?, ?, ?)',
            (user_id, name, pool_type, code)
        )
        conn.commit()

def remove_from_user_pool(user_id, pool_id):
    """从用户个人池中移除标的"""
    with get_db() as conn:
        conn.execute(
            'DELETE FROM stock_pools WHERE id = ? AND user_id = ?',
            (pool_id, user_id)
        )
        conn.commit()

def save_user_analysis_history(user_id, analysis_type, results):
    """保存用户个人分析历史"""
    with get_db() as conn:
        conn.execute(
            'INSERT INTO analysis_history (user_id, analysis_type, results) VALUES (?, ?, ?)',
            (user_id, analysis_type, json.dumps(results, ensure_ascii=False))
        )
        conn.commit()

def get_user_analysis_history(user_id, limit=50):
    """获取用户个人分析历史"""
    with get_db() as conn:
        results = conn.execute(
            'SELECT * FROM analysis_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        return [dict(row) for row in results]

def migrate_database():
    """迁移数据库结构"""
    with get_db() as conn:
        # 检查是否需要迁移
        try:
            # 检查user_configs表是否存在
            conn.execute('SELECT 1 FROM user_configs LIMIT 1')
            # 如果执行到这里，说明表已存在，不需要迁移
            return
        except sqlite3.OperationalError:
            # 表不存在，需要迁移
            print("开始数据库迁移...")
            
            # 备份现有数据
            try:
                # 检查并备份现有数据
                old_pools = []
                old_configs = []
                old_history = []
                
                try:
                    old_pools = conn.execute('SELECT * FROM stock_pools').fetchall()
                except sqlite3.OperationalError:
                    pass  # 表不存在
                
                try:
                    old_configs = conn.execute('SELECT * FROM config').fetchall()
                except sqlite3.OperationalError:
                    pass  # 表不存在
                
                try:
                    old_history = conn.execute('SELECT * FROM analysis_history').fetchall()
                except sqlite3.OperationalError:
                    pass  # 表不存在
                
                # 删除旧表
                conn.execute('DROP TABLE IF EXISTS stock_pools')
                conn.execute('DROP TABLE IF EXISTS analysis_history')
                
                # 重新创建表结构
                conn.execute('''
                    CREATE TABLE stock_pools (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL CHECK (type IN ('etf', 'stock')),
                        code TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE analysis_history (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        analysis_type TEXT NOT NULL,
                        results TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # 创建user_configs表
                conn.execute('''
                    CREATE TABLE user_configs (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        config_key TEXT NOT NULL,
                        config_value TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                        UNIQUE(user_id, config_key)
                    )
                ''')
                
                # 迁移数据到admin用户（如果admin用户存在）
                try:
                    admin_user = conn.execute('SELECT id FROM users WHERE username = ?', ('admin',)).fetchone()
                    if admin_user:
                        admin_id = admin_user['id']
                        
                        # 迁移标的池数据
                        for pool in old_pools:
                            conn.execute(
                                'INSERT INTO stock_pools (id, user_id, name, type, code, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                                (pool[0], admin_id, pool[1], pool[2], pool[3], pool[4])
                            )
                        
                        # 迁移分析历史数据
                        for history in old_history:
                            conn.execute(
                                'INSERT INTO analysis_history (id, user_id, analysis_type, results, created_at) VALUES (?, ?, ?, ?, ?)',
                                (history[0], admin_id, history[1], history[2], history[3])
                            )
                        
                        # 迁移配置数据到admin用户
                        for config in old_configs:
                            conn.execute(
                                'INSERT INTO user_configs (user_id, config_key, config_value) VALUES (?, ?, ?)',
                                (admin_id, config[1], config[2])
                            )
                except sqlite3.OperationalError:
                    # users表不存在，跳过数据迁移
                    pass
                
                conn.commit()
                print("✅ 数据库迁移完成")
                
            except Exception as e:
                print(f"❌ 数据库迁移失败: {e}")
                conn.rollback()
                raise

def init_db():
    """初始化数据库"""
    # 先执行数据库迁移
    migrate_database()
    
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stock_pools (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('etf', 'stock')),
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                analysis_type TEXT NOT NULL,
                results TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_configs (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                config_key TEXT NOT NULL,
                config_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, config_key)
            )
        ''')
        
        # 检查是否需要创建默认管理员用户
        admin_user = conn.execute('SELECT id FROM users WHERE username = ?', ('admin',)).fetchone()
        if not admin_user:
            # 创建默认管理员用户 (用户名: admin, 密码: admin123)
            default_password_hash = generate_password_hash('admin123')
            cursor = conn.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                ('admin', default_password_hash)
            )
            admin_id = cursor.lastrowid
            logger.info('已创建默认管理员用户: admin (密码: admin123)')
            
            # 为admin用户创建默认个人配置
            default_user_configs = [
                ('LLM_API_BASE', ''),
                ('LLM_API_KEY', ''),
                ('LLM_MODEL_NAME', 'Qwen/Qwen3-8B'),
                ('CACHE_EXPIRE_SECONDS', '60')
            ]
            
            for key, value in default_user_configs:
                conn.execute(
                    'INSERT INTO user_configs (user_id, config_key, config_value) VALUES (?, ?, ?)',
                    (admin_id, key, value)
                )
            logger.info('已为admin用户创建默认个人配置')
        else:
            # 如果admin用户已存在，检查是否有个人配置，如果没有则创建
            admin_id = admin_user['id']
            existing_config = conn.execute(
                'SELECT 1 FROM user_configs WHERE user_id = ? LIMIT 1', 
                (admin_id,)
            ).fetchone()
            
            if not existing_config:
                # 为现有admin用户创建默认个人配置
                default_user_configs = [
                    ('LLM_API_BASE', ''),
                    ('LLM_API_KEY', ''),
                    ('LLM_MODEL_NAME', 'Qwen/Qwen3-8B'),
                    ('CACHE_EXPIRE_SECONDS', '60')
                ]
                
                for key, value in default_user_configs:
                    conn.execute(
                        'INSERT INTO user_configs (user_id, config_key, config_value) VALUES (?, ?, ?)',
                        (admin_id, key, value)
                    )
                logger.info('已为现有admin用户创建默认个人配置')
        
        # 插入默认配置
        default_configs = [
            ('LLM_API_BASE', ''),
            ('LLM_API_KEY', ''),
            ('LLM_MODEL_NAME', 'Qwen/Qwen3-8B'),
            ('CACHE_EXPIRE_SECONDS', '60')
        ]
        
        for key, value in default_configs:
            conn.execute(
                'INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)',
                (key, value)
            )
        
        # 不再插入默认标的池数据，让用户自己添加
        
        conn.commit()

def get_config(key, default=None):
    """获取配置值"""
    with get_db() as conn:
        result = conn.execute('SELECT value FROM config WHERE key = ?', (key,)).fetchone()
        return result['value'] if result else default

def set_config(key, value):
    """设置配置值"""
    with get_db() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, ?)',
            (key, value, datetime.now())
        )
        conn.commit()

def get_stock_pools(pool_type=None):
    """获取标的池"""
    with get_db() as conn:
        if pool_type:
            results = conn.execute(
                'SELECT * FROM stock_pools WHERE type = ? ORDER BY name',
                (pool_type,)
            ).fetchall()
        else:
            results = conn.execute(
                'SELECT * FROM stock_pools ORDER BY type, name'
            ).fetchall()
        return [dict(row) for row in results]

def add_to_pool(name, pool_type, code):
    """添加到标的池"""
    with get_db() as conn:
        # 检查是否已存在相同代码和类型的标的
        existing_code = conn.execute(
            'SELECT name FROM stock_pools WHERE type = ? AND code = ?',
            (pool_type, code)
        ).fetchone()
        
        if existing_code:
            raise ValueError(f"该{pool_type}代码已存在：{existing_code['name']} ({code})")
        
        # 检查是否已存在相同名称和类型的标的
        existing_name = conn.execute(
            'SELECT code FROM stock_pools WHERE type = ? AND name = ?',
            (pool_type, name)
        ).fetchone()
        
        if existing_name:
            raise ValueError(f"该{pool_type}名称已存在：{name} ({existing_name['code']})")
        
        conn.execute(
            'INSERT INTO stock_pools (name, type, code) VALUES (?, ?, ?)',
            (name, pool_type, code)
        )
        conn.commit()

def remove_from_pool(pool_id):
    """从股票池移除"""
    with get_db() as conn:
        conn.execute('DELETE FROM stock_pools WHERE id = ?', (pool_id,))
        conn.commit()

def save_analysis_history(analysis_type, results):
    """保存分析历史"""
    with get_db() as conn:
        conn.execute(
            'INSERT INTO analysis_history (analysis_type, results) VALUES (?, ?)',
            (analysis_type, json.dumps(results, ensure_ascii=False))
        )
        conn.commit()

# 认证相关路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('请输入用户名和密码')
            return render_template('login.html')
        
        user = verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # 验证输入
        if not username or not password:
            flash('请输入用户名和密码')
            return render_template('register.html')
        
        if len(username) < 3 or len(username) > 20:
            flash('用户名长度必须在3-20个字符之间')
            return render_template('register.html')
        
        if not username.replace('_', '').replace('-', '').isalnum():
            flash('用户名只能包含字母、数字和下划线')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('密码长度至少需要6个字符')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致')
            return render_template('register.html')
        
        # 创建用户
        if create_user(username, password):
            flash('注册成功！请登录', 'success')
            return redirect(url_for('login'))
        else:
            flash('用户名已存在，请选择其他用户名')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """用户登出"""
    session.clear()
    flash('已成功登出', 'success')
    return redirect(url_for('login'))

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/config')
@login_required
def config_page():
    """配置页面"""
    user_id = session['user_id']
    configs = {}
    config_keys = ['LLM_API_BASE', 'LLM_API_KEY', 'LLM_MODEL_NAME', 'CACHE_EXPIRE_SECONDS']
    
    for key in config_keys:
        configs[key] = get_user_config(user_id, key, '')
    
    return render_template('config.html', configs=configs)

@app.route('/api/config')
@login_required
def get_user_config_api():
    """获取用户配置API"""
    try:
        user_id = session['user_id']
        
        # 获取用户个人配置
        configs = {}
        config_keys = ['LLM_API_BASE', 'LLM_API_KEY', 'LLM_MODEL_NAME', 'CACHE_EXPIRE_SECONDS']
        for key in config_keys:
            configs[key] = get_user_config(user_id, key, '')
        
        return jsonify({
            "success": True,
            "configs": configs
        })
        
    except Exception as e:
        logger.error(f"获取用户配置失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"获取配置失败: {str(e)}"
        }), 500

@app.route('/config', methods=['POST'])
@login_required
def update_config():
    """更新配置"""
    try:
        user_id = session['user_id']
        
        # 处理模型名称
        model_name = request.form.get('LLM_MODEL_NAME', '')
        custom_model_name = request.form.get('customModelName', '')
        
        # 如果选择了自定义模型且有自定义模型名称，使用自定义模型名称
        if model_name == 'custom' and custom_model_name.strip():
            model_name = custom_model_name.strip()
        
        # 更新用户个人配置
        config_data = {
            'LLM_API_BASE': request.form.get('LLM_API_BASE', ''),
            'LLM_API_KEY': request.form.get('LLM_API_KEY', ''),
            'LLM_MODEL_NAME': model_name,
            'CACHE_EXPIRE_SECONDS': request.form.get('CACHE_EXPIRE_SECONDS', '60')
        }
        
        for key, value in config_data.items():
            set_user_config(user_id, key, value)
            # 更新环境变量（仅当前会话）
            os.environ[key] = value
        
        flash('个人配置更新成功！', 'success')
        return redirect(url_for('config_page'))
    except Exception as e:
        flash(f'配置更新失败：{str(e)}', 'error')
        return redirect(url_for('config_page'))

@app.route('/pools')
@login_required
def pools_page():
    """标的池管理页面"""
    user_id = session['user_id']
    etf_pools = get_user_stock_pools(user_id, 'etf')
    stock_pools = get_user_stock_pools(user_id, 'stock')
    return render_template('pools.html', etf_pools=etf_pools, stock_pools=stock_pools)

@app.route('/pools/add', methods=['POST'])
@login_required
def add_pool():
    """添加股票到池中"""
    try:
        user_id = session['user_id']
        name = request.form.get('name')
        pool_type = request.form.get('type')
        code = request.form.get('code')
        
        if not all([name, pool_type, code]):
            flash('请填写完整信息', 'error')
        else:
            add_to_user_pool(user_id, name, pool_type, code)
            flash(f'成功添加 {name} 到个人{pool_type}池', 'success')
    except Exception as e:
        flash(f'添加失败：{str(e)}', 'error')
    
    return redirect(url_for('pools_page'))

@app.route('/pools/remove/<int:pool_id>', methods=['POST'])
@login_required
def remove_pool(pool_id):
    """从池中移除股票"""
    try:
        user_id = session['user_id']
        remove_from_user_pool(user_id, pool_id)
        flash('移除成功', 'success')
    except Exception as e:
        flash(f'移除失败：{str(e)}', 'error')
    
    return redirect(url_for('pools_page'))

@app.route('/analysis')
def analysis_page():
    """分析页面"""
    return render_template('analysis.html')

# 调试配置API已注释
# @app.route('/api/debug-config')
# def api_debug_config():
#     """获取调试配置信息"""
#     try:
#         # 获取当前配置
#         configs = {
#             'LLM_API_BASE': get_config('LLM_API_BASE', ''),
#             'LLM_API_KEY': get_config('LLM_API_KEY', ''),
#             'LLM_MODEL_NAME': get_config('LLM_MODEL_NAME', ''),
#             'CACHE_EXPIRE_SECONDS': get_config('CACHE_EXPIRE_SECONDS', '60')
#         }
#         
#         # 获取环境变量中的实际值
#         env_configs = {
#             'LLM_API_BASE': os.getenv('LLM_API_BASE', ''),
#             'LLM_API_KEY': os.getenv('LLM_API_KEY', ''),
#             'LLM_MODEL_NAME': os.getenv('LLM_MODEL_NAME', ''),
#             'CACHE_EXPIRE_SECONDS': os.getenv('CACHE_EXPIRE_SECONDS', '60')
#         }
#         
#         return jsonify({
#             'success': True,
#             'database_config': configs,
#             'environment_config': env_configs,
#             'real_model_name': configs['LLM_MODEL_NAME'] or env_configs['LLM_MODEL_NAME']
#         })
#     except Exception as e:
#         return jsonify({
#             'success': False,
#             'error': str(e)
#         })

@app.route('/api/analyze/<analysis_type>')
@login_required
def api_analyze(analysis_type):
    """API分析接口"""
    try:
        user_id = session['user_id']
        
        # 检查用户个人AI API配置是否完整
        llm_api_base = get_user_config(user_id, 'LLM_API_BASE')
        llm_api_key = get_user_config(user_id, 'LLM_API_KEY')
        llm_model_name = get_user_config(user_id, 'LLM_MODEL_NAME')
        
        if not llm_api_base or not llm_api_key or not llm_model_name:
            missing_configs = []
            if not llm_api_base:
                missing_configs.append("API基础URL")
            if not llm_api_key:
                missing_configs.append("API密钥")
            if not llm_model_name:
                missing_configs.append("AI模型名称")
            
            error_message = f"个人AI API配置不完整，请前往配置页面填写：{', '.join(missing_configs)}"
            return jsonify({"success": False, "error": error_message})
        
        # 更新环境变量
        for key in ['LLM_API_BASE', 'LLM_API_KEY', 'LLM_MODEL_NAME', 'CACHE_EXPIRE_SECONDS']:
            value = get_user_config(user_id, key)
            if value:
                os.environ[key] = value
        
        if analysis_type == 'etf':
            pools = get_user_stock_pools(user_id, 'etf')
            if not pools:
                return jsonify({"success": False, "error": "ETF标的池为空，请先添加ETF标的"})
            core_pool = [{'code': p['code'], 'name': p['name'], 'type': 'etf'} for p in pools]
            
            # 运行异步分析
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    generate_ai_driven_report(get_all_etf_spot_realtime, get_etf_daily_history, core_pool)
                )
            finally:
                loop.close()
                
        elif analysis_type == 'stock':
            pools = get_user_stock_pools(user_id, 'stock')
            if not pools:
                return jsonify({"success": False, "error": "个人股票标的池为空，请先添加股票标的"})
            core_pool = [{'code': p['code'], 'name': p['name'], 'type': 'stock'} for p in pools]
            
            # 运行异步分析
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    generate_ai_driven_report(get_all_stock_spot_realtime, get_stock_daily_history, core_pool)
                )
            finally:
                loop.close()
                
        elif analysis_type == 'etf_debug':
            pools = get_user_stock_pools(user_id, 'etf')
            if not pools:
                return jsonify({"success": False, "error": "个人ETF标的池为空，请先添加ETF标的"})
            core_pool = [{'code': p['code'], 'name': p['name']} for p in pools]
            
            # 调试模式调用异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                logger.info(f"开始调试分析，标的池: {core_pool}")
                results = loop.run_until_complete(
                    get_detailed_analysis_report_for_debug(get_all_etf_spot_realtime, get_etf_daily_history, core_pool)
                )
                logger.info(f"调试分析完成，结果类型: {type(results)}")
            except Exception as e:
                logger.error(f"调试分析失败: {str(e)}", exc_info=True)
                return jsonify({"success": False, "error": f"调试分析失败: {str(e)}"})
            finally:
                loop.close()
                
        elif analysis_type == 'stock_debug':
            pools = get_user_stock_pools(user_id, 'stock')
            if not pools:
                return jsonify({"success": False, "error": "个人股票标的池为空，请先添加股票标的"})
            core_pool = [{'code': p['code'], 'name': p['name']} for p in pools]
            
            # 调试模式调用异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                logger.info(f"开始调试分析，标的池: {core_pool}")
                results = loop.run_until_complete(
                    get_detailed_analysis_report_for_debug(get_all_stock_spot_realtime, get_stock_daily_history, core_pool)
                )
                logger.info(f"调试分析完成，结果类型: {type(results)}")
            except Exception as e:
                logger.error(f"调试分析失败: {str(e)}", exc_info=True)
                return jsonify({"success": False, "error": f"调试分析失败: {str(e)}"})
            finally:
                loop.close()
        else:
            return jsonify({'error': '不支持的分析类型'}), 400
        
        # 检查分析结果
        if results is None or len(results) == 0:
            return jsonify({
                'success': False,
                'error': '分析失败，无法获取数据。请检查网络连接或稍后重试。'
            })
        
        # 保存分析历史
        save_user_analysis_history(user_id, analysis_type, results)
        
        return jsonify({
            'success': True,
            'data': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"分析失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'分析失败: {str(e)}'
        }), 500

@app.route('/history')
@login_required
def history_page():
    """历史记录页面"""
    user_id = session['user_id']
    history = get_user_analysis_history(user_id, 50)
    return render_template('history.html', history=history)

@app.route('/api/history/<int:record_id>')
@login_required
def get_history_detail(record_id):
    """获取历史记录详情"""
    try:
        user_id = session['user_id']
        
        # 从数据库获取历史记录详情
        with get_db() as conn:
            result = conn.execute(
                'SELECT * FROM analysis_history WHERE id = ? AND user_id = ?',
                (record_id, user_id)
            ).fetchone()
            
            if not result:
                return jsonify({"success": False, "error": "记录不存在"}), 404
            
            # 解析结果数据
            import json
            try:
                results_data = json.loads(result['results']) if result['results'] else []
            except:
                results_data = []
            
            return jsonify({
                "success": True,
                "data": {
                    "id": result['id'],
                    "analysis_type": result['analysis_type'],
                    "created_at": result['created_at'],
                    "results": results_data,
                    "total_count": len(results_data)
                }
            })
            
    except Exception as e:
        logger.error(f"获取历史记录详情失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"获取详情失败: {str(e)}"}), 500

@app.route('/api/history/<int:record_id>', methods=['DELETE'])
@login_required
def delete_history_record(record_id):
    """删除历史记录"""
    try:
        user_id = session['user_id']
        
        with get_db() as conn:
            # 检查记录是否存在且属于当前用户
            result = conn.execute(
                'SELECT id FROM analysis_history WHERE id = ? AND user_id = ?',
                (record_id, user_id)
            ).fetchone()
            
            if not result:
                return jsonify({"success": False, "error": "记录不存在或无权限删除"}), 404
            
            # 删除记录
            conn.execute(
                'DELETE FROM analysis_history WHERE id = ? AND user_id = ?',
                (record_id, user_id)
            )
            conn.commit()
            
            return jsonify({"success": True, "message": "记录已删除"})
            
    except Exception as e:
        logger.error(f"删除历史记录失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"删除失败: {str(e)}"}), 500

@app.route('/api/history/clear', methods=['DELETE'])
@login_required
def clear_all_history():
    """清空所有历史记录"""
    try:
        user_id = session['user_id']
        
        with get_db() as conn:
            # 删除当前用户的所有历史记录
            cursor = conn.execute(
                'DELETE FROM analysis_history WHERE user_id = ?',
                (user_id,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            
            return jsonify({
                "success": True, 
                "message": f"已清空 {deleted_count} 条历史记录"
            })
            
    except Exception as e:
        logger.error(f"清空历史记录失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"清空失败: {str(e)}"}), 500

@app.route('/api/test-config', methods=['POST'])
@login_required
def save_test_config():
    """保存测试配置到临时存储"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # 保存到临时测试配置
        test_configs = {
            'LLM_API_BASE': data.get('LLM_API_BASE', ''),
            'LLM_API_KEY': data.get('LLM_API_KEY', ''),
            'LLM_MODEL_NAME': data.get('LLM_MODEL_NAME', ''),
            'CACHE_EXPIRE_SECONDS': data.get('CACHE_EXPIRE_SECONDS', '60')
        }
        
        # 使用session存储测试配置
        session['test_config'] = test_configs
        
        return jsonify({"success": True, "message": "测试配置已保存"})
    except Exception as e:
        logger.error(f"保存测试配置失败: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/clear-test-config', methods=['POST'])
@login_required
def clear_test_config():
    """清除测试配置"""
    try:
        # 清除session中的测试配置
        session.pop('test_config', None)
        return jsonify({"success": True, "message": "测试配置已清除"})
    except Exception as e:
        logger.error(f"清除测试配置失败: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/test-connection', methods=['POST'])
@login_required
def test_api_connection():
    """测试API连接"""
    try:
        user_id = session['user_id']
        
        # 优先使用测试配置，如果没有则使用数据库配置
        test_config = session.get('test_config')
        if test_config:
            api_base = test_config.get('LLM_API_BASE')
            api_key = test_config.get('LLM_API_KEY')
            model_name = test_config.get('LLM_MODEL_NAME')
            logger.info(f"使用测试配置进行连接测试: {model_name}")
        else:
            # 获取用户配置
            api_base = get_user_config(user_id, 'LLM_API_BASE')
            api_key = get_user_config(user_id, 'LLM_API_KEY')
            model_name = get_user_config(user_id, 'LLM_MODEL_NAME')
            logger.info(f"使用数据库配置进行连接测试: {model_name}")
        
        if not api_base or not api_key or not model_name:
            return jsonify({
                "success": False, 
                "error": "请先配置完整的API信息"
            }), 400
        
        # 临时设置环境变量
        os.environ['LLM_API_BASE'] = api_base
        os.environ['LLM_API_KEY'] = api_key
        os.environ['LLM_MODEL_NAME'] = model_name
        
        # 导入LLM分析器进行测试
        from core.llm_analyzer import _get_openai_client
        
        # 获取客户端
        client = _get_openai_client()
        if not client:
            return jsonify({
                "success": False,
                "error": "无法初始化API客户端"
            }), 500
        
        # 不进行预验证，直接通过API调用测试
        # 让服务商告诉我们模型是否存在
        
        # 发送测试请求
        import asyncio
        
        async def test_request():
            try:
                logger.info(f"发送API测试请求: model={model_name}, base_url={api_base}")
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model_name,
                    messages=[
                        {"role": "user", "content": "Hello, this is a test message. Please respond with 'OK'."}
                    ],
                    max_tokens=10
                )
                logger.info(f"API测试请求成功: {response.choices[0].message.content}")
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"API测试请求失败: {e}")
                # 解析API错误信息
                error_msg = str(e).lower()
                error_type = type(e).__name__
                
                # 检查各种可能的错误类型
                if 'model' in error_msg and ('not found' in error_msg or 'invalid' in error_msg or 'does not exist' in error_msg or 'unknown' in error_msg):
                    raise Exception(f"模型 '{model_name}' 不存在或无效，请检查模型名称是否正确")
                elif 'unauthorized' in error_msg or '401' in error_msg or 'authentication' in error_msg:
                    raise Exception("API密钥无效或已过期，请检查密钥是否正确")
                elif 'forbidden' in error_msg or '403' in error_msg or 'permission' in error_msg:
                    raise Exception("API密钥权限不足，请检查密钥权限或配额")
                elif 'rate limit' in error_msg or '429' in error_msg:
                    raise Exception("API调用频率超限，请稍后重试")
                elif 'quota' in error_msg or 'billing' in error_msg:
                    raise Exception("API配额不足或账单问题，请检查账户状态")
                elif 'timeout' in error_msg or 'connection' in error_msg:
                    raise Exception("网络连接超时，请检查网络连接")
                elif 'server' in error_msg or '500' in error_msg or '502' in error_msg or '503' in error_msg:
                    raise Exception("API服务暂时不可用，请稍后重试")
                else:
                    # 对于其他错误，提供更详细的错误信息
                    raise Exception(f"API调用失败: {str(e)}")
        
        # 运行测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_request())
            return jsonify({
                "success": True,
                "message": "API连接测试成功",
                "response": result[:100] if result else "无响应"
            })
        except Exception as e:
            # 如果test_request内部抛出异常，这里会捕获到
            logger.error(f"API测试请求失败: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"连接测试失败: {str(e)}"
            }), 500
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"API连接测试失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"连接测试失败: {str(e)}"
        }), 500

@app.route('/pools/export')
@login_required
def export_pools():
    """导出标的池"""
    try:
        user_id = session['user_id']
        etf_pools = get_user_stock_pools(user_id, 'etf')
        stock_pools = get_user_stock_pools(user_id, 'stock')
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'version': '1.0',
            'etf_pools': [{'name': p['name'], 'code': p['code']} for p in etf_pools],
            'stock_pools': [{'name': p['name'], 'code': p['code']} for p in stock_pools]
        }
        
        from flask import Response
        response = Response(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=stock_pools_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            }
        )
        return response
        
    except Exception as e:
        flash(f'导出失败：{str(e)}', 'error')
        return redirect(url_for('pools_page'))

@app.route('/pools/import', methods=['POST'])
@login_required
def import_pools():
    """导入标的池"""
    try:
        if 'file' not in request.files:
            flash('请选择要导入的文件', 'error')
            return redirect(url_for('pools_page'))
        
        file = request.files['file']
        if file.filename == '':
            flash('请选择要导入的文件', 'error')
            return redirect(url_for('pools_page'))
        
        if not file.filename.lower().endswith('.json'):
            flash('只支持JSON格式文件', 'error')
            return redirect(url_for('pools_page'))
        
        # 读取文件内容
        content = file.read().decode('utf-8')
        import_data = json.loads(content)
        
        # 验证数据格式
        if 'etf_pools' not in import_data or 'stock_pools' not in import_data:
            flash('文件格式不正确，缺少必要字段', 'error')
            return redirect(url_for('pools_page'))
        
        # 导入数据到用户个人池
        user_id = session['user_id']
        imported_count = 0
        skipped_count = 0
        
        for etf in import_data.get('etf_pools', []):
            if 'name' in etf and 'code' in etf:
                try:
                    add_to_user_pool(user_id, etf['name'], 'etf', etf['code'])
                    imported_count += 1
                except Exception as e:
                    logger.warning(f"导入ETF失败: {e}")
                    skipped_count += 1
        
        for stock in import_data.get('stock_pools', []):
            if 'name' in stock and 'code' in stock:
                try:
                    add_to_user_pool(user_id, stock['name'], 'stock', stock['code'])
                    imported_count += 1
                except ValueError:
                    skipped_count += 1  # 重复数据
                except Exception as e:
                    logger.warning(f"导入股票失败: {e}")
        
        if imported_count > 0 and skipped_count > 0:
            flash(f'成功导入 {imported_count} 个标的，跳过 {skipped_count} 个重复标的', 'success')
        elif imported_count > 0:
            flash(f'成功导入 {imported_count} 个标的', 'success')
        elif skipped_count > 0:
            flash(f'所有标的均已存在，跳过 {skipped_count} 个重复标的', 'warning')
        else:
            flash('没有找到有效的标的数据', 'warning')
        
    except json.JSONDecodeError:
        flash('文件格式错误，请检查JSON格式', 'error')
    except Exception as e:
        flash(f'导入失败：{str(e)}', 'error')
    
    return redirect(url_for('pools_page'))

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=8888)
