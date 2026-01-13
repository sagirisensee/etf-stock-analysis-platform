#!/usr/bin/env python3
"""
恢复标的池数据的脚本
如果你的标的池数据丢失了，可以使用这个脚本手动添加回来
"""

import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), "etf_analysis.db")


def restore_pools():
    """恢复常见的ETF和股票池数据"""

    # 常见的ETF池
    etf_pools = [
        ("沪深300ETF", "etf", "159919"),
        ("创业板ETF", "etf", "159915"),
        ("人工智能ETF", "etf", "159819"),
        ("新能源ETF", "etf", "159941"),
        ("医药ETF", "etf", "159938"),
    ]

    # 常见的股票池（示例）
    stock_pools = [
        ("杭叉集团", "stock", "603298"),
        ("宁德时代", "stock", "300750"),
        ("贵州茅台", "stock", "600519"),
    ]

    with sqlite3.connect(DB_PATH) as conn:
        # 为admin用户（假设ID为1）添加池子
        user_id = 1

        print("正在恢复标的池数据...")

        for name, pool_type, code in etf_pools + stock_pools:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO stock_pools (user_id, name, type, code) VALUES (?, ?, ?, ?)",
                    (user_id, name, pool_type, code),
                )
                print(f"✓ 添加 {name} ({code}) 到 {pool_type} 池")
            except Exception as e:
                print(f"✗ 添加 {name} 失败: {e}")

        conn.commit()
        print("恢复完成！请重启应用并刷新页面查看。")


if __name__ == "__main__":
    restore_pools()
