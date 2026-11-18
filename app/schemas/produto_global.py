
"""
app/schemas/produto_global.py

Esquemas de Validação DTO (Data Transfer Objects) para o
Catálogo Global de Produtos do ÁgiLista.

Este módulo define os contratos de entrada e saída (payloads JSON)
para a API de Produtos Globais.

O catálogo global armazena informações compartilhadas entre todos
os usuários do AgiLista, permitindo localizar produtos por código
de barras e reutilizar suas informações no cadastro pessoal.

Responsabilidades:
- Validar código de barras, nome oficial e unidade de medida.
- Associar obrigatoriamente cada produto a uma categoria padrão.
- Sanitizar strings, removendo espaços nas extremidades.
- Bloquear campos não autorizados nas requisições.
- Rejeitar valores nulos em campos obrigatórios.
- Rejeitar requisições vazias durante atualizações parciais.
- Permitir consultas dos dados do produto e de sua categoria.
"""

from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator
)


# =====================================================================
# SEÇÃO 1: ESQUEMA BASE (PROPRIEDADES COMPARTILHADAS)
# =====================================================================

class ProdutoGlobalBase(BaseModel):
    """
    Atributos fundamentais do produto global.

    Define os campos compartilhados entre os esquemas de criação
    e leitura, incluindo os limites e as descrições utilizados
    na documentação automática da OpenAPI/Swagger.
    """

    # Código de barras utilizado para identificar o produto.
    # Deve ser único no catálogo global.
    codigo_barras: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código de barras único do produto global.",
        examples=["7891000100103"]
    )

    # Nome oficial do produto compartilhado no catálogo.
    nome_oficial: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Descrição oficial do produto no catálogo global.",
        examples=["Arroz Tipo 1 5kg"]
    )

    # Unidade de medida padrão do produto.
    # Exemplos: Un, Kg, L, Cx e Pacote.
    unidade_medida_padrao: str = Field(
        default="Un",
        min_length=1,
        max_length=20,
        description="Unidade de medida padrão do produto.",
        examples=["Un"]
    )

    # Identificador da categoria padrão associada ao produto.
    # Deve corresponder a uma categoria global existente,
    # ou seja, uma categoria cujo usuario_id seja NULL.
    categoria_id: int = Field(
        ...,
        gt=0,
        description="ID da categoria padrão associada ao produto global.",
        examples=[1]
    )

    # Configurações compartilhadas do Pydantic v2.
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid"
    )


# =====================================================================
# SEÇÃO 2: ESQUEMA DE CRIAÇÃO (POST)
# =====================================================================

class ProdutoGlobalCreate(ProdutoGlobalBase):
    """
    DTO para cadastro de produtos no catálogo global.

    Endpoint previsto:
    POST /api/v1/produtos-globais/

    Todos os campos obrigatórios devem possuir valores válidos.
    O cadastro será permitido somente para administradores.
    """

    @model_validator(mode="before")
    @classmethod
    def validar_payload_criacao(cls, values: dict) -> dict:
        """
        Pré-processa o dicionário recebido antes da validação
        dos tipos e limites definidos pelo Pydantic.

        Regras:
        - Cria uma cópia defensiva do payload.
        - Rejeita valores nulos em campos obrigatórios.
        - Rejeita strings vazias ou compostas apenas por espaços.
        - Preserva o código de barras como string, inclusive
          quando possuir zeros à esquerda.
        """

        if isinstance(values, dict):

            # Cópia defensiva para evitar alterações no payload original.
            values = values.copy()

            # Valida os campos obrigatórios contra valores nulos.
            campos_obrigatorios = [
                "codigo_barras",
                "nome_oficial",
                "categoria_id"
            ]

            for campo in campos_obrigatorios:
                if campo in values and values[campo] is None:
                    raise ValueError(
                        f"O campo '{campo}' não pode ser nulo."
                    )

            # Verifica se os campos de texto não estão vazios.
            campos_texto = [
                "codigo_barras",
                "nome_oficial",
                "unidade_medida_padrao"
            ]

            for campo in campos_texto:
                valor = values.get(campo)

                if isinstance(valor, str) and not valor.strip():
                    raise ValueError(
                        f"O campo '{campo}' não pode ficar vazio."
                    )

        return values


# =====================================================================
# SEÇÃO 3: ESQUEMA DE ATUALIZAÇÃO PARCIAL (PUT)
# =====================================================================

