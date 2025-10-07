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
        "   - 例如：'股价高于20日均线，短期趋势向上；MACD金叉，多头力量增强；布林带突破上轨，市场活跃。'\n"
        "   - **避免直接引用列表中的原句，而是整合为连贯的分析性语句**。\n"
        "5. **综合评分和精炼点评**：\n"
        "   - **评分必须根据具体的技术指标表现进行差异化评分，不能给出相同的分数**。\n"
        "   - **每个投资标的的技术指标都不同，必须根据其独特的技术面表现给出不同的评分**。\n"
        "   - **评分权重和标准**：\n"
        "     * **均线指标（最重要，权重最高）**：\n"
        "       - 重点关注：金叉/死叉信号、多头/空头排列、均线位置关系\n"
        "       - 均线是技术分析的核心，应给予最高重视\n"
        "     * **MACD指标（次重要，权重较高）**：\n"
        "       - 重点关注：金叉/死叉、零轴位置、红绿柱变化\n"
        "       - MACD是重要的趋势指标，应给予较高重视\n"
        "     * **布林带指标（重要，权重中等）**：\n"
        "       - 重点关注：突破/跌破上轨下轨、中轨位置\n"
        "       - 布林带反映价格波动和支撑阻力，应给予中等重视\n"
        "     * **其他指标（辅助，权重较低）**：\n"
        "       - 趋势强度、震荡情况等作为辅助判断\n"
        "   - **最终评分范围**：\n"
        "     * 95-99分：技术面极强，多个重要指标显示强烈买入信号，无明显风险\n"
        "     * 85-94分：技术面很强，主要指标显示买入信号，风险较小\n"
        "     * 75-84分：技术面较强，部分指标显示买入信号，需注意风险\n"
        "     * 65-74分：技术面偏强，指标混合但偏多，有一定风险\n"
        "     * 55-64分：技术面中性偏强，指标混合，需要谨慎\n"
        "     * 45-54分：技术面中性，指标无明显方向\n"
        "     * 35-44分：技术面中性偏弱，指标混合但偏空\n"
        "     * 25-34分：技术面偏弱，部分指标显示卖出信号\n"
        "     * 15-24分：技术面较弱，主要指标显示卖出信号\n"
        "     * 5-14分：技术面极弱，多个指标显示强烈卖出信号\n"
        "     * 0-4分：技术面极差，数据严重缺失或指标全部显示卖出\n"
        "   - **重要：如果点评中提到'风险'、'谨慎'、'警惕'、'回调'等词汇，评分应该相应降低**\n"
        "   - **重要：必须仔细分析每个标的的具体技术指标表现，给出差异化的评分**。\n"
        "   - 撰写一句精炼的交易点评（作为comment字段内容）。\n"
        "   - **点评应是流畅的自然语言字符串，而不是嵌套的JSON或字典**。\n\n"
        "请严格以JSON格式返回，包含'score'（数字类型）和'comment'（字符串类型）两个键，例如:\n"
        '{"score": 75, "comment": "上证50ETF目前技术面表现强劲，股价站上多条均线，MACD呈金叉，但需注意量能是否持续。建议关注。"} \n'
        "确保comment字段是**纯字符串**，不包含任何嵌套JSON结构。\n"
        "**特别注意：每个投资标的的技术指标表现都不同，必须根据其具体的技术面表现给出不同的评分，不能给出相同的分数。**" # 再次强调
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
            # Perplexity AI 不使用response_format
            request_params.update({
                "max_tokens": 1000,
                "temperature": 0.7,
                "top_p": 0.9
            })
            logger.info("使用Perplexity AI格式请求（无response_format）")
        else:
            # OpenAI 使用json_object格式
            request_params.update({
                "response_format": {
                    "type": "json_object"
                }
            })
            logger.info("使用OpenAI格式请求（json_object）")
        
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
        
        # 直接使用LLM给出的分数，不进行算法调整
        if score is not None and isinstance(score, (int, float)):
            # 检查数据缺失情况
            technical_indicators = daily_trend_data.get('technical_indicators_summary', [])
            data_missing_keywords = ['数据缺失', '数据不足', '无法分析', '数据异常', '数据源暂时不可用']
            has_data_missing = any(any(keyword in indicator.lower() for keyword in data_missing_keywords) 
                                 for indicator in technical_indicators)
            
            # 如果数据缺失，返回特殊状态
            if has_data_missing:
                return None, "数据缺失，无法进行评分分析"
            
            # 限制分数范围在0-99之间
            score = max(0, min(99, score))
            score = round(score, 1)  # 保留一位小数
        
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

