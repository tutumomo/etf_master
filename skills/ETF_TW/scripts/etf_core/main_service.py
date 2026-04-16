"""
ETF_TW Pro - 主服務模組
整合報價、情報、模擬盤功能與真實券商 API，提供統一入口
"""
from db.database import init_db
from utils.quote import get_stock_info, calculate_technical_indicators, get_price_change
from utils.news_crawler import get_daily_news_summary
from simulator import get_simulator_status, buy_etf, sell_etf, reset_simulator
from brokers import BrokerManager
from typing import Dict, List, Optional
from datetime import datetime

class ETF_TW_Pro:
    """ETF_TW Pro 主服務"""
    
    def __init__(self, use_real_broker: bool = False, active_broker_name: str = "simulator"):
        """
        初始化服務
        :param use_real_broker: 是否使用真實券商 API (False 則使用本地 SQLite 模擬盤)
        :param active_broker_name: 如果使用真實券商，指定要使用的券商名稱
        """
        init_db()
        self.use_real_broker = use_real_broker
        self.active_broker_name = active_broker_name
        self.broker_manager = BrokerManager()
        
        # 預先註冊未來可能使用的券商 (Placeholder 狀態)
        self.broker_manager.add_broker(
            broker_name="sinopac_tomo", 
            broker_type="sinopac", 
            account_id="A123456789", 
            api_key="placeholder_key", 
            secret_key="placeholder_secret",
            is_simulation=True # 測試階段預設為模擬
        )
        self.broker_manager.add_broker(
            broker_name="cathay_tomo", 
            broker_type="cathay", 
            account_id="B987654321", 
            api_key="placeholder_key", 
            secret_key="placeholder_secret",
            is_simulation=True
        )
        
        mode_str = f"真實券商 ({self.active_broker_name})" if self.use_real_broker else "本地模擬盤"
        print(f"✅ ETF_TW Pro 服務已啟動，目前模式：{mode_str}")
    
    def switch_broker_mode(self, use_real: bool, broker_name: str = "sinopac_tomo"):
        """切換交易模式 (模擬盤 vs 真實券商)"""
        self.use_real_broker = use_real
        if use_real:
            self.active_broker_name = broker_name
        else:
            self.active_broker_name = "simulator"
        return f"已切換至: {'真實券商 ' + self.active_broker_name if use_real else '本地模擬盤'}"
    
    def get_market_summary(self) -> Dict:
        """
        取得市場摘要
        """
        main_etfs = ['0050.TW', '006208.TW', '00881.TW']
        etf_data = []
        for etf in main_etfs:
            info = get_stock_info(etf)
            if info:
                tech = calculate_technical_indicators(etf)
                change = get_price_change(etf, '1d')
                
                etf_data.append({
                    'symbol': etf,
                    'name': info['name'],
                    'price': info['price'],
                    'change': change.get('change', 0),
                    'change_percent': change.get('change_percent', 0),
                    'volume': info['volume'],
                    'rsi': tech.get('rsi'),
                    'ma20': tech.get('ma20'),
                    'signal': self._generate_signal(info, tech)
                })
        
        news = get_daily_news_summary()
        return {
            'timestamp': datetime.now().isoformat(),
            'etf_summary': etf_data,
            'news_summary': news[:5],
            'market_status': '盤中' if self._is_trading_hours() else '收盤'
        }
    
    def _generate_signal(self, info: Dict, tech: Dict) -> str:
        """生成買賣信號"""
        signals = []
        rsi = tech.get('rsi')
        if rsi:
            if rsi < 30:
                signals.append('RSI 超賣')
            elif rsi > 70:
                signals.append('RSI 超買')
        
        price = info.get('price', 0)
        ma20 = tech.get('ma20')
        if ma20 and price:
            if price > ma20:
                signals.append('站上 MA20')
            else:
                signals.append('跌破 MA20')
        
        return ', '.join(signals) if signals else '中性'
    
    def _is_trading_hours(self) -> bool:
        """檢查是否為交易時間"""
        now = datetime.now()
        return 9 <= now.hour < 14 and (now.hour != 13 or now.minute <= 30)
    
    def get_portfolio_report(self) -> Dict:
        """取得投資組合報告"""
        if self.use_real_broker:
            broker = self.broker_manager.get_broker(self.active_broker_name)
            if broker:
                # 這裡目前是串接真實券商的 placeholder
                balance = broker.get_account_balance()
                inventory = broker.get_inventory()
                return {
                    'timestamp': datetime.now().isoformat(),
                    'mode': f'Real Broker ({self.active_broker_name})',
                    'cash': balance.get('cash', 0),
                    'holdings': inventory
                }
            return {'error': 'Broker not found'}
        else:
            status = get_simulator_status()
            return {
                'timestamp': datetime.now().isoformat(),
                'mode': 'Simulator',
                'cash': status['cash'],
                'holdings_value': status['holdings_value'],
                'total_assets': status['total_assets'],
                'profit_loss': status['total_profit_loss'],
                'profit_loss_percent': status['total_profit_loss_percent'],
                'holdings': status['holding_details']
            }
    
    def execute_buy(self, symbol: str, quantity: int, price: Optional[float] = None) -> Dict:
        """執行買進"""
        if self.use_real_broker:
            broker = self.broker_manager.get_broker(self.active_broker_name)
            if broker:
                success, msg, data = broker.place_order(symbol, 'BUY', quantity, price)
                return {'success': success, 'message': msg, 'data': data, 'timestamp': datetime.now().isoformat()}
            return {'success': False, 'message': 'Broker not found'}
        else:
            success, msg, data = buy_etf(symbol, quantity, price)
            return {'success': success, 'message': msg, 'data': data, 'timestamp': datetime.now().isoformat()}
    
    def execute_sell(self, symbol: str, quantity: int, price: Optional[float] = None) -> Dict:
        """執行賣出"""
        if self.use_real_broker:
            broker = self.broker_manager.get_broker(self.active_broker_name)
            if broker:
                success, msg, data = broker.place_order(symbol, 'SELL', quantity, price)
                return {'success': success, 'message': msg, 'data': data, 'timestamp': datetime.now().isoformat()}
            return {'success': False, 'message': 'Broker not found'}
        else:
            success, msg, data = sell_etf(symbol, quantity, price)
            return {'success': success, 'message': msg, 'data': data, 'timestamp': datetime.now().isoformat()}
    
    def reset(self) -> Dict:
        """重置模擬盤"""
        if self.use_real_broker:
            return {'success': False, 'message': '真實券商模式下無法重置', 'timestamp': datetime.now().isoformat()}
        success, msg = reset_simulator()
        return {'success': success, 'message': msg, 'timestamp': datetime.now().isoformat()}
    
    def get_etf_detail(self, symbol: str) -> Dict:
        """取得 ETF 詳細資訊"""
        info = get_stock_info(symbol)
        tech = calculate_technical_indicators(symbol)
        change_1d = get_price_change(symbol, '1d')
        change_1w = get_price_change(symbol, '5d')
        change_1m = get_price_change(symbol, '1mo')
        
        return {
            'symbol': symbol,
            'info': info,
            'technical': tech,
            'changes': {
                '1d': change_1d,
                '1w': change_1w,
                '1m': change_1m
            },
            'signal': self._generate_signal(info or {}, tech or {})
        }

if __name__ == "__main__":
    # 測試主服務 (模擬盤)
    print("🚀 測試 ETF_TW Pro 主服務 (Simulator Mode)")
    service = ETF_TW_Pro(use_real_broker=False)
    print(service.get_portfolio_report())
    
    # 測試主服務 (真實券商 Placeholder)
    print("\n🚀 測試 ETF_TW Pro 主服務 (Real Broker Mode)")
    service.switch_broker_mode(use_real=True, broker_name="sinopac_tomo")
    print(service.execute_buy('0050.TW', 1000))
