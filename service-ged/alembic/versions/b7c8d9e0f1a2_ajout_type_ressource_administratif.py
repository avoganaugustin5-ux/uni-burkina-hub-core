"""ajout_type_ressource_administratif

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-06-30

AJOUT UTS — ajoute la valeur 'ADMINISTRATIF' à l'enum typeressourceenum
pour distinguer les documents du circuit administratif (Cabinet, SG,
Vice-Présidences, Directions, Services) des ressources académiques
(COURS / TD / EXAMEN / ARCHIVE).
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TYPE ... ADD VALUE doit s'exécuter en autocommit (hors transaction)
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE typeressourceenum ADD VALUE IF NOT EXISTS 'ADMINISTRATIF'")


def downgrade():
    # PostgreSQL ne permet pas de retirer une valeur d'ENUM facilement.
    # Aucune action de downgrade fournie (cohérent avec les contraintes du projet).
    pass
