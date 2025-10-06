# llm_analyzer.py (优化 prompt_data 和 system_prompt)

import os
import json
import logging
import asyncio
from openai import OpenAI

logger = logging.getLogger(__name__)

# --- 配置 ---
def _get_api_provider():
    """检测API提供商类型"""
    api_base = os.getenv("LLM_API_BASE", "").lower()
    if "perplexity" in api_base:
        return "perplexity"
    elif "openai" in api_base or "siliconflow" in api_base:
        return "openai"
    else:
        return "openai"  # 默认为OpenAI格式

def _get_openai_client():
    """动态获取OpenAI客户端，优先使用环境变量中的配置"""
    try:
        api_base = os.getenv("LLM_API_BASE")
        api_key = os.getenv("LLM_API_KEY")
        
        if not api_base or not api_key:
            logger.warning("LLM API配置不完整，请在Web界面配置或设置环境变量")
            return None
            
        return OpenAI(
            base_url=api_base,
            api_key=api_key,
        )
    except Exception as e:
        logger.error(f"初始化OpenAI客户端失败: {e}")
        return None

# 全局客户端变量
client = None

# --- 核心函数 ---
async def get_llm_score_and_analysis(etf_data, daily_trend_data):
    """调用大模型对单支ETF进行分析和打分"""
    # 动态获取客户端
    current_client = _get_openai_client()
    if current_client is None:
        return None, "LLM服务未配置或初始化失败。请在配置页面设置AI模型参数。"
    
    # 检测API提供商
    api_provider = _get_api_provider()
    logger.info(f"检测到API提供商: {api_provider}")
        
    # --- 1. 修改 prompt_data 的结构 ---
    # 将所有必要的信息都扁平化，直接传递给LLM
    # LLM会看到 etf_data 和 daily_trend_data 组合在一起的完整信息
    combined_data = {
        "投资标的名称": etf_data.get('name'),
        "代码": etf_data.get('code'),
        "日内涨跌幅": f"{etf_data.get('change', 0):.2f}%",
        "日线级别整体趋势": daily_trend_data.get('status'), # 例如 '🟢 强势上升趋势'
        "盘中技术信号": daily_trend_data.get('intraday_signals'), # 这个daily_trend_data中没有，应该是etf_data里
        "详细技术指标分析列表": daily_trend_data.get('technical_indicators_summary', []) # 这是关键，传递详细的列表
    }
    # 修正：intraday_signals应该从etf_data获取
    if etf_data.get('analysis_points'):
        combined_data["盘中技术信号"] = etf_data.get('analysis_points')
    else:
        combined_data["盘中技术信号"] = [] # 确保始终是列表

    # --- 2. 优化 system_prompt ---
    # 明确指示LLM如何利用 '详细技术指标分析列表'，并要求输出为一段自然语言的点评字符串
    system_prompt = (
        "你是一个专业的金融数据分析师。请根据用户提供的JSON数据，进行全面、客观的投资标的分析。\n"
        "分析内容包括：\n"
        "1. **概览**：投资标的名称、代码、日内涨跌幅。\n"
        "2. **宏观趋势**：日线级别整体趋势。\n"
        "3. **即时信号**：盘中技术信号（如果有）。\n"
        "4. **详细技术面**：根据提供的'详细技术指标分析列表'，对均线、布林通道位置、MACD等进行综合分析，\n"
        "   - **务必提及列表中的每一项指标（即使是数据缺失或中性信号），并用清晰的自然语言描述其含义**。\n"
        "   - 例如：'股价高于20日均线，短期趋势向上；MACD金叉，多头力量增强；成交量较60日均量显著放大，市场活跃。'\n"
        "   - **避免直接引用列表中的原句，而是整合为连贯的分析性语句**。\n"
        "5. **综合评分和精炼点评**：\n"
        "   - 综合上述分析，给出一个0-100分的综合评分（50为中性）。\n"
        "   - 撰写一句精炼的交易点评（作为comment字段内容）。\n"
        "   - **点评应是流畅的自然语言字符串，而不是嵌套的JSON或字典**。\n\n"
        "请严格以JSON格式返回，包含'score'（数字类型）和'comment'（字符串类型）两个键，例如:\n"
        '{"score": 75, "comment": "上证50ETF目前技术面表现强劲，股价站上多条均线，MACD呈金叉，但需注意量能是否持续。建议关注。"} \n'
        "确保comment字段是**纯字符串**，不包含任何嵌套JSON结构。" # 再次强调
    )

    try:
        # 根据API提供商构建不同的请求参数
        request_params = {
            "model": os.getenv("LLM_MODEL_NAME", "sonar-pro"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(combined_data, ensure_ascii=False, indent=2)}
            ]
        }
        
        # 根据API提供商添加不同的参数
        if api_provider == "perplexity":
            # Perplexity AI 特殊处理
            request_params.update({
                "max_tokens": 1000,
                "temperature": 0.7,
                "top_p": 0.9
            })
            logger.info("使用Perplexity AI格式请求")
        else:
            # OpenAI 兼容格式
            request_params.update({
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "number", "description": "0到100分的综合评分"},
                                "comment": {"type": "string", "description": "一段流畅的、总结性的自然语言交易点评"}
                            },
                            "required": ["score", "comment"]
                        }
                    }
                }
            })
            logger.info("使用OpenAI兼容格式请求")
        
        response = await asyncio.to_thread(
            current_client.chat.completions.create,
            **request_params
        )
        
        raw_content = response.choices[0].message.content
        if not raw_content:
            logger.warning(f"LLM为空内容返回: {etf_data.get('name')}")
            return 50, "模型未提供有效分析。"

        # 根据API提供商进行不同的解析
        if api_provider == "perplexity":
            # Perplexity AI 特殊解析：从文本中提取JSON
            score, comment = _parse_perplexity_response(raw_content)
        else:
            # OpenAI 兼容格式解析
            score, comment = _parse_openai_response(raw_content)
        
        return score, comment

    except Exception as e:
        logger.error(f"调用或解析LLM响应时出错: {e}", exc_info=True)
        return 50, f"LLM分析服务异常: {e}" # 返回50分和错误信息，确保程序不崩溃

