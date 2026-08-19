"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

Portability rules (this project runs migrations on PostgreSQL AND SQLite):
- UUID columns: sa.Uuid()
- JSON columns: sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
- enums: sa.Enum(..., name="...")
- ALTER TABLE: use op.batch_alter_table(...) so SQLite works.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
