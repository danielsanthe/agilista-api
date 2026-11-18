"""
=============================================================================
AGILISTA API — ROTAS DE AUTENTICAÇÃO
=============================================================================

Este arquivo concentra os endpoints responsáveis pela autenticação
e identificação dos usuários da API AgiLista.

Responsabilidades:
1. Autenticar o usuário por email e senha.
2. Gerar tokens JWT de acesso e renovação.
3. Renovar os tokens utilizando um refresh token válido.
4. Retornar os dados do usuário autenticado.

Observações:
- A identificação do usuário utiliza o campo id_usuario.
- A senha armazenada no banco permanece no campo senha_hash.
- As senhas são verificadas utilizando bcrypt.
- O JWT utiliza as configurações definidas em app/config.py.
- O refresh token é renovado a cada solicitação bem-sucedida.
"""

# =============================================================================
# IMPORTAÇÕES
# =============================================================================

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import obter_usuario_atual
from app.models.usuario import Usuario
import random
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    EsqueciSenhaRequest,
    EsqueciSenhaResponse,
    RedefinirSenhaRequest,
)
from app.security import (
    create_jwt_token,
    decodificar_token,
    verificar_senha,
    obter_hash_senha,
)
from app.config import settings


# =============================================================================
# CONFIGURAÇÃO DO ROUTER
# =============================================================================

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Autenticação"]
)


# =============================================================================
# CONFIGURAÇÃO DOS TEMPOS DE VALIDADE DOS TOKENS
# =============================================================================

# Tempo de validade do token de acesso.
TEMPO_ACCESS_TOKEN = timedelta(
    minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
)

# Tempo de validade do token de renovação.
TEMPO_REFRESH_TOKEN = timedelta(days=7)


# =============================================================================
# FUNÇÃO AUXILIAR — GERAÇÃO DOS TOKENS
# =============================================================================

