"""
巴菲特指标API接口
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging

from datetime import timedelta
from app.core.cache_manager import CacheManager, CacheConfig, CacheLevel

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/data")
async def get_buffett_index_data() -> List[Dict[str, Any]]:
    """
    获取巴菲特指标数据

    Returns:
        巴菲特指标历史数据列表
    """
    try:
        # 尝试从缓存获取
        cache_key = "all_data"
        cache_config = CacheConfig(
            ttl=timedelta(hours=6),
            level=CacheLevel.BOTH,
            namespace="buffett_index"
        )

        cache_manager = CacheManager()
        cached_data = await cache_manager.get(cache_key, cache_config)

        if cached_data is not None:
            logger.info("从缓存获取巴菲特指标数据")
            return cached_data

        # 延迟导入AKShare以提高启动速度
        import akshare as ak

        logger.info("从AKShare获取巴菲特指标数据")
        df = ak.stock_buffett_index_lg()

        # 转换为JSON格式
        df['日期'] = df['日期'].astype(str)

        # 去除重复日期，保留最后一条
        df = df.drop_duplicates(subset=['日期'], keep='last')

        # 计算总市值/GDP比率
        df['总市值GDP比'] = df['总市值'] / df['GDP']

        data = df.to_dict('records')

        # 缓存数据
        await cache_manager.set(cache_key, data, cache_config)

        logger.info(f"成功获取巴菲特指标数据，共 {len(data)} 条记录")
        return data

    except Exception as e:
        logger.error(f"获取巴菲特指标数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取巴菲特指标数据失败: {str(e)}")


@router.get("/latest")
async def get_latest_buffett_index() -> Dict[str, Any]:
    """
    获取最新的巴菲特指标数据

    Returns:
        最新的巴菲特指标数据
    """
    try:
        data = await get_buffett_index_data()

        if not data:
            raise HTTPException(status_code=404, detail="未找到巴菲特指标数据")

        return data[-1]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最新巴菲特指标数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取最新巴菲特指标数据失败: {str(e)}")


@router.get("/stats")
async def get_buffett_index_stats() -> Dict[str, Any]:
    """
    获取巴菲特指标统计信息

    Returns:
        统计信息
    """
    try:
        data = await get_buffett_index_data()

        if not data:
            raise HTTPException(status_code=404, detail="未找到巴菲特指标数据")

        # 计算统计信息
        ratio_values = [item['总市值GDP比'] for item in data]
        percentile_10y = [item['近十年分位数'] for item in data if item['近十年分位数'] is not None]
        percentile_all = [item['总历史分位数'] for item in data if item['总历史分位数'] is not None]

        latest = data[-1]

        stats = {
            "total_records": len(data),
            "date_range": {
                "start": data[0]['日期'],
                "end": latest['日期']
            },
            "buffett_ratio": {
                "current": latest['总市值GDP比'],
                "max": max(ratio_values),
                "min": min(ratio_values),
                "avg": sum(ratio_values) / len(ratio_values)
            },
            "percentile_10y": {
                "current": latest['近十年分位数']
            },
            "percentile_all": {
                "current": latest['总历史分位数']
            },
            "market_cap": {
                "current": latest['总市值']
            },
            "gdp": {
                "current": latest['GDP']
            },
            "close_price": {
                "current": latest['收盘价']
            }
        }

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取巴菲特指标统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取巴菲特指标统计信息失败: {str(e)}")
