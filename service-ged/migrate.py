"""
migrate.py — Migration UniBurkina Hub (sans pgAdmin)

Utilisation :
    1. Place ce fichier n'importe où (ex: C:\\projets\\UniBurkina_Hub\\migrate.py)
    2. Ouvre un terminal DANS un dossier qui a un venv avec sqlalchemy + psycopg2
       (n'importe lequel de tes services fait l'affaire : service-ged, service-ocr...)
    3. Active ce venv puis lance :
           python migrate.py

Le script affiche chaque étape et s'arrête proprement en cas d'erreur,
sans jamais rien exécuter à l'aveugle.
"""
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://uniburkina_admin:UTS_Burkina2025!@localhost:5432/uniburkina_db"
)

ETAPES = [
    (
        "Ajout colonne documents.visibilite",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS visibilite VARCHAR;"
    ),
    (
        "Suppression ancienne colonne documents_ocr.id_utilisateur (Integer, vide)",
        "ALTER TABLE documents_ocr DROP COLUMN IF EXISTS id_utilisateur;"
    ),
    (
        "Recreation documents_ocr.id_utilisateur en UUID",
        "ALTER TABLE documents_ocr ADD COLUMN id_utilisateur UUID;"
    ),
    (
        "Verification/ajout de TOUTES les colonnes document_circuits (exhaustif, cf. models.py)",
        """
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS document_id INTEGER;
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS auteur_id UUID;
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS auteur_poste_id VARCHAR(50);
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS circuit JSONB;
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS niveau_index INTEGER DEFAULT 0;
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS statut VARCHAR(20);
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS objet VARCHAR(300);
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS commentaire_init TEXT;
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS date_envoi TIMESTAMP;
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS date_derniere_action TIMESTAMP;
        ALTER TABLE document_circuits ADD COLUMN IF NOT EXISTS date_cloture TIMESTAMP;
        """
    ),
    (
        "Suppression de l'ancienne colonne circuit_historique.etape_poste_id (NOT NULL, "
        "obsolete, plus jamais renseignee -> bloquait tout insert)",
        "ALTER TABLE circuit_historique DROP COLUMN IF EXISTS etape_poste_id;"
    ),
    (
        "Verification/ajout de TOUTES les colonnes circuit_historique (exhaustif, cf. models.py)",
        """
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS circuit_id INTEGER;
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS acteur_id UUID;
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS acteur_poste_id VARCHAR(50);
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS acteur_nom VARCHAR(200);
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS action VARCHAR(20);
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS niveau_avant INTEGER;
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS niveau_apres INTEGER;
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS nouveau_fichier VARCHAR(500);
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS commentaire TEXT;
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS date_action TIMESTAMP;
        ALTER TABLE circuit_historique ADD COLUMN IF NOT EXISTS duree_etape_secondes INTEGER;
        """
    ),
]

def main():
    print(f"Connexion a : {DATABASE_URL.split('@')[-1]}")
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            for description, sql in ETAPES:
                print(f"\n-> {description}")
                print(f"   SQL : {sql}")
                conn.execute(text(sql))
                conn.commit()
                print("   OK")
    except Exception as e:
        print(f"\n!!! ERREUR : {e}")
        print("Rien apres cette etape n'a ete execute. Colle-moi ce message d'erreur.")
        return

    print("\n✅ Migration terminee avec succes.")
    print("Verification :")

    with engine.connect() as conn:
        cols_documents = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'documents' AND column_name = 'visibilite';"
        )).fetchall()
        cols_ocr = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'documents_ocr' AND column_name = 'id_utilisateur';"
        )).fetchall()

        print(f"  documents.visibilite       -> {cols_documents}")
        print(f"  documents_ocr.id_utilisateur -> {cols_ocr}")

        cols_circuits = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'document_circuits' ORDER BY ordinal_position;"
        )).fetchall()
        cols_histo = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'circuit_historique' ORDER BY ordinal_position;"
        )).fetchall()
        print(f"\n  document_circuits ({len(cols_circuits)} colonnes) :")
        for c in cols_circuits: print(f"    - {c[0]} ({c[1]})")
        print(f"\n  circuit_historique ({len(cols_histo)} colonnes) :")
        for c in cols_histo: print(f"    - {c[0]} ({c[1]})")

if __name__ == "__main__":
    main()
