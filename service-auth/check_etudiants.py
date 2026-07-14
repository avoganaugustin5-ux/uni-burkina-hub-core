"""
Script diagnostic — affiche les étudiants sans inscription
et la liste des filières disponibles.
A exécuter depuis service-auth/ :
    python check_etudiants.py
"""
from database import SessionLocal
from models import Utilisateur, RoleEnum

db = SessionLocal()

# Étudiants sans inscription
etudiants = db.query(Utilisateur).filter(
    Utilisateur.role.in_([RoleEnum.ETUDIANT, RoleEnum.DELEGUE])
).all()

print(f"\n{'='*60}")
print(f"ÉTUDIANTS/DÉLÉGUÉS ({len(etudiants)} comptes)")
print(f"{'='*60}")
for u in etudiants:
    print(f"  id={u.id}  |  {u.prenom} {u.nom}  |  email={u.email}  |  id_univ={u.id_univ}")

# Filières disponibles
try:
    from models import Filiere, UFR
    filieres = db.query(Filiere).join(UFR).all()
    print(f"\n{'='*60}")
    print(f"FILIÈRES DISPONIBLES ({len(filieres)})")
    print(f"{'='*60}")
    for f in filieres[:20]:
        print(f"  id_filiere={f.id_filiere}  |  {f.nom_filiere}  |  id_ufr={f.id_ufr}")
    if len(filieres) > 20:
        print(f"  ... et {len(filieres)-20} autres")
except Exception as e:
    print(f"Erreur lecture filières: {e}")

db.close()