def gerar_tokens(usuario: Usuario) -> LoginResponse:
    """
    Gera os tokens de acesso e renovação para o usuário informado.

    O campo sub identifica o usuário pelo id_usuario.
    O campo type diferencia access de refresh.
    """

    dados_usuario = {
        "sub": str(usuario.id_usuario)
    }

    access_token = create_jwt_token(
        {
            **dados_usuario,
            "type": "access"
        },
        expires_delta=TEMPO_ACCESS_TOKEN
    )

    refresh_token = create_jwt_token(
        {
            **dados_usuario,
            "type": "refresh"
        },
        expires_delta=TEMPO_REFRESH_TOKEN
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


# =============================================================================
# ENDPOINT — LOGIN
# =============================================================================

@router.post(
    "/signin",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Autenticar usuário",
    description="Valida as credenciais do usuário por email e senha e retorna os tokens JWT de acesso e renovação.",
    responses={
        200: {
            "description": "Autenticação realizada com sucesso. Retorna os tokens JWT."
        },
        401: {
            "description": "Email ou senha inválidos. As credenciais não foram autenticadas."
        },
        422: {
            "description": "Dados da requisição inválidos. Verifique se o email e a senha foram informados corretamente."
        }
    }
)
def signin(
    dados: LoginRequest,
    session: Session = Depends(get_session)
):
    """
    Autentica o usuário utilizando email e senha.

    Se as credenciais forem válidas, gera os tokens JWT.
    """

    # -------------------------------------------------------------------------
    # 1. Localiza o usuário pelo email.
    # -------------------------------------------------------------------------

    usuario = session.exec(
        select(Usuario).where(
            Usuario.email == dados.email
        )
    ).first()

    # -------------------------------------------------------------------------
    # 2. Verifica se o usuário existe e se a senha está correta.
    # -------------------------------------------------------------------------

    if not usuario or not verificar_senha(
        dados.password,
        usuario.senha_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # -------------------------------------------------------------------------
    # 3. Gera e retorna os tokens JWT.
    # -------------------------------------------------------------------------

    return gerar_tokens(usuario)


# =============================================================================
# ENDPOINT — RENOVAÇÃO DOS TOKENS
# =============================================================================

@router.post(
    "/refresh",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Renovar tokens",
    description="Valida o refresh token informado e gera um novo par de tokens JWT de acesso e renovação.",
    responses={
        200: {
            "description": "Tokens renovados com sucesso."
        },
        401: {
            "description": "Refresh token inválido, expirado, de tipo incorreto ou associado a um usuário que não existe mais."
        },
        422: {
            "description": "Dados da requisição inválidos. O refresh_token não foi informado corretamente."
        }
    }
)
def refresh(
    dados: RefreshRequest,
    session: Session = Depends(get_session)
):
    """
    Renova os tokens de autenticação.

    Somente tokens identificados como refresh são aceitos.
    """

    # -------------------------------------------------------------------------
    # 1. Decodifica e valida o refresh token.
    # -------------------------------------------------------------------------

    try:
        payload = decodificar_token(dados.refresh_token)

        # ---------------------------------------------------------------------
        # 2. Verifica se o token é realmente do tipo refresh.
        # ---------------------------------------------------------------------

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token informado não é um refresh token.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # ---------------------------------------------------------------------
        # 3. Recupera o ID do usuário armazenado no token.
        # ---------------------------------------------------------------------

        usuario_id = int(payload.get("sub"))

    except HTTPException:
        raise

    except (JWTError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # -------------------------------------------------------------------------
    # 4. Verifica se o usuário ainda existe no banco.
    # -------------------------------------------------------------------------

    usuario = session.get(Usuario, usuario_id)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # -------------------------------------------------------------------------
    # 5. Gera novos tokens.
    # -------------------------------------------------------------------------

    return gerar_tokens(usuario)


# =============================================================================
# ENDPOINT — USUÁRIO AUTENTICADO
# =============================================================================

@router.get(
    "/me",
    summary="Consultar usuário autenticado",
    description="Retorna os dados básicos do usuário identificado pelo token JWT de acesso.",
    responses={
        200: {
            "description": "Dados do usuário autenticado retornados com sucesso."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado. Também ocorre quando o usuário não é encontrado."
        }
    }
)
def obter_me(
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """
    Retorna os dados básicos do usuário autenticado.

    Não retorna senha, hash de senha ou informações confidenciais.
    """

    return {
        "id_usuario": usuario.id_usuario,
        "nome_usuario": usuario.nome_usuario,
        "email": usuario.email,
        "tipo_usuario": usuario.tipo_usuario,
        "tipo_plano": usuario.tipo_plano,
        "data_cadastro": usuario.data_cadastro,
        "ultima_sincronizacao": usuario.ultima_sincronizacao
    }
  

# =============================================================================
# ENDPOINT — ESQUECI A SENHA
# =============================================================================
  
# Armazenamento temporário em memória dos códigos ativos: {email_limpo: token_jwt_15min}
_CODIGOS_RECUPERACAO: dict[str, str] = {}


@router.post(
    "/esqueci-senha",
    response_model=EsqueciSenhaResponse,
    status_code=status.HTTP_200_OK,
    summary="Solicitar código de recuperação de senha",
    description="Gera um código temporário de 6 dígitos (válido por 15 minutos) para redefinição de senha.",
)
def esqueci_senha(
    dados: EsqueciSenhaRequest,
    session: Session = Depends(get_session),
):
    email_limpo = dados.email.strip().lower()
    usuario = session.exec(
        select(Usuario).where(Usuario.email == email_limpo)
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma conta encontrada com o e-mail informado.",
        )

    codigo = f"{random.randint(100000, 999999)}"
    token_reset = create_jwt_token(
        {
            "sub": str(usuario.id_usuario),
            "email": email_limpo,
            "codigo": codigo,
            "type": "reset_password",
        },
        expires_delta=timedelta(minutes=15),
    )

    _CODIGOS_RECUPERACAO[email_limpo] = token_reset
    print(f"[AGILISTA-API] Código de recuperação para {email_limpo}: {codigo}")

    return EsqueciSenhaResponse(
        mensagem="Código de verificação gerado! Válido por 15 minutos.",
        codigo_recuperacao=codigo,
    )



# =============================================================================
# ENDPOINT —  REDEFINI SENHA
# =============================================================================

@router.post(
    "/redefinir-senha",
    status_code=status.HTTP_200_OK,
    summary="Redefinir senha com código de verificação",
    description="Valida o código de 6 dígitos e atualiza a senha do usuário no banco de dados.",
)
def redefinir_senha(
    dados: RedefinirSenhaRequest,
    session: Session = Depends(get_session),
):
    email_limpo = dados.email.strip().lower()
    nova_senha_limpa = dados.nova_senha.strip()

    if len(nova_senha_limpa) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A nova senha deve conter no mínimo 6 caracteres.",
        )

    token_salvo = _CODIGOS_RECUPERACAO.get(email_limpo)
    if not token_salvo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma solicitação de recuperação ativa para este e-mail. Solicite um novo código.",
        )

    try:
        payload = decodificar_token(token_salvo)
        if (
            payload.get("type") != "reset_password"
            or payload.get("email") != email_limpo
            or payload.get("codigo") != dados.codigo.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de verificação inválido.",
            )

        usuario_id = int(payload.get("sub"))
    except HTTPException:
        raise
    except (JWTError, TypeError, ValueError):
        _CODIGOS_RECUPERACAO.pop(email_limpo, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de verificação expirado. Solicite um novo código.",
        )

    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    usuario.senha_hash = obter_hash_senha(nova_senha_limpa)
    session.add(usuario)
    session.commit()

    # Invalida o código após o uso
    _CODIGOS_RECUPERACAO.pop(email_limpo, None)

    return {"mensagem": "Senha redefinida com sucesso!"}