def _parse_perplexity_response(raw_content):
    """解析Perplexity AI的响应"""
    import re
    
    try:
        # 尝试直接解析JSON
        parsed_json = json.loads(raw_content)
        if isinstance(parsed_json, dict):
            score = parsed_json.get('score', 50)
            comment = parsed_json.get('comment', 'Perplexity AI分析完成')
            return float(score) if isinstance(score, (int, float)) else 50, str(comment)
    except json.JSONDecodeError:
        pass
    
    # 如果直接解析失败，尝试从文本中提取JSON
    try:
        # 查找JSON模式
        json_pattern = r'\{[^{}]*"score"[^{}]*"comment"[^{}]*\}'
        json_match = re.search(json_pattern, raw_content, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(0)
            parsed_json = json.loads(json_str)
            score = parsed_json.get('score', 50)
            comment = parsed_json.get('comment', 'Perplexity AI分析完成')
            return float(score) if isinstance(score, (int, float)) else 50, str(comment)
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # 如果都失败了，尝试提取数字评分
    try:
        # 查找评分数字
        score_pattern = r'"score":\s*(\d+(?:\.\d+)?)'
        score_match = re.search(score_pattern, raw_content)
        score = float(score_match.group(1)) if score_match else 50
        
        # 查找评论内容
        comment_pattern = r'"comment":\s*"([^"]*)"'
        comment_match = re.search(comment_pattern, raw_content)
        comment = comment_match.group(1) if comment_match else "Perplexity AI分析完成"
        
        return score, comment
    except (AttributeError, ValueError):
        pass
    
    # 最后的兜底方案
    logger.warning(f"Perplexity AI响应解析失败，使用默认值: {raw_content[:200]}...")
    return 50, "Perplexity AI分析完成，但响应格式需要优化"

def _parse_openai_response(raw_content):
    """解析OpenAI兼容格式的响应"""
    try:
        parsed_json = json.loads(raw_content)
        
        # 确保解析结果是字典
        result_dict = None
        if isinstance(parsed_json, list) and parsed_json:
            result_dict = parsed_json[0]
        elif isinstance(parsed_json, dict):
            result_dict = parsed_json

        if result_dict and isinstance(result_dict, dict):
            score = result_dict.get('score')
            comment = result_dict.get('comment')
            if not isinstance(score, (int, float)):
                score = 50
            return float(score), str(comment)
        else:
            logger.error(f"OpenAI返回格式错误，不是预期的JSON字典: {raw_content}")
            return 50, "OpenAI返回格式错误或内容不符合预期。"
    except json.JSONDecodeError as e:
        logger.error(f"OpenAI响应JSON解析失败: {e}, 内容: {raw_content}")
        return 50, "OpenAI响应解析失败"
