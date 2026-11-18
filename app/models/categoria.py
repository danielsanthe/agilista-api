"""
Modelo de Categoria do AgiLista.

Representa as categorias utilizadas para organizar os produtos.
Uma categoria pode ser padrão (compartilhada por todos os usuários)
ou personalizada (pertencente a um usuário específico).
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class Categoria(SQLModel, table=True):

    # Nome da tabela que será criada no banco de dados.
    __tablename__ = "categorias"

    # Identificador da categoria no banco de dados do servidor.
    id_categoria: Optional[int] = Field(default=None, primary_key=True)

    # Identificador da categoria no banco local do aplicativo.
    servidor_id: Optional[int] = Field(default=None)

    # NULL representa uma categoria padrão, compartilhada.
    # Quando preenchido, identifica o usuário proprietário da categoria.
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuarios.id_usuario", ondelete="CASCADE")

    # Nome que será exibido no aplicativo.
    nome_categoria: str = Field(max_length=100)

    # Indica se a categoria está ativa (1) ou inativa (0).
    ativo: int = Field(default=1)

    # Situação geral da categoria, conforme o aplicativo.
    status_categoria: str = Field(default="ATIVO", max_length=20)

    # Campo mantido para compatibilidade com a estrutura SQLite local.
    # No servidor, o controle de sincronização será feito pela API.
    flag_sincronizado: int = Field(default=1)