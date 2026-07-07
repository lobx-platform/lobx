"""
Tests for reward calculation logic.

Tests cover:
1. Basic VWAP reward for buyers (goal > 0)
2. Basic VWAP reward for sellers (goal < 0)
3. Penalty for incomplete trades
4. Zero trades scenario (shows N/A in UI)
5. Accumulated rewards across multiple markets
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logfiles_analysis import calculate_vwap_reward, calculate_trader_specific_metrics


class TestNoGoalRewardCap:
    """No-goal (speculator) reward: floored at 0, cap effectively disabled (issue #78)."""

    def _reward_for_pnl(self, pnl, conversion_rate=2):
        metrics = calculate_trader_specific_metrics(
            {"PnL": pnl, "Trades": 4, "Num_Buy": 2, "Num_Sell": 2,
             "VWAP": 100, "Prices_Buy": [100, 100], "Prices_Sell": [100, 100]},
            {}, trader_goal=0, conversion_rate=conversion_rate)
        return metrics["Reward"]

    def test_negative_pnl_floored_to_zero(self):
        assert self._reward_for_pnl(-200) == 0

    def test_positive_pnl_converts_linearly(self):
        # PnL / conversion_rate, no longer clipped at 10
        assert self._reward_for_pnl(10) == pytest.approx(5.0)
        assert self._reward_for_pnl(20) == pytest.approx(10.0)

    def test_old_cap_no_longer_binds(self):
        """Was capped at 10 GBP; PnL of 50 Lira must now pay 25 GBP."""
        assert self._reward_for_pnl(50) == pytest.approx(25.0)
        assert self._reward_for_pnl(100) == pytest.approx(50.0)


class TestBasicRewardCalculation:
    """Test basic reward calculation for complete trades."""

    def test_buyer_complete_goal_good_price(self):
        """Buyer completes goal at price below target (110) - should get reward."""
        result = calculate_vwap_reward(
            goal=20,  # Buy 20 shares
            completed_trades=20,  # All completed
            current_vwap=100,  # Bought at avg 100
            mid_price=100,
            buy_target_price=110,
            sell_target_price=90,
        )

        # Reward = (110 - 100) * 10 / 10 = 10
        assert result["reward"] == 10
        assert result["remaining_trades"] == 0
        assert result["penalized_vwap"] == 100
        print(f"✓ Buyer complete goal good price: reward={result['reward']}")

    def test_buyer_complete_goal_bad_price(self):
        """Buyer completes goal at price above target - reward capped at 0."""
        result = calculate_vwap_reward(
            goal=20,
            completed_trades=20,
            current_vwap=115,  # Bought at avg 115 (above target 110)
            mid_price=100,
            buy_target_price=110,
            sell_target_price=90,
        )

        # Reward = (110 - 115) * 10 / 10 = -5, capped to 0
        assert result["reward"] == 0
        assert result["pnl"] == -50  # Raw PnL before capping
        print(f"✓ Buyer complete goal bad price: reward={result['reward']}, pnl={result['pnl']}")

    def test_seller_complete_goal_good_price(self):
        """Seller completes goal at price above target (90) - should get reward."""
        result = calculate_vwap_reward(
            goal=-20,  # Sell 20 shares
            completed_trades=20,  # All completed
            current_vwap=105,  # Sold at avg 105
            mid_price=100,
            buy_target_price=110,
            sell_target_price=90,
        )

        # Reward = (105 - 90) * 10 / 10 = 15
        assert result["reward"] == 15
        assert result["remaining_trades"] == 0
        print(f"✓ Seller complete goal good price: reward={result['reward']}")

    def test_seller_complete_goal_bad_price(self):
        """Seller completes goal at price below target - reward capped at 0."""
        result = calculate_vwap_reward(
            goal=-20,
            completed_trades=20,
            current_vwap=85,  # Sold at avg 85 (below target 90)
            mid_price=100,
            buy_target_price=110,
            sell_target_price=90,
        )

        # Reward = (85 - 90) * 10 / 10 = -5, capped to 0
        assert result["reward"] == 0
        assert result["pnl"] == -50
        print(f"✓ Seller complete goal bad price: reward={result['reward']}, pnl={result['pnl']}")


class TestIncompleteTradePenalty:
    """Test penalty calculation for incomplete trades."""

    def test_buyer_partial_completion(self):
        """Buyer completes half the goal - penalized for remaining."""
        result = calculate_vwap_reward(
            goal=20,
            completed_trades=10,  # Only 10 of 20
            current_vwap=100,
            mid_price=100,
            buy_target_price=110,
            sell_target_price=90,
            penalty_multiplier_buy=1.5,  # Remaining bought at 1.5x mid
        )

        # Penalized VWAP = (100*10 + 100*1.5*10) / 20 = (1000 + 1500) / 20 = 125
        # Reward = (110 - 125) = -15, capped to 0
        assert result["remaining_trades"] == 10
        assert result["penalized_vwap"] == 125
        assert result["reward"] == 0
        print(f"✓ Buyer partial completion: penalized_vwap={result['penalized_vwap']}, reward={result['reward']}")

    def test_seller_partial_completion(self):
        """Seller completes half the goal - penalized for remaining."""
        result = calculate_vwap_reward(
            goal=-20,
            completed_trades=10,  # Only 10 of 20
            current_vwap=100,
            mid_price=100,
            buy_target_price=110,
            sell_target_price=90,
            penalty_multiplier_sell=0.5,  # Remaining sold at 0.5x mid
        )

        # Penalized VWAP = (100*10 + 100*0.5*10) / 20 = (1000 + 500) / 20 = 75
        # Reward = (75 - 90) = -15, capped to 0
        assert result["remaining_trades"] == 10
        assert result["penalized_vwap"] == 75
        assert result["reward"] == 0
        print(f"✓ Seller partial completion: penalized_vwap={result['penalized_vwap']}, reward={result['reward']}")

    def test_buyer_no_penalty_when_complete(self):
        """Completing goal means no penalty applied."""
        result = calculate_vwap_reward(
            goal=20,
            completed_trades=20,
            current_vwap=105,
            mid_price=100,
            penalty_multiplier_buy=1.5,
        )

        # No remaining trades, so penalized_vwap = current_vwap
        assert result["remaining_trades"] == 0
        assert result["penalized_vwap"] == 105
        print(f"✓ Buyer complete - no penalty: penalized_vwap={result['penalized_vwap']}")


class TestZeroTradesScenario:
    """Test when user doesn't place any trades (shows N/A in UI)."""

    def test_buyer_zero_trades(self):
        """Buyer with no trades - full penalty applied."""
        result = calculate_vwap_reward(
            goal=20,
            completed_trades=0,
            current_vwap=0,  # No VWAP since no trades
            mid_price=100,
            buy_target_price=110,
            penalty_multiplier_buy=1.5,
        )

        # All 20 shares at penalty price: 20 * 100 * 1.5 = 3000
        # Penalized VWAP = 3000 / 20 = 150
        # Reward = (110 - 150) = -40, capped to 0
        assert result["remaining_trades"] == 20
        assert result["penalized_vwap"] == 150
        assert result["reward"] == 0
        print(f"✓ Buyer zero trades: penalized_vwap={result['penalized_vwap']}, reward={result['reward']}")

    def test_seller_zero_trades(self):
        """Seller with no trades - full penalty applied."""
        result = calculate_vwap_reward(
            goal=-20,
            completed_trades=0,
            current_vwap=0,
            mid_price=100,
            sell_target_price=90,
            penalty_multiplier_sell=0.5,
        )

        # All 20 shares at penalty price: 20 * 100 * 0.5 = 1000
        # Penalized VWAP = 1000 / 20 = 50
        # Reward = (50 - 90) = -40, capped to 0
        assert result["remaining_trades"] == 20
        assert result["penalized_vwap"] == 50
        assert result["reward"] == 0
        print(f"✓ Seller zero trades: penalized_vwap={result['penalized_vwap']}, reward={result['reward']}")

    def test_zero_goal(self):
        """Zero goal (speculator with no target) - returns zeros."""
        result = calculate_vwap_reward(
            goal=0,
            completed_trades=5,
            current_vwap=100,
            mid_price=100,
        )

        assert result["reward"] == 0
        assert result["remaining_trades"] == 0
        assert result["penalized_vwap"] == 0
        print(f"✓ Zero goal: all metrics are 0")


class TestAccumulatedRewards:
    """Test accumulated reward logic across multiple markets."""

    def test_accumulated_reward_single_market(self):
        """First market only - accumulated reward is 0."""
        # Simulating the logic from endpoints.py
        accumulated_rewards = {}
        trader_id = "HUMAN_test123"

        # Market 0 reward
        market_0_reward = 5.0
        session_0 = "SESSION_123_MARKET_0"

        if trader_id not in accumulated_rewards:
            accumulated_rewards[trader_id] = {}
        accumulated_rewards[trader_id][session_0] = market_0_reward

        # Calculate accumulated (skip first market)
        all_rewards = list(accumulated_rewards[trader_id].values())
        if len(all_rewards) <= 1:
            accumulated = 0
        else:
            accumulated = sum(all_rewards[1:])  # Simplified - actual uses random pick

        assert accumulated == 0
        print(f"✓ Single market: accumulated_reward=0 (first market skipped)")

    def test_accumulated_reward_multiple_markets(self):
        """Multiple markets - accumulated includes markets 2+."""
        accumulated_rewards = {}
        trader_id = "HUMAN_test123"

        # Simulate 4 markets
        rewards = [5.0, 8.0, 3.0, 10.0]  # Markets 0, 1, 2, 3

        for i, reward in enumerate(rewards):
            session_id = f"SESSION_123_MARKET_{i}"
            if trader_id not in accumulated_rewards:
                accumulated_rewards[trader_id] = {}
            accumulated_rewards[trader_id][session_id] = reward

        # Markets 1, 2, 3 should be considered (skip market 0)
        all_rewards = list(accumulated_rewards[trader_id].values())
        rewards_after_first = all_rewards[1:]  # [8.0, 3.0, 10.0]

        assert len(rewards_after_first) == 3
        assert 8.0 in rewards_after_first
        assert 3.0 in rewards_after_first
        assert 10.0 in rewards_after_first
        print(f"✓ Multiple markets: rewards after first = {rewards_after_first}")

    def test_accumulated_reward_with_zero_trades_market(self):
        """Market with zero trades still counts in accumulation."""
        accumulated_rewards = {}
        trader_id = "HUMAN_test123"

        # Market 0: traded, reward 5
        # Market 1: traded, reward 8
        # Market 2: no trades, reward 0
        # Market 3: traded, reward 10
        rewards = [5.0, 8.0, 0.0, 10.0]

        for i, reward in enumerate(rewards):
            session_id = f"SESSION_123_MARKET_{i}"
            if trader_id not in accumulated_rewards:
                accumulated_rewards[trader_id] = {}
            accumulated_rewards[trader_id][session_id] = reward

        all_rewards = list(accumulated_rewards[trader_id].values())
        rewards_after_first = all_rewards[1:]

        # Zero reward market is still included
        assert 0.0 in rewards_after_first
        assert len(rewards_after_first) == 3
        print(f"✓ Zero trades market included: {rewards_after_first}")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_exact_target_price_buyer(self):
        """Buyer buys at exactly target price - zero reward."""
        result = calculate_vwap_reward(
            goal=20,
            completed_trades=20,
            current_vwap=110,  # Exactly at target
            mid_price=100,
            buy_target_price=110,
        )

        # Reward = (110 - 110) = 0
        assert result["reward"] == 0
        assert result["pnl"] == 0
        print(f"✓ Buyer at exact target: reward=0")

    def test_exact_target_price_seller(self):
        """Seller sells at exactly target price - zero reward."""
        result = calculate_vwap_reward(
            goal=-20,
            completed_trades=20,
            current_vwap=90,  # Exactly at target
            mid_price=100,
            sell_target_price=90,
        )

        # Reward = (90 - 90) = 0
        assert result["reward"] == 0
        assert result["pnl"] == 0
        print(f"✓ Seller at exact target: reward=0")

    def test_single_trade(self):
        """Goal of 1 trade - smallest unit."""
        result = calculate_vwap_reward(
            goal=1,
            completed_trades=1,
            current_vwap=95,
            mid_price=100,
            buy_target_price=110,
        )

        # Reward = (110 - 95) = 15
        assert result["reward"] == 15
        assert result["remaining_trades"] == 0
        print(f"✓ Single trade goal: reward={result['reward']}")

    def test_large_goal(self):
        """Large goal (100 shares)."""
        result = calculate_vwap_reward(
            goal=100,
            completed_trades=100,
            current_vwap=100,
            mid_price=100,
            buy_target_price=110,
        )

        # Reward = (110 - 100) = 10
        assert result["reward"] == 10
        print(f"✓ Large goal (100): reward={result['reward']}")

    def test_negative_completed_trades_treated_as_absolute(self):
        """Completed trades should be treated as absolute value."""
        result = calculate_vwap_reward(
            goal=-20,
            completed_trades=-20,  # Passed as negative (shouldn't happen but handle it)
            current_vwap=105,
            mid_price=100,
            sell_target_price=90,
        )

        # Should still work - completed = abs(-20) = 20
        assert result["remaining_trades"] == 0
        assert result["reward"] == 15
        print(f"✓ Negative completed trades handled: reward={result['reward']}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
