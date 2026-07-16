"""统一返回体（契约：业务码放在 body.code）"""

from fastapi.responses import JSONResponse


def ok(data=None, msg: str = "success"):
    return {"code": 0, "msg": msg, "data": data}


def fail(code: int, msg: str, http_status: int = 200, data=None):
    """失败响应；V2 允许 data 携带补充信息（如 4002 的 doc_id/status）"""
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "msg": msg, "data": data},
    )
