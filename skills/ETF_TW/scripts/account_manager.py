#!/usr/bin/env python3
"""
Account manager for multi-broker, multi-account support.

This module handles:
- Loading account configurations
- Managing account routing
- Adapter instantiation
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
try:
    from adapters.base import BaseAdapter, get_adapter
except ImportError:
    from scripts.adapters.base import BaseAdapter, get_adapter

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from scripts.etf_core import context


class AccountManager:
    """
    Manages multiple trading accounts across different brokers.
    
    Features:
    - Load account configurations from JSON
    - Route orders to appropriate broker adapters
    - Manage account states
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize account manager.
        
        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = config_path or self._find_config()
        self.config = self._load_config()
        self.adapters: Dict[str, BaseAdapter] = {}
        self.broker_registry = self._load_broker_registry()
        
    def _find_config(self) -> str:
        """Find configuration file, prioritizing instance-specific config."""
        instance_config = context.get_instance_config()
        if instance_config.exists():
            return str(instance_config)
            
        # Fallback to common locations
        paths = [
            Path(__file__).parent.parent / 'assets' / 'config.json',
        ]
        
        for path in paths:
            if path.exists():
                return str(path)
        
        # Return default even if not exists
        return str(Path(__file__).parent.parent / 'assets' / 'config.json')
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            # Return default config if file doesn't exist
            return {
                'accounts': {
                    'default': {
                        'alias': 'default',
                        'broker_id': 'paper',
                        'account_id': 'paper_001',
                        'mode': 'paper',
                        'initial_balance': 1000000
                    }
                },
                'default_account': 'default'
            }
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_broker_registry(self) -> Dict[str, Any]:
        """Load broker registry."""
        registry_path = Path(__file__).parent.parent / 'data' / 'broker_registry.json'
        
        if not registry_path.exists():
            return {}
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_account(self, alias: Optional[str] = None) -> Dict[str, Any]:
        """
        Get account configuration by alias.
        
        Args:
            alias: Account alias (uses default if None)
            
        Returns:
            Account configuration dictionary
        """
        if alias is None:
            alias = self.config.get('default_account', 'default')
        
        accounts = self.config.get('accounts', {})
        
        if alias not in accounts:
            available = ', '.join(accounts.keys())
            raise ValueError(f"Account '{alias}' not found. Available: {available}")
        
        return accounts[alias]
    
    def get_adapter(self, alias: Optional[str] = None) -> BaseAdapter:
        """
        Get adapter for an account.
        
        Args:
            alias: Account alias (uses default if None)
            
        Returns:
            Adapter instance
        """
        # Use cached adapter if available
        cache_key = alias or 'default'
        if cache_key in self.adapters:
            return self.adapters[cache_key]
        
        # Get account config
        account = self.get_account(alias)
        broker_id = account.get('broker_id', 'paper')
        
        # Get broker info from registry
        broker_info = self.broker_registry.get('brokers', {}).get(broker_id, {})
        
        # Build adapter config
        account_credentials = account.get('credentials', {}) or {}
        broker_credentials = self.config.get('brokers', {}).get(broker_id, {}) or {}
        
        adapter_config = {
            'api_key': account_credentials.get('api_key') or account_credentials.get('key') or broker_credentials.get('api_key') or broker_info.get('api_key'),
            'secret_key': account_credentials.get('api_secret') or account_credentials.get('secret_key') or account_credentials.get('secret') or broker_credentials.get('secret_key') or broker_info.get('secret_key'),
            'mode': account.get('mode', 'paper'),
            'account_id': account.get('account_id'),
            'initial_balance': account.get('initial_balance', 1000000),
            'fee_rate': broker_info.get('fee_rate', 0.001425),
            'tax_rate': broker_info.get('tax_rate', 0.003),
            'min_fee': broker_info.get('min_fee', 20),
            'capabilities': broker_info.get('capabilities', []),
        }
        
        # Create adapter
        adapter = get_adapter(broker_id, adapter_config)
        
        # Cache it
        self.adapters[cache_key] = adapter
        
        return adapter
    
    async def authenticate_account(self, alias: Optional[str] = None) -> bool:
        """
        Authenticate an account.
        
        Args:
            alias: Account alias (uses default if None)
            
        Returns:
            True if authentication successful
        """
        adapter = self.get_adapter(alias)
        return await adapter.authenticate()
    
    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"儲存設定失敗：{e}")
            return False

    def set_default_account(self, alias: str) -> bool:
        """Set the default account alias."""
        if alias not in self.config.get('accounts', {}):
            return False
        self.config['default_account'] = alias
        return self.save_config()

    def get_config(self) -> Dict[str, Any]:
        """Get the full configuration."""
        return self.config
    
    def list_accounts(self) -> List[Dict[str, Any]]:
        """
        List all configured accounts.
        
        Returns:
            List of account information dictionaries
        """
        accounts = self.config.get('accounts', {})
        default = self.config.get('default_account', 'default')
        result = []
        
        for alias, config in accounts.items():
            result.append({
                'alias': alias,
                'broker_id': config.get('broker_id'),
                'account_id': config.get('account_id'),
                'mode': config.get('mode'),
                'is_default': alias == default,
                'description': config.get('description', '')
            })
        
        return result
    
    def list_brokers(self) -> List[Dict[str, Any]]:
        """
        List all available brokers.
        
        Returns:
            List of broker information dictionaries
        """
        brokers = self.broker_registry.get('brokers', {})
        result = []
        
        for broker_id, info in brokers.items():
            result.append({
                'broker_id': broker_id,
                'name': info.get('name'),
                'name_en': info.get('name_en'),
                'type': info.get('type'),
                'supports_paper': info.get('supports_paper', False),
                'supports_sandbox': info.get('supports_sandbox', False),
                'supports_live': info.get('supports_live', False),
            })
        
        return result


# Global account manager instance
_account_manager: Optional[AccountManager] = None


def get_account_manager(config_path: Optional[str] = None) -> AccountManager:
    """
    Get or create the global account manager.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        AccountManager instance
    """
    global _account_manager
    
    if _account_manager is None or config_path is not None:
        _account_manager = AccountManager(config_path)
    
    return _account_manager
