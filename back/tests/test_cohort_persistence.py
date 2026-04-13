#!/usr/bin/env python3
"""
Test cohort persistence with:
- 13 participants, cohorts of 3 (so 4 full cohorts + 1 leftover)
- 3 markets per participant
- Random join order each market
- Verify: same users stick together, leftover doesn't join, correct session/market IDs
"""

import asyncio
import aiohttp
import json
import random
import os
from pathlib import Path

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
PARAM_HISTORY_PATH = Path("back/logs/parameters/parameter_history.json")


async def reset_state(session):
    """Reset state using test endpoint"""
    try:
        async with session.post(f"{BACKEND_URL}/test/reset_state") as resp:
            return resp.status == 200
    except:
        return False


async def update_settings(session, **kwargs):
    async with session.post(f"{BACKEND_URL}/admin/update_base_settings",
                           json={"settings": kwargs}) as resp:
        return resp.status == 200


async def upload_treatments(session, yaml_content):
    async with session.post(f"{BACKEND_URL}/admin/update_treatments",
                           json={"yaml_content": yaml_content}) as resp:
        return resp.status == 200


async def start_trading(session, username, retries=2):
    params = {"PROLIFIC_PID": username, "STUDY_ID": "cohort_test", "SESSION_ID": f"s_{username}"}
    for attempt in range(retries + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(f"{BACKEND_URL}/trading/start", params=params,
                                   json={"username": "user1", "password": "password1"},
                                   timeout=timeout) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    text = await resp.text()
                    return {"status": "error", "code": resp.status, "message": text[:200]}
        except Exception as e:
            if attempt < retries:
                await asyncio.sleep(0.5)
                continue
            return {"status": "error", "exception": str(e)}


async def main():
    print("\n" + "="*70)
    print("Test: Cohort Persistence")
    print("13 participants, cohorts of 3, 3 markets each, random join order")
    print("="*70)
    
    print("\nWaiting 3 seconds for server to stabilize...")
    await asyncio.sleep(3)
    
    async with aiohttp.ClientSession() as session:
        # Reset state
        if await reset_state(session):
            print("✓ State reset")
        else:
            print("✗ State reset failed")
            return
        
        # Upload 3 treatments
        yaml_content = """
treatments:
  - name: "Treatment A"
    num_noise_traders: 1
  - name: "Treatment B"
    num_noise_traders: 1
  - name: "Treatment C"
    num_noise_traders: 1
"""
        await upload_treatments(session, yaml_content)
        print("✓ Uploaded 3 treatments")
        
        # Configure: 13 users, cohorts of 3, 3 markets each
        # 13 / 3 = 4 full cohorts (12 users) + 1 leftover
        await update_settings(
            session,
            predefined_goals=[100, 50, 0],  # 3 goals for 3 participants per cohort
            max_markets_per_human=3,         # 3 markets per participant
            trading_day_duration=0.25,       # 15 seconds
            num_noise_traders=1,
            num_informed_traders=0
        )
        print("✓ Settings: 4 cohorts of 3, 3 markets each, 15-second duration")
        
        # Create 13 users
        all_users = [f"p{i}" for i in range(13)]
        print(f"✓ Users: {all_users}")
        
        # Track results per user
        user_results = {u: [] for u in all_users}
        
        # Run 3 markets with random join order each time
        for market_num in range(3):
            print(f"\n{'='*50}")
            print(f"MARKET {market_num}")
            print("="*50)
            
            # Shuffle users for random join order
            shuffled_users = all_users.copy()
            random.shuffle(shuffled_users)
            print(f"Join order: {shuffled_users}")
            
            print("\n--- Starting trading ---")
            for username in shuffled_users:
                result = await start_trading(session, username)
                status = result.get('status', 'unknown')
                msg = result.get('message', '')[:50] if result.get('message') else ''
                
                if status == 'success':
                    all_ready = result.get('all_ready', False)
                    if all_ready:
                        user_results[username].append(f"M{market_num}:STARTED")
                        print(f"  {username}: ✓ (trading started)")
                    else:
                        user_results[username].append(f"M{market_num}:WAITING")
                        print(f"  {username}: ⏳ (waiting for others)")
                elif "Maximum" in str(result):
                    user_results[username].append(f"M{market_num}:MAX")
                    print(f"  {username}: MAX (no cohort space)")
                else:
                    user_results[username].append(f"M{market_num}:ERR")
                    print(f"  {username}: ✗ {msg}")
                
                await asyncio.sleep(0.1)  # Small delay between joins
            
            # Wait for market to complete
            print(f"\nWaiting 20 seconds for Market {market_num} to complete...")
            await asyncio.sleep(20)
        
        # ===== RESULTS =====
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        
        # Check parameter_history.json
        print("\n--- Checking parameter_history.json ---")
        if PARAM_HISTORY_PATH.exists():
            with open(PARAM_HISTORY_PATH) as f:
                history = json.load(f)
            
            # Find market_start entries for this test
            import time
            cutoff_time = time.time() - 90  # Last 90 seconds (one test run)
            market_starts = [
                (ts, entry) for ts, entry in history.items()
                if entry.get("source") == "market_start"
                and any(f"p{i}" in str(entry.get("participants", [])) for i in range(13))
                and entry.get("unix_timestamp", 0) > cutoff_time
            ]
            
            # Group by session_id
            by_session = {}
            for ts, entry in sorted(market_starts, key=lambda x: x[0]):
                sid = entry.get('session_id', 'unknown')
                if sid not in by_session:
                    by_session[sid] = []
                by_session[sid].append(entry)
            
            print(f"\nUnique sessions: {len(by_session)}")
            print(f"Total markets: {len(market_starts)}")
            print(f"Expected: 4 sessions, 12 markets (4 cohorts × 3 markets)")
            
            # Verify cohort consistency
            print("\n--- Cohort Consistency Check ---")
            cohort_members = {}
            for session_id, markets in by_session.items():
                # Get participants from first market
                first_participants = set(markets[0]['participants'])
                cohort_members[session_id] = first_participants
                
                # Check all markets have same participants
                all_same = True
                for m in markets:
                    if set(m['participants']) != first_participants:
                        all_same = False
                        break
                
                status = "✓" if all_same else "✗"
                print(f"\n  Session: {session_id}")
                print(f"    Members: {sorted(first_participants)}")
                print(f"    Markets: {len(markets)}")
                print(f"    Consistent: {status}")
                
                for m in markets:
                    print(f"      - {m['market_id'].split('_')[-1]}: {m['participants']} ({m.get('treatment_name', 'N/A')})")
            
            # Check for leftover user
            print("\n--- Leftover User Check ---")
            all_participants = set()
            for members in cohort_members.values():
                all_participants.update(members)
            
            leftover = set(all_users) - all_participants
            print(f"Users in cohorts: {sorted(all_participants)}")
            print(f"Leftover users: {sorted(leftover)}")
            
            if len(leftover) == 1:
                print("✓ Exactly 1 leftover user (as expected with 13 users, cohorts of 3)")
            else:
                print(f"✗ Expected 1 leftover, got {len(leftover)}")
            
            # Summary per user
            print("\n--- User Summary ---")
            for user in sorted(all_users):
                results = user_results[user]
                in_cohort = user in all_participants
                print(f"  {user}: {results} {'(in cohort)' if in_cohort else '(leftover)'}")
        
        print("\n" + "="*70)
        print("Test completed")
        print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
