"""
app/schemas/item_lista.py

Schemas Pydantic v2 para gerenciamento dos itens das listas de compras
do AgiLista.
"""

from typing import Any, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# STATUS OFICIAIS DO APLICATIVO FLUTTER
# ============================================================

# Tipo literal estrito com os valores de status aceitos pelo aplicativo Flutter
StatusItem = Literal["Pendente", "Comprado", "Comprado FL"]

# Dicionário para mapeamento e normalização case-insensitive das variações de status
STATUS_ITEM_MAP = {
    "pendente": "Pendente",
    "comprado": "Comprado",
    "comprado fl": "Comprado FL",
    "compradofl": "Comprado FL",
}


# ============================================================
# FUNÇÕES AUXILIARES DE VALIDAÇÃO
# ============================================================

def normalizar_status(value: Any) -> Any:
    """
    Normaliza a string de status enviada para a formatação oficial do Flutter.
    
    Lança ValueError se o valor for nulo ou não corresponder a um status suportado.
    """
    if value is None:
        raise ValueError(
            "O status não pode receber null."
        )

    if isinstance(value, str):
        valor_limpo = value.strip().lower()

        if valor_limpo in STATUS_ITEM_MAP:
            return STATUS_ITEM_MAP[valor_limpo]

    raise ValueError(
        "Status inválido. Os valores permitidos são: "
        "'Pendente', 'Comprado' e 'Comprado FL'."
    )


def validar_combinacao_status_origem(
    status_item: Optional[str],
    flag_fora_da_lista: Optional[int],
) -> None:
    """
    Valida a correspondência entre o status do item e o indicador de origem (fora da lista).
    
    'Pendente' e 'Comprado' exigem flag_fora_da_lista = 0.
    'Comprado FL' exige flag_fora_da_lista = 1.
    """
    if status_item is None or flag_fora_da_lista is None:
        return

    combinacoes_validas = {
        ("Pendente", 0),
        ("Comprado", 0),
        ("Comprado FL", 1),
    }

    if (status_item, flag_fora_da_lista) not in combinacoes_validas:
        raise ValueError(
            "Combinação inválida entre 'status_item' e "
            "'flag_fora_da_lista'. "
            "'Pendente' e 'Comprado' exigem flag 0; "
            "'Comprado FL' exige flag 1."
        )


def validar_promocao(
    flag_promocao: int,
    qtd_minima_promocional: Optional[float],
    preco_promocional: Optional[float],
) -> None:
    """
    Valida se os campos obrigatórios de promoção foram preenchidos
    quando a flag_promocao estiver ativada (igual a 1).
    """
    if flag_promocao == 1:
        if qtd_minima_promocional is None:
            raise ValueError(
                "Quando 'flag_promocao' for 1, "
                "'qtd_minima_promocional' é obrigatória."
            )

        if preco_promocional is None:
            raise ValueError(
                "Quando 'flag_promocao' for 1, "
                "'preco_promocional' é obrigatório."
            )


# ============================================================
# SCHEMA BASE DE ENTRADA
# ============================================================

