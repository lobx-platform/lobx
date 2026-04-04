#!/usr/bin/env python3
"""
Analysis of lab trading experiment (2026-04-01).
33 sessions, 30 complete (6 markets each), 3 incomplete.
Single treatment: informed_trade_intensity=0.69.
Each market: 1 informed buyer (goal=80), 1 noise trader, 1 human speculator.
Human may not trade in every market (0 trades = valid observation).
"""

import os
import re
import json
import glob
import warnings
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

BASE_DIR = '/Users/kaliwu/code/RHUL/trading_platform/experiment_logs_20260401'
OUT_DIR = os.path.join(BASE_DIR, 'analysis')
QUEST_DIR = os.path.join(BASE_DIR, 'questionnaire')
os.makedirs(OUT_DIR, exist_ok=True)

INITIAL_MID = 100.0

# ── Log parsing ──────────────────────────────────────────────────────────────

def parse_timestamp(ts_str):
    return datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S,%f')

ADD_RE = re.compile(
    r"^(.+?) - INFO - ADD_ORDER: \{.*?'id': '(.+?)'.*?'price': ([\d.]+).*?"
    r"'order_type': <OrderType\.(BID|ASK).*?'trader_id': '(.+?)'.*?\}$"
)
MATCH_RE = re.compile(
    r"^(.+?) - INFO - MATCHED_ORDER: \{.*?'bid_order_id': '(.+?)'.*?"
    r"'ask_order_id': '(.+?)'.*?'transaction_price': ([\d.]+).*?'amount': ([\d.]+).*?\}$"
)

def parse_log(filepath):
    orders_by_id = {}
    matches = []
    trader_ids_seen = set()

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = ADD_RE.match(line)
            if m:
                ts_str, oid, price, otype, tid = m.groups()
                ts = parse_timestamp(ts_str)
                orders_by_id[oid] = {
                    'trader_id': tid, 'price': float(price),
                    'order_type': otype, 'timestamp': ts,
                }
                trader_ids_seen.add(tid)
                continue
            m = MATCH_RE.match(line)
            if m:
                ts_str, bid_id, ask_id, tx_price, amount = m.groups()
                ts = parse_timestamp(ts_str)
                matches.append({
                    'bid_id': bid_id, 'ask_id': ask_id,
                    'price': float(tx_price), 'amount': float(amount),
                    'timestamp': ts,
                })

    # Find human trader_id (anything not BOOK_INITIALIZER/INFORMED/NOISE)
    human_id = None
    for tid in trader_ids_seen:
        if tid not in ('BOOK_INITIALIZER', 'INFORMED_1', 'NOISE_1'):
            human_id = tid
            break

    return orders_by_id, matches, human_id, trader_ids_seen


