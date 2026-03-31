"""
Elegant Session Manager - Replaces complex market assignment with simple session pools.

This dramatically simplifies the architecture by:
1. Users join lightweight session pools (not heavy markets)
2. Markets only created when actually needed (on trading start)
3. Zero resource waste from zombie markets
4. Clear separation between waiting and active states
"""

import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .data_models import TradingParameters, TraderRole
from .trader_manager import TraderManager
from .treatment_manager import treatment_manager
from .parameter_logger import ParameterLogger
from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)

# Shared parameter logger instance
parameter_logger = ParameterLogger()


@dataclass
class RoleSlot:
    """A role slot in a session - SIMPLER approach."""
    goal: int
    role: TraderRole
    assigned_to: Optional[str] = None  # username who got this slot
    joined_at: Optional[datetime] = None
    
    @property
    def is_available(self) -> bool:
        return self.assigned_to is None


@dataclass
class WaitingUser:
    """Lightweight user waiting to join a market (kept for compatibility)."""
    username: str
    role: TraderRole
    goal: int
    joined_at: datetime
    session_id: str
    params: TradingParameters

    def to_trader_id(self) -> str:
        return f"HUMAN_{self.username}"


class SessionStatus(Enum):
    WAITING = "waiting"      # User in pool, waiting for others
    READY = "ready"          # Enough users, can start trading
    ACTIVE = "active"        # Market created and trading
    FINISHED = "finished"    # Market completed


