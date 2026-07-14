# ==============================================================================
# seed_ujkz.py — UniBurkina Hub — Exécution du seed UFR/Filières (sans pgAdmin)
# AVOGAN Koudjo Augustin Sandaogo
#
# Contourne pgAdmin : se connecte directement à PostgreSQL via SQLAlchemy
# (la même bibliothèque déjà utilisée par service-auth) et exécute le
# script seed_ujkz.sql tel quel, dans une seule transaction.
#
# Usage :
#   1. Place ce fichier dans le même dossier que seed_ujkz.sql
#      (par exemple service-auth/)
#   2. pip install sqlalchemy psycopg2-binary python-dotenv   (si pas déjà fait)
#   3. python seed_ujkz.py
#
# Le script ne fait aucun UPDATE/DELETE — uniquement des INSERT, donc
# aucun risque pour les données déjà en place (Thomas SANKARA notamment).
# ==============================================================================

import os
import sys
from pathlib import Path

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("[ERREUR] SQLAlchemy n'est pas installé.")
    print("Lance d'abord : pip install sqlalchemy psycopg2-binary python-dotenv")
    sys.exit(1)

# ── Charger .env si présent (cohérent avec service-auth) ────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # pas grave si python-dotenv n'est pas installé, on a un fallback

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://uniburkina_admin:UTS_Burkina2025!@localhost:5432/uniburkina_db"
)

SQL_FILE = Path(__file__).parent / "seed_ujkz.sql"

def main():
    if not SQL_FILE.exists():
        print(f"[ERREUR] Fichier introuvable : {SQL_FILE}")
        print("Place seed_ujkz.sql dans le même dossier que ce script.")
        sys.exit(1)

    sql_script = SQL_FILE.read_text(encoding="utf-8")

    print(f"Connexion à : {DATABASE_URL.split('@')[-1]}")  # masque user:pass dans le log
    engine = create_engine(DATABASE_URL)

    try:
        # exec_driver_sql() ne gère pas bien certains scripts multi-statements
        # avec DO $$ ... $$ ; on passe par la connexion brute psycopg2 (raw_connection)
        # qui exécute le script tel que psql le ferait.
        raw_conn = engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            cursor.execute(sql_script)
            raw_conn.commit()
            cursor.close()
        finally:
            raw_conn.close()

        print("\n✅ Seed exécuté avec succès — UFR et filières de Joseph KI-ZERBO créées.")
        print("\nVérification :")

        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT f.nom_ufr, f.code_ufr, COUNT(fil.id_filiere) AS nb_filieres
                FROM ufrs f
                LEFT JOIN filieres fil ON fil.id_ufr = f.id_ufr
                WHERE f.id_univ = 2
                GROUP BY f.nom_ufr, f.code_ufr
                ORDER BY f.nom_ufr
            """))
            for row in result:
                print(f"  - {row.nom_ufr:55s} ({row.code_ufr:18s}) : {row.nb_filieres} filière(s)")

    except Exception as e:
        print(f"\n[ERREUR] L'exécution a échoué : {e}")
        print("Aucune modification n'a été appliquée (transaction annulée).")
        sys.exit(1)


if __name__ == "__main__":
    main()
