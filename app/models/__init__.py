"""
Centralização dos modelos do banco de dados do AgiLista.

A importação dos modelos neste arquivo permite que o SQLModel
reconheça todas as tabelas registradas na aplicação.
"""

from app.models.usuario import Usuario
from app.models.categoria import Categoria
from app.models.produto_global import ProdutoGlobal
from app.models.produto_usuario import ProdutoUsuario
from app.models.lista import Lista
from app.models.item_lista import ItemLista
from app.models.preco_estabelecimento import PrecoEstabelecimento


# Lista dos modelos disponíveis para importação.
__all__ = [
    "Usuario",
    "Categoria",
    "ProdutoGlobal",
    "ProdutoUsuario",
    "Lista",
    "ItemLista",
    "PrecoEstabelecimento",
]