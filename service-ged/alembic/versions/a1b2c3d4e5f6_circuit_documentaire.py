from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5f6'
down_revision = '4189d6178f88'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "DO $body$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'statutcircuitenum') THEN "
        "CREATE TYPE statutcircuitenum AS ENUM ('EN_COURS', 'EN_ATTENTE', 'VALIDE', 'REJETE', 'PUBLIE'); "
        "END IF; "
        "END $body$;"
    )
    op.execute(
        "DO $body$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actioncircuitenum') THEN "
        "CREATE TYPE actioncircuitenum AS ENUM ('ENVOYE', 'RECU', 'MODIFIE', 'REMPLACE', 'TRANSMIS', 'VALIDE', 'REJETE', 'RETOURNE'); "
        "END IF; "
        "END $body$;"
    )

    op.create_table(
        'document_circuits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('auteur_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('circuit', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('niveau_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('statut', postgresql.ENUM(
            'EN_COURS', 'EN_ATTENTE', 'VALIDE', 'REJETE', 'PUBLIE',
            name='statutcircuitenum', create_type=False
        ), nullable=False, server_default='EN_COURS'),
        sa.Column('date_envoi', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('date_derniere_action', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['auteur_id'], ['utilisateurs.id']),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id_doc']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'circuit_historique',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('circuit_id', sa.Integer(), nullable=False),
        sa.Column('etape_poste_id', sa.String(), nullable=False),
        sa.Column('action', postgresql.ENUM(
            'ENVOYE', 'RECU', 'MODIFIE', 'REMPLACE', 'TRANSMIS', 'VALIDE', 'REJETE', 'RETOURNE',
            name='actioncircuitenum', create_type=False
        ), nullable=False),
        sa.Column('commentaire', sa.Text(), nullable=True),
        sa.Column('date_action', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('duree_etape_secondes', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['circuit_id'], ['document_circuits.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('circuit_historique')
    op.drop_table('document_circuits')
    op.execute('DROP TYPE IF EXISTS actioncircuitenum')
    op.execute('DROP TYPE IF EXISTS statutcircuitenum')
