from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Same shape the database enforces in app_user_username_format, so a bad
# username is rejected at the edge with a useful message instead of coming back
# as a constraint violation.
USERNAME_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,31}$"


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=1024)

    @field_validator("username")
    @classmethod
    def normalise_username(cls, value: str) -> str:
        """Lowercase before validating, so Alice and alice are one account."""
        import re

        lowered = value.strip().lower()
        if not re.fullmatch(USERNAME_PATTERN, lowered):
            raise ValueError(
                "username must be 3-32 characters of letters, digits, dot, "
                "dash or underscore, and start with a letter or digit"
            )
        return lowered


class AccountOut(BaseModel):
    username: str


class AvailabilityOut(BaseModel):
    username: str
    available: bool
    # True when the filter alone settled it, i.e. no database round trip was
    # needed. Useful for seeing the filter earn its keep.
    answered_by_filter: bool
