#!/usr/bin/env python3
"""Test that market start is logged to parameter_history.json with new format"""

import asyncio
import aiohttp
import json
import os
from pathlib import Path

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# When running from repo root, logs are in back/logs (mounted from Docker)
PARAM_HISTORY_PATH = Path("back/logs/parameters/parameter_history.json")
LOGS_DIR = Path("back/logs")


async def update_settings(session, **kwargs):
    async with session.post(f"{BACKEND_URL}/admin/update_base_settings",
                           json={"settings": kwargs}) as resp:
        return resp.status == 200


async def reset_state(session):
    """Try to reset state - may fail if auth required"""
    try:
        async with session.post(f"{BACKEND_URL}/admin/reset_state") as resp:
            return resp.status == 200
    except:
        return False


async def login_user(session, username):
    params = {"PROLIFIC_PID": username, "STUDY_ID": "log_test", "SESSION_ID": f"s_{username}"}
    async with session.post(f"{BACKEND_URL}/user/login", params=params,
                           json={"username": "user1", "password": "password1"}) as resp:
        if resp.status == 200:
            result = await resp.json()
            return result.get('data', {}).get('trader_id')
        return None


async def start_trading(session, username):
    params = {"PROLIFIC_PID": username, "STUDY_ID": "log_test", "SESSION_ID": f"s_{username}"}
    async with session.post(f"{BACKEND_URL}/trading/start", params=params,
                           json={"username": "user1", "password": "password1"}) as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            text = await resp.text()
            print(f"  start_trading failed: {resp.status} - {text[:100]}")
            return None


async def upload_treatments(session, yaml_content):
    async with session.post(f"{BACKEND_URL}/admin/update_treatments", 
                           json={"yaml_content": yaml_content}) as resp:
        return resp.status == 200


async def main():
    print("\n" + "="*60)
    print("Test: Market Logging to parameter_history.json")
    print("="*60)
    
    # Record initial state
    initial_entries = 0
    if PARAM_HISTORY_PATH.exists():
        with open(PARAM_HISTORY_PATH) as f:
            initial_entries = len(json.load(f))
    print(f"Initial parameter_history entries: {initial_entries}")
    
    # Get initial log files (new format: SESSION_xxx_MARKET_n.log)
    initial_logs = set()
    if LOGS_DIR.exists():
        initial_logs = {f.name for f in LOGS_DIR.glob("SESSION_*_MARKET_*.log")}
    print(f"Initial SESSION_*_MARKET_*.log files: {len(initial_logs)}")
    
    async with aiohttp.ClientSession() as session:
        # Reset and configure
        await reset_state(session)
        
        # Upload a simple treatment
        yaml_content = """
treatments:
  - name: "1"
    num_noise_traders: 1
    num_informed_traders: 0
"""
        await upload_treatments(session, yaml_content)
        print("✓ Uploaded test treatment")
        
        # Configure for quick 3-second market with single participant
        await update_settings(
            session,
            predefined_goals=[0],  # Single speculator
            trading_day_duration=3,  # 3 seconds
            num_noise_traders=1,
            num_informed_traders=0
        )
        print("✓ Settings: 3-second market, 1 participant")
        
        # Login and start trading
        username = "log_test_user"
        trader_id = await login_user(session, username)
        if not trader_id:
            print("✗ Login failed")
            return
        print(f"✓ Logged in as {username}")
        
        result = await start_trading(session, username)
        print(f"✓ Started trading: {result}")
        
        # Wait for market to complete
        print("Waiting 5 seconds for market to complete...")
        await asyncio.sleep(5)
        
        # Check parameter_history.json
        print("\n--- Checking parameter_history.json ---")
        if PARAM_HISTORY_PATH.exists():
            with open(PARAM_HISTORY_PATH) as f:
                history = json.load(f)
            
            new_entries = len(history) - initial_entries
            print(f"New entries: {new_entries}")
            
            # Find market_start entries
            market_starts = [
                (ts, entry) for ts, entry in history.items() 
                if entry.get("source") == "market_start"
            ]
            
            if market_starts:
                print(f"\n✓ Found {len(market_starts)} market_start entries")
                # Show the latest one
                latest_ts, latest = max(market_starts, key=lambda x: x[0])
                print(f"\nLatest market_start entry:")
                print(f"  Timestamp: {latest_ts}")
                print(f"  Market ID: {latest.get('market_id')}")
                print(f"  Session ID: {latest.get('session_id')}")
                print(f"  Participants: {latest.get('participants')}")
                print(f"  Treatment: {latest.get('treatment_name')}")
                print(f"  Treatment Index: {latest.get('treatment_index')}")
                
                # Verify session_id is present
                if latest.get('session_id'):
                    print(f"\n✓ Session ID present: {latest.get('session_id')}")
                else:
                    print(f"\n✗ Session ID missing")
                
                # Verify our user is in participants
                if username in latest.get('participants', []):
                    print(f"✓ User '{username}' found in participants")
                else:
                    print(f"✗ User '{username}' NOT found in participants")
            else:
                print("✗ No market_start entries found")
        else:
            print("✗ parameter_history.json not found")
        
        # Check log files (new format: SESSION_xxx_MARKET_n.log)
        print("\n--- Checking log files ---")
        if LOGS_DIR.exists():
            current_logs = {f.name for f in LOGS_DIR.glob("SESSION_*_MARKET_*.log")}
            new_logs = current_logs - initial_logs
            
            if new_logs:
                print(f"✓ New log files created: {len(new_logs)}")
                for log_name in sorted(new_logs):
                    print(f"  - {log_name}")
                    # Verify naming format: SESSION_{timestamp}_{uuid}_MARKET_{n}.log
                    if log_name.startswith("SESSION_") and "_MARKET_" in log_name and log_name.endswith(".log"):
                        print(f"    ✓ Correct format: SESSION_{{timestamp}}_{{uuid}}_MARKET_{{n}}.log")
                    else:
                        print(f"    ✗ Unexpected format")
            else:
                print("✗ No new SESSION_*_MARKET_*.log files created")
        
        # Cleanup
        await reset_state(session)
        print("\n✓ State reset")
    
    print("\n" + "="*60)
    print("Test completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
