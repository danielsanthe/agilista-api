
"""adicionar_tipo_usuario_em_usuarios

Revision ID: 516579b042ff
Revises: b2c3d4e5f6a7
Create Date: 2026-11-03 10:44:10.331093

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '516579b042ff'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona o perfil de acesso dos usuários."""

    op.add_column(
        'usuarios',
        sa.Column(
            'tipo_usuario',
            sa.String(length=20),
            nullable=False,
            server_default='COMUM'
        )
    )


def downgrade() -> None:
    """Remove o perfil de acesso dos usuários."""

    op.drop_column('usuarios', 'tipo_usuario')
