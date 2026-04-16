"""
Broker Factory to manage multiple broker instances
"""
from typing import Dict, Optional
from .base_broker import BaseBroker
from .sinopac_broker import SinopacBroker
from .cathay_broker import CathayBroker

class BrokerManager:
    def __init__(self):
        self.brokers: Dict[str, BaseBroker] = {}
        
    def add_broker(self, broker_name: str, broker_type: str, account_id: str, api_key: str, secret_key: str, is_simulation: bool = True):
        """Add a broker instance to the manager"""
        broker_type = broker_type.lower()
        if broker_type == "sinopac":
            self.brokers[broker_name] = SinopacBroker(account_id, api_key, secret_key, is_simulation)
        elif broker_type == "cathay":
            self.brokers[broker_name] = CathayBroker(account_id, api_key, secret_key, is_simulation)
        else:
            raise ValueError(f"Unknown broker type: {broker_type}")
            
    def get_broker(self, broker_name: str) -> Optional[BaseBroker]:
        return self.brokers.get(broker_name)
        
    def get_all_balances(self) -> Dict[str, Dict]:
        balances = {}
        for name, broker in self.brokers.items():
            balances[name] = broker.get_account_balance()
        return balances
        
    def get_all_inventories(self) -> Dict[str, list]:
        inventories = {}
        for name, broker in self.brokers.items():
            inventories[name] = broker.get_inventory()
        return inventories