class ProdutoGlobalUpdate(BaseModel):
    """
    DTO para atualização parcial de produtos globais.

    Endpoint previsto:
    PUT /api/v1/produtos-globais/{id_produto_global}

    Todos os campos são opcionais individualmente, permitindo
    atualizar somente as informações desejadas.

    Regras:
    - Não permite payload vazio.
    - Não permite valores nulos nos campos obrigatórios.
    - Não permite campos extras não autorizados.
    - Permite alterar a categoria, desde que seja padrão.
    """

    # Novo código de barras do produto.
    codigo_barras: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Novo código de barras do produto.",
        examples=["7891000100104"]
    )

    # Nova descrição oficial do produto.
    nome_oficial: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=200,
        description="Nova descrição oficial do produto.",
        examples=["Arroz Integral 5kg"]
    )

    # Nova unidade de medida padrão.
    unidade_medida_padrao: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=20,
        description="Nova unidade de medida padrão.",
        examples=["Kg"]
    )

    # Novo identificador da categoria padrão.
    categoria_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Novo ID da categoria padrão do produto.",
        examples=[2]
    )

    # Configurações do Pydantic v2 para atualização parcial.
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid"
    )

    @model_validator(mode="before")
    @classmethod
    def validar_payload_atualizacao(cls, values: dict) -> dict:
        """
        Pré-processa o payload recebido durante a atualização.

        Regras:
        - Cria uma cópia defensiva do dicionário.
        - Rejeita requisições com JSON vazio.
        - Rejeita valores nulos explicitamente enviados.
        - Rejeita strings vazias ou compostas apenas por espaços.
        """

        if isinstance(values, dict):

            # Cópia defensiva para preservar o payload original.
            values = values.copy()

            # Impede atualizações sem nenhum campo informado.
            if not values:
                raise ValueError(
                    "O corpo da requisição de atualização "
                    "não pode estar vazio."
                )

            # Campos que não aceitam valores nulos.
            campos_obrigatorios = [
                "codigo_barras",
                "nome_oficial",
                "unidade_medida_padrao",
                "categoria_id"
            ]

            for campo in campos_obrigatorios:
                if campo in values and values[campo] is None:
                    raise ValueError(
                        f"O campo '{campo}' não aceita valores nulos."
                    )

            # Valida os campos de texto informados.
            campos_texto = [
                "codigo_barras",
                "nome_oficial",
                "unidade_medida_padrao"
            ]

            for campo in campos_texto:
                valor = values.get(campo)

                if isinstance(valor, str) and not valor.strip():
                    raise ValueError(
                        f"O campo '{campo}' não pode ficar vazio."
                    )

        return values


# =====================================================================
# SEÇÃO 4: ESQUEMA RESUMIDO DA CATEGORIA (RESPONSE)
# =====================================================================

class CategoriaGlobalResumoResponse(BaseModel):
    """
    DTO resumido da categoria associada ao produto global.

    Permite que a API apresente o nome da categoria junto
    com os demais dados do produto, sem retornar todos os
    dados internos do cadastro de categorias.
    """

    # Identificador da categoria no servidor.
    id_categoria: int = Field(
        ...,
        description="Identificador da categoria padrão."
    )

    # Nome da categoria padrão.
    nome_categoria: str = Field(
        ...,
        description="Nome da categoria associada ao produto.",
        examples=["Mercearia"]
    )

    # Conversão de atributos do modelo ORM para o Pydantic.
    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# SEÇÃO 5: ESQUEMA DE RESPOSTA / LEITURA (RESPONSE)
# =====================================================================

class ProdutoGlobalResponse(BaseModel):
    """
    DTO de saída contendo os dados completos do produto global.

    Utilizado nas consultas por ID, listagens e principalmente
    na busca por código de barras.

    Retorna:
    - Identificador do produto global.
    - Código de barras.
    - Descrição oficial.
    - Unidade de medida padrão.
    - Identificador da categoria.
    - Dados resumidos da categoria associada.
    """

    # Identificador único do produto global no servidor.
    id_produto_global: int = Field(
        ...,
        description="Identificador único do produto global."
    )

    # Código de barras do produto.
    codigo_barras: str

    # Descrição oficial do produto.
    nome_oficial: str

    # Unidade de medida padrão.
    unidade_medida_padrao: str

    # Identificador da categoria padrão.
    categoria_id: int

    # Dados resumidos da categoria associada.
    categoria: CategoriaGlobalResumoResponse = Field(
        ...,
        description="Dados da categoria padrão vinculada ao produto."
    )

    # Configuração para conversão dos objetos ORM.
    model_config = ConfigDict(
        from_attributes=True
    )

# =====================================================================
# SEÇÃO 6: ESQUEMA DE RESPOSTA PAGINADA (PAINEL ADMINISTRATIVO)
# =====================================================================

class ProdutoGlobalPaginadoResponse(BaseModel):
    """
    DTO de saída paginada para listagem de produtos globais em larga escala.
    Permite trafegar apenas a fatia necessária da página mantendo o total real.
    """

    # Total geral de produtos que correspondem aos filtros aplicados.
    total: int = Field(
        ...,
        ge=0,
        description="Total de registros encontrados para a consulta."
    )

    # Limite de itens solicitados por página.
    limit: int = Field(
        ...,
        gt=0,
        description="Quantidade máxima de itens retornados por página."
    )

    # Deslocamento (offset) aplicado na consulta.
    offset: int = Field(
        ...,
        ge=0,
        description="Índice inicial dos registros retornados."
    )

    # Lista dos produtos globais da página atual.
    itens: list[ProdutoGlobalResponse] = Field(
        default_factory=list,
        description="Lista de produtos globais da página atual."
    )
