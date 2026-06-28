"""行业/板块数据采集模块

提供行业板块表现、同行对比、供应链上下文等数据的获取函数。
"""

from __future__ import annotations

import pandas as pd

# ── 板块名称映射（scanner/sectors.py 中的板块名 -> akshare板块指数名称） ──
_SECTOR_BOARD_MAP = {
    "消费": "消费",
    "科技": "科技",
    "医药": "医药",
    "金融": "金融",
    "新能源": "新能源",
    "周期": "周期",
    "工业": "工业",
    "综合": "综合",
}

# ── 供应链上下文（基于板块的行业知识） ──
_SUPPLY_CHAIN_MAP = {
    "新能源": {
        "upstream": ["有色金属(锂钴镍/稀土)", "电力设备(电池/电机)", "化工(电解液/隔膜)"],
        "downstream": ["新能源汽车整车", "储能系统", "光伏电站/电网"],
        "risks": ["原材料价格大幅波动", "政策补贴退坡", "产能过剩导致价格战", "技术路线迭代(固态电池等)"],
    },
    "科技": {
        "upstream": ["半导体/芯片设计制造", "电子元器件/PCB", "精密光学/传感器"],
        "downstream": ["消费电子(手机/PC)", "AI/云计算/数据中心", "通信设备/5G"],
        "risks": ["技术封锁/地缘政治", "芯片供应链安全", "下游需求周期性波动"],
    },
    "医药": {
        "upstream": ["化工原料/中间体", "生物技术/实验室设备", "医用包装材料"],
        "downstream": ["医院/诊所终端", "药店零售", "第三方检测/医疗美容"],
        "risks": ["集采降价政策风险", "研发失败/专利到期", "行业监管趋严"],
    },
    "消费": {
        "upstream": ["农产品/原材料", "包装/物流", "品牌营销服务"],
        "downstream": ["电商/商超零售", "餐饮/酒店", "消费者(终端)"],
        "risks": ["消费降级/需求疲软", "原材料成本上涨", "行业竞争加剧"],
    },
    "金融": {
        "upstream": ["资金(存款/同业)", "金融科技/IT服务", "监管机构"],
        "downstream": ["企业贷款/融资", "个人财富管理", "保险/投资银行"],
        "risks": ["利率下行压缩息差", "资产质量(坏账)", "监管政策变化"],
    },
    "周期": {
        "upstream": ["矿产资源/能源", "基础化工/冶金", "运输/港口"],
        "downstream": ["房地产/基建", "制造业(机械/汽车)", "出口贸易"],
        "risks": ["宏观经济下行", "产能过剩", "大宗商品价格暴跌"],
    },
    "工业": {
        "upstream": ["钢材/有色金属", "数控机床/精密加工", "工业软件/自动化"],
        "downstream": ["汽车/航空航天", "基建/市政工程", "专用设备/机械"],
        "risks": ["制造业PMI下滑", "原材料涨价", "劳动力成本上升"],
    },
    "综合": {
        "upstream": ["多元化供应链"],
        "downstream": ["多元化市场"],
        "risks": ["综合型企业风险分散"],
    },
}


def get_sector_performance(sector_name: str) -> dict:
    """获取板块指数近期表现数据

    Returns:
        dict 包含 change_1d, change_5d, change_1m, change_3m, volume,
        top_gainers, top_losers, leader_count, laggard_count
    """
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return {"error": "板块数据不可用", "sector_name": sector_name}

        # 在 akshare 板块指数中模糊匹配
        candidates = df[df["板块名称"].str.contains(sector_name, na=False)]
        if candidates.empty:
            # 尝试英文/拼音匹配
            for col in df.columns:
                candidates = df[df[col].astype(str).str.contains(sector_name, na=False)]
                if not candidates.empty:
                    break

        if candidates.empty:
            return {"error": f"未找到板块 {sector_name}", "sector_name": sector_name}

        row = candidates.iloc[0]
        # 计算上涨下跌家数
        total = float(row.get("总市值", 0) or 0)
        up = float(row.get("上涨家数", 0) or 0)
        down = float(row.get("下跌家数", 0) or 0)

        # 领涨/领跌股
        gainers, losers = [], []
        try:
            cons = ak.stock_board_industry_cons_em(row.get("板块名称", ""))
            if cons is not None and not cons.empty:
                cons = cons.sort_values("涨跌幅", ascending=False)
                for _, c in cons.head(5).iterrows():
                    gainers.append({"name": str(c.get("名称", "")), "change_pct": round(float(c.get("涨跌幅", 0)), 2)})
                for _, c in cons.tail(5).iterrows():
                    losers.append({"name": str(c.get("名称", "")), "change_pct": round(float(c.get("涨跌幅", 0)), 2)})
        except Exception:
            pass

        return {
            "sector_name": sector_name,
            "change_1d": round(float(row.get("涨跌幅", 0)), 2),
            "change_5d": 0.0,
            "change_1m": 0.0,
            "change_3m": 0.0,
            "volume": round(float(row.get("成交额", 0) or 0) / 1e8, 2),
            "top_gainers": gainers,
            "top_losers": losers,
            "leader_count": int(up),
            "laggard_count": int(down),
        }
    except Exception as e:
        return {"error": str(e), "sector_name": sector_name}