class SessionManager:
    """
    Elegant session management with lazy market creation.
    
    Philosophy:
    - Fast user onboarding (lightweight sessions)
    - Markets created only when needed
    - Simple state management
    - Clear user experience
    
    Cohort System:
    - market_sizes defines cohort sizes (e.g., [10, 8] for 18 people)
    - Users are assigned to cohorts on first join
    - Cohort members always play together across all markets
    - Goals are sliced from predefined_goals based on cohort size
    """
    
    def __init__(self):
        # SIMPLER state management with RoleSlot
        self.session_slots: Dict[str, List[RoleSlot]] = {}     # session_id -> list of RoleSlot
        self.session_params: Dict[str, TradingParameters] = {} # session_id -> params
        self.active_markets: Dict[str, TraderManager] = {}     # market_id -> actual markets
        self.user_sessions: Dict[str, str] = {}                # username -> session_id
        
        # Keep historical tracking (needed for limits)
        self.user_historical_markets: Dict[str, Set[str]] = {}
        self.user_ready_status: Dict[str, bool] = {}  # username -> ready to start
        
        # Role persistence: Once assigned, role and goal magnitude stick
        self.permanent_speculators: Set[str] = set()  # username -> always SPECULATOR (goal=0)
        self.permanent_informed_goals: Dict[str, int] = {}  # username -> goal magnitude (e.g., 100)
        
        # Cohort system: Users stay together across markets
        self.user_cohorts: Dict[str, int] = {}  # username -> cohort_id (0, 1, 2, ...)
        self.cohort_sessions: Dict[int, str] = {}  # cohort_id -> current session_id (per-market)
        self.cohort_members: Dict[int, Set[str]] = {}  # cohort_id -> set of usernames
        self.market_sizes: List[int] = []  # e.g., [10, 8] - set via update_market_sizes()
        
        # Persistent session IDs: Each cohort gets one session_id that spans all their markets
        self.cohort_persistent_session_ids: Dict[int, str] = {}  # cohort_id -> SESSION_{timestamp}_{uuid}

        # Treatment groups: lab users can be forced into specific cohorts
        self.user_treatment_groups: Dict[str, int] = {}  # username -> treatment_group (cohort_id)
        # Per-cohort parameter overrides (e.g., {0: {"informed_trade_intensity": 0.36}, ...})
        self.cohort_treatment_overrides: Dict[int, dict] = {}

        # Concurrency control: Lock for atomic session join operations
        self._session_join_lock = asyncio.Lock()
        
    # Backward compatibility properties
    @property
    def session_pools(self) -> Dict[str, List[WaitingUser]]:
        """Convert RoleSlot sessions to WaitingUser format for compatibility."""
        result = {}
        for session_id, slots in self.session_slots.items():
            users = []
            params = self.session_params.get(session_id)
            for slot in slots:
                if slot.assigned_to:
                    users.append(WaitingUser(
                        username=slot.assigned_to,
                        role=slot.role,
                        goal=slot.goal,
                        joined_at=slot.joined_at or datetime.now(timezone.utc),
                        session_id=session_id,
                        params=params or TradingParameters()
                    ))
            result[session_id] = users
        return result
    
    @property
    def user_permanent_roles(self) -> Dict[str, TraderRole]:
        """Backward compatibility: Convert set to dict format."""
        return {username: TraderRole.SPECULATOR for username in self.permanent_speculators}
        
    async def join_session(self, username: str, params: TradingParameters) -> Tuple[str, str, TraderRole, int]:
        """
        User joins a session pool. Fast and lightweight!
        SIMPLER VERSION: Uses RoleSlot for clearer logic.
        ATOMIC: Uses lock to prevent race conditions when multiple traders join simultaneously.
        
        Returns: (session_id, trader_id, role, goal)
        """
        # Check if user can join
        if not await self._can_user_join(username, params):
            raise Exception("Maximum number of allowed markets reached")
        
        # Remove user from any existing session first
        await self.remove_user_from_session(username)
        
        # ATOMIC SECTION: Lock to prevent race conditions
        # Multiple traders arriving simultaneously must join one at a time
        async with self._session_join_lock:
            # Find or create appropriate session
            session_id = self._find_or_create_session(username, params)
            
            # Assign user to a slot in that session
            role, goal = self._assign_user_to_slot(username, session_id, params)
            
            # Track user in session
            self.user_sessions[username] = session_id
        
        trader_id = f"HUMAN_{username}"
        
        logger.info(f"User {username} joined session {session_id} with role {role} and goal {goal}")
        
        return session_id, trader_id, role, goal
    
    async def mark_user_ready(self, username: str) -> Tuple[bool, Dict]:
        """
        Mark user as ready to start trading.
        
        Returns: (all_ready, status_info)
        """
        session_id = self.user_sessions.get(username)
        if not session_id:
            raise Exception(f"User {username} not in any session")
        
        self.user_ready_status[username] = True
        
        # Check if this session is ready to start
        session_users = self.session_pools.get(session_id, [])
        if not session_users:
            raise Exception(f"Session {session_id} not found")
        
        # Get session parameters from first user (all have same params)
        params = session_users[0].params
        required_count = len(params.predefined_goals)
        ready_count = sum(1 for user in session_users if self.user_ready_status.get(user.username, False))
        
        # Check for Prolific users (can start with 1)
        # has_prolific = any("prolific" in user.username.lower() for user in session_users)
        # can_start = ready_count >= required_count or (has_prolific and ready_count > 0)
        can_start = ready_count >= required_count
        
        status_info = {
            "session_id": session_id,
            "ready_count": ready_count,
            "total_needed": required_count,
            "can_start": can_start,
            "status": SessionStatus.READY.value if can_start else SessionStatus.WAITING.value
        }
        
        return can_start, status_info
    
    async def start_trading_session(self, username: str) -> Tuple[str, TraderManager]:
        """
        Convert a session pool into an actual trading market.
        This is where the heavy lifting happens!
        
        Returns: (market_id, trader_manager)
        """
        session_id = self.user_sessions.get(username)
        if not session_id:
            raise Exception(f"User {username} not in any session")
        
        session_users = self.session_pools.get(session_id, [])
        if not session_users:
            raise Exception(f"Session {session_id} not found")
        
        # Check if already converted to market
        if session_id in self.active_markets:
            return session_id, self.active_markets[session_id]
        
        # NOW create the actual heavy market infrastructure
        logger.info(f"Converting session {session_id} to active market with {len(session_users)} users")

        # Use parameters from first user (all have same params for this session)
        base_params = session_users[0].params
        
        # Apply treatment based on first user's market count
        first_user = session_users[0].username
        market_count = len(self.user_historical_markets.get(first_user, set()))
        
        # Get treatment-modified params
        base_params_dict = base_params.model_dump()
        merged_params_dict = treatment_manager.get_merged_params(market_count, base_params_dict)

        # Apply treatment overrides: use user's treatment_group (not cohort_id)
        # so users in independent cohorts still get the right treatment params
        treatment_group = self.user_treatment_groups.get(first_user)
        if treatment_group is not None and treatment_group in self.cohort_treatment_overrides:
            overrides = self.cohort_treatment_overrides[treatment_group]
            merged_params_dict.update(overrides)
            logger.info(f"Applied treatment_group {treatment_group} overrides: {overrides}")
        else:
            # Fallback: try cohort_id (for non-lab flows)
            cohort_id = self.user_cohorts.get(first_user)
            if cohort_id is not None and cohort_id in self.cohort_treatment_overrides:
                overrides = self.cohort_treatment_overrides[cohort_id]
                merged_params_dict.update(overrides)
                logger.info(f"Applied cohort {cohort_id} treatment overrides: {overrides}")

        # Create new TradingParameters with merged settings
        params = TradingParameters(**merged_params_dict)
        logger.info(f"Applied treatment {market_count} for session {session_id} (user {first_user})")
        
        # Create the heavy TraderManager (only now!)
        # Use session_id as market_id to ensure uniqueness
        trader_manager = TraderManager(params, market_id=session_id)
        market_id = trader_manager.trading_market.id
        
        # Add all human traders from the session pool
        for waiting_user in session_users:
            await trader_manager.add_human_trader(
                waiting_user.username,
                role=waiting_user.role,
                goal=waiting_user.goal
            )
            
            # Record in historical markets when trading starts
            if waiting_user.username not in self.user_historical_markets:
                self.user_historical_markets[waiting_user.username] = set()
            self.user_historical_markets[waiting_user.username].add(market_id)
        
        # Move from session pool to active market
        self.active_markets[market_id] = trader_manager
        
        # Clean up session pool - use the actual storage, not the property!
        if session_id in self.session_slots:
            del self.session_slots[session_id]
        if session_id in self.session_params:
            del self.session_params[session_id]
        
        # Clean up cohort session mapping (cohort will get new session next market)
        for cohort_id, cohort_session_id in list(self.cohort_sessions.items()):
            if cohort_session_id == session_id:
                del self.cohort_sessions[cohort_id]
                logger.info(f"Cleared cohort {cohort_id} session mapping (market started)")
        
        for user in session_users:
            self.user_sessions[user.username] = market_id  # Update to market_id
        
        # Log market start to parameter_history.json for session tracking
        treatment_info = treatment_manager.get_treatment(market_count)
        treatment_name = treatment_info.get("name") if treatment_info else None
        participant_usernames = [user.username for user in session_users]
        
        # Get the persistent session_id for this cohort
        first_user = session_users[0].username
        cohort_id = self.user_cohorts.get(first_user)
        persistent_session_id = self.cohort_persistent_session_ids.get(cohort_id) if cohort_id is not None else None
        
        parameter_logger.log_market_start(
            market_id=market_id,
            participants=participant_usernames,
            session_id=persistent_session_id,
            treatment_name=treatment_name,
            treatment_index=market_count,
            parameters=merged_params_dict
        )
        
        logger.info(f"Successfully created market {market_id} from session {session_id}")
        
        return market_id, trader_manager
    
    def get_session_status(self, username: str) -> Dict:
        """Get current status for a user."""
        session_id = self.user_sessions.get(username)
        if not session_id:
            return {"status": "not_found"}
        
        # Check if it's an active market
        if session_id in self.active_markets:
            trader_manager = self.active_markets[session_id]
            # If market is finished, return "finished" status so frontend knows to show summary
            if trader_manager.trading_market.is_finished:
                return {
                    "status": "finished",
                    "market_id": session_id,
                    "trading_started": True,
                    "is_finished": True
                }
            return {
                "status": SessionStatus.ACTIVE.value,
                "market_id": session_id,
                "trading_started": trader_manager.trading_market.trading_started,
                "is_finished": trader_manager.trading_market.is_finished
            }
        
        # It's a session pool
        session_users = self.session_pools.get(session_id, [])
        if not session_users:
            return {"status": "not_found"}
        
        # Find this user's info in the session
        user_info = next((u for u in session_users if u.username == username), None)
        
        params = session_users[0].params
        required_count = len(params.predefined_goals)
        ready_count = sum(1 for user in session_users if self.user_ready_status.get(user.username, False))
        
        result = {
            "status": SessionStatus.WAITING.value,
            "session_id": session_id,
            "current_users": len(session_users),
            "ready_count": ready_count,
            "total_needed": required_count,
            "users": [user.username for user in session_users]
        }
        
        # Add user-specific info if found
        if user_info:
            result["role"] = user_info.role
            result["goal"] = user_info.goal
            result["cash"] = params.initial_cash
            result["shares"] = params.initial_stocks
        
        return result
    
    def get_trader_manager(self, username: str) -> Optional[TraderManager]:
        """Get trader manager for a user (only if market is active)."""
        session_id = self.user_sessions.get(username)
        if not session_id:
            return None
        
        return self.active_markets.get(session_id)
    
    def list_all_sessions(self) -> List[Dict]:
        """List all sessions and markets for admin monitoring."""
        sessions = []
        
        # Add waiting session pools
        for session_id, users in self.session_pools.items():
            if users:  # Only non-empty sessions
                params = users[0].params
                # Find cohort for this session
                cohort_id = None
                for cid, sid in self.cohort_sessions.items():
                    if sid == session_id:
                        cohort_id = cid
                        break
                
                sessions.append({
                    "id": session_id,
                    "type": "session_pool",
                    "status": SessionStatus.WAITING.value,
                    "user_count": len(users),
                    "required_count": len(params.predefined_goals),
                    "users": [user.username for user in users],
                    "cohort_id": cohort_id
                })
        
        # Add active markets
        for market_id, trader_manager in self.active_markets.items():
            sessions.append({
                "id": market_id,
                "type": "active_market",
                "status": SessionStatus.ACTIVE.value,
                "trading_started": trader_manager.trading_market.trading_started,
                "is_finished": trader_manager.trading_market.is_finished,
                "user_count": len(trader_manager.human_traders)
            })
        
        return sessions
    
    async def cleanup_finished_markets(self):
        """Clean up finished markets."""
        finished_markets = []
        
        for market_id, trader_manager in self.active_markets.items():
            if trader_manager.trading_market.is_finished:
                finished_markets.append(market_id)
                await trader_manager.cleanup()
        
        for market_id in finished_markets:
            del self.active_markets[market_id]
            # Remove user session mappings for this market
            users_to_remove = [username for username, session_id in self.user_sessions.items() 
                             if session_id == market_id]
            for username in users_to_remove:
                del self.user_sessions[username]
        
        logger.info(f"Cleaned up {len(finished_markets)} finished markets")
    
    async def reset_all(self):
        """Reset all state (for admin reset)."""
        # Cleanup active markets
        for trader_manager in self.active_markets.values():
            try:
                await trader_manager.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up trader manager: {e}")
        
        # Clear all state (using new structures)
        self.session_slots.clear()
        self.session_params.clear()
        self.active_markets.clear()
        self.user_sessions.clear()
        self.user_ready_status.clear()
        
        # Clear cohort state (users get reassigned on next join)
        self.user_cohorts.clear()
        self.cohort_sessions.clear()
        self.cohort_members.clear()
        self.cohort_persistent_session_ids.clear()  # Clear persistent session IDs
        # Keep market_sizes - that's a configuration, not state
        
        # Keep user_historical_markets for limit tracking
        # Keep permanent_speculators for role consistency across sessions
        
        logger.info("Session manager state reset (including cohorts and session IDs)")

    def update_session_pool_goals(self, new_params: TradingParameters):
        """
        Update goals in waiting session pools after settings change.

        This method:
        1. Clears permanent role/goal memory (allows reassignment)
        2. Updates goals in waiting sessions (not active markets)
        3. Maintains role assignments but updates goal magnitudes

        Args:
            new_params: Updated TradingParameters with new predefined_goals
        """
        # Clear permanent role memory - users can be reassigned new goals
        self.permanent_speculators.clear()
        self.permanent_informed_goals.clear()
        logger.info("Cleared permanent role assignments - users will be reassigned on next join")

        # Update waiting sessions (skip active markets)
        updated_sessions = 0
        for session_id, slots in list(self.session_slots.items()):
            # Update session parameters
            self.session_params[session_id] = new_params

            # Recreate slots with new goals while preserving assignments
            old_assignments = {}
            for slot in slots:
                if slot.assigned_to:
                    old_assignments[slot.assigned_to] = {
                        'role': slot.role,
                        'joined_at': slot.joined_at
                    }

            # Recreate slots with new goals
            import random
            new_goals = new_params.predefined_goals.copy()
            random.shuffle(new_goals)

            new_slots = []
            for goal in new_goals:
                role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
                new_slots.append(RoleSlot(goal=goal, role=role))

            # Reassign users to matching role slots
            for username, assignment in old_assignments.items():
                assigned = False
                for slot in new_slots:
                    if slot.is_available and slot.role == assignment['role']:
                        slot.assigned_to = username
                        slot.joined_at = assignment['joined_at']
                        assigned = True
                        logger.info(f"Reassigned {username} to {slot.role.value} slot with new goal {slot.goal}")
                        break

                if not assigned:
                    logger.warning(f"Could not reassign {username} with role {assignment['role']} - no matching slots in new configuration")

            self.session_slots[session_id] = new_slots
            updated_sessions += 1
            logger.info(f"Updated session {session_id} with new goals {new_goals}")

        logger.info(f"Updated {updated_sessions} waiting sessions with new goal configuration")

    # Private helper methods
    
    async def _can_user_join(self, username: str, params: TradingParameters) -> bool:
        """Check if user can join based on historical limits."""
        # Admin users can always join
        admin_users = params.admin_users or []
        if username in admin_users:
            return True
        
        # Check historical market count
        historical_count = len(self.user_historical_markets.get(username, set()))
        return historical_count < params.max_markets_per_human
    
    async def remove_user_from_session(self, username: str):
        """
        Remove user from any existing session (public method).
        Used when user logs in/refreshes to start fresh.
        SIMPLER: Just free up their slot.
        """
        current_session = self.user_sessions.get(username)
        if not current_session:
            return
        
        # Free up slot in session (if in waiting room)
        if current_session in self.session_slots:
            for slot in self.session_slots[current_session]:
                if slot.assigned_to == username:
                    slot.assigned_to = None
                    slot.joined_at = None
                    logger.info(f"Freed slot for {username} in session {current_session}")
            
            # Clean up empty sessions
            if all(slot.is_available for slot in self.session_slots[current_session]):
                del self.session_slots[current_session]
                if current_session in self.session_params:
                    del self.session_params[current_session]
                logger.info(f"Deleted empty session {current_session}")
        
        # Remove from active market (if in active trading session)
        # Note: This effectively abandons the trading session on refresh
        if current_session in self.active_markets:
            logger.info(f"User {username} abandoned active market {current_session} (e.g., via refresh)")
            # Note: We don't remove the entire market, just the user mapping
            # The market itself will continue with other traders or finish naturally
        
        # Remove session mapping (so user is no longer associated with this session)
        del self.user_sessions[username]
        
        # Remove ready status
        if username in self.user_ready_status:
            del self.user_ready_status[username]
        
        logger.info(f"Removed user {username} from session {current_session}")
    
    async def _remove_user_from_current_session(self, username: str):
        """Remove user from any existing session (internal use)."""
        await self.remove_user_from_session(username)
    
    def _create_session_slots(self, session_id: str, params: TradingParameters, required_goal_magnitude: Optional[int] = None):
        """
        Create role slots for a new session.
        
        Args:
            session_id: Unique session identifier
            params: Trading parameters with predefined_goals
            required_goal_magnitude: If provided, ensure this goal magnitude is included in slots
                                     (used when user has permanent goal magnitude not in predefined_goals)
        """
        import random
        
        # Shuffle goals to randomize assignment across sessions
        goals = params.predefined_goals.copy()
        
        # If a required goal magnitude is specified and not already in goals, add it
        if required_goal_magnitude is not None:
            goal_magnitudes = [abs(g) for g in goals]
            if required_goal_magnitude not in goal_magnitudes:
                # Add the required magnitude (use positive, will be flipped randomly if allow_random_goals)
                goals.append(required_goal_magnitude)
                logger.info(f"Added required goal magnitude {required_goal_magnitude} to session slots")
        
        random.shuffle(goals)
        
        slots = []
        for goal in goals:
            role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR
            slots.append(RoleSlot(goal=goal, role=role))
        
        self.session_slots[session_id] = slots
        self.session_params[session_id] = params
        logger.info(f"Created session {session_id} with {len(slots)} slots (shuffled goals: {goals})")
    
    def _get_effective_market_sizes(self, params: TradingParameters) -> List[int]:
        """
        Get effective market sizes for cohort system.
        If market_sizes is set, use it. Otherwise, use predefined_goals length.
        """
        if self.market_sizes:
            return self.market_sizes
        # Default: single cohort with size = number of predefined goals
        return [len(params.predefined_goals)]
    
    def _find_or_create_session(self, username: str, params: TradingParameters) -> str:
        """
        Find existing session with space or create new one.
        ALWAYS uses cohort system - users who play together stay together.
        
        Cohort logic:
        - If user has a cohort, find/create session for that cohort
        - If no cohort, assign to first cohort with space or create new cohort
        - market_sizes defines cohort sizes, or defaults to len(predefined_goals)
        """
        # ALWAYS use cohort system
        cohort_id = self._get_or_assign_cohort(username, params)
        return self._find_or_create_cohort_session(username, cohort_id, params)
    
    def _get_or_assign_cohort(self, username: str, params: TradingParameters) -> int:
        """
        Get user's cohort or assign them to one.
        Cohorts fill up in order based on effective market_sizes.
        """
        # User already has a cohort
        if username in self.user_cohorts:
            return self.user_cohorts[username]

        effective_sizes = self._get_effective_market_sizes(params)

        # Note: treatment_group is NOT used for cohort assignment.
        # Each user gets their own independent cohort; treatment overrides
        # are applied via user_treatment_groups lookup at market start time.

        # Find first cohort with space
        for cohort_id, max_size in enumerate(effective_sizes):
            if cohort_id not in self.cohort_members:
                self.cohort_members[cohort_id] = set()
            
            if len(self.cohort_members[cohort_id]) < max_size:
                # Assign user to this cohort
                self.user_cohorts[username] = cohort_id
                self.cohort_members[cohort_id].add(username)
                # Create persistent session_id for this cohort if first member
                self._get_or_create_cohort_session_id(cohort_id)
                logger.info(f"Assigned {username} to cohort {cohort_id} (size {len(self.cohort_members[cohort_id])}/{max_size})")
                return cohort_id
        
        # All cohorts full - create overflow cohort using last market_size
        overflow_cohort_id = len(effective_sizes)
        while overflow_cohort_id in self.cohort_members:
            if len(self.cohort_members[overflow_cohort_id]) < effective_sizes[-1]:
                break
            overflow_cohort_id += 1
        
        if overflow_cohort_id not in self.cohort_members:
            self.cohort_members[overflow_cohort_id] = set()
        
        self.user_cohorts[username] = overflow_cohort_id
        self.cohort_members[overflow_cohort_id].add(username)
        # Create persistent session_id for overflow cohort
        self._get_or_create_cohort_session_id(overflow_cohort_id)
        logger.info(f"Assigned {username} to overflow cohort {overflow_cohort_id}")
        return overflow_cohort_id
    
    def _find_or_create_cohort_session(self, username: str, cohort_id: int, params: TradingParameters) -> str:
        """
        Find or create a session for a specific cohort.
        Goals are sliced from predefined_goals based on cohort size.
        """
        import uuid
        
        # Check if cohort already has a waiting session
        if cohort_id in self.cohort_sessions:
            session_id = self.cohort_sessions[cohort_id]
            if session_id in self.session_slots:
                # Session exists and is still waiting
                available_slots = [s for s in self.session_slots[session_id] if s.is_available]
                if available_slots:
                    return session_id
        
        # Get the persistent session_id for this cohort
        persistent_session_id = self._get_or_create_cohort_session_id(cohort_id)
        
        # Create new market for this cohort
        # Format: {SESSION_ID}_MARKET_{market_number}
        # Count existing markets for this session to get market number
        market_count = sum(1 for mid in self.active_markets.keys() 
                         if mid.startswith(persistent_session_id))
        # Also count historical markets from user_historical_markets
        first_user = next(iter(self.cohort_members.get(cohort_id, set())), None)
        if first_user:
            market_count = len(self.user_historical_markets.get(first_user, set()))
        
        market_id = f"{persistent_session_id}_MARKET_{market_count}"
        
        # Determine cohort size from effective market sizes
        effective_sizes = self._get_effective_market_sizes(params)
        if cohort_id < len(effective_sizes):
            cohort_size = effective_sizes[cohort_id]
        else:
            cohort_size = effective_sizes[-1]  # Use last size for overflow
        
        # Slice goals for this cohort size
        cohort_goals = params.predefined_goals[:cohort_size]
        if len(cohort_goals) < cohort_size:
            # Pad with zeros (speculators) if not enough goals defined
            cohort_goals.extend([0] * (cohort_size - len(cohort_goals)))
        
        # Create modified params with cohort-specific goals
        cohort_params = params.model_copy()
        cohort_params.predefined_goals = cohort_goals
        
        self._create_session_slots(market_id, cohort_params)
        self.cohort_sessions[cohort_id] = market_id
        
        logger.info(f"Created market {market_id} for cohort {cohort_id} (session {persistent_session_id}) with {cohort_size} slots, goals: {cohort_goals}")
        return market_id
    
    def update_market_sizes(self, market_sizes: List[int]):
        """
        Update market sizes for cohort system.
        Call this when admin updates settings.
        
        Args:
            market_sizes: List of market sizes, e.g., [10, 8] for 18 people total
        """
        self.market_sizes = market_sizes
        logger.info(f"Updated market_sizes to {market_sizes}")
    
    def _get_or_create_cohort_session_id(self, cohort_id: int) -> str:
        """
        Get or create a persistent session_id for a cohort.
        This ID spans all markets the cohort plays together.
        
        Returns: SESSION_{timestamp}_{uuid} format
        """
        import uuid
        
        if cohort_id not in self.cohort_persistent_session_ids:
            timestamp = int(time.time())
            unique_suffix = str(uuid.uuid4())[:8]
            session_id = f"SESSION_{timestamp}_{unique_suffix}"
            self.cohort_persistent_session_ids[cohort_id] = session_id
            logger.info(f"Created persistent session_id {session_id} for cohort {cohort_id}")
        
        return self.cohort_persistent_session_ids[cohort_id]
    
    def get_session_id_for_user(self, username: str) -> Optional[str]:
        """Get the persistent session_id for a user's cohort."""
        cohort_id = self.user_cohorts.get(username)
        if cohort_id is not None:
            return self.cohort_persistent_session_ids.get(cohort_id)
        return None
    
    def get_cohort_info(self) -> Dict:
        """Get current cohort assignments for admin monitoring."""
        return {
            "market_sizes": self.market_sizes,
            "cohorts": {
                cohort_id: {
                    "members": list(members),
                    "size": len(members),
                    "max_size": self.market_sizes[cohort_id] if cohort_id < len(self.market_sizes) else self.market_sizes[-1] if self.market_sizes else 0,
                    "current_session": self.cohort_sessions.get(cohort_id)
                }
                for cohort_id, members in self.cohort_members.items()
            },
            "user_cohorts": self.user_cohorts
        }
    
    def _assign_user_to_slot(self, username: str, session_id: str, params: TradingParameters) -> Tuple[TraderRole, int]:
        """
        Assign user to an available slot in the session.
        Respects permanent role and goal magnitude.
        
        Returns: (role, goal)
        """
        import random
        
        slots = self.session_slots[session_id]
        is_permanent_speculator = username in self.permanent_speculators
        permanent_goal_magnitude = self.permanent_informed_goals.get(username)
        
        # Find suitable slot
        for slot in slots:
            if not slot.is_available:
                continue
            
            # If user is permanent SPECULATOR, only give SPECULATOR slots
            if is_permanent_speculator:
                if slot.role != TraderRole.SPECULATOR:
                    continue
            # If user is permanent INFORMED, only give INFORMED slots with matching magnitude
            elif permanent_goal_magnitude is not None:
                if slot.role != TraderRole.INFORMED or abs(slot.goal) != permanent_goal_magnitude:
                    continue
            
            # Assign this slot
            goal = slot.goal
            
            # For INFORMED traders, randomly flip goal direction if enabled
            if slot.role == TraderRole.INFORMED and params.allow_random_goals:
                goal = abs(goal) * random.choice([-1, 1])
                slot.goal = goal  # Update slot with flipped goal
            
            # Update slot assignment
            slot.assigned_to = username
            slot.joined_at = datetime.now(timezone.utc)
            
            # Record permanent role on first assignment
            if slot.role == TraderRole.SPECULATOR and username not in self.permanent_speculators:
                self.permanent_speculators.add(username)
                logger.info(f"User {username} assigned permanent SPECULATOR role (goal=0)")
            elif slot.role == TraderRole.INFORMED and username not in self.permanent_informed_goals:
                self.permanent_informed_goals[username] = abs(goal)
                logger.info(f"User {username} assigned permanent INFORMED role (|goal|={abs(goal)})")
            
            logger.info(f"Assigned {username} to slot with role {slot.role.value} and goal {goal}")
            return slot.role, goal
        
        raise Exception(f"No suitable slot available for {username} in session {session_id}") 