"""
=============================================================================
AGILISTA API — SCHEMAS DE AUTENTICAÇÃO
=============================================================================

Este arquivo define os schemas utilizados no processo de autenticação
da API AgiLista.

Responsabilidades:
1. Validar os dados enviados durante o login.
2. Definir a estrutura da resposta de autenticação.
3. Validar os dados enviados para renovação dos tokens JWT.

Observações:
- O email identifica o usuário no processo de login.
- A senha é recebida apenas para validação e nunca é armazenada
  diretamente neste schema ou retornada pela API.
- O campo senha_hash permanece exclusivamente no modelo Usuario.
- Os tokens JWT são utilizados para autenticar as requisições.
"""

# =============================================================================
# IMPORTAÇÕES
# =============================================================================

from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =============================================================================
# SCHEMA DE ENTRADA — LOGIN
# =============================================================================

class LoginRequest(BaseModel):
    """
    Dados necessários para autenticar um usuário.

    Recebe o email e a senha informados no formulário de login.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    email: EmailStr = Field(
        description="Email cadastrado pelo usuário."
    )

    password: str = Field(
        min_length=1,
        description="Senha informada pelo usuário."
    )


# =============================================================================
# SCHEMA DE RESPOSTA — AUTENTICAÇÃO
# =============================================================================

class LoginResponse(BaseModel):
    """
    Resposta retornada após uma autenticação bem-sucedida.

    Contém os tokens JWT necessários para acessar a API.
    """

    access_token: str = Field(
        description="Token utilizado para autenticar as requisições."
    )

    refresh_token: str = Field(
        description="Token utilizado para renovar a autenticação."
    )

    token_type: str = Field(
        default="bearer",
        description="Tipo de autenticação utilizado."
    )


# =============================================================================
# SCHEMA DE ENTRADA — RENOVAÇÃO DO TOKEN
# =============================================================================

class RefreshRequest(BaseModel):
    """
    Dados necessários para solicitar a renovação dos tokens JWT.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    refresh_token: str = Field(
        min_length=1,
        description="Token de renovação da autenticação."
    )
    
# =============================================================================
# SCHEMA RECUPERAÇAO DE SENHA
# =============================================================================
    
class EsqueciSenhaRequest(BaseModel):
    email: EmailStr = Field(..., description="E-mail cadastrado do usuário")


class EsqueciSenhaResponse(BaseModel):
    mensagem: str
    codigo_recuperacao: Optional[str] = Field(
        default=None,
        description="Código temporário de 6 dígitos (exibido em ambiente de desenvolvimento/testes)"
    )


class RedefinirSenhaRequest(BaseModel):
    email: EmailStr = Field(..., description="E-mail cadastrado do usuário")
    codigo: str = Field(..., min_length=6, max_length=6, description="Código de 6 dígitos")
    nova_senha: str = Field(..., min_length=6, description="Nova senha (mínimo 6 caracteres)")