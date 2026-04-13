#!/usr/bin/env python3
"""Test treatment sequence for per-market trader configurations"""

import asyncio
import aiohttp
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

SAMPLE_YAML = """
treatments:
  - name: "1"
    num_noise_traders: 5
    num_informed_traders: 0

  - name: "2"
    num_noise_traders: 3
    num_informed_traders: 1

  - name: "3"
    num_noise_traders: 2
    num_informed_traders: 2
"""


async def upload_treatments(session, yaml_content):
    async with session.post(f"{BACKEND_URL}/admin/update_treatments", 
                           json={"yaml_content": yaml_content}) as resp:
        result = await resp.json()
        return resp.status == 200, result


async def get_treatments(session):
    async with session.get(f"{BACKEND_URL}/admin/get_treatments") as resp:
        return await resp.json() if resp.status == 200 else None


async def get_treatment_for_user(session, username):
    async with session.get(f"{BACKEND_URL}/admin/get_treatment_for_user/{username}") as resp:
        return await resp.json() if resp.status == 200 else None


async def login_user(session, username):
    params = {"PROLIFIC_PID": username, "STUDY_ID": "treatment_test", "SESSION_ID": f"s_{username}"}
    async with session.post(f"{BACKEND_URL}/user/login", params=params,
                           json={"username": "user1", "password": "password1"}) as resp:
        if resp.status == 200:
            result = await resp.json()
            return result.get('data', {}).get('trader_id')
        return None


async def start_trading(session, username):
    params = {"PROLIFIC_PID": username, "STUDY_ID": "treatment_test", "SESSION_ID": f"s_{username}"}
    async with session.post(f"{BACKEND_URL}/trading/start", params=params,
                           json={"username": "user1", "password": "password1"}) as resp:
        return await resp.json() if resp.status == 200 else None


async def get_trader_market(session, trader_id, username):
    params = {"PROLIFIC_PID": username, "STUDY_ID": "treatment_test", "SESSION_ID": f"s_{username}"}
    async with session.get(f"{BACKEND_URL}/trader/{trader_id}/market", params=params) as resp:
        return await resp.json() if resp.status == 200 else None


async def update_settings(session, **kwargs):
    async with session.post(f"{BACKEND_URL}/admin/update_base_settings",
                           json={"settings": kwargs}) as resp:
        return resp.status == 200


async def reset_state(session):
    async with session.post(f"{BACKEND_URL}/admin/reset_state") as resp:
        return resp.status == 200


async def test_treatment_upload():
    print("\n" + "="*60)
    print("Test 1: Upload and retrieve treatments")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        success, result = await upload_treatments(session, SAMPLE_YAML)
        print(f"Upload result: {result}")
        
        if success:
            print(f"✓ Uploaded {len(result.get('treatments', []))} treatments")
            
            treatments = await get_treatments(session)
            if treatments:
                print(f"\nStored treatments:")
                for i, t in enumerate(treatments.get('treatments', [])):
                    print(f"  {i}: {t.get('name')}")
                print(f"\n✓ Retrieved {len(treatments.get('treatments', []))} treatments")
            else:
                print("✗ Failed to retrieve treatments")
        else:
            print(f"✗ Upload failed: {result}")


async def test_treatment_lookup():
    print("\n" + "="*60)
    print("Test 2: Treatment lookup for users")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        await upload_treatments(session, SAMPLE_YAML)
        
        for username in ["new_user", "u0", "u1"]:
            result = await get_treatment_for_user(session, username)
            if result:
                print(f"\n{username}:")
                print(f"  Markets played: {result.get('markets_played')}")
                print(f"  Next treatment index: {result.get('next_treatment_index')}")
                treatment = result.get('next_treatment')
                if treatment:
                    print(f"  Treatment: noise={treatment.get('num_noise_traders')}, "
                          f"informed={treatment.get('num_informed_traders')}")
                else:
                    print("  Treatment: None (will use base settings)")


async def test_treatment_application():
    print("\n" + "="*60)
    print("Test 3: Treatment application in market creation")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        await reset_state(session)
        await upload_treatments(session, SAMPLE_YAML)
        
        await update_settings(
            session,
            predefined_goals=[0],
            trading_day_duration=0.1,
            num_noise_traders=1,
            num_informed_traders=0
        )
        print("Base settings: 1 noise trader")
        
        username = "treatment_test_user"
        trader_id = await login_user(session, username)
        if not trader_id:
            print("✗ Login failed")
            return
        
        print(f"\n✓ Logged in as {username} (trader_id: {trader_id})")
        
        for market_num in range(1, 4):
            print(f"\n--- Market {market_num} ---")
            
            before = await get_treatment_for_user(session, username)
            print(f"Markets played before: {before.get('markets_played')}")
            expected_treatment = before.get('next_treatment')
            if expected_treatment:
                print(f"Expected treatment: noise={expected_treatment.get('num_noise_traders')}")
            
            await start_trading(session, username)
            await asyncio.sleep(0.5)
            
            market_info = await get_trader_market(session, trader_id, username)
            if market_info and market_info.get('status') == 'success':
                traders = market_info.get('data', {}).get('traders', [])
                noise_count = sum(1 for t in traders if t.startswith('NOISE_'))
                informed_count = sum(1 for t in traders if t.startswith('INFORMED_'))
                print(f"Actual traders: noise={noise_count}, informed={informed_count}")
                
                if expected_treatment:
                    expected_noise = expected_treatment.get('num_noise_traders', 1)
                    if noise_count == expected_noise:
                        print(f"✓ Treatment applied correctly")
                    else:
                        print(f"✗ Mismatch: expected {expected_noise} noise, got {noise_count}")
            else:
                print(f"Market info status: {market_info.get('status') if market_info else 'None'}")
            
            await asyncio.sleep(10)
            await login_user(session, username)
        
        await reset_state(session)
        print("\n✓ State reset")


async def test_yaml_file_sync():
    print("\n" + "="*60)
    print("Test 4: YAML file synchronization")
    print("="*60)
    
    import os
    yaml_path = "config/treatments.yaml"
    
    async with aiohttp.ClientSession() as session:
        await upload_treatments(session, SAMPLE_YAML)
        
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as f:
                content = f.read()
            print(f"✓ YAML file exists at {yaml_path}")
            print(f"Content preview:\n{content[:300]}...")
        else:
            print(f"✗ YAML file not found at {yaml_path}")


async def main():
    print("\n" + "="*60)
    print("Treatment Sequence Tests")
    print("="*60)
    
    await test_treatment_upload()
    await test_treatment_lookup()
    await test_yaml_file_sync()
    await test_treatment_application()
    
    print("\n" + "="*60)
    print("All tests completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