def get_industry_peers(symbol: str, max_peers: int = 30) -> list[dict]:
    """获取同行业可比公司列表"""
    try:
        from scanner.sectors import get_industry_name
        from data.market import get_realtime_quote

        ind_name = get_industry_name(symbol)
        if not ind_name:
            return []

        import akshare as ak
        # 获取同行业成分股
        boards = ak.stock_board_industry_name_em()
        if boards is None or boards.empty:
            return []

        match = boards[boards["板块名称"].str.contains(ind_name[:4], na=False)]
        if match.empty:
            return []

        board_name = match.iloc[0]["板块名称"]
        cons = ak.stock_board_industry_cons_em(board_name)
        if cons is None or cons.empty:
            return []

        peers = []
        for _, row in cons.iterrows():
            code = str(row.get("代码", ""))
            if not code:
                continue
            peers.append({
                "symbol": code,
                "name": str(row.get("名称", "")),
                "price": float(row.get("最新价", 0) or 0),
                "change_pct": float(row.get("涨跌幅", 0) or 0),
                "market_cap": float(row.get("总市值", 0) or 0) / 1e8,
                "pe": float(row.get("市盈率-动态", 0) or 0),
            })

        peers.sort(key=lambda x: x["market_cap"], reverse=True)
        return peers[:max_peers]

    except Exception as e:
        print(f"  ⚠️ 获取行业可比公司失败: {e}")
        return []


def get_industry_ranking(symbol: str, peers: list[dict]) -> dict:
    """计算股票在行业内的排名"""
    if not peers:
        return {"total_peers": 0}

    # 找到自己
    target = None
    for p in peers:
        if p["symbol"] == symbol or p["symbol"].endswith(symbol):
            target = p
            break
    if not target:
        return {"total_peers": len(peers)}

    mc = target.get("market_cap", 0)
    pe = target.get("pe", 0)

    # 市值排名
    sorted_by_mc = sorted(peers, key=lambda x: x.get("market_cap", 0), reverse=True)
    mc_rank = next((i + 1 for i, p in enumerate(sorted_by_mc) if p["symbol"] == target["symbol"]), len(peers))

    # PE排名 (从小到大)
    valid_pe = [p for p in peers if p.get("pe", 0) > 0]
    sorted_by_pe = sorted(valid_pe, key=lambda x: x.get("pe", 0))
    pe_rank = next((i + 1 for i, p in enumerate(sorted_by_pe) if p["symbol"] == target["symbol"]), None)
    pe_median = sorted_by_pe[len(sorted_by_pe) // 2].get("pe", 0) if sorted_by_pe else 0
    mc_median = sorted_by_mc[len(sorted_by_mc) // 2].get("market_cap", 0) if sorted_by_mc else 0

    return {
        "total_peers": len(peers),
        "market_cap_rank": f"{mc_rank}/{len(peers)}",
        "market_cap_percentile": round((1 - mc_rank / len(peers)) * 100, 1) if peers else 0,
        "market_cap": mc,
        "market_cap_median": mc_median,
        "pe": pe,
        "pe_rank": f"{pe_rank}/{len(valid_pe)}" if pe_rank else "N/A",
        "pe_percentile": round((1 - pe_rank / len(valid_pe)) * 100, 1) if pe_rank and valid_pe else 0,
        "pe_median": pe_median,
    }


def get_supply_chain_context(sector: str, industry_name: str = "") -> dict:
    """基于板块的供应链上下文"""
    sc = _SUPPLY_CHAIN_MAP.get(sector, _SUPPLY_CHAIN_MAP["综合"])
    return {
        "sector": sector,
        "industry_name": industry_name,
        "upstream_sectors": sc["upstream"],
        "downstream_sectors": sc["downstream"],
        "typical_risks": sc["risks"],
    }