def _adjust_score_by_comment(score, comment):
    """
    根据点评内容智能调整评分
    如果点评中提到风险、谨慎、警惕等词汇，应该降低评分
    """
    if not comment:
        return score
    
    comment_lower = comment.lower()
    
    # 风险词汇，需要降低评分
    risk_keywords = [
        '风险', '谨慎', '警惕', '回调', '调整', '下跌', '压力', '阻力',
        '超买', '超卖', '震荡', '不确定', '观望', '注意', '关注',
        '空头', '减弱', '缩短', '死叉', '跌破', '下方', '偏弱'
    ]
    
    # 积极词汇，可以保持或略微提高评分
    positive_keywords = [
        '强势', '突破', '金叉', '多头', '上方', '增长', '增强',
        '看好', '乐观', '积极', '买入', '持有', '推荐'
    ]
    
    # 计算风险词汇数量
    risk_count = sum(1 for keyword in risk_keywords if keyword in comment_lower)
    positive_count = sum(1 for keyword in positive_keywords if keyword in comment_lower)
    
    # 根据风险词汇调整评分
    if risk_count > 0:
        # 每个风险词汇降低1-3分，最多降低20分
        risk_adjustment = min(risk_count * 2, 20)  # 最多降低20分
        score = max(score - risk_adjustment, 0)
        logger.info(f"检测到{risk_count}个风险词汇，降低评分{risk_adjustment}分")
    
    # 如果只有积极词汇且没有风险词汇，可以略微提高
    elif positive_count > 0 and risk_count == 0:
        # 最多提高2分
        positive_adjustment = min(positive_count, 2)
        score = min(score + positive_adjustment, 99)
        logger.info(f"检测到{positive_count}个积极词汇，提高评分{positive_adjustment}分")
    
    return score

def _calculate_weighted_score(base_score, technical_indicators):
    """
    基于技术指标重要性进行权重评分调整
    根据实际技术分析中指标的重要性来分配权重
    """
    if not technical_indicators:
        return base_score
    
    # 检查是否有数据缺失情况
    data_missing_keywords = ['数据缺失', '数据不足', '无法分析', '数据异常', '数据源暂时不可用']
    has_data_missing = any(any(keyword in indicator.lower() for keyword in data_missing_keywords) 
                          for indicator in technical_indicators)
    
    # 如果数据缺失，返回特殊值表示无法评分
    if has_data_missing:
        logger.warning("检测到数据缺失，无法进行评分")
        return None  # 返回None表示无法评分
    
    # 技术指标权重配置（基于实际重要性）
    indicator_weights = {
        # 均线指标权重（最重要，占40%）
        '均线': 0.4,
        'SMA': 0.4,
        'MA': 0.4,
        '金叉': 0.35,
        '死叉': 0.35,
        '多头排列': 0.4,
        '空头排列': 0.4,
        
        # MACD指标权重（次重要，占30%）
        'MACD': 0.3,
        'MACD金叉': 0.3,
        'MACD死叉': 0.3,
        '红柱': 0.25,
        '绿柱': 0.25,
        '零轴': 0.2,
        
        # 布林带指标权重（第三重要，占20%）
        '布林': 0.2,
        '布林上轨': 0.2,
        '布林下轨': 0.2,
        '布林中轨': 0.15,
        '突破': 0.25,
        '跌破': 0.25,
        
        # 其他指标权重（占10%）
        '成交量': 0.1,
        '量能': 0.1,
        '震荡': 0.05,
        '趋势': 0.1
    }
    
    # 计算权重调整
    total_weight = 0
    positive_signals = 0
    negative_signals = 0
    neutral_signals = 0
    
    for indicator in technical_indicators:
        indicator_lower = indicator.lower()
        
        # 计算该指标的权重
        indicator_weight = 0
        for key, weight in indicator_weights.items():
            if key.lower() in indicator_lower:
                indicator_weight = max(indicator_weight, weight)
        
        total_weight += indicator_weight
        
        # 判断信号类型
        if any(keyword in indicator_lower for keyword in ['金叉', '多头', '突破', '上方', '增长', '增强', '向上', '积极']):
            positive_signals += 1
        elif any(keyword in indicator_lower for keyword in ['死叉', '空头', '跌破', '下方', '缩短', '减弱', '向下', '谨慎', '超买', '超卖']):
            negative_signals += 1
        else:
            neutral_signals += 1
    
    # 基于信号类型和权重计算调整
    if total_weight == 0:
        return base_score
    
    # 信号强度计算
    signal_ratio = (positive_signals - negative_signals) / max(1, len(technical_indicators))
    
    # 权重调整（基于总权重和信号强度）
    # 限制调整幅度，确保不会超过99分
    max_adjustment = min(99 - base_score, 15)  # 最多调整15分，且不能超过99分
    weight_adjustment = total_weight * signal_ratio * 5  # 减少调整系数从10到5
    weight_adjustment = max(-max_adjustment, min(max_adjustment, weight_adjustment))  # 限制调整范围
    
    # 应用调整
    adjusted_score = base_score + weight_adjustment
    
    logger.info(f"权重评分调整: 基础分={base_score:.1f}, 权重={total_weight:.2f}, 信号比例={signal_ratio:.2f}, 调整={weight_adjustment:.1f}, 最终分={adjusted_score:.1f}")
    
    return adjusted_score

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
