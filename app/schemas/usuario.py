"""
=============================================================================
AGILISTA API — SCHEMAS DE USUÁRIO (PYDANTIC DTOs)
=============================================================================

Este arquivo define as classes de validação e modelagem de dados (DTOs)
utilizadas pelo FastAPI e Pydantic v2 para receber, validar e responder
requisições HTTP referentes ao módulo de Usuários e Clientes.

Define os contratos de entrada, atualização e resposta para o módulo de Usuários.
Aplica validações estritas de dados, sanitiza strings, impede payloads de edição
vazios e rejeita valores nulos (null) explicitamente.

Responsabilidades Principais:
1. Garantir a integridade do nome, e-mail e dados cadastrais.
2. Rejeitar payloads de atualização vazios {} ou com valores nulos (null) explícitos.
3. Proteger a senha em texto plano convertendo-a ou omitindo-a na saída.
4. Formatar o JSON final de resposta retornado para o aplicativo mobile e admin.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# =====================================================================
# 1. SCHEMA BASE (Campos Comuns e Regras Fundamentais)
# =====================================================================
class UsuarioBaseSchema(BaseModel):
    """
    Atributos base e validações essenciais compartilhadas entre os schemas do módulo.
    """
    nome_usuario: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Nome completo do usuário",
        examples=["Daniel Santos"]
    )
    
    email: EmailStr = Field(
        ...,
        description="Endereço de e-mail único do usuário",
        examples=["usuario@agilista.com"]
    )
    
    cpf: Optional[str] = Field(
        default=None,
        max_length=14,
        description="CPF do usuário (apenas números ou formatado)"
    )
    
    telefone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Telefone celular de contato"
    )
    
    cep: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Código de Endereçamento Postal"
    )
    
    logradouro: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Nome da rua/logradouro"
    )
    
    numero: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Número do imóvel ou complemento"
    )
    
    bairro: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Bairro residencial"
    )
    
    cidade: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Cidade do usuário"
    )
    
    uf: Optional[str] = Field(
        default=None,
        max_length=2,
        description="Unidade Federativa (ex: PI, SP)"
    )

    @field_validator("nome_usuario")
    @classmethod
    def validar_nome_nao_vazio(cls, v: str) -> str:
        """
        Garante que o nome do usuário não seja nulo, vazio ou composto apenas por espaços.
        """
        if v is None:
            raise ValueError("O nome do usuário não pode ser nulo.")
        
        texto_limpo = v.strip()
        if len(texto_limpo) < 2:
            raise ValueError("O nome do usuário deve conter no mínimo 2 caracteres válidos.")
            
        if len(texto_limpo) > 150:
            raise ValueError("O nome do usuário deve conter no máximo 150 caracteres.")
            
        return texto_limpo


# =====================================================================
# 2. SCHEMA DE CRIAÇÃO (Payload do POST)
# =====================================================================
class UsuarioCriarSchema(UsuarioBaseSchema):
    """
    Dados recebidos na requisição para cadastrar um novo usuário.
    A senha é recebida em texto plano para ser tratada e convertida em hash pelo backend.
    """
    senha: str = Field(
        ...,
        min_length=6,
        description="Senha de acesso em texto plano (mínimo de 6 caracteres)",
        examples=["senhaSegura123"]
    )

    @field_validator("senha")
    @classmethod
    def validar_senha_minima(cls, v: str) -> str:
        """
        Garante que a senha possua no mínimo 6 caracteres sem espaços nas extremidades.
        """
        if v is None or not v.strip():
            raise ValueError("A senha não pode ser nula ou vazia.")
        if len(v.strip()) < 6:
            raise ValueError("A senha deve conter no mínimo 6 caracteres.")
        return v.strip()


# =====================================================================
# 3. SCHEMA DE ATUALIZAÇÃO (Payload do PUT)
# =====================================================================
class UsuarioAtualizarSchema(BaseModel):
    """
    Campos permitidos para modificação parcial do perfil do usuário.
    Garante que a requisição contenha pelo menos uma alteração válida e rejeita nulos explícitos.
    """
    nome_usuario: Optional[str] = Field(default=None, min_length=2, max_length=150)
    email: Optional[EmailStr] = Field(default=None)
    senha: Optional[str] = Field(default=None, min_length=6)
    cpf: Optional[str] = Field(default=None, max_length=14)
    telefone: Optional[str] = Field(default=None, max_length=20)
    cep: Optional[str] = Field(default=None, max_length=10)
    logradouro: Optional[str] = Field(default=None, max_length=200)
    numero: Optional[str] = Field(default=None, max_length=20)
    bairro: Optional[str] = Field(default=None, max_length=100)
    cidade: Optional[str] = Field(default=None, max_length=100)
    uf: Optional[str] = Field(default=None, max_length=2)

    @model_validator(mode="before")
    @classmethod
    def rejeitar_nulo_explicito(cls, dados):
        """
        Rejeita valores null enviados explicitamente no JSON pelo aplicativo.
        """
        if isinstance(dados, dict):
            for campo in ("nome_usuario", "email", "senha"):
                if campo in dados and dados[campo] is None:
                    raise ValueError(f"O campo '{campo}' não aceita valor nulo (null).")
        return dados

    @model_validator(mode="after")
    def validar_payload_nao_vazio(self):
        """
        Impede atualizações com payload totalmente vazio {}.
        """
        campos_enviados = self.model_fields_set
        if not campos_enviados:
            raise ValueError("Informe pelo menos um campo para realizar a atualização.")
        return self


# =====================================================================
# 4. SCHEMA DE RESPOSTA (Payload de Saída em GET/POST/PUT)
# =====================================================================
class UsuarioRespostaSchema(UsuarioBaseSchema):
    """
    Estrutura completa devolvida pela API nas consultas e respostas de escrita.
    Omite a senha e expõe apenas dados públicos do perfil.
    """
    id_usuario: int = Field(description="Identificador único (PK) no banco do servidor")
    servidor_id: Optional[int] = Field(default=None, description="Identificador no servidor de sync")
    tipo_plano: Optional[str] = Field(default=None, description="Plano atual do cliente (nulo para ADMIN)")
    tipo_usuario: str = Field(default="CLIENTE", description="Nível de acesso (CLIENTE ou ADMIN)")
    flag_sincronizado: int = Field(default=1, description="Indicador de sincronização (1 = OK)")
    data_cadastro: str = Field(description="Data de criação da conta em formato ISO-8601")
    ultima_sincronizacao: Optional[str] = Field(default=None, description="Data da última sincronização")

    model_config = ConfigDict(from_attributes=True)