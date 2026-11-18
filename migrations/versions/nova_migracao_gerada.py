"""Altera exclusao de produto em itens lista para ON DELETE SET NULL.

Revision ID: b2c3d4e5f6a7
Revises: 9ad1abdef0ae
Create Date: 2026-11-02 12:15:00.000000

"""
from typing import Sequence, Union
from alembic import op

# Identificadores de revisão do Alembic para encadeamento do histórico de migrações
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "9ad1abdef0ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Convenção explícita de nomes para resolver chaves estrangeiras sem nome no SQLite
NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
}


def upgrade() -> None:
    """
    Aplica ON DELETE SET NULL à chave estrangeira produto_id na tabela itens_lista.
    
    Utiliza op.batch_alter_table com NAMING_CONVENTION para permitir que o SQLite
    reconstrua a tabela mapeando a FK legada que não possuía nome explícito.
    """
    with op.batch_alter_table(
        "itens_lista",
        naming_convention=NAMING_CONVENTION
    ) as batch_op:
        # 1. Remove a restrição legada refletida via convenção de nomes
        batch_op.drop_constraint(
            "fk_itens_lista_produto_id_produtos_usuario",
            type_="foreignkey"
        )
        
        # 2. Recria a restrição de chave estrangeira com a regra ON DELETE SET NULL
        batch_op.create_foreign_key(
            "fk_itens_lista_produto_id_produtos_usuario",
            "produtos_usuario",
            ["produto_id"],
            ["id_produto_usuario"],
            ondelete="SET NULL"
        )


def downgrade() -> None:
    """
    Reverte a chave estrangeira produto_id para o estado original (sem ON DELETE).
    """
    with op.batch_alter_table(
        "itens_lista",
        naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_itens_lista_produto_id_produtos_usuario",
            type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_itens_lista_produto_id_produtos_usuario",
            "produtos_usuario",
            ["produto_id"],
            ["id_produto_usuario"]
        )