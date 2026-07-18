"""业务异常：由全局 handler 转为统一 {code, msg, data} 响应。"""


class BusinessException(Exception):
    def __init__(self, code: int, msg: str, http_status: int = 200):
        self.code = code
        self.msg = msg
        self.http_status = http_status
