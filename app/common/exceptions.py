from fastapi import HTTPException


class BusinessException(HTTPException):
    def __init__(self, error_code: int, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        super().__init__(status_code=status_code, detail={"code": error_code, "message": message})
