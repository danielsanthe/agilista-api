
"""
Modelo de Produto Global do AgiLista.

Representa o catálogo compartilhado de produtos.
Armazena informações genéricas que podem ser utilizadas
por todos os usuários, independentemente de seus cadastros pessoais.

Cada produto global deve estar associado a uma categoria
padrão cadastrada no sistema.
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class ProdutoGlobal(SQLModel, table=True):

    # Nome da tabela no banco de dados.
    __tablename__ = "produtos_globais"

    # Identificador único do produto no servidor.
    id_produto_global: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    # Código de barras utilizado para identificar o produto.
    # Deve ser único no catálogo global.
    codigo_barras: str = Field(
        unique=True,
        index=True,
        max_length=50
    )

    # Nome oficial do produto.
    nome_oficial: str = Field(
        index=True,
        max_length=200
    )

    # Unidade de medida padrão do produto.
    # Exemplos: Un, Kg, L.
    unidade_medida_padrao: str = Field(
        default="Un",
        max_length=20
    )

    # Categoria padrão associada ao produto global (indexada para filtros).
    # Deve referenciar uma categoria existente no sistema.
    # A exclusão da categoria será impedida enquanto
    # houver produtos globais associados.
    categoria_id: int = Field(
        foreign_key="categorias.id_categoria",
        index=True,
        ondelete="RESTRICT"
    )
