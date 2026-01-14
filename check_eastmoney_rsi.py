#!/usr/bin/env python3
"""
检查东方财富RSI设置
东方财富通常提供RSI6、RSI12、RSI24三个指标
"""

import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta


def get_maotai_data():
    """获取贵州茅台数据"""
    print("获取贵州茅台数据...")

    try:
        end_date = "20260113"
        start_date = "20251101"

        df = ak.stock_zh_a_hist(
            symbol="600519",
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )

        df = df.rename(
            columns={
                "日期": "date",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
            }
        )

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        return df

    except Exception as e:
        print(f"获取数据失败: {e}")
        return None


def calculate_multiple_rsi(df):
    """计算多个周期的RSI（匹配东方财富）"""
    print("\n东方财富RSI设置说明:")
    print("=" * 60)
    print("东方财富通常提供3个RSI指标:")
    print("1. RSI6 - 短期（6日周期）")
    print("2. RSI12 - 中期（12日周期）")
    print("3. RSI24 - 长期（24日周期）")
    print("=" * 60)

    df_rsi = df.copy()

    # 计算不同周期的RSI
    periods = [6, 12, 24]

    for period in periods:
        # 使用EMA计算RSI（标准公式）
        delta = df_rsi["close"].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1 / period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / period, adjust=False).mean()
        rs = gain / loss
        df_rsi[f"RSI_{period}"] = 100 - (100 / (1 + rs))

    return df_rsi


def analyze_rsi_values(df_rsi, target_date="2026-01-13"):
    """分析RSI值"""
    target = pd.to_datetime(target_date)

    if target not in df_rsi["date"].values:
        print(f"未找到{target_date}的数据")
        return

    row = df_rsi[df_rsi["date"] == target].iloc[0]

    print(f"\n贵州茅台 {target_date} RSI计算结果:")
    print(f"收盘价: {row['close']:.2f}")
    print()

    # 显示不同周期的RSI
    periods = [6, 12, 24]
    for period in periods:
        col = f"RSI_{period}"
        if col in df_rsi.columns:
            print(f"RSI{period}: {row[col]:.2f}")

    print(f"\n之前计算的RSI_14: 49.98")
    print("\n可能的问题:")
    print("1. 东方财富可能使用RSI6/12/24，而不是RSI14")
    print("2. 数据源可能不同（前复权 vs 后复权）")
    print("3. 初始值处理方式不同")


def check_eastmoney_common_settings():
    """检查东方财富常见设置"""
    print(f"\n{'=' * 60}")
    print("东方财富技术指标常见设置")
    print(f"{'=' * 60}")

    settings = {
        "RSI指标": ["RSI6", "RSI12", "RSI24"],
        "KDJ指标": ["KDJ(9,3,3)"],
        "威廉指标": ["WR%(WR1=10, WR2=6)"],
        "CCI指标": ["CCI(14)"],
        "MACD指标": ["MACD(12,26,9)"],
        "布林带": ["BOLL(20,2)"],
    }

    for indicator, params in settings.items():
        print(f"{indicator}: {', '.join(params)}")

    print(f"\n建议:")
    print("1. 在东方财富网站上查看具体使用哪个RSI周期")
    print("2. 检查是否使用默认的RSI6、RSI12、RSI24")
    print("3. 对比我们计算的RSI6、RSI12、RSI24值")


def main():
    print("=" * 60)
    print("东方财富RSI设置分析")
    print("东方财富通常提供RSI6、RSI12、RSI24")
    print("=" * 60)

    # 获取数据
    df = get_maotai_data()
    if df is None:
        return

    # 计算多个RSI
    df_rsi = calculate_multiple_rsi(df)

    # 分析RSI值
    analyze_rsi_values(df_rsi)

    # 检查常见设置
    check_eastmoney_common_settings()

    # 保存结果
    output_file = "eastmoney_rsi_analysis.csv"
    df_rsi[["date", "close", "RSI_6", "RSI_12", "RSI_24"]].tail(10).to_csv(
        output_file, index=False
    )
    print(f"\n✅ RSI分析结果已保存到: {output_file}")

    print(f"\n{'=' * 60}")
    print("下一步:")
    print("1. 在东方财富网站查看实际使用的RSI周期")
    print("2. 对比我们计算的RSI6、RSI12、RSI24值")
    print("3. 如果需要，更新项目使用相应的RSI周期")
    print("=" * 60)


if __name__ == "__main__":
    main()
