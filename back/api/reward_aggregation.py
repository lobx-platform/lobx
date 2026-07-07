def average_positive_rewards(rewards):
    """Average of max(reward, 0) over the given markets (issue #78).

    Replaces the seeded random pick of a single paying market. Rewards are
    floored at 0 per market before averaging, so one bad market cannot drag
    the payment below what the other markets earned.
    """
    if not rewards:
        return 0
    return sum(max(reward, 0) for reward in rewards) / len(rewards)
