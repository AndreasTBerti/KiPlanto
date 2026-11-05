"""Schemas de /auth (cadastro, login e sessão)."""
import re

from pydantic import BaseModel, Field, field_validator

MIN_PASSWORD = 8
# Limite alto para uma senha real e baixo o bastante para não pesar no scrypt.
MAX_PASSWORD = 128
MAX_EMAIL = 254
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterInput(BaseModel):
    name: str = Field(..., description="Nome de exibição, de 2 a 80 caracteres")
    email: str = Field(..., description="E-mail, usado para entrar")
    password: str = Field(..., description=f"Senha, de {MIN_PASSWORD} a {MAX_PASSWORD} caracteres")

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        name = " ".join(value.split())
        if not 2 <= len(name) <= 80:
            raise ValueError("o nome precisa ter de 2 a 80 caracteres")
        return name

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        email = value.strip()
        if len(email) > MAX_EMAIL or not _EMAIL.match(email):
            raise ValueError("informe um e-mail válido")
        return email

    @field_validator("password")
    @classmethod
    def _valid_password(cls, value: str) -> str:
        if not MIN_PASSWORD <= len(value) <= MAX_PASSWORD:
            raise ValueError(f"a senha precisa ter de {MIN_PASSWORD} a {MAX_PASSWORD} caracteres")
        return value


class LoginInput(BaseModel):
    email: str = Field(..., min_length=1, max_length=MAX_EMAIL)
    password: str = Field(..., min_length=1, max_length=MAX_PASSWORD)


class UserOutput(BaseModel):
    id: int
    name: str
    email: str


class AuthOutput(BaseModel):
    token: str = Field(..., description="Envie em `Authorization: Bearer <token>`")
    user: UserOutput
