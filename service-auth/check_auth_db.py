from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    r = conn.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'utilisateurs' "
        "AND column_name IN ('poste_id', 'branche', 'type_poste', 'id_ufr_gere')"
    ))
    rows = list(r)
    print("Colonnes UTS trouvees dans 'utilisateurs':")
    if not rows:
        print("  AUCUNE -> la migration n'a pas ete generee/appliquee.")
    for row in rows:
        print(f"  {row[0]} ({row[1]})")
