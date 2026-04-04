import re
from datetime import datetime
import polars as pl
from typing import Dict, List, Optional
import ast
import json
import io
import csv

def parse_log_line(line: str) -> Optional[Dict]:
    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (\w+): (.+)$', line.strip())
    if not match:
        return None

    timestamp_str, _, message_type, content = match.groups()
    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')

    content = (content.replace('<OrderStatus.BUFFERED: \'buffered\'>', "'BUFFERED'")
                      .replace('<OrderType.BID: 1>', "'BID'")
                      .replace('<OrderType.ASK: -1>', "'ASK'"))

    datetime_match = re.search(r"datetime\.datetime\((\d+, \d+, \d+, \d+, \d+, \d+, \d+)\)", content)
    if datetime_match:
        datetime_str = datetime_match.group(1)
        content = content.replace(datetime_match.group(0), f"'{datetime_str}'")

    content_dict = ast.literal_eval(content)

    if 'timestamp' in content_dict:
        timestamp_parts = [int(part.strip()) for part in content_dict['timestamp'].split(',')]
        content_dict['timestamp'] = datetime(*timestamp_parts)

    return {
        'timestamp': timestamp,
        'message_type': message_type,
        'content': content_dict
    }

def process_message(message: Dict, order_book: Dict[str, Dict[int, int]], timestamp: float) -> Dict:
    price = int(message.get('price', 0))
    size = float(message.get('amount', 0))
    direction = 1 if message.get('order_type') == 'BID' else -1

    if direction == 1:
        if price not in order_book['bids']:
            order_book['bids'][price] = 0
        order_book['bids'][price] += size
    else:
        if price not in order_book['asks']:
            order_book['asks'][price] = 0
        order_book['asks'][price] += size

    bid_prices = sorted(order_book['bids'].keys(), reverse=True)
    ask_prices = sorted(order_book['asks'].keys())

    return {
        'seconds_into_market': timestamp,
        'source': message.get('trader_id', ''),
        'message_type': 'ADDED_ORDER',
        'incoming_message': f"{price},{size},{direction}",
        'price': price,
        'size': size,
        'direction': direction,
        'Event_Type': 1,
        'Ask_Price_1': ask_prices[0] if ask_prices else None,
        'Bid_Price_1': bid_prices[0] if bid_prices else None,
        'Midprice': (ask_prices[0] + bid_prices[0]) / 2 if ask_prices and bid_prices else None,
        'Ask_Prices': json.dumps(ask_prices),
        'Ask_Sizes': json.dumps([order_book['asks'][p] for p in ask_prices]),
        'Bid_Prices': json.dumps(bid_prices),
        'Bid_Sizes': json.dumps([order_book['bids'][p] for p in bid_prices]),
        'matched_bid_id': None,
        'matched_ask_id': None,
    }

def process_log_file(log_file_path: str) -> List[Dict]:
    with open(log_file_path, 'r') as file:
        log_lines = file.readlines()

    parsed_logs = [parse_log_line(line) for line in log_lines if parse_log_line(line) is not None]

    if not parsed_logs:
        return []

    df = pl.DataFrame(parsed_logs)

    start_time = df['timestamp'].min()
    order_book = {'bids': {}, 'asks': {}}
    processed_messages = []

    for row in df.iter_rows(named=True):
        if row['message_type'] == 'ADD_ORDER':
            timestamp = (row['timestamp'] - start_time).total_seconds()
            processed_message = process_message(row['content'], order_book, timestamp)
            processed_messages.append(processed_message)
        elif row['message_type'] == 'MATCHED_ORDER':
            if processed_messages:
                processed_messages[-1]['matched_bid_id'] = row['content'].get('bid_order_id')
                processed_messages[-1]['matched_ask_id'] = row['content'].get('ask_order_id')

    return processed_messages

def write_to_csv(data: List[Dict], output_file: io.StringIO):
    if not data:
        return
    fieldnames = list(data[0].keys())
    writer = csv.DictWriter(output_file, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        writer.writerow(row)
