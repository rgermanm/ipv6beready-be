from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    hashed_password: str | None = None
    google_id: str | None = None
    avatar: str | None = None
    is_active: bool = True
    is_superuser: bool = False


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    avatar: str | None = None
    is_active: bool
    is_superuser: bool = False


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(..., min_length=8)
    recaptcha_token: str | None = None


class PasswordChange(BaseModel):
    old_password: str = ""
    new_password: str = Field(..., min_length=8)


class GoogleToken(BaseModel):
    credential: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str


def to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar=user.avatar,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
    )
