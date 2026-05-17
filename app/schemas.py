from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    image_url: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class FaceVerifyResponse(BaseModel):
    user_id: int
    matched: bool
    distance: float
    similarity_percent: float


class MessageResponse(BaseModel):
    message: str
