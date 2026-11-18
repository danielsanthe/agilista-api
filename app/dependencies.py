"""
=============================================================================
AGILISTA API — DEPENDÊNCIAS DO SISTEMA (FASTAPI DEPENDS)
=============================================================================

Este arquivo concentra as funções de dependência reutilizáveis injetadas nos
roteadores da aplicação através do mecanismo 'Depends' do FastAPI.

Responsabilidades Principais:
1. Identificar o usuário que está realizando a requisição.
2. Reutilizar a sessão ativa com o banco de dados (get_session).
3. Validar a autenticação através de tokens JWT.
4. Controlar o acesso às operações administrativas do sistema.
"""

# =============================================================================
# IMPORTAÇÕES
# =============================================================================

# Utilitários do FastAPI para dependências e erros HTTP.
from fastapi import Depends, HTTPException, status

# Sessão do banco de dados.
from sqlmodel import Session

# Exceções utilizadas na validação dos tokens JWT.
from jose import JWTError

# Dependência responsável por fornecer a sessão do banco.
from app.database import get_session

# Modelo ORM de usuário.
from app.models.usuario import Usuario

# Esquema OAuth2 e função de decodificação do JWT.
from app.security import oauth2_scheme, decodificar_token


# =============================================================================
# DEPENDÊNCIA — OBTENÇÃO DO USUÁRIO AUTENTICADO
# =============================================================================

def obter_usuario_atual(
    token: str = Depends(oauth2_scheme),
    sessao: Session = Depends(get_session)
) -> Usuario:
    """
    Identifica e retorna o usuário autenticado através do JWT.

    Funcionamento:
    1. Recebe o token pelo cabeçalho Authorization: Bearer.
    2. Decodifica e valida o token JWT.
    3. Verifica se o token é do tipo access.
    4. Recupera o id_usuario armazenado no campo sub.
    5. Busca o usuário no banco de dados.
    6. Retorna o objeto Usuario autenticado.

    Lança erro 401 caso o token seja inválido, expirado ou
    não corresponda a um usuário cadastrado.
    """

    # -------------------------------------------------------------------------
    # 1. Decodifica e valida o token JWT.
    # -------------------------------------------------------------------------

    try:
        payload = decodificar_token(token)

        # ---------------------------------------------------------------------
        # 2. Verifica se o token é do tipo access.
        # ---------------------------------------------------------------------

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido para autenticação.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # ---------------------------------------------------------------------
        # 3. Recupera o ID do usuário armazenado no campo sub.
        # ---------------------------------------------------------------------

        usuario_id = int(payload.get("sub"))

    except HTTPException:
        raise

    except (JWTError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # -------------------------------------------------------------------------
    # 4. Busca o usuário pelo ID no banco de dados.
    # -------------------------------------------------------------------------

    usuario = sessao.get(Usuario, usuario_id)

    # -------------------------------------------------------------------------
    # 5. Verifica se o usuário ainda existe.
    # -------------------------------------------------------------------------

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário autenticado não foi localizado no banco de dados.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Retorna o usuário autenticado.
    return usuario


# =============================================================================
# DEPENDÊNCIA — VERIFICAÇÃO DE ACESSO ADMINISTRATIVO
# =============================================================================

def obter_admin_atual(
    usuario: Usuario = Depends(obter_usuario_atual)
) -> Usuario:
    """
    Dependência de autorização administrativa.

    Funcionamento:
    1. Reutiliza a identificação fornecida por obter_usuario_atual().
    2. Verifica se o tipo de usuário é ADMIN.
    3. Permite a operação somente para administradores.
    4. Retorna erro 403 Forbidden para usuários comuns.

    A autenticação JWT identifica o usuário.
    Esta função verifica se ele possui permissão administrativa.
    """

    # Verifica o perfil de acesso do usuário.
    if usuario.tipo_usuario != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido somente para administradores."
        )

    # Retorna o usuário autorizado.
    return usuario
