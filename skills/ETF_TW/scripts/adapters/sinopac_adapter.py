#!/usr/bin/env python3
"""
SinoPac Securities Adapter for ETF_TW.
Enhanced with:
- [OK] 漲跌停檢查
- [OK] 價格偏離警告
- [OK] 零股提醒
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List, Any, Optional, Callable

try:
    import shioaji as sj
    from shioaji.constant import Action, StockPriceType, OrderType, StockOrderLot
    SHIOAJI_AVAILABLE = True
except ImportError:
    SHIOAJI_AVAILABLE = False

try:
    from .base import BaseAdapter, Order, Position, AccountBalance
except ImportError:
    from base import BaseAdapter, Order, Position, AccountBalance
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.append(str(ROOT))
sys.path.append(str(SCRIPTS_DIR))
from orders_open_callback import handle_order_event
from sinopac_callback_normalizer import normalize_sinopac_callback

class SinopacAdapter(BaseAdapter):
    """
    SinoPac Securities (Shioaji) adapter.
    包含漲跌停檢查與完整訂單驗證
    """
    
    def __init__(self, broker_id: str, config: Dict[str, Any]):
        super().__init__(broker_id, config)
        self.api_key = config.get('api_key')
        self.secret_key = config.get('secret_key')
        self.password = config.get('password')
        self.mode = config.get('mode', 'paper')
        self.api = None
        self.stock_account = None
        self.order_callbacks: List[Callable] = []
        self.last_trade_snapshot: Dict[str, Any] = {}
        
        if SHIOAJI_AVAILABLE:
            # simulation=True if not in live mode
            self.api = sj.Shioaji(simulation=self.mode != 'live')
    
    async def authenticate(self) -> bool:
        """Authenticate with Shioaji API."""
        if not SHIOAJI_AVAILABLE:
            print("[SinoPac] Error: shioaji library not installed")
            return False
        
        try:
            print(f"[SinoPac] Logging in (Mode: {self.mode})...")
            accounts = self.api.login(
                api_key=self.api_key,
                secret_key=self.secret_key
            )
            
            if accounts:
                self.authenticated = True
                print(f"[SinoPac] Login successful. Found {len(accounts)} accounts.")
                self._debug_accounts(accounts)
                
                # 自動設定預設帳戶：優先使用 config 指定的證券帳戶，其次才是 account_id 0737121
                preferred_account_id = str(self.config.get('account_id') or '').split('-')[-1]
                stock_candidates = []
                
                for acc in accounts:
                    acc_id = str(getattr(acc, 'account_id', ''))
                    acc_type = str(getattr(acc, 'account_type', '')).lower()
                    acc_type_text = str(getattr(acc, 'type', '')).lower()
                    acc_kind = str(getattr(acc, 'kind', '')).lower()
                    
                    if acc_id == preferred_account_id or acc_id == "0737121":
                        self.stock_account = acc
                        break
                    
                    if any(token in acc_type for token in ('stock', 'securities')) or any(token in acc_type_text for token in ('stock', 'securities')) or any(token in acc_kind for token in ('stock', 'securities')):
                        stock_candidates.append(acc)
                
                if not self.stock_account and stock_candidates:
                    self.stock_account = stock_candidates[0]
                
                if not self.stock_account:
                    raise RuntimeError("找不到證券帳戶，請確認 API 權限與 account_id 設定")

                # 🔧 Activate CA if not already activated
                try:
                    ca_cert_path = ROOT / "private" / "certs" / "sinopac_ca_new.pfx"
                    if ca_cert_path.exists():
                        person_id = 'L120185111'  # Default from account
                        try:
                            self.api.activate_ca(
                                ca_path=str(ca_cert_path),
                                ca_passwd='L120185111',
                                person_id=person_id
                            )
                            print("[SinoPac] CA activated successfully")
                        except Exception as ca_err:
                            print(f"[SinoPac] CA activation warning: {ca_err}")
                except Exception as e:
                    print(f"[SinoPac] CA activation error: {e}")

                self.register_default_state_callback()
                print(f"[SinoPac] Selected stock account: {getattr(self.stock_account, 'account_id', 'unknown')}")
                return True
            else:
                print("[SinoPac] Login failed: No accounts returned")
                return False
        except Exception as e:
            print(f"[SinoPac] Authentication error: {e}")
            self.authenticated = False
            return False

    def _debug_accounts(self, accounts: Any) -> None:
        """Print account metadata for diagnosis without guessing the active account."""
        try:
            print("[SinoPac] Account list dump:")
            for idx, acc in enumerate(accounts, start=1):
                print(
                    f"  - #{idx} id={getattr(acc, 'account_id', '')} "
                    f"type={getattr(acc, 'account_type', '')} "
                    f"kind={getattr(acc, 'kind', '')} "
                    f"currency={getattr(acc, 'currency', '')}"
                )
        except Exception as e:
            print(f"[SinoPac] Account debug dump failed: {e}")
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data using Shioaji contract lookup and fallback provider."""
        if not self.authenticated:
            price = await self.market_provider.get_price(symbol)
            return {
                'symbol': symbol,
                'price': price,
                'change': 0.0,
                'change_percent': 0.0,
                'volume': 0,
                'bid': None,
                'ask': None,
                'timestamp': datetime.now()
            }
        
        try:
            clean_symbol = symbol.split('.')[0]
            contract = self.api.Contracts.Stocks[clean_symbol]
            
            # Prefer Shioaji contract reference/limits when available, but use fallback market provider for price
            fallback = await self.market_provider.get_full_data(symbol)
            price = float(fallback.get('price') or 0.0)
            
            if contract:
                return {
                    'symbol': symbol,
                    'price': price,
                    'change': fallback.get('change', 0.0),
                    'change_percent': fallback.get('change_percent', 0.0),
                    'volume': fallback.get('volume', 0),
                    'bid': fallback.get('bid'),
                    'ask': fallback.get('ask'),
                    'reference': getattr(contract, 'reference', None),
                    'limit_up': getattr(contract, 'limit_up', None),
                    'limit_down': getattr(contract, 'limit_down', None),
                    'timestamp': datetime.now()
                }
            
            return {
                'symbol': symbol,
                'price': price,
                'change': fallback.get('change', 0.0),
                'change_percent': fallback.get('change_percent', 0.0),
                'volume': fallback.get('volume', 0),
                'bid': fallback.get('bid'),
                'ask': fallback.get('ask'),
                'timestamp': datetime.now()
            }
        except Exception as e:
            print(f"[SinoPac] Market data error: {e}. Falling back to default provider.")
            price = await self.market_provider.get_price(symbol)
            return {
                'symbol': symbol,
                'price': price,
                'change': 0.0,
                'change_percent': 0.0,
                'volume': 0,
                'bid': None,
                'ask': None,
                'timestamp': datetime.now()
            }
    
    async def get_account_balance(self, account_id: str = None) -> AccountBalance:
        """Get account balance."""
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            target_account = self.stock_account
            if account_id:
                candidate = str(account_id).split('-')[-1]
                if candidate == str(getattr(self.stock_account, 'account_id', '')):
                    target_account = self.stock_account
            
            if target_account is None:
                raise RuntimeError("沒有可用的證券帳戶")
            
            # 依官方 flow，帳務查詢需要明確帶 stock account
            balance_data = self.api.account_balance(target_account)
            acc_balance = float(getattr(balance_data, 'acc_balance', 0) or 0)
            
            return AccountBalance(
                account_id=account_id or getattr(target_account, 'account_id', self.config.get('account_id', '')),
                broker_id=self.broker_id,
                buying_power=acc_balance,
                cash_available=acc_balance,
                market_value=0.0,
                total_value=acc_balance,
                unrealized_pnl=0.0
            )
        except Exception as e:
            print(f"[SinoPac] Balance query error: {e}")
            raise
    
    async def get_positions(self, account_id: str = None) -> List[Position]:
        """Get account positions."""
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            target_account = self.stock_account
            if account_id:
                candidate = str(account_id).split('-')[-1]
                if candidate == str(getattr(self.stock_account, 'account_id', '')):
                    target_account = self.stock_account
            
            if target_account is None:
                raise RuntimeError("沒有可用的證券帳戶")
            
            # 使用 Unit.Share 確保持倉數量與 ETF_TW 內部的「股」單位對齊
            from shioaji.constant import Unit
            api_positions = self.api.list_positions(target_account, unit=Unit.Share)
            positions = []
            
            for p in api_positions:
                positions.append(Position(
                    symbol=p.code,
                    quantity=p.quantity,
                    average_price=p.price,
                    current_price=p.last_price,
                    market_value=p.last_price * p.quantity,
                    unrealized_pnl=p.pnl
                ))
            
            return positions
        except Exception as e:
            print(f"[SinoPac] Positions query error: {e}")
            raise
    
    async def preview_order(self, order: Order) -> Order:
        """Preview order with Shioaji's fee structure."""
        try:
            if isinstance(order, dict):
                order = Order(
                    symbol=str(order.get('symbol') or '').upper(),
                    action=str(order.get('side') or order.get('action') or 'buy').lower(),
                    quantity=int(order.get('quantity') or 0),
                    price=order.get('price'),
                    order_type=str(order.get('order_type') or 'limit').lower(),
                    account_id=order.get('account'),
                    broker_id=order.get('broker'),
                    mode=str(order.get('mode') or self.mode).lower(),
                )
            
            market_data = await self.get_market_data(order.symbol)
            price = order.price or float(market_data.get('price') or 0.0)
            
            quantity = order.quantity
            amount = price * quantity
            
            fee = self.calculate_fee(amount)
            tax = self.calculate_tax(amount, order.action.lower() == 'sell')
            
            order.price = price
            order.fee = fee
            order.tax = tax
            order.status = 'preview'
            
            print(f"[SinoPac] Order preview: {order.action} {quantity} {order.symbol} @ {price}")
            print(f" Fee: {fee}, Tax: {tax}")
            
            return order
        except Exception as e:
            print(f"[SinoPac] Order preview error: {e}")
            raise
    
    # ✅ 新增：漲跌停檢查
    async def check_price_limits(self, symbol: str, price: float) -> Dict[str, Any]:
        """
        檢查價格是否超過漲跌停限制
        
        Returns:
            {
                'valid': bool,
                'limit_up': float,
                'limit_down': float,
                'reference': float,
                'warnings': List[str]
            }
        """
        result = {
            'valid': True,
            'limit_up': None,
            'limit_down': None,
            'reference': None,
            'warnings': []
        }
        
        try:
            clean_symbol = symbol.split('.')[0]
            contract = self.api.Contracts.Stocks[clean_symbol]
            
            if contract:
                result['limit_up'] = contract.limit_up
                result['limit_down'] = contract.limit_down
                result['reference'] = contract.reference
                
                # 檢查漲停
                if price > contract.limit_up:
                    result['valid'] = False
                    result['warnings'].append(f"價格 {price} 超過漲停價 {contract.limit_up}")
                
                # 檢查跌停
                if price < contract.limit_down:
                    result['valid'] = False
                    result['warnings'].append(f"價格 {price} 低於跌停價 {contract.limit_down}")
                
                # 檢查偏離參考價過遠
                if contract.reference:
                    deviation = abs(price - contract.reference) / contract.reference
                    if deviation > 0.10:  # 偏離超過 10%
                        result['warnings'].append(f"價格 {price} 偏離參考價 {contract.reference} 達 {deviation*100:.2f}%")
        
        except Exception as e:
            result['warnings'].append(f"無法檢查漲跌停：{e}")
        
        return result
    
    async def validate_order(self, order: Order) -> tuple[bool, List[str]]:
        """
        Validate order before submission.
        包含：基本驗證 + 交易時間檢查 + 漲跌停檢查 + 零股提醒
        """
        warnings = []
        errors = []
        
        if isinstance(order, dict):
            order = Order(
                symbol=str(order.get('symbol') or '').upper(),
                action=str(order.get('side') or order.get('action') or 'buy').lower(),
                quantity=int(order.get('quantity') or 0),
                price=order.get('price'),
                order_type=str(order.get('order_type') or 'limit').lower(),
                account_id=order.get('account'),
                broker_id=order.get('broker'),
                mode=str(order.get('mode') or self.mode).lower(),
            )
        
        # 基本驗證
        if not self.authenticated:
            return False, ['未認證']
        
        if not order.symbol:
            return False, ['需要指定標的']
        
        if order.quantity <= 0:
            return False, ['數量必須為正數']
        
        # ✅ 交易時間檢查（台股一般盤）
        now = datetime.now()
        current_time = now.time()
        is_weekday = now.weekday() < 5
        market_open = time(9, 0)
        market_close = time(13, 30)
        
        if not is_weekday:
            warnings.append('目前為非交易日（週末），正式委託可能無法成交')
        elif current_time < market_open or current_time > market_close:
            warnings.append('目前不在台股一般交易時段（09:00-13:30）內')
        
        # ✅ 漲跌停檢查
        if order.price:
            limit_check = await self.check_price_limits(order.symbol, order.price)
            
            if not limit_check['valid']:
                errors.extend(limit_check['warnings'])
            
            if limit_check['warnings']:
                warnings.extend(limit_check['warnings'][:-1] if len(limit_check['warnings']) > 1 else [])
        
        # 檢查零股
        if order.quantity % 1000 != 0:
            warnings.append('非整股交易（Odd Lot），請確認券商介面支援')
        
        if errors:
            return False, errors
        
        return True, warnings
    
    async def _submit_order_impl(self, order: Order) -> Order:
        """Submit order via Shioaji implementation."""
        if isinstance(order, dict):
            order = Order(
                symbol=str(order.get('symbol') or '').upper(),
                action=str(order.get('side') or order.get('action') or 'buy').lower(),
                quantity=int(order.get('quantity') or 0),
                price=order.get('price'),
                order_type=str(order.get('order_type') or 'limit').lower(),
                account_id=order.get('account'),
                broker_id=order.get('broker'),
                mode=str(order.get('mode') or self.mode).lower(),
            )
        
        if not self.authenticated:
            order.status = 'rejected'
            order.error = '未認證'
            return order
        
        try:
            # 1. Get Contract
            clean_symbol = order.symbol.split('.')[0]
            contract = self.api.Contracts.Stocks[clean_symbol]
            
            # 2. Map Constants
            action = Action.Buy if order.action.lower() == 'buy' else Action.Sell
            price_type = StockPriceType.LMT if order.order_type and order.order_type.lower() == 'limit' else StockPriceType.MKT
            
            # 3. Validate quantity (must be positive)
            if order.quantity <= 0:
                order.status = 'rejected'
                order.error = '數量必須 > 0'
                return order
                
            # --- 修正後的單位與市場別判定邏輯 (WR-01) ---
            # 依據台股規則：1000 股為 1 張 (Common)，1-999 股為零股 (IntradayOdd)
            if order.quantity % 1000 == 0:
                # 整股交易：單位為「張」
                lots = order.quantity // 1000
                order_lot = StockOrderLot.Common
            else:
                # 零股交易：單位為「股」
                # 注意：盤中零股單筆上限通常為 999 股
                lots = order.quantity
                order_lot = StockOrderLot.IntradayOdd
                
                # 盤中零股 (IntradayOdd) 在 Shioaji 僅支援 LMT 限價 (FUSE-03)
                if price_type != StockPriceType.LMT:
                    print("[SinoPac] IntradayOdd only supports LMT. Overriding price_type.")
                    price_type = StockPriceType.LMT
            
            sj_order = self.api.Order(
                price=order.price,
                quantity=lots,
                action=action,
                price_type=price_type,
                order_type=OrderType.ROD,
                order_lot=order_lot,  # 🔧 添加：指定是整股還是零股
                account=self.api.stock_account
            )
            
            # 4. Place Order
            print(f"[SinoPac] Placing {order.action} order for {order.symbol} (Market: {order_lot}, Qty: {lots})...")
            trade = self.api.place_order(contract, sj_order)
            
            order.status = 'submitted'
            order.order_id = str(getattr(trade.status, 'order_id', ''))
            order.created_at = datetime.now()
            
            return order
        except Exception as e:
            print(f"[SinoPac] Order submission error: {e}")
            order.status = 'rejected'
            order.error = str(e)
            return order
    
    def register_order_callback(self, callback: Callable) -> None:
        """註冊訂單事件 callback。"""
        self.order_callbacks.append(callback)

    def _default_state_callback(self, event_type: str, payload: Dict[str, Any]) -> None:
        handle_order_event(event_type, payload)

    def _callback_bridge(self, api: Any, order: Any, status: Any) -> None:
        row = normalize_sinopac_callback(api, order, status)
        if row:
            handle_order_event('status_update', row)

    def register_default_state_callback(self) -> None:
        """註冊預設 state updater callback。"""
        if self._default_state_callback not in self.order_callbacks:
            self.order_callbacks.append(self._default_state_callback)
        if self._callback_bridge not in self.order_callbacks:
            self.order_callbacks.append(self._callback_bridge)

    def _dispatch_order_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """分發訂單事件。"""
        for callback in self.order_callbacks:
            try:
                callback(event_type, payload)
            except TypeError:
                # Skip callbacks expecting the raw shioaji (api, order, status) signature.
                continue
            except Exception as e:
                print(f'[SinoPac] Callback error: {e}')

    async def list_trades(self) -> List[Any]:
        """List trades from Shioaji API with conservative wording for empty results."""
        if not self.authenticated:
            return []
        try:
            # We don't use await here because self.api.list_trades() is likely a synchronous call in shioaji
            trades = self.api.list_trades() or []
            if not trades:
                print("本次查詢沒看到任何委託，不代表委託失敗或已成交，請稍後再試或檢查網路")
            return trades
        except Exception as e:
            print(f"[SinoPac] list_trades error: {e}")
            return []

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order by matching current trades and canceling the matched trade."""
        if not self.authenticated:
            return False
        
        try:
            trades = await self.list_trades()
            for trade in trades:
                trade_order_id = str(getattr(getattr(trade, 'status', None), 'order_id', ''))
                if trade_order_id == str(order_id):
                    self.api.cancel_order(trade)
                    self._dispatch_order_event('cancel_requested', {
                        'order_id': order_id,
                        'timestamp': datetime.now().isoformat()
                    })
                    return True
            return False
        except Exception as e:
            print(f'[SinoPac] Cancel order error: {e}')
            return False
    
    async def get_order_status(self, order_id: str) -> Order:
        """Fetch updated order status from current trade list."""
        if not self.authenticated:
            return None
        
        try:
            trades = await self.list_trades()
            for trade in trades:
                status_obj = getattr(trade, 'status', None)
                trade_order_id = str(getattr(status_obj, 'order_id', ''))
                if trade_order_id == str(order_id):
                    status_text = str(getattr(status_obj, 'status', 'unknown')).lower()
                    mapped_status = 'submitted'
                    if 'filled' in status_text or 'deal' in status_text:
                        mapped_status = 'filled'
                    elif 'cancel' in status_text:
                        mapped_status = 'cancelled'
                    elif 'fail' in status_text or 'reject' in status_text:
                        mapped_status = 'rejected'
                    
                    result = Order(
                        symbol=getattr(getattr(trade, 'contract', None), 'code', ''),
                        action=str(getattr(getattr(trade, 'order', None), 'action', '')).lower(),
                        quantity=int(getattr(getattr(trade, 'order', None), 'quantity', 0)) * 1000,
                        price=float(getattr(getattr(trade, 'order', None), 'price', 0) or 0),
                        order_type='limit',
                        status=mapped_status
                    )
                    result.order_id = trade_order_id
                    self._dispatch_order_event('status_update', {
                        'order_id': trade_order_id,
                        'status': mapped_status,
                        'raw_status': status_text,
                        'timestamp': datetime.now().isoformat()
                    })
                    return result
            return None
        except Exception as e:
            print(f'[SinoPac] Get order status error: {e}')
            return None


def create_sinopac_adapter(config: Dict[str, Any]) -> SinopacAdapter:
    """建立永豐證券適配器"""
    return SinopacAdapter('sinopac', config)
