from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
import sqlite3
from contextlib import contextmanager

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

def init_db():
    """初始化数据库"""
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
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('etf', 'stock')),
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY,
                analysis_type TEXT NOT NULL,
                results TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/config')
def config_page():
    """配置页面"""
    configs = {}
    config_keys = ['LLM_API_BASE', 'LLM_API_KEY', 'LLM_MODEL_NAME', 'CACHE_EXPIRE_SECONDS']
    
    for key in config_keys:
        configs[key] = get_config(key, '')
    
    return render_template('config.html', configs=configs)

@app.route('/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        # 处理模型名称
        model_name = request.form.get('LLM_MODEL_NAME', '')
        custom_model_name = request.form.get('customModelName', '')
        
        # 如果选择了自定义模型且有自定义模型名称，使用自定义模型名称
        if model_name == 'custom' and custom_model_name.strip():
            model_name = custom_model_name.strip()
        
        # 更新配置
        config_data = {
            'LLM_API_BASE': request.form.get('LLM_API_BASE', ''),
            'LLM_API_KEY': request.form.get('LLM_API_KEY', ''),
            'LLM_MODEL_NAME': model_name,
            'CACHE_EXPIRE_SECONDS': request.form.get('CACHE_EXPIRE_SECONDS', '60')
        }
        
        for key, value in config_data.items():
            set_config(key, value)
            # 更新环境变量
            os.environ[key] = value
        
        flash('配置更新成功！', 'success')
        return redirect(url_for('config_page'))
    except Exception as e:
        flash(f'配置更新失败：{str(e)}', 'error')
        return redirect(url_for('config_page'))

@app.route('/pools')
def pools_page():
    """标的池管理页面"""
    etf_pools = get_stock_pools('etf')
    stock_pools = get_stock_pools('stock')
    return render_template('pools.html', etf_pools=etf_pools, stock_pools=stock_pools)

@app.route('/pools/add', methods=['POST'])
def add_pool():
    """添加股票到池中"""
    try:
        name = request.form.get('name')
        pool_type = request.form.get('type')
        code = request.form.get('code')
        
        if not all([name, pool_type, code]):
            flash('请填写完整信息', 'error')
        else:
            add_to_pool(name, pool_type, code)
            flash(f'成功添加 {name} 到{pool_type}池', 'success')
    except Exception as e:
        flash(f'添加失败：{str(e)}', 'error')
    
    return redirect(url_for('pools_page'))

@app.route('/pools/remove/<int:pool_id>', methods=['POST'])
def remove_pool(pool_id):
    """从池中移除股票"""
    try:
        remove_from_pool(pool_id)
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
def api_analyze(analysis_type):
    """API分析接口"""
    try:
        # 检查AI API配置是否完整
        llm_api_base = get_config('LLM_API_BASE')
        llm_api_key = get_config('LLM_API_KEY')
        llm_model_name = get_config('LLM_MODEL_NAME')
        
        if not llm_api_base or not llm_api_key or not llm_model_name:
            missing_configs = []
            if not llm_api_base:
                missing_configs.append("API基础URL")
            if not llm_api_key:
                missing_configs.append("API密钥")
            if not llm_model_name:
                missing_configs.append("AI模型名称")
            
            error_message = f"AI API配置不完整，请前往系统配置页面填写：{', '.join(missing_configs)}"
            return jsonify({"success": False, "error": error_message})
        
        # 更新环境变量
        for key in ['LLM_API_BASE', 'LLM_API_KEY', 'LLM_MODEL_NAME', 'CACHE_EXPIRE_SECONDS']:
            value = get_config(key)
            if value:
                os.environ[key] = value
        
        if analysis_type == 'etf':
            pools = get_stock_pools('etf')
            if not pools:
                return jsonify({"success": False, "error": "ETF标的池为空，请先添加ETF标的"})
            core_pool = [{'code': p['code'], 'name': p['name']} for p in pools]
            
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
            pools = get_stock_pools('stock')
            if not pools:
                return jsonify({"success": False, "error": "股票标的池为空，请先添加股票标的"})
            core_pool = [{'code': p['code'], 'name': p['name']} for p in pools]
            
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
            pools = get_stock_pools('etf')
            if not pools:
                return jsonify({"success": False, "error": "ETF标的池为空，请先添加ETF标的"})
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
            pools = get_stock_pools('stock')
            if not pools:
                return jsonify({"success": False, "error": "股票标的池为空，请先添加股票标的"})
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
        save_analysis_history(analysis_type, results)
        
        return jsonify({
            'success': True,
            'data': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"分析失败: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def history_page():
    """历史记录页面"""
    with get_db() as conn:
        results = conn.execute(
            'SELECT * FROM analysis_history ORDER BY created_at DESC LIMIT 50'
        ).fetchall()
        history = [dict(row) for row in results]
    
    return render_template('history.html', history=history)

@app.route('/pools/export')
def export_pools():
    """导出标的池"""
    try:
        etf_pools = get_stock_pools('etf')
        stock_pools = get_stock_pools('stock')
        
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
        
        # 导入数据
        imported_count = 0
        skipped_count = 0
        
        for etf in import_data.get('etf_pools', []):
            if 'name' in etf and 'code' in etf:
                try:
                    add_to_pool(etf['name'], 'etf', etf['code'])
                    imported_count += 1
                except ValueError:
                    skipped_count += 1  # 重复数据
                except Exception as e:
                    logger.warning(f"导入ETF失败: {e}")
        
        for stock in import_data.get('stock_pools', []):
            if 'name' in stock and 'code' in stock:
                try:
                    add_to_pool(stock['name'], 'stock', stock['code'])
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
    app.run(debug=True, host='0.0.0.0', port=8888)
