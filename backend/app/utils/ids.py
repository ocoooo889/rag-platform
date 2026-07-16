"""生成契约约定的字符串 ID"""

import uuid


def new_id(prefix: str) -> str:
    """例如 prefix='kb' -> 'kb' + 短 uuid"""
    return f"{prefix}{uuid.uuid4().hex[:8]}"
