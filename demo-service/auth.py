"""无状态令牌：user_id.HMAC 签名，便于演示「凭证无效」类测试场景。"""

import hmac
import hashlib


def _sign(user_id, secret_key):
    return hmac.new(secret_key.encode(), str(user_id).encode(), hashlib.sha256).hexdigest()[:32]


def encode_token(user_id, secret_key):
    return f"{user_id}.{_sign(user_id, secret_key)}"


def decode_token(token, secret_key):
    """校验通过返回 user_id，否则返回 None。"""
    if not isinstance(token, str) or token.count(".") != 1:
        return None
    raw_id, signature = token.split(".")
    if not raw_id.isdigit():
        return None
    user_id = int(raw_id)
    if not hmac.compare_digest(signature, _sign(user_id, secret_key)):
        return None
    return user_id
