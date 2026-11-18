"""
adicionar_categoria_id_em_produtos_globais

Adiciona a associação obrigatória entre produtos globais
e categorias padrão do sistema.

Revision ID: 32c7d25b9668
Revises: 516579b042ff
Create Date: 2026-11-03 16:04:49.783662
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# =====================================================================
# IDENTIFICAÇÃO DA MIGRAÇÃO
# =====================================================================

revision: str = '32c7d25b9668'

down_revision: Union[str, Sequence[str], None] = '516579b042ff'

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# =====================================================================
# MIGRAÇÃO: ADICIONAR CATEGORIA AOS PRODUTOS GLOBAIS
# =====================================================================

def upgrade() -> None:
    """
    Adiciona a coluna categoria_id à tabela produtos_globais.

    A coluna:
    - É obrigatória (NOT NULL).
    - Referencia categorias.id_categoria.
    - Impede a exclusão de uma categoria ainda utilizada.
    """
    bind = op.get_bind()
    recreate_mode = 'always' if bind.dialect.name == 'sqlite' else 'auto'

    with op.batch_alter_table(
        'produtos_globais',
        recreate=recreate_mode
    ) as batch_op:

        # Adiciona a identificação obrigatória da categoria.
        batch_op.add_column(
            sa.Column(
                'categoria_id',
                sa.Integer(),
                nullable=False
            )
        )

        # Cria a chave estrangeira com nome explícito.
        batch_op.create_foreign_key(
            'fk_produtos_globais_categoria_id_categorias',
            'categorias',
            ['categoria_id'],
            ['id_categoria'],
            ondelete='RESTRICT'
        )


# =====================================================================
# REVERSÃO DA MIGRAÇÃO
# =====================================================================

def downgrade() -> None:
    """
    Remove a associação entre produtos globais e categorias.

    A coluna e sua chave estrangeira são removidas.
    """
    bind = op.get_bind()
    recreate_mode = 'always' if bind.dialect.name == 'sqlite' else 'auto'

    with op.batch_alter_table(
        'produtos_globais',
        recreate=recreate_mode
    ) as batch_op:

        # Remove primeiro a chave estrangeira.
        batch_op.drop_constraint(
            'fk_produtos_globais_categoria_id_categorias',
            type_='foreignkey'
        )

        # Depois remove a coluna da tabela.
        batch_op.drop_column('categoria_id')