class ItemListaBase(BaseModel):
    """
    Atributos permitidos na criação de um item.

    Campos controlados pelo servidor não são aceitos.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    produto_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="ID opcional do produto do catálogo pessoal.",
    )

    nome_item_planejado: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nome descritivo do item.",
    )

    qtd_planejada: float = Field(
        default=1.0,
        ge=0.0,
        description="Quantidade planejada.",
    )

    preco_estimado: float = Field(
        default=0.0,
        ge=0.0,
        description="Preço unitário estimado.",
    )

    flag_promocao: int = Field(
        default=0,
        ge=0,
        le=1,
        description="Indica se existe promoção por quantidade.",
    )

    qtd_minima_promocional: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Quantidade mínima para aplicar a promoção.",
    )

    preco_promocional: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Preço unitário promocional.",
    )

    flag_fora_da_lista: int = Field(
        default=0,
        ge=0,
        le=1,
        description="Indica se o item foi adicionado durante a compra.",
    )

    @field_validator("nome_item_planejado")
    @classmethod
    def validar_nome(cls, value: str) -> str:
        """Garante que o nome do item não seja vazio ou composto apenas por espaços."""
        if not value or not value.strip():
            raise ValueError(
                "O nome do item não pode ser vazio."
            )

        return value.strip()

    @model_validator(mode="after")
    def validar_regras_criacao(self):
        """Valida promoção e origem do item na criação."""

        if self.flag_promocao == 0:
            self.qtd_minima_promocional = None
            self.preco_promocional = None
        else:
            validar_promocao(
                self.flag_promocao,
                self.qtd_minima_promocional,
                self.preco_promocional,
            )

        if self.flag_fora_da_lista == 1:
            if self.qtd_planejada != 0:
                raise ValueError(
                    "Itens fora da lista devem possuir "
                    "'qtd_planejada' igual a 0."
                )

        return self


# ============================================================
# SCHEMA DE CRIAÇÃO - POST
# ============================================================

class ItemListaCreate(ItemListaBase):
    """
    Dados permitidos para adicionar um item à lista.
    Suporta inclusão em uma única etapa para itens fora da lista (T14).
    Valores padrão definidos como None para permitir diferenciação entre
    campos omitidos e valores zerados informados no payload.
    """

    qtd_comprada: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Quantidade comprada do item."
    )

    preco_unitario: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Preço unitário efetivamente pago."
    )


# ============================================================
# SCHEMA DE ATUALIZAÇÃO PARCIAL - PUT
# ============================================================

class ItemListaUpdate(BaseModel):
    """
    Dados permitidos para atualização parcial.

    Campos omitidos permanecem inalterados.
    Campos opcionais podem receber null explicitamente
    quando a regra de negócio permitir.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    produto_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="ID do produto; null desvincula o produto.",
    )

    nome_item_planejado: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    qtd_planejada: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    preco_estimado: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    qtd_comprada: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    preco_unitario: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    status_item: Optional[StatusItem] = Field(
        default=None,
        description="Novo status operacional do item.",
    )

    flag_promocao: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
    )

    qtd_minima_promocional: Optional[float] = Field(
        default=None,
        gt=0.0,
    )

    preco_promocional: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    flag_fora_da_lista: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
    )

    @field_validator("status_item", mode="before")
    @classmethod
    def validar_status(cls, value: Any) -> Optional[str]:
        """Rejeita null e normaliza o status recebido."""
        if value is None:
            raise ValueError(
                "O campo 'status_item' não pode receber null."
            )
        return normalizar_status(value)

    @field_validator(
        "nome_item_planejado",
        "qtd_planejada",
        "preco_estimado",
        "qtd_comprada",
        "preco_unitario",
        "flag_promocao",
        "flag_fora_da_lista",
        mode="before",
    )
    @classmethod
    def rejeitar_null_campos_obrigatorios(cls, value: Any) -> Any:
        """Impede null explícito nos campos que não aceitam valores nulos."""
        if value is None:
            raise ValueError(
                "Este campo não pode receber null."
            )
        return value

    @field_validator("nome_item_planejado")
    @classmethod
    def validar_nome_update(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        """Garante que o nome do item não seja atualizado para uma string vazia."""
        if value is not None and not value.strip():
            raise ValueError(
                "O nome do item não pode ser vazio."
            )

        return value.strip() if value is not None else None

    @model_validator(mode="before")
    @classmethod
    def validar_payload_nao_vazio(cls, data: Any) -> Any:
        """Garante que o corpo da requisição PUT contenha ao menos um campo para atualização."""
        if isinstance(data, dict) and not data:
            raise ValueError(
                "Informe pelo menos um campo para atualizar."
            )

        return data


# ============================================================
# SCHEMA DE RESPOSTA HTTP
# ============================================================

class ItemListaResponse(BaseModel):
    """
    Representação de saída do item.

    Independente dos schemas de entrada para evitar efeitos
    colaterais durante a serialização.
    """

    model_config = ConfigDict(from_attributes=True)

    id_item_lista: int
    lista_id: int
    produto_id: Optional[int] = None
    servidor_id: Optional[int] = None

    nome_item_planejado: str
    qtd_planejada: float
    preco_estimado: float

    qtd_comprada: Optional[float] = 0.0
    preco_unitario: Optional[float] = 0.0
    subtotal_item: Optional[float] = 0.0

    status_item: StatusItem

    flag_promocao: int
    qtd_minima_promocional: Optional[float] = None
    preco_promocional: Optional[float] = None

    flag_fora_da_lista: int
    flag_sincronizado: int