import sys

try:
    import psycopg2
except ImportError:
    print("[ERREUR] psycopg2 non installe dans ce venv.")
    print("Installez-le : .\\venv\\Scripts\\pip.exe install psycopg2-binary==2.9.9")
    sys.exit(1)

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "uniburkina_db",
    "user":     "uniburkina_admin",
    "password": "UTS_Burkina2025!"
}

STEPS = [
    {
        "label": "Ajout CHEF_DEPARTEMENT dans roleenum",
        "sql": """
            DO $$
            BEGIN
                ALTER TYPE roleenum ADD VALUE 'CHEF_DEPARTEMENT';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE 'CHEF_DEPARTEMENT deja present — ignore.';
            END;
            $$
        """,
        "ignore_error": True,
    },
    {
        "label": "Ajout colonne perimetre_ufr dans utilisateurs",
        "sql": """
            ALTER TABLE utilisateurs
                ADD COLUMN IF NOT EXISTS perimetre_ufr INTEGER
        """,
        "ignore_error": False,
    },
    {
        "label": "Commentaire sur perimetre_ufr",
        "sql": """
            COMMENT ON COLUMN utilisateurs.perimetre_ufr IS
                'UFR de perimetre pour DELEGUE et CHEF_DEPARTEMENT. NULL = perimetre global.'
        """,
        "ignore_error": True,
    },
]

VERIFICATIONS = [
    {
        "label": "Colonne perimetre_ufr presente",
        "sql": """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'utilisateurs' AND column_name = 'perimetre_ufr'
        """,
        "expect_rows": True,
    },
    {
        "label": "Roles disponibles dans roleenum",
        "sql": "SELECT unnest(enum_range(NULL::roleenum)) AS role",
        "expect_rows": True,
    },
]


def run():
    print("=" * 60)
    print("UniBurkina Hub - Migration BDD v2.1")
    print("=" * 60)

    print("\n[1/3] Connexion a PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        print("      [OK] Connexion etablie - uniburkina_db@localhost:5432")
    except psycopg2.OperationalError as e:
        print(f"      [ERREUR] {e}")
        print("\nVerifiez que PostgreSQL est demarre et accessible sur localhost:5432")
        sys.exit(1)

    print("\n[2/3] Execution des migrations...")
    errors = 0
    for i, step in enumerate(STEPS, 1):
        label = step["label"]
        print(f"      [{i}/{len(STEPS)}] {label}...", end=" ", flush=True)
        try:
            cur.execute(step["sql"])
            print("OK")
        except Exception as e:
            if step.get("ignore_error"):
                print(f"NOTICE : {str(e).strip()[:80]}")
            else:
                print(f"ERREUR : {e}")
                errors += 1

    print("\n[3/3] Verifications post-migration...")
    for v in VERIFICATIONS:
        print(f"      {v['label']} :")
        try:
            cur.execute(v["sql"])
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    print(f"        -> {', '.join(str(c) for c in row)}")
            else:
                print("        -> (aucun resultat)")
        except Exception as e:
            print(f"        -> ERREUR : {e}")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    if errors == 0:
        print("Migration v2.1 terminee avec SUCCES !")
        print("\nEtapes suivantes :")
        print("  1. Ajouter CHEF_DEPARTEMENT dans service-auth/models.py (RoleEnum)")
        print("  2. Redemarrer service-auth (port 8001)")
        print("  3. Copier service_ged_main.py -> service-ged/main.py")
        print("  4. Redemarrer service-ged (port 8002)")
    else:
        print(f"Migration terminee avec {errors} erreur(s) - verifiez les messages ci-dessus")
    print("=" * 60)


if __name__ == "__main__":
    run()
