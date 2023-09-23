from pydantic import BaseModel


class UserBase(BaseModel):
    username: str