# -*- coding: utf-8 -*-
"""
Migration manuelle (sans Alembic) pour service-auth.
Ajoute les colonnes UTS sur 'utilisateurs' + les nouvelles valeurs de RoleEnum.
Idempotent : peut être relancé sans risque (IF NOT EXISTS / vérifications).

Usage :
    cd service-auth
    python migrate_auth_uts.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(encoding="utf-8")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERREUR : DATABASE_URL introuvable dans .env")
    raise SystemExit(1)

engine = create_engine(DATABASE_URL)

NOUVELLES_VALEURS_ROLE = [
    "CHEF_DEPARTEMENT", "VP_EIP", "VP_RCU", "SG",
    "CABINET", "DIRECTEUR", "EMPLOYE",
]

NOUVELLES_COLONNES = [
    ("poste_id", "VARCHAR(50)"),
    ("branche", "VARCHAR(50)"),
    ("type_poste", "VARCHAR(30)"),
    ("id_ufr_gere", "INTEGER REFERENCES ufrs(id_ufr)"),
]

def trouver_nom_enum(conn):
    """Trouve le nom réel du type ENUM utilisé par la colonne 'role'."""
    row = conn.execute(text("""
        SELECT udt_name FROM information_schema.columns
        WHERE table_name = 'utilisateurs' AND column_name = 'role'
    """)).fetchone()
    return row[0] if row else None

def main():
    with engine.begin() as conn:
        # 1. Colonnes
        for nom, ddl_type in NOUVELLES_COLONNES:
            print(f"Colonne '{nom}' -> ajout si absente...")
            conn.execute(text(
                f"ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS {nom} {ddl_type}"
            ))

        # 2. Enum role
        enum_name = trouver_nom_enum(conn)
        if not enum_name:
            print("ATTENTION : impossible de déterminer le type ENUM de 'role'. "
                  "Vérifiez manuellement.")
        else:
            print(f"Type ENUM détecté : {enum_name}")
            existantes = conn.execute(text(f"""
                SELECT enumlabel FROM pg_enum
                WHERE enumtypid = '{enum_name}'::regtype
            """)).scalars().all()
            for val in NOUVELLES_VALEURS_ROLE:
                if val in existantes:
                    print(f"  - {val} : déjà présente")
                else:
                    # ALTER TYPE ... ADD VALUE ne peut pas être dans un bloc transactionnel
                    # avec d'autres opérations sur le même type dans certaines versions PG,
                    # donc on l'exécute en autocommit séparé ci-dessous.
                    pass

    # ALTER TYPE ADD VALUE doit être hors transaction explicite (PG < 12) -> connexion autocommit
    if enum_name:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            existantes = conn.execute(text(f"""
                SELECT enumlabel FROM pg_enum
                WHERE enumtypid = '{enum_name}'::regtype
            """)).scalars().all()
            for val in NOUVELLES_VALEURS_ROLE:
                if val not in existantes:
                    print(f"  + ajout de la valeur ENUM : {val}")
                    conn.execute(text(f"ALTER TYPE {enum_name} ADD VALUE '{val}'"))

    print("\nTerminé. Relancez check_auth_db.py pour confirmer.")

if __name__ == "__main__":
    main()
