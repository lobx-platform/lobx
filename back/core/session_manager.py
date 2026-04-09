"""
Session Manager - Multi-participant lab sessions.

Users in the same treatment group share a waiting room.
Markets start when all N participants (defined by predefined_goals) are ready.
Role assignment is deterministic: P1→goals[0], P2→goals[1], etc.
"""

import time
import uuid
import random
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
parameter_logger = ParameterLogger()


@dataclass
class WaitingUser:
    """Lightweight user waiting to join a market."""
    username: str
    role: TraderRole
    goal: int
    joined_at: datetime
    session_id: str
    params: TradingParameters

    def to_trader_id(self) -> str:
        return f"HUMAN_{self.username}"


class SessionStatus(Enum):
    WAITING = "waiting"
    READY = "ready"
    ACTIVE = "active"
    FINISHED = "finished"


class SessionManager:
    """
    Multi-participant session management.

    Users in the same treatment group are placed in a shared waiting room.
    The waiting room key is T{treatment_group}_M{market_number}, so the same
    group plays sequential markets together.
    """

    def __init__(self):
        # Core state
        self.session_pools: Dict[str, List[WaitingUser]] = {}    # room_key -> waiting users
        self.active_markets: Dict[str, TraderManager] = {}       # market_id -> trader manager
        self.user_sessions: Dict[str, str] = {}                  # username -> room_key or market_id
        self.user_historical_markets: Dict[str, Set[str]] = {}   # username -> set of market_ids
        self.user_ready_status: Dict[str, bool] = {}             # username -> ready flag

        # Treatment groups: lab users can be assigned specific treatment groups
        self.user_treatment_groups: Dict[str, int] = {}          # username -> treatment_group

        # Persistent random goal signs (so direction doesn't flip between markets)
        self._goal_signs: Dict[str, int] = {}

        self.user_market_count: Dict[str, int] = {}              # username -> markets completed in current sequence

        # Concurrency control
        self._session_join_lock = asyncio.Lock()

    async def join_session(self, username: str, params: TradingParameters) -> Tuple[str, str, TraderRole, int]:
        """User joins a session. Returns (session_id, trader_id, role, goal).

        Multi-participant: users in the same treatment_group share a waiting room.
        The room key is T{treatment_group}_M{market_count} so the same group
        progresses through sequential markets together.
        """
        if not await self._can_user_join(username, params):
            raise Exception("Maximum number of allowed markets reached")

        await self.remove_user_from_session(username)

        async with self._session_join_lock:
            treatment_group = self.user_treatment_groups.get(username)
            market_count = self.user_market_count.get(username, 0)

            if treatment_group is not None:
                # Multi-participant: find/create shared waiting room
                room_key = f"T{treatment_group}_M{market_count}"
            else:
                # Non-lab users: create individual session
                ts = int(time.time())
                uid = uuid.uuid4().hex[:8]
                room_key = f"SESSION_{ts}_{uid}_{username}_MARKET_{market_count}"

            if room_key not in self.session_pools:
                self.session_pools[room_key] = []

            # Goal index = position in the waiting room (join order)
            position = len(self.session_pools[room_key])
            role, goal = self._assign_role(username, room_key, params, position)
            self.user_sessions[username] = room_key

        trader_id = f"HUMAN_{username}"
        logger.info(f"User {username} joined room {room_key} role={role} goal={goal} position={position}")
        return room_key, trader_id, role, goal

    async def mark_user_ready(self, username: str) -> Tuple[bool, Dict]:
        """Mark user ready. Returns (all_ready, status_info)."""
        session_id = self.user_sessions.get(username)
        if not session_id:
            raise Exception(f"User {username} not in any session")

        self.user_ready_status[username] = True

        users = self.session_pools.get(session_id, [])
        if not users:
            raise Exception(f"Session {session_id} not found")

        params = users[0].params
        required = len(params.predefined_goals)
        ready = sum(1 for u in users if self.user_ready_status.get(u.username, False))
        can_start = ready >= required

        return can_start, {
            "session_id": session_id, "ready_count": ready,
            "total_needed": required, "can_start": can_start,
            "users": [u.username for u in users],
            "status": SessionStatus.READY.value if can_start else SessionStatus.WAITING.value
        }

    async def start_trading_session(self, username: str) -> Tuple[str, TraderManager]:
        """Convert waiting session into active market. Returns (market_id, trader_manager)."""
        session_id = self.user_sessions.get(username)
        if not session_id:
            raise Exception(f"User {username} not in any session")

        if session_id in self.active_markets:
            return session_id, self.active_markets[session_id]

        users = self.session_pools.get(session_id, [])
        if not users:
            raise Exception(f"Session {session_id} not found")

        first_user = users[0].username
        market_count = self.user_market_count.get(first_user, 0)

        # Build merged params: base -> treatment (by treatment_group index)
        base_params_dict = users[0].params.model_dump()
        treatment_group = self.user_treatment_groups.get(first_user)

        if treatment_group is not None:
            # Use treatment_group as index into treatments list
            treatment_settings = treatment_manager.get_treatment_for_market(treatment_group)
            if treatment_settings:
                merged = base_params_dict.copy()
                merged.update(treatment_settings)
                logger.info(f"Applied treatment_group {treatment_group}: {treatment_settings}")
            else:
                merged = base_params_dict.copy()
                logger.warning(f"No treatment found for treatment_group {treatment_group}")
        else:
            # No treatment_group: fall back to market_count-based treatment
            merged = treatment_manager.get_merged_params(market_count, base_params_dict)

        params = TradingParameters(**merged)
        timestamped_id = f"{session_id}_{int(time.time())}"
        trader_manager = TraderManager(params, market_id=timestamped_id)
        market_id = trader_manager.trading_market.id

        for wu in users:
            await trader_manager.add_human_trader(wu.username, role=wu.role, goal=wu.goal)
            if wu.username not in self.user_historical_markets:
                self.user_historical_markets[wu.username] = set()
            self.user_historical_markets[wu.username].add(market_id)
            # Increment market count for sequential markets
            self.user_market_count[wu.username] = self.user_market_count.get(wu.username, 0) + 1

        self.active_markets[market_id] = trader_manager

        # Clean up waiting pool
        self.session_pools.pop(session_id, None)

        for u in users:
            self.user_sessions[u.username] = market_id

        # Log market start
        treatment_info = treatment_manager.get_treatment(market_count)
        treatment_name = treatment_info.get("name") if treatment_info else None
        parameter_logger.log_market_start(
            market_id=market_id,
            participants=[u.username for u in users],
            session_id=session_id,
            treatment_name=treatment_name,
            treatment_index=market_count,
            parameters=merged
        )

        logger.info(f"Created market {market_id} from room {session_id} with {len(users)} participants")
        return market_id, trader_manager

    def get_session_status(self, username: str) -> Dict:
        """Get current status for a user."""
        session_id = self.user_sessions.get(username)
        if not session_id:
            return {"status": "not_found"}

        if session_id in self.active_markets:
            tm = self.active_markets[session_id]
            if tm.trading_market.is_finished:
                return {"status": "finished", "market_id": session_id, "trading_started": True, "is_finished": True}
            return {"status": SessionStatus.ACTIVE.value, "market_id": session_id,
                    "trading_started": tm.trading_market.trading_started, "is_finished": False}

        users = self.session_pools.get(session_id, [])
        if not users:
            return {"status": "not_found"}

        user_info = next((u for u in users if u.username == username), None)
        params = users[0].params
        required = len(params.predefined_goals)
        ready = sum(1 for u in users if self.user_ready_status.get(u.username, False))

        result = {"status": SessionStatus.WAITING.value, "session_id": session_id,
                  "current_users": len(users), "ready_count": ready, "total_needed": required,
                  "users": [u.username for u in users]}
        if user_info:
            result.update({"role": user_info.role, "goal": user_info.goal,
                           "cash": params.initial_cash, "shares": params.initial_stocks})
        return result

    def get_trader_manager(self, username: str) -> Optional[TraderManager]:
        session_id = self.user_sessions.get(username)
        return self.active_markets.get(session_id) if session_id else None

    def list_all_sessions(self) -> List[Dict]:
        sessions = []
        for sid, users in self.session_pools.items():
            if users:
                params = users[0].params
                sessions.append({
                    "id": sid, "type": "session_pool", "status": SessionStatus.WAITING.value,
                    "user_count": len(users), "required_count": len(params.predefined_goals),
                    "users": [u.username for u in users]
                })
        for mid, tm in self.active_markets.items():
            sessions.append({
                "id": mid, "type": "active_market", "status": SessionStatus.ACTIVE.value,
                "trading_started": tm.trading_market.trading_started,
                "is_finished": tm.trading_market.is_finished,
                "user_count": len(tm.human_traders)
            })
        return sessions

    async def cleanup_finished_markets(self):
        finished = [mid for mid, tm in list(self.active_markets.items()) if tm.trading_market.is_finished]
        for mid in finished:
            await self.active_markets[mid].cleanup()
            self.active_markets.pop(mid, None)
            for username in [u for u, sid in list(self.user_sessions.items()) if sid == mid]:
                self.user_sessions.pop(username, None)
        if finished:
            logger.info(f"Cleaned up {len(finished)} finished markets")

    async def reset_all(self):
        for tm in list(self.active_markets.values()):
            try:
                await tm.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up trader manager: {e}")
        self.session_pools.clear()
        self.active_markets.clear()
        self.user_sessions.clear()
        self.user_ready_status.clear()
        self.user_market_count.clear()
        logger.info("Session manager state reset")

    async def remove_user_from_session(self, username: str):
        """Remove user from waiting pool or active mapping."""
        session_id = self.user_sessions.get(username)
        if not session_id:
            return

        if session_id in self.session_pools:
            self.session_pools[session_id] = [u for u in self.session_pools[session_id] if u.username != username]
            if not self.session_pools[session_id]:
                del self.session_pools[session_id]

        self.user_sessions.pop(username, None)
        self.user_ready_status.pop(username, None)

    # --- Private helpers ---

    async def _can_user_join(self, username: str, params: TradingParameters) -> bool:
        return len(self.user_historical_markets.get(username, set())) < params.max_markets_per_human

    def _assign_role(self, username: str, session_id: str, params: TradingParameters,
                     position: int = 0) -> Tuple[TraderRole, int]:
        """Assign role and goal by position in the waiting room.

        Position is simply the join order:
          first to join  (position=0) → goals[0]
          second to join (position=1) → goals[1]
          third to join  (position=2) → goals[2]
        """
        goals = params.predefined_goals
        goal = goals[position % len(goals)] if goals else 0

        # Random direction flipping (only on first assignment, then persisted)
        if goal != 0 and params.allow_random_goals:
            persist_key = f"{username}_goal_sign"
            if persist_key not in self._goal_signs:
                self._goal_signs[persist_key] = random.choice([-1, 1])
            goal = abs(goal) * self._goal_signs[persist_key]

        role = TraderRole.INFORMED if goal != 0 else TraderRole.SPECULATOR

        self.session_pools[session_id].append(WaitingUser(
            username=username, role=role, goal=goal,
            joined_at=datetime.now(timezone.utc),
            session_id=session_id, params=params
        ))

        logger.info(f"Assigned {username} role={role.value} goal={goal} position={position}")
        return role, goal
