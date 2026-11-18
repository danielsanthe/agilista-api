
"""
app/schemas/lista.py

Schemas Pydantic v2 para gerenciamento de Listas de Compras do ÁgiLista.

Regras:
- Criação: nome_lista e valor_orcamento são obrigatórios.
- valor_orcamento aceita zero.
- Toda lista nasce com status Planejada.
- O estabelecimento é informado ao iniciar a compra.
- Localização do estabelecimento é opcional.
- IDs, totais, sincronização e datas são controlados pelo backend.
"""

from typing import Optional, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.item_lista import ItemListaCreate


StatusLista = Literal["Planejada", "Em Andamento", "Concluída"]


STATUS_PERMITIDOS_MAP = {
    "planejada": "Planejada",
    "em andamento": "Em Andamento",
    "concluida": "Concluída",
    "concluída": "Concluída",
}


# =====================================================================
# FUNÇÕES AUXILIARES
# =====================================================================

def normalizar_status(value: Any) -> str:
    """Normaliza os status aceitos, sem diferenciar maiúsculas/minúsculas."""

    if isinstance(value, str):
        valor_limpo = value.strip().lower()

        if valor_limpo in STATUS_PERMITIDOS_MAP:
            return STATUS_PERMITIDOS_MAP[valor_limpo]

    raise ValueError(
        "Status inválido. Os status permitidos são: "
        "'Planejada', 'Em Andamento' e 'Concluída'."
    )


# =====================================================================
# SCHEMA BASE
# =====================================================================

class ListaBase(BaseModel):
    """Campos compartilhados entre criação e resposta."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    nome_lista: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Nome de identificação da lista de compras.",
        examples=["Compras da Semana"]
    )

    valor_orcamento: float = Field(
        ...,
        ge=0.0,
        description="Orçamento obrigatório da lista. Aceita zero.",
        examples=[250.00, 0.0]
    )

    nome_estabelecimento: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150,
        description=(
            "Nome do estabelecimento. Pode ficar vazio durante o "
            "planejamento e deve ser informado ao iniciar a compra."
        ),
        examples=["Supermercado Carvalho"]
    )

    endereco_estabelecimento: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Endereço opcional do estabelecimento."
    )

    bairro: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Bairro do estabelecimento."
    )

    cidade: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Cidade do estabelecimento."
    )

    uf: Optional[str] = Field(
        default=None,
        max_length=2,
        description="Sigla do estado com dois caracteres."
    )

    @field_validator("nome_lista")
    @classmethod
    def validar_nome_lista(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError(
                "O nome da lista não pode ser vazio."
            )

        return value.strip()

    @field_validator(
        "nome_estabelecimento",
        "endereco_estabelecimento",
        "bairro",
        "cidade",
        "uf",
        mode="before"
    )
    @classmethod
    def normalizar_campos_textuais_opcionais(
        cls,
        value: Optional[str]
    ) -> Optional[str]:
        """Converte textos vazios ou com espaços em None."""

        if isinstance(value, str):
            valor_limpo = value.strip()
            return valor_limpo if valor_limpo else None

        return value

    @field_validator("uf")
    @classmethod
    def normalizar_uf(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


# =====================================================================
# SCHEMAS DE CRIAÇÃO (POST)
# =====================================================================

class ListaCreate(ListaBase):
    """
    Criação de lista sem itens.

    Toda lista deve começar como Planejada.
    O estabelecimento será informado posteriormente,
    quando o usuário iniciar a compra.
    """

    status_lista: Literal["Planejada"] = Field(
        default="Planejada",
        description="Toda lista é criada inicialmente como Planejada."
    )


class ListaPlanejadaComItensCreate(ListaBase):
    """
    Criação de lista planejada acompanhada de seus itens.

    Todos os itens devem ser planejados, não podendo ser
    itens adicionados durante uma compra.
    """

    itens: list[ItemListaCreate] = Field(
        ...,
        min_length=1,
        description="Itens que serão cadastrados junto com a lista."
    )

    @model_validator(mode="after")
    def validar_itens_planejados(self):
        for indice, item in enumerate(self.itens, start=1):
            if item.flag_fora_da_lista != 0:
                raise ValueError(
                    f"O item {indice} não pode ser incluído como "
                    "fora da lista durante o planejamento."
                )

        return self


# =====================================================================
# SCHEMA DE ATUALIZAÇÃO PARCIAL (PUT)
# =====================================================================

class ListaUpdate(BaseModel):
    """Permite atualização parcial dos dados da lista."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    nome_lista: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    valor_orcamento: Optional[float] = Field(
        default=None,
        ge=0.0
    )

    nome_estabelecimento: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    status_lista: Optional[StatusLista] = Field(
        default=None
    )

    endereco_estabelecimento: Optional[str] = Field(
        default=None,
        max_length=200
    )

    bairro: Optional[str] = Field(
        default=None,
        max_length=100
    )

    cidade: Optional[str] = Field(
        default=None,
        max_length=100
    )

    uf: Optional[str] = Field(
        default=None,
        max_length=2
    )

    @field_validator(
        "nome_lista",
        "valor_orcamento",
        "nome_estabelecimento",
        "status_lista",
        mode="before"
    )
    @classmethod
    def rejeitar_null_em_campos_obrigatorios(
        cls,
        value: Any,
        info: Any
    ) -> Any:
        if value is None:
            raise ValueError(
                f"O campo '{info.field_name}' não pode ser nulo."
            )

        return value

    @field_validator(
        "nome_lista",
        "nome_estabelecimento",
        mode="before"
    )
    @classmethod
    def validar_textos_obrigatorios(
        cls,
        value: Optional[str],
        info: Any
    ) -> Optional[str]:
        if value is not None:
            valor_limpo = value.strip()

            if not valor_limpo:
                raise ValueError(
                    f"O campo '{info.field_name}' não pode ser vazio."
                )

            return valor_limpo

        return value

    @field_validator(
        "endereco_estabelecimento",
        "bairro",
        "cidade",
        "uf",
        mode="before"
    )
    @classmethod
    def normalizar_localizacao(
        cls,
        value: Optional[str]
    ) -> Optional[str]:
        if isinstance(value, str):
            valor_limpo = value.strip()
            return valor_limpo if valor_limpo else None

        return value

    @field_validator("uf")
    @classmethod
    def normalizar_uf(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value

    @field_validator("status_lista", mode="before")
    @classmethod
    def normalizar_status_update(cls, value: Any) -> str:
        return normalizar_status(value)

    @model_validator(mode="before")
    @classmethod
    def validar_payload_update(cls, data: Any) -> Any:
        """
        Rejeita payload vazio ou composto somente por valores null.

        Campos opcionais de localização podem ser limpos enviando
        uma string vazia ou contendo apenas espaços.
        """

        if not isinstance(data, dict):
            return data

        chaves_validas = [
            chave
            for chave, valor in data.items()
            if valor is not None
        ]

        if not chaves_validas:
            raise ValueError(
                "A atualização deve conter ao menos um campo válido."
            )

        return data


# =====================================================================
# SCHEMA DE RESPOSTA
# =====================================================================

class ListaResponse(ListaBase):
    """Dados retornados pela API."""

    model_config = ConfigDict(from_attributes=True)

    id_lista: int

    usuario_id: int

    servidor_id: Optional[int] = None

    valor_total_atual: float

    status_lista: StatusLista

    flag_sincronizado: int

    data_criacao: str

    data_hora_inicio: Optional[str] = None

    data_hora_termino: Optional[str] = None
