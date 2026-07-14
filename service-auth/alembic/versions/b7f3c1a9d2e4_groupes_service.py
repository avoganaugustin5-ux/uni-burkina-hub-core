"""Ajout cloisonnement documentaire par service (groupes_service)

AJOUT SECURITE UTS — Point 4/5 : cloisonnement des documents par service
et code de securite partage.

C'est la TOUTE PREMIERE migration Alembic de service-auth (aucun historique
Alembic n'existait avant — les tables utilisateurs/universites/etc. ont ete
creees via Base.metadata.create_all(), pas via Alembic). down_revision=None
est donc correct : cette migration ne cree QUE les 2 nouvelles tables et ne
touche a rien d'existant.

Revision ID: b7f3c1a9d2e4
Revises:
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b7f3c1a9d2e4"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "groupes_service",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role_code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("branche", sa.String(length=50), nullable=True),
        sa.Column("couleur", sa.String(length=20), nullable=True),
        sa.Column("code_acces_hash", sa.String(length=255), nullable=True),
        sa.Column("date_creation", sa.DateTime(), nullable=True),
        sa.Column("date_modification", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "groupes_service_membres",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("groupe_id", sa.Integer(),
                  sa.ForeignKey("groupes_service.id"), nullable=False),
        sa.Column("poste_id", sa.String(length=50), nullable=False, unique=True),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("branche_supervisee", sa.String(length=50), nullable=True),
    )

    op.create_index(
        "ix_groupes_service_membres_poste_id",
        "groupes_service_membres", ["poste_id"], unique=True,
    )


def downgrade():
    op.drop_index("ix_groupes_service_membres_poste_id", table_name="groupes_service_membres")
    op.drop_table("groupes_service_membres")
    op.drop_table("groupes_service")
