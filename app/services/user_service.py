from pydantic import EmailStr

from app.models.user import User, UserCreate
from app.repositories import users as user_repo
from app.security import get_password_hash, verify_password


class UserService:
    @staticmethod
    def get_user_by_email(email: EmailStr | str) -> User | None:
        return user_repo.get_user_by_email(str(email))

    @staticmethod
    def get_user_by_google_id(google_id: str) -> User | None:
        return user_repo.get_user_by_google_id(google_id)

    @staticmethod
    def get_user_by_id(user_id: str) -> User | None:
        return user_repo.get_user_by_id(user_id)

    @staticmethod
    def create_db_user(user_in: UserCreate) -> User:
        user = User(
            id="",
            email=user_in.email,
            name=user_in.name,
            hashed_password=get_password_hash(user_in.password),
        )
        return user_repo.create_user_or_raise(user)

    @staticmethod
    def authenticate_user(email: str, password: str) -> User | None:
        user = UserService.get_user_by_email(email)
        if not user or not user.is_active:
            return None
        if not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> bool:
        if not user.hashed_password:
            user.hashed_password = get_password_hash(new_password)
            user_repo.save_user(user)
            return True
        if not verify_password(old_password, user.hashed_password):
            return False
        user.hashed_password = get_password_hash(new_password)
        user_repo.save_user(user)
        return True

    @staticmethod
    def delete_account(user: User) -> None:
        user_repo.delete_user(user)

    @staticmethod
    def create_or_get_google_user(
        google_id: str,
        email: str,
        name: str,
        avatar: str | None = None,
    ) -> User:
        user = UserService.get_user_by_google_id(google_id)
        if user:
            if user.email != email or user.name != name or (
                avatar and user.avatar != avatar
            ):
                user.email = email
                user.name = name
                if avatar:
                    user.avatar = avatar
                user_repo.save_user(user)
            return user

        user = UserService.get_user_by_email(email)
        if user:
            user.google_id = google_id
            if avatar:
                user.avatar = avatar
            user_repo.save_user(user)
            return user

        return user_repo.create_user_or_raise(
            User(
                id="",
                email=email,
                name=name,
                google_id=google_id,
                hashed_password=None,
                avatar=avatar,
                is_active=True,
            )
        )
