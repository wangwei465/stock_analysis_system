"""
股债利差API接口
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging

from datetime import timedelta
from app.core.cache_manager import CacheManager, CacheConfig, CacheLevel

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/data")
async def get_equity_bond_spread_data() -> List[Dict[str, Any]]:
    """
    获取股债利差数据

    Returns:
        股债利差历史数据列表
    """
    try:
        # 尝试从缓存获取
        cache_key = "all_data"
        cache_config = CacheConfig(
            ttl=timedelta(hours=6),
            level=CacheLevel.BOTH,
            namespace="equity_bond_spread"
        )

        cache_manager = CacheManager()
        cached_data = await cache_manager.get(cache_key, cache_config)

        if cached_data is not None:
            logger.info("从缓存获取股债利差数据")
            return cached_data

        # 延迟导入AKShare以提高启动速度
        import akshare as ak

        logger.info("从AKShare获取股债利差数据")
        df = ak.stock_ebs_lg()

        # 转换为JSON格式
        df['日期'] = df['日期'].astype(str)

        # 计算滚动标准差（使用250天窗口，约1年交易日）
        window = 250
        df['股债利差滚动标准差'] = df['股债利差'].rolling(window=window, min_periods=1).std()

        # 添加标准差上下界（基于均线 ± 2倍滚动标准差）
        df['股债利差标准差上界'] = df['股债利差均线'] + 2 * df['股债利差滚动标准差']
        df['股债利差标准差下界'] = df['股债利差均线'] - 2 * df['股债利差滚动标准差']

        # 删除临时列
        df = df.drop(columns=['股债利差滚动标准差'])

        data = df.to_dict('records')

        # 缓存数据（使用L1+L2双层缓存，TTL为6小时）
        await cache_manager.set(cache_key, data, cache_config)

        logger.info(f"成功获取股债利差数据，共 {len(data)} 条记录")
        return data

    except Exception as e:
        logger.error(f"获取股债利差数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取股债利差数据失败: {str(e)}")


@router.get("/latest")
async def get_latest_equity_bond_spread() -> Dict[str, Any]:
    """
    获取最新的股债利差数据

    Returns:
        最新的股债利差数据
    """
    try:
        data = await get_equity_bond_spread_data()

        if not data:
            raise HTTPException(status_code=404, detail="未找到股债利差数据")

        # 返回最后一条记录（最新数据）
        latest = data[-1]

        return latest

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最新股债利差数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取最新股债利差数据失败: {str(e)}")


@router.get("/stats")
async def get_equity_bond_spread_stats() -> Dict[str, Any]:
    """
    获取股债利差统计信息

    Returns:
        统计信息（最大值、最小值、平均值等）
    """
    try:
        data = await get_equity_bond_spread_data()

        if not data:
            raise HTTPException(status_code=404, detail="未找到股债利差数据")

        # 计算统计信息
        ebs_values = [item['股债利差'] for item in data]
        ebs_ma_values = [item['股债利差均线'] for item in data]

        stats = {
            "total_records": len(data),
            "date_range": {
                "start": data[0]['日期'],
                "end": data[-1]['日期']
            },
            "equity_bond_spread": {
                "current": data[-1]['股债利差'],
                "max": max(ebs_values),
                "min": min(ebs_values),
                "avg": sum(ebs_values) / len(ebs_values)
            },
            "equity_bond_spread_ma": {
                "current": data[-1]['股债利差均线'],
                "max": max(ebs_ma_values),
                "min": min(ebs_ma_values),
                "avg": sum(ebs_ma_values) / len(ebs_ma_values)
            },
            "hs300_index": {
                "current": data[-1]['沪深300指数']
            }
        }

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股债利差统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取股债利差统计信息失败: {str(e)}")
