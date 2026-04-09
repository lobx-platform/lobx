import math
import json


def sanitize_websocket_message(message):
    """Sanitize a message before sending over WebSocket to prevent JSON parsing errors."""
    def sanitize_value(value):
        if isinstance(value, dict):
            return {str(k): sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [sanitize_value(item) for item in value]
        elif isinstance(value, float):
            if math.isnan(value) or math.isinf(value) or abs(value) > 1e100:
                return 0.0
            return value
        elif isinstance(value, (int, complex)):
            if isinstance(value, complex) or abs(value) > 1e15:
                return 0
            return value
        elif isinstance(value, str):
            try:
                json.dumps(value)
                if '--' in value or value.endswith('-') or (value.startswith('-') and not value[1:].replace('.', '').isdigit()):
                    cleaned_value = value.replace('--', '_').strip('-')
                    return cleaned_value if cleaned_value else '0'
                return value
            except (TypeError, ValueError):
                safe_value = str(value).replace('--', '_').strip('-')
                return safe_value if safe_value else '0'
        elif value is None:
            return None
        else:
            try:
                json.dumps(value)
                return value
            except (TypeError, ValueError):
                str_value = str(value)
                if 'datetime' in str_value or 'object at 0x' in str_value:
                    return 'object'
                safe_value = str_value.replace('--', '_').strip('-')
                return safe_value if safe_value else 'unknown'

    return sanitize_value(message)
