"""
Simple Market Handler - Adapter that maintains the same external interface
but uses the elegant SessionManager underneath.

This provides backward compatibility while dramatically simplifying the logic.
"""

from typing import Dict, List, Optional, Tuple
from .session_manager import SessionManager
from .data_models import TradingParameters, TraderRole
from .trader_manager import TraderManager
from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)


class SimpleMarketHandler:
    """
    Elegant adapter that provides the same interface as the old MarketHandler
    but uses SessionManager underneath for simplicity.

    External APIs remain unchanged - this is a drop-in replacement!
    """

    def __init__(self):
        self.session_manager = SessionManager()
    
    # Main external interface methods (keep same signatures for compatibility)
    
    async def validate_and_assign_role(self, gmail_username: str, params: TradingParameters) -> Tuple[str, str, TraderRole, int]:
        """
        Main entry point - replaces complex market assignment with simple session joining.
        
        Returns: (session_id, trader_id, role, goal)
        """
        return await self.session_manager.join_session(gmail_username, params)
    
    def get_trader_manager_by_trader_id(self, trader_id: str) -> Optional[TraderManager]:
        """Get trader manager using only trader ID - no session/market ID needed."""
        # Extract username from trader_id
        if not trader_id.startswith("HUMAN_"):
            return None
        
        username = trader_id[6:]  # Remove "HUMAN_" prefix
        return self.session_manager.get_trader_manager(username)
    
    def get_trader_manager(self, trader_id: str) -> Optional[TraderManager]:
        """Get trader manager for trader - now much simpler."""
        return self.get_trader_manager_by_trader_id(trader_id)
    
    def get_session_status_by_trader_id(self, trader_id: str) -> Dict:
        """Get session status using only trader ID."""
        if not trader_id.startswith("HUMAN_"):
            return {"status": "not_found"}
        
        username = trader_id[6:]  # Remove "HUMAN_" prefix
        return self.session_manager.get_session_status(username)
    
    async def mark_trader_ready_by_trader_id(self, trader_id: str) -> bool:
        """Mark trader as ready using only trader ID."""
        if not trader_id.startswith("HUMAN_"):
            return False
        
        username = trader_id[6:]  # Remove "HUMAN_" prefix
        
        try:
            can_start, status_info = await self.session_manager.mark_user_ready(username)
            
            # If ready to start, convert session to market
            if can_start:
                await self.session_manager.start_trading_session(username)
            
            return can_start
        except Exception as e:
            logger.error(f"Error marking trader ready: {e}")
            return False
    
    async def mark_trader_ready(self, trader_id: str, market_id: str) -> bool:
        """Mark trader as ready to start trading."""
        # Ignore market_id parameter - use trader-based lookup
        return await self.mark_trader_ready_by_trader_id(trader_id)
    
    async def cleanup_finished_markets(self) -> None:
        """Clean up finished markets."""
        await self.session_manager.cleanup_finished_markets()
    
    async def reset_state(self):
        """Reset all state."""
        await self.session_manager.reset_all()
        return True
    
    # Properties for backward compatibility
    
    @property
    def trader_to_market_lookup(self) -> Dict[str, str]:
        """Provide trader->market lookup for backward compatibility."""
        lookup = {}
        
        # Add active markets
        for username, session_id in self.session_manager.user_sessions.items():
            trader_id = f"HUMAN_{username}"
            lookup[trader_id] = session_id
        
        return lookup
    
    @property
    def trader_managers(self) -> Dict[str, TraderManager]:
        """Provide access to active trader managers."""
        return self.session_manager.active_markets.copy()
    
    @property
    def active_users(self) -> Dict[str, set]:
        """Provide active users for backward compatibility."""
        users = {}
        
        # Add session pool users
        for session_id, waiting_users in self.session_manager.session_pools.items():
            users[session_id] = {user.username for user in waiting_users}
        
        # Add active market users
        for market_id, trader_manager in self.session_manager.active_markets.items():
            users[market_id] = {trader.gmail_username for trader in trader_manager.human_traders}
        
        return users
    
    @property
    def user_historical_markets(self) -> Dict[str, set]:
        """Provide historical markets for backward compatibility."""
        return self.session_manager.user_historical_markets
    
    @property
    def market_ready_traders(self) -> Dict[str, set]:
        """Provide ready traders info for backward compatibility."""
        ready_traders = {}
        
        # For session pools, check ready status
        for session_id, waiting_users in self.session_manager.session_pools.items():
            ready_traders[session_id] = {
                f"HUMAN_{user.username}" 
                for user in waiting_users 
                if self.session_manager.user_ready_status.get(user.username, False)
            }
        
        # For active markets, all traders are considered ready
        for market_id, trader_manager in self.session_manager.active_markets.items():
            ready_traders[market_id] = {trader.id for trader in trader_manager.human_traders}
        
        return ready_traders
    
    # Utility methods for backward compatibility
    
    def add_user_to_market(self, gmail_username: str, market_id: str):
        """Backward compatibility - users are already added through session joining."""
        pass  # No-op, handled by session manager
    
    def remove_user_from_market(self, gmail_username: str, market_id: str):
        """Remove user from market/session."""
        # This is handled by session cleanup, but we can trigger it manually
        # Implementation would depend on specific cleanup needs
        pass
    
    async def can_join_market(self, gmail_username: str, params: TradingParameters) -> bool:
        """Check if user can join - delegate to session manager."""
        return await self.session_manager._can_user_join(gmail_username, params)
    
    def record_market_for_user(self, username: str, market_id: str):
        """Record market in historical data."""
        if username not in self.session_manager.user_historical_markets:
            self.session_manager.user_historical_markets[username] = set()
        self.session_manager.user_historical_markets[username].add(market_id)
    
    def get_historical_markets_count(self, username: str) -> int:
        """Get count of historical markets for user."""
        return len(self.session_manager.user_historical_markets.get(username, set()))
    
    # New methods that expose the simplified interface
    
    def get_session_status(self, username: str) -> Dict:
        """Get current session status for a user."""
        return self.session_manager.get_session_status(username)
    
    def list_all_sessions(self) -> list:
        """List all sessions and markets for monitoring."""
        return self.session_manager.list_all_sessions()
    
    async def force_start_session(self, username: str) -> Tuple[str, TraderManager]:
        """Force start a session (for admin use)."""
        return await self.session_manager.start_trading_session(username)
    
    async def remove_user_from_session(self, username: str):
        """Remove user from any existing session (e.g., on login/refresh)."""
        await self.session_manager.remove_user_from_session(username) 