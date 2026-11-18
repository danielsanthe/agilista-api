"""
app/schemas/produto_usuario.py

Esquemas de Validação DTO (Data Transfer Objects) para o Módulo de Produtos do Usuário.

Este módulo define os contratos de entrada e saída (payloads JSON) para a API de Produtos do ÁgiLista.
Aplica regras estritas de validação do Pydantic v2, incluindo:
- Sanitização automática de strings (remoção de espaços nas extremidades via `str_strip_whitespace=True`).
- Bloqueio de campos não autorizados em requisições via `extra="forbid"`.
- Proteção contra injeção de valores nulos (`None`) em campos obrigatórios via `@model_validator(mode="before")`.
- Cópia defensiva do dicionário (`values.copy()`) durante pré-validações para prevenir efeitos colaterais.
- Rejeição de JSONs vazios `{}` no fluxo de atualização parcial (`PUT`).
- Normalização de código de barras vazio (string de espaços) para `None` (SQL NULL).
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


# =====================================================================
# SEÇÃO 1: ESQUEMA BASE (PROPRIEDADES COMPARTILHADAS)
# =====================================================================

class ProdutoUsuarioBase(BaseModel):
    """
    Atributos fundamentais do produto reutilizados na criação e atualização.

    Define os tipos, limites de caracteres e mensagens de documentação para a OpenAPI/Swagger.
    """

    # Nome personalizado do produto atribuído pelo usuário (Ex: "Leite Integral 1L")
    nome_produto: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nome personalizado do produto do usuário. Não pode ser vazio.",
        examples=["Leite Desnatado 1L"]
    )

    # Identificador da categoria à qual o produto pertence (deve ser um inteiro estritamente positivo)
    categoria_id: int = Field(
        ...,
        gt=0,
        description="ID da categoria (padrão ou personalizada) à qual o produto está vinculado.",
        examples=[1]
    )

    # Código de barras opcional no formato EAN/UPC (string de até 50 caracteres)
    codigo_barras: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Código de barras EAN/UPC opcional para leitura via scanner.",
        examples=["7891000100103"]
    )

    # Unidade de medida do produto (Ex: Un, Kg, L, Cx, Pacote)
    unidade_medida: str = Field(
        default="Un",
        min_length=1,
        max_length=20,
        description="Unidade de medida de comercialização (ex: Un, Kg, L, Cx). Padrão é 'Un'.",
        examples=["Un"]
    )

    # Marcador de recorrência mantido para estrita compatibilidade com a base SQLite (v5) do aplicativo Flutter
    flag_produto_recorrente: int = Field(
        default=0,
        ge=0,
        le=1,
        description="Indica se o produto é recorrente nas compras (0 = Não, 1 = Sim). Mantido para compatibilidade.",
        examples=[0]
    )

    # Vínculo opcional com a tabela de produtos globais do catálogo base do servidor
    produto_global_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="ID opcional do produto correspondente no catálogo global.",
        examples=[None]
    )

    # Configuração de comportamento do Pydantic v2 compartilhada
    model_config = ConfigDict(
        from_attributes=True,       # Permite conversão direta a partir de objetos ORM do SQLModel
        str_strip_whitespace=True, # Remove automaticamente espaços em branco no início e fim de strings
        extra="forbid"             # Lança erro HTTP 422 se a requisição enviar campos extras não mapeados
    )


# =====================================================================
# SEÇÃO 2: ESQUEMA DE CRIAÇÃO (POST)
# =====================================================================

class ProdutoUsuarioCreate(ProdutoUsuarioBase):
    """
    DTO para o cadastro de novos produtos (POST /api/v1/produtos/).

    Herda as propriedades do ProdutoUsuarioBase e adiciona validações prévias
    para barrar valores nulos explícitos em campos obrigatórios.
    """

    @model_validator(mode="before")
    @classmethod
    def validar_payload_criacao(cls, values: dict) -> dict:
        """
        Pré-processa o dicionário da requisição antes da validação dos tipos Pydantic.

        - Cria uma cópia defensiva do dicionário para evitar efeitos colaterais.
        - Rejeita valores nulos explicitamente passados em `nome_produto` e `categoria_id`.
        - Converte códigos de barras compostos apenas por espaços em `None`.
        """
        if isinstance(values, dict):
            # Cópia defensiva para não alterar a referência original do objeto recepcionado
            values = values.copy()

            # Validação de nulidade explícita em campos obrigatórios
            if "nome_produto" in values and values["nome_produto"] is None:
                raise ValueError("O campo 'nome_produto' não pode ser nulo.")

            if "categoria_id" in values and values["categoria_id"] is None:
                raise ValueError("O campo 'categoria_id' não pode ser nulo.")

            # Trata código de barras: se for informado como string vazia ou espaços, converte para None
            if values.get("codigo_barras") is not None:
                if isinstance(values["codigo_barras"], str) and not values["codigo_barras"].strip():
                    values["codigo_barras"] = None

        return values


# =====================================================================
# SEÇÃO 3: ESQUEMA DE ATUALIZAÇÃO PARCIAL (PUT)
# =====================================================================

class ProdutoUsuarioUpdate(BaseModel):
    """
    DTO para atualização parcial de produto (PUT /api/v1/produtos/{id_produto_usuario}).

    Todos os campos são opcionais, permitindo atualizar apenas atributos específicos.
    Bloqueia envios com JSON vazio `{}`, injeção de nulos em campos obrigatórios e
    campos extras não autorizados.
    """

    # Novo nome opcional para o produto
    nome_produto: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Novo nome para o produto. Não aceita nulo nem string vazia.",
        examples=["Leite Desnatado Zero Lactose 1L"]
    )

    # Novo ID de categoria opcional
    categoria_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Novo ID de categoria vinculado. Deve ser maior que 0.",
        examples=[2]
    )

    # Novo código de barras opcional (permite envio explícito de null para remover)
    codigo_barras: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Novo código de barras.",
        examples=["7891000100104"]
    )

    # Nova unidade de medida opcional
    unidade_medida: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=20,
        description="Nova unidade de medida.",
        examples=["L"]
    )

    # Novo valor de recorrência opcional (0 ou 1)
    flag_produto_recorrente: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
        description="Novo status de recorrência (0 ou 1). Não aceita valor nulo.",
        examples=[1]
    )

    # Novo ID do catálogo global opcional (permite passar null para desvincular do produto global)
    produto_global_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Novo ID de vínculo com o catálogo global. Permite `null` para desvincular.",
        examples=[15]
    )

    # Configuração Pydantic v2 do DTO de atualização
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid"  # Impede a injeção não autorizada de campos como usuario_id ou id_produto_usuario
    )

    @model_validator(mode="before")
    @classmethod
    def validar_payload_atualizacao(cls, values: dict) -> dict:
        """
        Pré-processa a requisição de atualização parcial (`PUT`).

        - Cria uma cópia defensiva do dicionário.
        - Rejeita corpos de requisição vazios (`{}`).
        - Bloqueia a injeção explícita de `null` nos campos que requerem valores válidos.
        - Normaliza strings de código de barras vazias para `None`.
        """
        if isinstance(values, dict):
            # Cópia defensiva para preservação dos dados de entrada
            values = values.copy()

            # Rejeita JSONs totalmente vazios no corpo da requisição
            if not values:
                raise ValueError("O corpo da requisição de atualização não pode estar vazio.")

            # Bloqueia nulos explícitos em campos essenciais fornecidos no payload
            if "nome_produto" in values and values["nome_produto"] is None:
                raise ValueError("O campo 'nome_produto' não aceita valores nulos.")

            if "categoria_id" in values and values["categoria_id"] is None:
                raise ValueError("O campo 'categoria_id' não aceita valores nulos.")

            if "unidade_medida" in values and values["unidade_medida"] is None:
                raise ValueError("O campo 'unidade_medida' não aceita valores nulos.")

            if "flag_produto_recorrente" in values and values["flag_produto_recorrente"] is None:
                raise ValueError("O campo 'flag_produto_recorrente' não aceita valores nulos.")

            # Se o código de barras for passado como string vazia de espaços, converte para None
            if "codigo_barras" in values and isinstance(values["codigo_barras"], str):
                if not values["codigo_barras"].strip():
                    values["codigo_barras"] = None

        return values


# =====================================================================
# SEÇÃO 4: ESQUEMA DE RESPOSTA / LEITURA (RESPONSE)
# =====================================================================

class ProdutoUsuarioResponse(BaseModel):
    """
    DTO de saída contendo a representação completa do produto retornada pelas rotas da API.

    Inclui os dados salvos no banco, identificadores gerados, o proprietário (`usuario_id`)
    e a flag de sincronização com o dispositivo móvel.
    """

    # Identificador único do produto no banco de dados do servidor
    id_produto_usuario: int = Field(
        ...,
        description="Identificador único do produto do usuário no servidor."
    )

    # ID do usuário proprietário do produto
    usuario_id: int = Field(
        ...,
        description="ID do usuário proprietário deste produto."
    )

    # Nome do produto
    nome_produto: str

    # ID da categoria vinculada
    categoria_id: int

    # Código de barras (pode ser None)
    codigo_barras: Optional[str] = None

    # Unidade de medida
    unidade_medida: str

    # Status de recorrência (0 ou 1)
    flag_produto_recorrente: int

    # Vínculo com produto global (pode ser None)
    produto_global_id: Optional[int] = None

    # Flag de sincronização para o banco local SQLite do app mobile (1 = sincronizado/pendente)
    flag_sincronizado: int = Field(
        default=1,
        description="Flag de controle de sincronização com o banco local do aplicativo mobile."
    )

    # Configuração de conversão de atributos do ORM para o Pydantic
    model_config = ConfigDict(from_attributes=True)