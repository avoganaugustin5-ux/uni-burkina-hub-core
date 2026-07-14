"""Ajout delai de traitement + tracabilite renforcee (hash/IP/user-agent)

AJOUT SECURITE UTS — Points 2 et 3.

CORRIGE — cette migration chaine desormais apres b7c8d9e0f1a2 (ajout du
type ADMINISTRATIF), qui est la tete reelle actuelle de service-ged.

Revision ID: c4d8e2f1a6b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

revision = "c4d8e2f1a6b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade():
    # Point 3 — delai de traitement du circuit
    op.add_column("document_circuits",
                  sa.Column("date_limite", sa.DateTime(), nullable=True))

    # Point 2 — tracabilite renforcee
    op.add_column("documents",
                  sa.Column("hash_fichier", sa.String(length=64), nullable=True))
    op.add_column("circuit_historique",
                  sa.Column("hash_fichier", sa.String(length=64), nullable=True))
    op.add_column("circuit_historique",
                  sa.Column("ip_address", sa.String(length=50), nullable=True))
    op.add_column("circuit_historique",
                  sa.Column("user_agent", sa.String(length=500), nullable=True))


def downgrade():
    op.drop_column("circuit_historique", "user_agent")
    op.drop_column("circuit_historique", "ip_address")
    op.drop_column("circuit_historique", "hash_fichier")
    op.drop_column("documents", "hash_fichier")
    op.drop_column("document_circuits", "date_limite")
