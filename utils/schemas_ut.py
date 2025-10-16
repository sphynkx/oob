from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class MeResponse(BaseModel):
    id: int
    email: EmailStr
    name: str | None = None
    avatar_url: str | None = None
    role: str | None = None


class LogoutRequest(BaseModel):
    all: bool | None = False


class ProductCreate(BaseModel):
    title: str
    description: str | None = None
    price: float
    currency: str | None = "USD"
    image_url: str | None = None


class ProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    currency: str | None = None
    image_url: str | None = None


class ProductOut(BaseModel):
    id: int
    seller_id: int
    title: str
    description: str | None = None
    price: float
    currency: str
    image_url: str | None = None
