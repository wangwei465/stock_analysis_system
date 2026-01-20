"""WebSocket real-time quote and intraday data endpoint"""
import asyncio
from datetime import datetime
from typing import Dict, Set, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.data_fetcher import StockDataFetcher

router = APIRouter()

class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        # Map: stock_code -> set of websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._running = False
        self._task = None

    async def connect(self, websocket: WebSocket, code: str):
        """Connect a new client"""
        await websocket.accept()
        if code not in self.active_connections:
            self.active_connections[code] = set()
        self.active_connections[code].add(websocket)

        # Start broadcast task if not running
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._broadcast_loop())

    def disconnect(self, websocket: WebSocket, code: str):
        """Disconnect a client"""
        if code in self.active_connections:
            self.active_connections[code].discard(websocket)
            if not self.active_connections[code]:
                del self.active_connections[code]

        # Stop broadcast if no connections
        if not self.active_connections and self._running:
            self._running = False
            if self._task:
                self._task.cancel()

    async def broadcast(self, code: str, data: dict):
        """Broadcast data to all connections for a stock"""
        if code not in self.active_connections:
            return

        dead_connections = set()
        for connection in self.active_connections[code]:
            try:
                await connection.send_json(data)
            except Exception:
                dead_connections.add(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.active_connections[code].discard(conn)

    async def _broadcast_loop(self):
        """Background task to fetch and broadcast quotes"""
        while self._running:
            try:
                codes = list(self.active_connections.keys())
                for code in codes:
                    if code not in self.active_connections:
                        continue

                    try:
                        quote = await StockDataFetcher.get_realtime_quote_async(code)
                        if quote:
                            await self.broadcast(code, quote)
                    except Exception as e:
                        print(f"Error fetching quote for {code}: {e}")

                # Wait 3 seconds between updates
                await asyncio.sleep(3)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Broadcast loop error: {e}")
                await asyncio.sleep(5)


class IntradayConnectionManager:
    """Manage WebSocket connections for intraday data"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._running = False
        self._task = None
        # Cache last data point time for each stock to detect new data
        self._last_data_time: Dict[str, Optional[str]] = {}

    async def connect(self, websocket: WebSocket, code: str):
        """Connect a new client"""
        await websocket.accept()
        if code not in self.active_connections:
            self.active_connections[code] = set()
        self.active_connections[code].add(websocket)

        # Start broadcast task if not running
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._broadcast_loop())

    def disconnect(self, websocket: WebSocket, code: str):
        """Disconnect a client"""
        if code in self.active_connections:
            self.active_connections[code].discard(websocket)
            if not self.active_connections[code]:
                del self.active_connections[code]
                # Clean up cache
                if code in self._last_data_time:
                    del self._last_data_time[code]

        # Stop broadcast if no connections
        if not self.active_connections and self._running:
            self._running = False
            if self._task:
                self._task.cancel()

    async def broadcast(self, code: str, data: dict):
        """Broadcast data to all connections for a stock"""
        if code not in self.active_connections:
            return

        dead_connections = set()
        for connection in self.active_connections[code]:
            try:
                await connection.send_json(data)
            except Exception:
                dead_connections.add(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.active_connections[code].discard(conn)

    async def _get_intraday_data(self, code: str) -> tuple[List[dict], float]:
        """Get intraday data for a stock"""
        quote_task = StockDataFetcher.get_realtime_quote_async(code)
        intraday_task = StockDataFetcher.get_intraday_data_async(code)
        quote, df = await asyncio.gather(quote_task, intraday_task)

        pre_close = quote['pre_close'] if quote else 0
        if df.empty:
            return [], pre_close

        intraday_data = []
        cumulative_amount = 0
        cumulative_volume = 0

        for _, row in df.iterrows():
            # AKShare 分钟线（stock_zh_a_minute）返回的 volume 字段口径通常为“手”（1 手 = 100 股）。
            # websocket 推送端与 REST 接口保持一致：统一换算为“股”，便于前端直接展示/计算。
            volume = int(row['volume']) * 100
            cumulative_volume += volume

            # Calculate amount: price * volume
            amount = float(row['close']) * volume
            cumulative_amount += amount
            avg_price = cumulative_amount / cumulative_volume if cumulative_volume > 0 else float(row['close'])

            time_str = row['time'].strftime('%Y-%m-%d %H:%M')
            intraday_data.append({
                'time': time_str,
                'price': round(float(row['close']), 2),
                'avg_price': round(avg_price, 2),
                'volume': volume,
                'amount': round(amount, 2)
            })

        return intraday_data, pre_close

    async def _broadcast_loop(self):
        """Background task to fetch and broadcast intraday data"""
        while self._running:
            try:
                codes = list(self.active_connections.keys())
                for code in codes:
                    if code not in self.active_connections:
                        continue

                    try:
                        intraday_data, pre_close = await self._get_intraday_data(code)
                        if intraday_data:
                            last_time = intraday_data[-1]['time']
                            cached_time = self._last_data_time.get(code)

                            # Only broadcast if there's new data
                            if cached_time != last_time:
                                self._last_data_time[code] = last_time
                                await self.broadcast(code, {
                                    'type': 'update',
                                    'code': code,
                                    'pre_close': pre_close,
                                    'data': intraday_data[-1],  # Send only latest point
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                    except Exception as e:
                        print(f"Error fetching intraday data for {code}: {e}")

                # Wait 5 seconds between updates
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Intraday broadcast loop error: {e}")
                await asyncio.sleep(5)


manager = ConnectionManager()
intraday_manager = IntradayConnectionManager()


@router.websocket("/quote/{code}")
async def websocket_quote(websocket: WebSocket, code: str):
    """
    WebSocket endpoint for real-time stock quotes

    Connect to receive real-time quote updates for a specific stock.
    Updates are sent every 3 seconds during market hours.
    """
    await manager.connect(websocket, code)
    try:
        # Send initial quote
        quote = await StockDataFetcher.get_realtime_quote_async(code)
        if quote:
            await websocket.send_json(quote)

        # Keep connection alive
        while True:
            try:
                # Wait for ping/pong or client messages
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send ping to keep alive
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, code)


@router.websocket("/intraday/{code}")
async def websocket_intraday(websocket: WebSocket, code: str):
    """
    WebSocket endpoint for real-time intraday data

    Connect to receive real-time intraday (minute-level) data updates.
    - On connect: sends full intraday data for the current trading day
    - Updates: sends new data points every 5 seconds when available
    """
    print(f"[WebSocket] New intraday connection request for {code}")
    try:
        await intraday_manager.connect(websocket, code)
        print(f"[WebSocket] Connected for {code}")
    except Exception as e:
        print(f"[WebSocket] Connection failed for {code}: {e}")
        return

    try:
        # Send initial full intraday data
        print(f"[WebSocket] Fetching initial data for {code}")
        intraday_data, pre_close = await intraday_manager._get_intraday_data(code)
        print(f"[WebSocket] Got {len(intraday_data)} data points for {code}")

        stock_info = await StockDataFetcher.get_stock_info_async(code)

        await websocket.send_json({
            'type': 'init',
            'code': code,
            'name': stock_info.get('name', code) if stock_info else code,
            'pre_close': pre_close,
            'data': intraday_data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        print(f"[WebSocket] Sent initial data for {code}")

        # Update last data time cache
        if intraday_data:
            intraday_manager._last_data_time[code] = intraday_data[-1]['time']

        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break

    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected for {code}")
    except Exception as e:
        print(f"[WebSocket] Error for {code}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[WebSocket] Cleanup for {code}")
        intraday_manager.disconnect(websocket, code)
