from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from schemas.auth_schema import AuthOutput, LoginInput, RegisterInput, UserOutput
from services import auth_service
from services.auth_service import User

router = APIRouter(prefix="/auth", tags=["Autenticação"])

_bearer = HTTPBearer(auto_error=False, description="Token devolvido por /auth/login ou /auth/register")
Credentials = Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)]


def require_user(credentials: Credentials) -> User:
    """Exige uma sessão válida. As rotas de /ai e /news usam esta dependência (ver main.py)."""
    user = auth_service.user_from_token(credentials.credentials) if credentials else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Faça login para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _client(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def _auth_output(user: User) -> AuthOutput:
    return AuthOutput(
        token=auth_service.create_session(user),
        user=UserOutput(id=user.id, name=user.name, email=user.email),
    )


@router.post(
    "/register",
    response_model=AuthOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma conta e já inicia a sessão",
    responses={
        409: {"description": "Já existe uma conta com este e-mail"},
        429: {"description": "Muitos cadastros a partir deste endereço"},
    },
)
def register(data: RegisterInput, request: Request):
    if not auth_service.take_registration_attempt(_client(request)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitos cadastros. Tente novamente mais tarde.")
    try:
        user = auth_service.create_user(data.name, data.email, data.password)
    except auth_service.EmailAlreadyRegistered as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com este e-mail.") from exc
    return _auth_output(user)


@router.post(
    "/login",
    response_model=AuthOutput,
    summary="Inicia uma sessão",
    responses={
        401: {"description": "E-mail ou senha incorretos"},
        429: {"description": "Muitas tentativas para este e-mail"},
    },
)
def login(data: LoginInput, request: Request):
    client = _client(request)
    if not auth_service.take_login_attempt(client, data.email):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas. Aguarde 15 minutos.")
    user = auth_service.authenticate(data.email, data.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    auth_service.clear_login_attempts(client, data.email)
    return _auth_output(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Encerra a sessão atual",
    dependencies=[Depends(require_user)],
)
def logout(credentials: Credentials):
    # require_user já garantiu que há uma sessão válida.
    auth_service.delete_session(credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOutput, summary="A conta da sessão atual")
def me(user: Annotated[User, Depends(require_user)]):
    return UserOutput(id=user.id, name=user.name, email=user.email)
