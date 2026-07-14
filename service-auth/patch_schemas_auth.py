# Ce script patch service-auth/schemas.py en place
# A executer depuis C:\projets\UniBurkina_Hub\service-auth\

content = open('schemas.py', encoding='utf-8').read()

old = "    id_ufr_gere: Optional[int] = None"
new = """    id_ufr_gere: Optional[int] = None
    # ── AJOUT UTS — inscription académique (étudiant/délégué) ──
    id_filiere:   Optional[int] = None   # filière choisie lors de l'inscription
    niveau_etude: Optional[str] = None   # L1, L2, L3, M1, M2"""

if old in content:
    content = content.replace(old, new, 1)
    open('schemas.py', 'w', encoding='utf-8').write(content)
    print("OK — id_filiere et niveau_etude ajoutés à RegisterRequest")
else:
    print("ERREUR : ancienne chaîne introuvable — vérifiez manuellement")
