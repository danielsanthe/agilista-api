"""
=============================================================================
AGILISTA API — SEGURANÇA E AUTENTICAÇÃO (JWT)
=============================================================================

Este arquivo centraliza as funções relacionadas à segurança da API.

Responsabilidades:
1. Gerar hash de senhas utilizando bcrypt.
2. Verificar senhas informadas durante o login.
3. Criar tokens JWT de acesso e renovação.
4. Decodificar e validar tokens JWT.
5. Disponibilizar o esquema OAuth2 para autenticação das requisições.

Observações:
- A senha original nunca é armazenada no banco.
- O campo senha_hash do modelo Usuario continuará sendo utilizado.
- A identificação do usuário será feita pelo campo id_usuario.
- As configurações JWT são obtidas de app/config.py.
"""

# =============================================================================
# IMPORTAÇÕES
# =============================================================================

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt

from jose import jwt
from fastapi.security import OAuth2PasswordBearer

from app.config import settings


# =============================================================================
# CONFIGURAÇÃO DO OAUTH2
# =============================================================================

# Informa ao FastAPI o endpoint utilizado para obter o token de acesso.
# O caminho deverá corresponder à rota de login implementada em auth.py.

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/signin"
)


# =============================================================================
# FUNÇÕES DE SEGURANÇA DE SENHAS
# =============================================================================

def obter_hash_senha(senha: str) -> str:
    """
    Gera um hash bcrypt a partir da senha informada.

    A senha original não é armazenada no banco de dados.
    """

    senha_bytes = senha.encode("utf-8")

    hash_bytes = bcrypt.hashpw(
        senha_bytes,
        bcrypt.gensalt()
    )

    return hash_bytes.decode("utf-8")


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """
    Compara a senha informada com o hash armazenado no banco.

    Retorna:
        True: senha válida.
        False: senha inválida.
    """

    senha_bytes = senha_plana.encode("utf-8")
    hash_bytes = senha_hash.encode("utf-8")

    return bcrypt.checkpw(
        senha_bytes,
        hash_bytes
    )


# =============================================================================
# FUNÇÕES DE CRIAÇÃO DE TOKENS JWT
# =============================================================================

def create_jwt_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Cria um token JWT com os dados recebidos.

    Parâmetros:
        data: informações que serão armazenadas no payload.
        expires_delta: tempo de validade do token.

    Retorna:
        Token JWT codificado.
    """

    to_encode = data.copy()

    # Define o horário de expiração do token.
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({
        "exp": expire
    })

    # Codifica o token utilizando as configurações do AgiLista.
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


# =============================================================================
# FUNÇÃO DE DECODIFICAÇÃO E VALIDAÇÃO DO JWT
# =============================================================================

def decodificar_token(token: str) -> dict:
    """
    Decodifica e valida um token JWT.

    Verifica a assinatura, o algoritmo e a validade do token.

    Se o token estiver inválido ou expirado, a biblioteca
    python-jose lançará uma exceção JWTError.
    """

    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )