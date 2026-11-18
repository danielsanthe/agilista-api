"""
Modelo de Produto do Usuário do AgiLista.

Representa os produtos cadastrados no catálogo particular
de cada usuário.

Um produto pessoal pode estar associado a um produto global,
mas suas informações e configurações pertencem ao usuário.
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class ProdutoUsuario(SQLModel, table=True):

    # Nome da tabela no banco de dados.
    __tablename__ = "produtos_usuario"

    # Identificador único do produto pessoal no servidor.
    id_produto_usuario: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    # Identifica o usuário proprietário do produto.
    usuario_id: int = Field(
        foreign_key="usuarios.id_usuario",
        index=True
    )

    # Referência opcional ao produto do catálogo global.
    # Pode ficar NULL quando o usuário cadastrar um produto manualmente.
    produto_global_id: Optional[int] = Field(
        default=None,
        foreign_key="produtos_globais.id_produto_global"
    )

    # Identifica a categoria à qual o produto pertence.
    categoria_id: int = Field(
        foreign_key="categorias.id_categoria",
        ondelete="RESTRICT"
    )

    # Nome escolhido pelo usuário para identificar o produto.
    # Pode ser diferente do nome oficial do catálogo global.
    nome_produto: str = Field(max_length=200)

    # Código de barras do produto, quando informado.
    codigo_barras: Optional[str] = Field(
        default=None,
        max_length=50
    )

    # Unidade de medida utilizada pelo usuário.
    unidade_medida: str = Field(
        default="Un",
        max_length=20
    )

    # Indica se o produto é recorrente nas compras do usuário.
    flag_produto_recorrente: int = Field(default=0)

    # Campo mantido para compatibilidade com a sincronização do aplicativo.
    flag_sincronizado: int = Field(default=1)