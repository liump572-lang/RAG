from typing import Any, Optional


def success_response(data: Any = None, message: str = "success") -> dict:
    return {"code": 200, "message": message, "data": data}


def error_response(code: int, message: str, detail: Any = None) -> dict:
    resp = {"code": code, "message": message}
    if detail:
        resp["detail"] = detail
    return resp


def paginated_response(items: list, total: int, page: int, size: int) -> dict:
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
        },
    }
