"""
Modelo de Lista do AgiLista.

Representa as listas de compras criadas pelos usuários.
Cada lista pertence a um usuário e possui um orçamento próprio.
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class Lista(SQLModel, table=True):

    # Nome da tabela no banco de dados.
    __tablename__ = "listas"

    # Identificador único da lista no servidor.
    id_lista: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    # Identificador correspondente à lista no banco local.
    servidor_id: Optional[int] = Field(default=None)

    # Identifica o usuário proprietário da lista.
    usuario_id: int = Field(
        foreign_key="usuarios.id_usuario",
        index=True,
        ondelete="CASCADE"
    )

    # Nome escolhido para identificar a lista.
    nome_lista: str = Field(max_length=150)

    # Orçamento definido pelo usuário para a compra.
    valor_orcamento: float

    # Valor total atual da compra.
    # É mantido conforme a estrutura do SQLite v5.
    valor_total_atual: float = Field(default=0.0)

    # Situação atual da lista.
    # Exemplo: Planejada, Em andamento ou Concluída.
    status_lista: str = Field(
        default="Planejada",
        max_length=30
    )

    # Informações do estabelecimento onde a compra será realizada.
    nome_estabelecimento: Optional[str] = Field(
        default=None,
        max_length=150
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

    # Campo de controle de sincronização com o aplicativo.
    flag_sincronizado: int = Field(default=1)

    # Data em que a lista foi criada.
    data_criacao: str

    # Data e hora em que a compra foi iniciada.
    data_hora_inicio: Optional[str] = Field(default=None)

    # Data e hora em que a compra foi finalizada.
    data_hora_termino: Optional[str] = Field(default=None)