def get_trader_for_order(order_id, orders_by_id):
    if order_id in orders_by_id:
        return orders_by_id[order_id]['trader_id']
    parts = order_id.rsplit('_', 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return order_id


def analyze_market(filepath, known_human_id=None):
    """Analyze a single market. known_human_id used if human placed 0 orders."""
    orders_by_id, matches, detected_human, _ = parse_log(filepath)
    human_id = detected_human or known_human_id

    if not matches:
        return None

    market_start = matches[0]['timestamp']
    market_end = matches[-1]['timestamp']
    market_duration = (market_end - market_start).total_seconds()

    human_trades = []
    informed_trades = []
    all_trades = []

    for m in matches:
        ts, price, amount = m['timestamp'], m['price'], m['amount']
        bid_trader = get_trader_for_order(m['bid_id'], orders_by_id)
        ask_trader = get_trader_for_order(m['ask_id'], orders_by_id)
        all_trades.append((ts, price))

        if human_id:
            if bid_trader == human_id:
                human_trades.append({'timestamp': ts, 'side': 'buy', 'price': price, 'amount': amount})
            elif ask_trader == human_id:
                human_trades.append({'timestamp': ts, 'side': 'sell', 'price': price, 'amount': amount})

        if bid_trader.startswith('INFORMED'):
            informed_trades.append({'timestamp': ts, 'price': price, 'amount': amount, 'side': 'buy'})
        elif ask_trader.startswith('INFORMED'):
            informed_trades.append({'timestamp': ts, 'price': price, 'amount': amount, 'side': 'sell'})

    n_human_trades = len(human_trades)
    human_buys = [t for t in human_trades if t['side'] == 'buy']
    human_sells = [t for t in human_trades if t['side'] == 'sell']
    n_buys, n_sells = len(human_buys), len(human_sells)

    inventory = sum(t['amount'] for t in human_buys) - sum(t['amount'] for t in human_sells)

    cash_in = sum(t['price'] * t['amount'] for t in human_sells)
    cash_out = sum(t['price'] * t['amount'] for t in human_buys)
    final_price = all_trades[-1][1] if all_trades else INITIAL_MID
    pnl = cash_in - cash_out + inventory * final_price

    start_price = all_trades[0][1] if all_trades else INITIAL_MID
    end_price = final_price
    total_move = end_price - INITIAL_MID

    # Time to 50% of price move
    if abs(total_move) > 0.5:
        half_target = INITIAL_MID + total_move * 0.5
        time_to_half = None
        for ts, price in all_trades:
            if (total_move > 0 and price >= half_target) or \
               (total_move < 0 and price <= half_target):
                time_to_half = (ts - market_start).total_seconds()
                break
    else:
        time_to_half = None

    # Response times
    response_times = []
    informed_times = [t['timestamp'] for t in informed_trades]
    for ht in [t['timestamp'] for t in human_trades]:
        prev = [it for it in informed_times if it < ht]
        if prev:
            rt = (ht - max(prev)).total_seconds()
            if rt < 30:
                response_times.append(rt)

    # Timing fractions
    human_timing = []
    if market_duration > 0:
        for t in human_trades:
            elapsed = (t['timestamp'] - market_start).total_seconds()
            human_timing.append(elapsed / market_duration)

    return {
        'human_id': human_id,
        'n_human_trades': n_human_trades,
        'n_buys': n_buys, 'n_sells': n_sells,
        'inventory': inventory, 'pnl': pnl,
        'start_price': start_price, 'end_price': end_price,
        'total_move': total_move, 'time_to_half': time_to_half,
        'market_duration': market_duration,
        'response_times': response_times,
        'human_timing': human_timing,
        'human_buy_prices': [t['price'] for t in human_buys],
        'human_sell_prices': [t['price'] for t in human_sells],
        'n_informed_trades': len(informed_trades),
    }


# ── Load all sessions ────────────────────────────────────────────────────────

print("=" * 80)
print("LAB EXPERIMENT ANALYSIS — 2026-04-01")
print("=" * 80)

log_files = sorted(glob.glob(os.path.join(BASE_DIR, 'SESSION_*.log')))
print(f"\nFound {len(log_files)} log files")

sessions = defaultdict(dict)
for f in log_files:
    m = re.match(r'(SESSION_\d+_[a-f0-9]+)_MARKET_(\d+)\.log', os.path.basename(f))
    if m:
        sessions[m.group(1)][int(m.group(2))] = f

complete = {sid: mkts for sid, mkts in sessions.items() if len(mkts) == 6}
incomplete = {sid: mkts for sid, mkts in sessions.items() if len(mkts) < 6}
print(f"Sessions: {len(sessions)} total, {len(complete)} complete, {len(incomplete)} incomplete")
print(f"Incomplete: {', '.join(f'{sid[-20:]} ({len(m)} mkts)' for sid, m in incomplete.items())}")

# Discover human_id per session (scan all markets)
print("\nDiscovering human IDs per session...")
session_human_ids = {}
for sid, mkts in sessions.items():
    for mkt_num in sorted(mkts.keys()):
        _, _, hid, _ = parse_log(mkts[mkt_num])
        if hid:
            session_human_ids[sid] = hid
            break

sessions_with_humans = {sid for sid in complete if sid in session_human_ids}
sessions_no_humans = {sid for sid in complete if sid not in session_human_ids}
print(f"Complete sessions with identified human: {len(sessions_with_humans)}")
print(f"Complete sessions with NO human trades at all: {len(sessions_no_humans)}")
if sessions_no_humans:
    for sid in sessions_no_humans:
        print(f"  - {sid}")

# Parse all complete sessions with humans
print("\nParsing logs...")
session_data = {}
for sid in sorted(sessions_with_humans):
    hid = session_human_ids[sid]
    session_data[sid] = {}
    for mkt in range(6):
        result = analyze_market(complete[sid][mkt], known_human_id=hid)
        if result:
            session_data[sid][mkt] = result

valid_sessions = {sid: data for sid, data in session_data.items() if len(data) == 6}
print(f"Valid sessions (6 parseable markets): {len(valid_sessions)}")

# ══════════════════════════════════════════════════════════════════════════════
# 1. PER-PARTICIPANT SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("1. PER-PARTICIPANT SUMMARY ACROSS 6 MARKETS")
print("=" * 80)

print(f"\n{'Session':<24} {'Human ID':<16} | " + " | ".join([f"    Mkt {i}    " for i in range(6)]) + " |   TOTAL")
print("-" * 170)

participant_summaries = []
for sid in sorted(valid_sessions.keys()):
    hid = session_human_ids.get(sid, '?')
    parts = []
    total_pnl = 0
    total_trades = 0
    for mkt in range(6):
        d = valid_sessions[sid][mkt]
        parts.append(f"{d['n_human_trades']:2d}t {d['pnl']:+6.1f} {d['inventory']:+3.0f}i")
        total_pnl += d['pnl']
        total_trades += d['n_human_trades']
    participant_summaries.append({
        'session': sid, 'human_id': hid,
        'total_pnl': total_pnl, 'total_trades': total_trades
    })
    short_sid = sid.split('_', 1)[1] if '_' in sid else sid
    print(f"{short_sid:<24} {hid:<16} | " + " | ".join(parts) + f" | {total_trades:3d}t {total_pnl:+7.1f}")

total_pnls = [p['total_pnl'] for p in participant_summaries]
print(f"\nAggregate across {len(valid_sessions)} participants:")
print(f"  Mean total PnL (6 mkts): {np.mean(total_pnls):+.1f} (std={np.std(total_pnls):.1f})")
print(f"  Median total PnL: {np.median(total_pnls):+.1f}")
print(f"  Range: [{min(total_pnls):+.1f}, {max(total_pnls):+.1f}]")
print(f"  Profitable participants: {sum(1 for p in total_pnls if p > 0)}/{len(total_pnls)}")

# ══════════════════════════════════════════════════════════════════════════════
# 2. LEARNING EFFECTS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("2. LEARNING EFFECTS BY MARKET NUMBER")
print("=" * 80)

by_market = {m: {'trades': [], 'pnl': [], 'abs_inv': []} for m in range(6)}
for sid in valid_sessions:
    for mkt in range(6):
        d = valid_sessions[sid][mkt]
        by_market[mkt]['trades'].append(d['n_human_trades'])
        by_market[mkt]['pnl'].append(d['pnl'])
        by_market[mkt]['abs_inv'].append(abs(d['inventory']))

print(f"\n{'Mkt':<5} {'N':>3} {'Avg Trades':>10} {'Avg PnL':>10} {'Med PnL':>10} {'Avg |Inv|':>10}")
print("-" * 50)
for mkt in range(6):
    n = len(by_market[mkt]['trades'])
    print(f"  {mkt:<3} {n:>3} {np.mean(by_market[mkt]['trades']):>10.1f} "
          f"{np.mean(by_market[mkt]['pnl']):>+10.1f} "
          f"{np.median(by_market[mkt]['pnl']):>+10.1f} "
          f"{np.mean(by_market[mkt]['abs_inv']):>10.1f}")

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
markets = list(range(6))

for ax, key, ylabel, title, color in [
    (axes[0], 'trades', 'Number of Trades', 'Avg Human Trades per Market', 'steelblue'),
    (axes[1], 'pnl', 'PnL (Liras)', 'Avg Human PnL per Market', 'seagreen'),
    (axes[2], 'abs_inv', '|Inventory Imbalance|', 'Avg Absolute Inventory Imbalance', 'coral'),
]:
    means = [np.mean(by_market[m][key]) for m in markets]
    sems = [np.std(by_market[m][key]) / np.sqrt(len(by_market[m][key])) for m in markets]
    ax.bar(markets, means, yerr=sems, capsize=4, color=color, alpha=0.8)
    if key == 'pnl':
        ax.axhline(0, color='black', linewidth=0.5, linestyle='--')
    ax.set_xlabel('Market Number')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(markets)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'learning_effects.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f"\nSaved: {OUT_DIR}/learning_effects.png")

# ══════════════════════════════════════════════════════════════════════════════
# 3. PRICE DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("3. PRICE DISCOVERY")
print("=" * 80)

time_to_half_by_market = {m: [] for m in range(6)}
end_prices = {m: [] for m in range(6)}
total_moves = {m: [] for m in range(6)}

for sid in valid_sessions:
    for mkt in range(6):
        d = valid_sessions[sid][mkt]
        end_prices[mkt].append(d['end_price'])
        total_moves[mkt].append(d['total_move'])
        if d['time_to_half'] is not None:
            time_to_half_by_market[mkt].append(d['time_to_half'])

# Also compute overall time_to_half
all_t_half = []
for m in range(6):
    all_t_half.extend(time_to_half_by_market[m])

print(f"\n{'Mkt':<5} {'Avg End$':>9} {'Avg Move':>9} {'Avg t_half':>11} {'N t_half':>9}")
print("-" * 46)
for mkt in range(6):
    avg_end = np.mean(end_prices[mkt])
    avg_move = np.mean(total_moves[mkt])
    th = time_to_half_by_market[mkt]
    avg_th = np.mean(th) if th else float('nan')
    print(f"  {mkt:<3} {avg_end:>9.1f} {avg_move:>+9.1f} {avg_th:>11.1f}s {len(th):>9}")

print(f"\nOverall time to 50% price discovery: mean={np.mean(all_t_half):.1f}s, "
      f"median={np.median(all_t_half):.1f}s (N={len(all_t_half)})")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

ax = axes[0]
data_box = [time_to_half_by_market[m] if time_to_half_by_market[m] else [0] for m in markets]
bp = ax.boxplot(data_box, positions=markets, widths=0.6, patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('lightblue')
ax.set_xlabel('Market Number')
ax.set_ylabel('Time to 50% Price Move (s)')
ax.set_title('Price Discovery Speed')
ax.set_xticks(markets)

ax = axes[1]
for mkt in markets:
    ax.scatter([mkt] * len(end_prices[mkt]), end_prices[mkt], alpha=0.3, s=20, color='steelblue')
ax.plot(markets, [np.mean(end_prices[m]) for m in markets], 'ro-', markersize=8, label='Mean')
ax.axhline(INITIAL_MID, color='gray', linestyle='--', label=f'Initial mid ({INITIAL_MID})')
ax.set_xlabel('Market Number')
ax.set_ylabel('End Price')
ax.set_title('Final Prices by Market')
ax.set_xticks(markets)
ax.legend()

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'price_discovery.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {OUT_DIR}/price_discovery.png")

# ══════════════════════════════════════════════════════════════════════════════
# 4. HUMAN TRADING PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("4. HUMAN TRADING PATTERNS")
print("=" * 80)

all_buys = all_sells = 0
all_response_times = []
all_timing = []
buy_sell_by_market = {m: {'buys': 0, 'sells': 0} for m in range(6)}

for sid in valid_sessions:
    for mkt in range(6):
        d = valid_sessions[sid][mkt]
        all_buys += d['n_buys']
        all_sells += d['n_sells']
        buy_sell_by_market[mkt]['buys'] += d['n_buys']
        buy_sell_by_market[mkt]['sells'] += d['n_sells']
        all_response_times.extend(d['response_times'])
        all_timing.extend(d['human_timing'])

total_ht = all_buys + all_sells
print(f"\nOverall human trades: {total_ht} ({all_buys} buys, {all_sells} sells)")
if total_ht > 0:
    print(f"Buy fraction: {all_buys/total_ht:.1%}")
print(f"\nInformed trader consistently BUYS -> buying = WITH informed, selling = AGAINST")

print(f"\nBuy/Sell by market:")
for mkt in range(6):
    b, s = buy_sell_by_market[mkt]['buys'], buy_sell_by_market[mkt]['sells']
    t = b + s
    pct = f"{b/t:.1%}" if t else "N/A"
    print(f"  Mkt {mkt}: {b:3d} buys, {s:3d} sells (buy%={pct})")

if all_response_times:
    rt = np.array(all_response_times)
    print(f"\nResponse time after informed trade (<30s window):")
    print(f"  N={len(rt)}, Mean={np.mean(rt):.2f}s, Median={np.median(rt):.2f}s, "
          f"P25={np.percentile(rt,25):.2f}s, P75={np.percentile(rt,75):.2f}s")

if all_timing:
    timing = np.array(all_timing)
    t1 = np.sum(timing < 1/3)
    t2 = np.sum((timing >= 1/3) & (timing < 2/3))
    t3 = np.sum(timing >= 2/3)
    tt = len(timing)
    print(f"\nHuman trade timing (fraction of market elapsed):")
    print(f"  First third:  {t1:3d} ({t1/tt:.1%})")
    print(f"  Middle third: {t2:3d} ({t2/tt:.1%})")
    print(f"  Last third:   {t3:3d} ({t3/tt:.1%})")

# Trading direction over time (do humans learn to trade with the informed?)
buy_frac_by_mkt = []
for mkt in range(6):
    b, s = buy_sell_by_market[mkt]['buys'], buy_sell_by_market[mkt]['sells']
    t = b + s
    buy_frac_by_mkt.append(b / t if t > 0 else 0.5)

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Buy vs sell by market
ax = axes[0, 0]
x = np.arange(6)
w = 0.35
ax.bar(x - w/2, [buy_sell_by_market[m]['buys'] for m in range(6)], w,
       label='Buys (with informed)', color='green', alpha=0.7)
ax.bar(x + w/2, [buy_sell_by_market[m]['sells'] for m in range(6)], w,
       label='Sells (against informed)', color='red', alpha=0.7)
ax.set_xlabel('Market Number')
ax.set_ylabel('Total Trades')
ax.set_title('Human Buy vs Sell by Market')
ax.set_xticks(x)
ax.legend()

# Response time histogram
ax = axes[0, 1]
if all_response_times:
    ax.hist(all_response_times, bins=30, color='steelblue', alpha=0.8, edgecolor='white')
    ax.axvline(np.median(all_response_times), color='red', linestyle='--',
               label=f'Median={np.median(all_response_times):.1f}s')
    ax.set_xlabel('Response Time (seconds)')
    ax.set_ylabel('Count')
    ax.set_title('Response Time After Informed Trade')
    ax.legend()

# Trade timing
ax = axes[1, 0]
if all_timing:
    ax.hist(all_timing, bins=20, color='coral', alpha=0.8, edgecolor='white')
    ax.axvline(1/3, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(2/3, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel('Fraction of Market Elapsed')
    ax.set_ylabel('Number of Trades')
    ax.set_title('When Do Humans Trade?')

# PnL distribution
ax = axes[1, 1]
all_pnl_flat = [valid_sessions[sid][m]['pnl'] for sid in valid_sessions for m in range(6)]
ax.hist(all_pnl_flat, bins=30, color='seagreen', alpha=0.8, edgecolor='white')
ax.axvline(0, color='black', linestyle='--', linewidth=0.5)
ax.axvline(np.mean(all_pnl_flat), color='red', linestyle='--',
           label=f'Mean={np.mean(all_pnl_flat):+.1f}')
ax.set_xlabel('PnL per Market')
ax.set_ylabel('Count')
ax.set_title('Distribution of Per-Market PnL')
ax.legend()

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'trading_patterns.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f"\nSaved: {OUT_DIR}/trading_patterns.png")

# Buy fraction trend
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(range(6), buy_frac_by_mkt, 'bo-', markersize=8)
ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5, label='50% (neutral)')
ax.set_xlabel('Market Number')
ax.set_ylabel('Buy Fraction')
ax.set_title('Do Humans Learn to Trade WITH the Informed Buyer?')
ax.set_xticks(range(6))
ax.set_ylim(0, 1)
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'buy_fraction_trend.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {OUT_DIR}/buy_fraction_trend.png")

# ══════════════════════════════════════════════════════════════════════════════
# 5. QUESTIONNAIRE CORRELATION
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("5. QUESTIONNAIRE CORRELATION")
print("=" * 80)

questionnaire_data = {}
for qf in glob.glob(os.path.join(QUEST_DIR, '*.json')):
    with open(qf) as f:
        data = json.load(f)
    tid = data.get('trader_id', '')
    if data.get('postmarket_responses'):
        questionnaire_data[tid] = data['postmarket_responses']

print(f"\nLoaded {len(questionnaire_data)} questionnaire responses with post-market data")

human_to_session = {session_human_ids[sid]: sid for sid in valid_sessions if sid in session_human_ids}

algo_bought, algo_sold, algo_no, algo_unknown = [], [], [], []
matched = 0

for hid, sid in human_to_session.items():
    qdata = questionnaire_data.get(hid)
    if not qdata:
        continue
    matched += 1
    total_pnl = sum(valid_sessions[sid][m]['pnl'] for m in range(6))
    avg_pnl = total_pnl / 6
    avg_trades = np.mean([valid_sessions[sid][m]['n_human_trades'] for m in range(6)])
    avg_abs_inv = np.mean([abs(valid_sessions[sid][m]['inventory']) for m in range(6)])
    n_buys = sum(valid_sessions[sid][m]['n_buys'] for m in range(6))
    n_sells = sum(valid_sessions[sid][m]['n_sells'] for m in range(6))
    buy_frac = n_buys / (n_buys + n_sells) if (n_buys + n_sells) > 0 else 0.5

    entry = {'hid': hid, 'total_pnl': total_pnl, 'avg_pnl': avg_pnl,
             'avg_trades': avg_trades, 'avg_abs_inv': avg_abs_inv, 'buy_frac': buy_frac}

    md = qdata.get('market_description', '').lower()
    if 'bought' in md:
        algo_bought.append(entry)
    elif 'sold' in md:
        algo_sold.append(entry)
    elif 'no_algo' in md:
        algo_no.append(entry)
    else:
        algo_unknown.append(entry)

print(f"Matched questionnaires to valid sessions: {matched}")
print(f"\nAlgo identification:")
print(f"  'algo_bought' (CORRECT - informed buys): {len(algo_bought)}")
print(f"  'algo_sold' (WRONG direction):           {len(algo_sold)}")
print(f"  'no_algo' (didn't detect):               {len(algo_no)}")
print(f"  Other/unknown:                           {len(algo_unknown)}")

for label, group in [('algo_bought (correct)', algo_bought),
                      ('algo_sold (wrong)', algo_sold),
                      ('no_algo', algo_no)]:
    if group:
        pnls = [e['total_pnl'] for e in group]
        trades = [e['avg_trades'] for e in group]
        bfracs = [e['buy_frac'] for e in group]
        print(f"\n  {label} (n={len(group)}):")
        print(f"    Total PnL:     mean={np.mean(pnls):+.1f}, median={np.median(pnls):+.1f}")
        print(f"    Avg trades/mkt: {np.mean(trades):.1f}")
        print(f"    Buy fraction:   {np.mean(bfracs):.2f}")

# Plot
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

ax = axes[0]
groups, labels, colors = [], [], []
for entries, lbl, col in [(algo_bought, f'Bought\n(correct, n={len(algo_bought)})', 'green'),
                           (algo_sold, f'Sold\n(wrong, n={len(algo_sold)})', 'red'),
                           (algo_no, f'No algo\n(n={len(algo_no)})', 'gray')]:
    if entries:
        groups.append([e['total_pnl'] for e in entries])
        labels.append(lbl)
        colors.append(col)

if groups:
    bp = ax.boxplot(groups, positions=range(len(groups)), widths=0.6, patch_artist=True)
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.4)
    ax.set_xticklabels(labels)
    ax.axhline(0, color='black', linestyle='--', linewidth=0.5)
    ax.set_ylabel('Total PnL (6 markets)')
    ax.set_title('PnL by Algo Direction Identification')

ax = axes[1]
for entries, color, label in [(algo_bought, 'green', 'Correct (bought)'),
                               (algo_sold, 'red', 'Wrong (sold)'),
                               (algo_no, 'gray', 'No algo')]:
    if entries:
        ax.scatter([e['avg_trades'] for e in entries],
                   [e['avg_pnl'] for e in entries],
                   c=color, alpha=0.6, s=80, label=label, edgecolors='black', linewidth=0.5)
ax.axhline(0, color='black', linestyle='--', linewidth=0.5)
ax.set_xlabel('Avg Trades per Market')
ax.set_ylabel('Avg PnL per Market')
ax.set_title('Trading Activity vs Performance by Algo Identification')
ax.legend()

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'questionnaire_correlation.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f"\nSaved: {OUT_DIR}/questionnaire_correlation.png")

# ══════════════════════════════════════════════════════════════════════════════
# SAMPLE PRICE TRAJECTORIES (all 6 markets for 2 participants)
# ══════════════════════════════════════════════════════════════════════════════

n_samples = min(3, len(valid_sessions))
sample_sids = sorted(valid_sessions.keys())[:n_samples]

for idx, sid in enumerate(sample_sids):
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    hid = session_human_ids.get(sid, '?')

    for mkt in range(6):
        ax = axes[mkt // 3][mkt % 3]
        orders_by_id, matches, _, _ = parse_log(complete[sid][mkt])

        if not matches:
            continue

        t0 = matches[0]['timestamp']
        for m in matches:
            t = (m['timestamp'] - t0).total_seconds()
            p = m['price']
            bid_t = get_trader_for_order(m['bid_id'], orders_by_id)
            ask_t = get_trader_for_order(m['ask_id'], orders_by_id)

            if bid_t == hid or ask_t == hid:
                ax.plot(t, p, 'go', markersize=7, zorder=3)
            elif bid_t.startswith('INFORMED') or ask_t.startswith('INFORMED'):
                ax.plot(t, p, 'r^', markersize=4, zorder=2, alpha=0.6)
            else:
                ax.plot(t, p, 'b.', markersize=3, zorder=1, alpha=0.3)

        times = [(m['timestamp'] - t0).total_seconds() for m in matches]
        prices = [m['price'] for m in matches]
        ax.plot(times, prices, 'k-', alpha=0.1, linewidth=0.5)
        ax.axhline(INITIAL_MID, color='gray', linestyle='--', alpha=0.4)
        ax.set_title(f'Market {mkt} (PnL={valid_sessions[sid][mkt]["pnl"]:+.0f})')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Price')

    fig.suptitle(f'{hid} -- green=human, red=informed, blue=noise', fontsize=13, y=1.01)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, f'trajectories_{hid}.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {OUT_DIR}/trajectories_{hid}.png")

# ══════════════════════════════════════════════════════════════════════════════
# FRONT-RUNNING & NET DIRECTION
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("FRONT-RUNNING & DIRECTIONAL ANALYSIS")
print("=" * 80)

profitable_buys = total_buys_analyzed = 0
for sid in valid_sessions:
    for mkt in range(6):
        d = valid_sessions[sid][mkt]
        for bp in d['human_buy_prices']:
            total_buys_analyzed += 1
            if bp < d['end_price']:
                profitable_buys += 1

if total_buys_analyzed:
    print(f"\nBuys below final price (would be profitable if held): "
          f"{profitable_buys}/{total_buys_analyzed} ({profitable_buys/total_buys_analyzed:.1%})")

net_buyers = net_sellers = balanced = 0
for sid in valid_sessions:
    tb = sum(valid_sessions[sid][m]['n_buys'] for m in range(6))
    ts = sum(valid_sessions[sid][m]['n_sells'] for m in range(6))
    if tb > ts + 2:
        net_buyers += 1
    elif ts > tb + 2:
        net_sellers += 1
    else:
        balanced += 1
print(f"\nNet direction per participant:")
print(f"  Net buyers (with informed):    {net_buyers}")
print(f"  Net sellers (against informed): {net_sellers}")
print(f"  Balanced (+/-2):                {balanced}")

# ══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL PARTICIPANT HEATMAP
# ══════════════════════════════════════════════════════════════════════════════

fig, ax = plt.subplots(figsize=(10, max(6, len(valid_sessions) * 0.4)))
pnl_matrix = []
ylabels = []
for sid in sorted(valid_sessions.keys()):
    hid = session_human_ids.get(sid, sid[-8:])
    row = [valid_sessions[sid][m]['pnl'] for m in range(6)]
    pnl_matrix.append(row)
    ylabels.append(hid)

pnl_arr = np.array(pnl_matrix)
vmax = max(abs(pnl_arr.min()), abs(pnl_arr.max()))
im = ax.imshow(pnl_arr, cmap='RdYlGn', aspect='auto', vmin=-vmax, vmax=vmax)
ax.set_xticks(range(6))
ax.set_xticklabels([f'Mkt {i}' for i in range(6)])
ax.set_yticks(range(len(ylabels)))
ax.set_yticklabels(ylabels, fontsize=8)
ax.set_title('PnL Heatmap (red=loss, green=profit)')
plt.colorbar(im, ax=ax, label='PnL')

# Add text annotations
for i in range(len(pnl_matrix)):
    for j in range(6):
        val = pnl_matrix[i][j]
        ax.text(j, i, f'{val:+.0f}', ha='center', va='center', fontsize=7,
                color='white' if abs(val) > vmax * 0.6 else 'black')

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'pnl_heatmap.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {OUT_DIR}/pnl_heatmap.png")

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)

all_trades_flat = [valid_sessions[sid][m]['n_human_trades'] for sid in valid_sessions for m in range(6)]
all_pnl_flat = [valid_sessions[sid][m]['pnl'] for sid in valid_sessions for m in range(6)]
all_inv_flat = [abs(valid_sessions[sid][m]['inventory']) for sid in valid_sessions for m in range(6)]
all_end_flat = [valid_sessions[sid][m]['end_price'] for sid in valid_sessions for m in range(6)]

N = len(all_trades_flat)
print(f"\nPer market-session (N={N} observations from {len(valid_sessions)} participants):")
print(f"  Trades: mean={np.mean(all_trades_flat):.1f}, median={np.median(all_trades_flat):.0f}, "
      f"std={np.std(all_trades_flat):.1f}, range=[{min(all_trades_flat)}, {max(all_trades_flat)}]")
print(f"  PnL: mean={np.mean(all_pnl_flat):+.1f}, median={np.median(all_pnl_flat):+.1f}, "
      f"std={np.std(all_pnl_flat):.1f}")
print(f"  |Inventory|: mean={np.mean(all_inv_flat):.1f}, median={np.median(all_inv_flat):.0f}")
print(f"  End price: mean={np.mean(all_end_flat):.1f} (avg move from 100: {np.mean(all_end_flat)-100:+.1f})")
print(f"  Markets with 0 human trades: {sum(1 for t in all_trades_flat if t == 0)}/{N}")

if all_response_times:
    print(f"\nResponse times (N={len(all_response_times)}):")
    print(f"  Mean={np.mean(all_response_times):.2f}s, Median={np.median(all_response_times):.2f}s")

print(f"\n{'='*80}")
print("Charts saved to:")
for f in sorted(os.listdir(OUT_DIR)):
    if f.endswith('.png'):
        print(f"  {OUT_DIR}/{f}")
print(f"{'='*80}")
