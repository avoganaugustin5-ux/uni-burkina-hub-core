# ==============================================================================
# service-auth/seed_groupes_service.py — UniBurkina Hub
# AJOUT SECURITE UTS — Peuple les groupes de service (cloisonnement documentaire)
# a partir de la structure deja definie dans uts_org_data.js (UTS_GROUPES_INSCRIPTION).
#
# A executer UNE FOIS apres la migration Alembic qui cree les tables
# groupes_service / groupes_service_membres :
#
#   cd service-auth && python seed_groupes_service.py
#
# Idempotent : peut etre relance sans dupliquer les groupes/membres existants
# (il met a jour le label/branche si le groupe existe deja).
# ==============================================================================

from database import SessionLocal
from models import GroupeService, GroupeServiceMembre

# Reproduction fidele de UTS_GROUPES_INSCRIPTION (frontend/static/js/uts_org_data.js)
# branche : reprise du champ `branche` de UTS_ORG pour les membres de chaque groupe
# branche_supervisee : uniquement pour les chefs de branche (vision globale validee)
GROUPES = [
    {
        "role_code": "DIRECTION",
        "label": "Direction — Presidence et Vice-Presidences",
        "description": "Presidence et Vice-Presidences",
        "branche": None,
        "couleur": "#C0392B",
        "membres": [
            {"poste_id": "president", "label": "President de l'Universite", "branche_supervisee": None},
            {"poste_id": "vp-eip", "label": "Vice-President EIP", "branche_supervisee": "VP-EIP"},
            {"poste_id": "vp-rcu", "label": "Vice-President RCU", "branche_supervisee": "VP-RCU"},
            {"poste_id": "sg", "label": "Secretaire General", "branche_supervisee": "SG"},
        ],
    },
    {
        "role_code": "CABINET",
        "label": "Cabinet du President",
        "description": "Membres du Cabinet (cascade CCAB -> PRCP incluse)",
        "branche": "Cabinet",
        "couleur": "#922B21",
        "membres": [
            {"poste_id": "ccab", "label": "Chef de Cabinet (CCAB)"},
            {"poste_id": "cj", "label": "Conseiller Juridique (CJ)"},
            {"poste_id": "cat", "label": "Charges d'Appui Technique (CAT)"},
            {"poste_id": "protocole", "label": "Protocole"},
            {"poste_id": "sp-cab", "label": "Secretariat Particulier du Cabinet"},
            {"poste_id": "sc", "label": "Service de la Communication (SC)"},
            {"poste_id": "ssu", "label": "Service de la Securite Universitaire (SSU)"},
            {"poste_id": "ci", "label": "Controle Interne (CI)"},
            {"poste_id": "ciaq", "label": "Cellule Interne d'Assurance Qualite (CIAQ)"},
            {"poste_id": "prcp", "label": "Personne Responsable de la Commande Publique (PRCP)"},
            {"poste_id": "smtpi", "label": "Service des Marches de Travaux (SMTPI)"},
            {"poste_id": "smfpc", "label": "Service des Marches de Fournitures (SMFPC)"},
            {"poste_id": "ssem", "label": "Service de Suivi de l'Execution des Marches (SSEM)"},
        ],
    },
    {
        "role_code": "EMPLOYE_DSI",
        "label": "VP-EIP — Direction des Systemes d'Information (DSI)",
        "description": "Informatique & Reseaux",
        "branche": "VP-EIP",
        "couleur": "#1E8449",
        "membres": [
            {"poste_id": "dsi", "label": "Directeur DSI"},
            {"poste_id": "seap", "label": "Service des Etudes et Applications (SEAp)"},
            {"poste_id": "srss", "label": "Service Reseaux, Systemes et Securite (SRSS)"},
            {"poste_id": "ssm", "label": "Service Support et Maintenance (SSM)"},
            {"poste_id": "sp-vpeip", "label": "Secretariat Particulier VP-EIP"},
        ],
    },
    {
        "role_code": "EMPLOYE_DEI",
        "label": "VP-EIP — Direction des Enseignements (DEI)",
        "description": "Pedagogie & Programmes",
        "branche": "VP-EIP",
        "couleur": "#1A5276",
        "membres": [
            {"poste_id": "dei", "label": "Directeur DEI"},
            {"poste_id": "spfee", "label": "Service Programmes, Formations et Examens (SPFEE)"},
            {"poste_id": "spu", "label": "Service de la Pedagogie Universitaire (SPU)"},
        ],
    },
    {
        "role_code": "EMPLOYE_DPE",
        "label": "VP-EIP — Direction Professionnalisation (DPE)",
        "description": "Insertion & Entrepreneuriat",
        "branche": "VP-EIP",
        "couleur": "#1A5276",
        "membres": [
            {"poste_id": "dpe", "label": "Directeur DPE"},
            {"poste_id": "spi", "label": "Service de la Professionnalisation et de l'Insertion (SPI)"},
            {"poste_id": "scie", "label": "Service Creativite, Incubation et Entrepreneuriat (SCIE)"},
        ],
    },
    {
        "role_code": "EMPLOYE_DAOI",
        "label": "VP-EIP — Direction Affaires Academiques (DAOI)",
        "description": "Orientation & Inscriptions",
        "branche": "VP-EIP",
        "couleur": "#1A5276",
        "membres": [
            {"poste_id": "daoi", "label": "Directeur DAOI"},
            {"poste_id": "siir", "label": "Service Information, Inscriptions et Reinscriptions (SIIR)"},
            {"poste_id": "std", "label": "Service Titres et Diplomes (STD)"},
        ],
    },
    {
        "role_code": "EMPLOYE_DRV",
        "label": "VP-RCU — Direction Recherche et Valorisation (DRV)",
        "description": "Recherche scientifique",
        "branche": "VP-RCU",
        "couleur": "#154360",
        "membres": [
            {"poste_id": "drv", "label": "Directeur DRV"},
            {"poste_id": "sar", "label": "Service d'Appui a la Recherche (SAR)"},
            {"poste_id": "svrr", "label": "Service Valorisation des Resultats (SVRR)"},
            {"poste_id": "sp-vprcu", "label": "Secretariat Particulier VP-RCU"},
        ],
    },
    {
        "role_code": "EMPLOYE_DCPE",
        "label": "VP-RCU — Direction Cooperation Universitaire (DCPE)",
        "description": "Cooperation & Promotion",
        "branche": "VP-RCU",
        "couleur": "#154360",
        "membres": [
            {"poste_id": "dcpe", "label": "Directeur DCPE"},
            {"poste_id": "scu", "label": "Service Cooperation Universitaire (SCU)"},
            {"poste_id": "spe-dcpe", "label": "Service Promotion des Enseignants (SPE)"},
        ],
    },
    {
        "role_code": "EMPLOYE_DPRUE",
        "label": "VP-RCU — Direction Prospective (DPRUE)",
        "description": "Relations Universite-Entreprises",
        "branche": "VP-RCU",
        "couleur": "#154360",
        "membres": [
            {"poste_id": "dprue", "label": "Directeur DPRUE"},
            {"poste_id": "spec", "label": "Service Prospective, Etudes et Consultation (SPEC)"},
            {"poste_id": "srue", "label": "Service Relations Universite-Entreprises (SRUE)"},
        ],
    },
    {
        "role_code": "EMPLOYE_SG_SERVICES",
        "label": "Secretariat General — Services directs",
        "description": "SP, BE, SCC, SR, SA, SSAC",
        "branche": "SG",
        "couleur": "#7D6608",
        "membres": [
            {"poste_id": "sp-sg", "label": "Secretariat Particulier du SG (SP-SG)"},
            {"poste_id": "be", "label": "Bureau d'Etudes (BE)"},
            {"poste_id": "scc", "label": "Service Central du Courrier (SCC)"},
            {"poste_id": "sr", "label": "Service de la Reprographie (SR)"},
            {"poste_id": "sa", "label": "Service des Archives (SA)"},
            {"poste_id": "ssac", "label": "Service Sports, Arts et Culture (SSAC)"},
        ],
    },
    {
        "role_code": "EMPLOYE_DAF",
        "label": "Secretariat General — Administration & Finances (DAF)",
        "description": "Gestion financiere",
        "branche": "SG",
        "couleur": "#6E2F0E",
        "membres": [
            {"poste_id": "daf", "label": "Directeur DAF"},
            {"poste_id": "saf", "label": "Service Administratif et Financier (SAF)"},
            {"poste_id": "scp", "label": "Service Commande Publique (SCP)"},
            {"poste_id": "ra", "label": "Regie d'Avance (RA)"},
        ],
    },
    {
        "role_code": "EMPLOYE_DEP",
        "label": "Secretariat General — Etudes et Planification (DEP)",
        "description": "Planification & Statistiques",
        "branche": "SG",
        "couleur": "#6E2F0E",
        "membres": [
            {"poste_id": "dep", "label": "Directeur DEP"},
            {"poste_id": "spse", "label": "Service Planification, Statistiques et Evaluation (SPSE)"},
            {"poste_id": "ssd", "label": "Service Suivi et Documentation (SSD)"},
        ],
    },
    {
        "role_code": "EMPLOYE_DRH",
        "label": "Secretariat General — Ressources Humaines (DRH)",
        "description": "Personnel & Carrieres",
        "branche": "SG",
        "couleur": "#6E2F0E",
        "membres": [
            {"poste_id": "drh", "label": "Directeur DRH"},
            {"poste_id": "ssgc", "label": "Service Solde et Gestion des Carrieres (SSGC)"},
            {"poste_id": "sgpep", "label": "Service Gestion Previsionnelle des Emplois (SGPEP)"},
        ],
    },
    {
        "role_code": "EMPLOYE_BCMP",
        "label": "Secretariat General — Comptabilite Matieres (BCMP)",
        "description": "Patrimoine & Matieres",
        "branche": "SG",
        "couleur": "#6E2F0E",
        "membres": [
            {"poste_id": "bcmp", "label": "Bureau Comptable Matieres Principal (BCMP)"},
            {"poste_id": "smcg", "label": "Service Matiere, Cessions et Gestion (SMCG)"},
            {"poste_id": "saie", "label": "Service Affaires Immobilieres et Environnement (SAIE)"},
        ],
    },
    {
        "role_code": "EMPLOYE_BUC",
        "label": "Secretariat General — Bibliotheque (BUC)",
        "description": "Documentation & Edition",
        "branche": "SG",
        "couleur": "#6E2F0E",
        "membres": [
            {"poste_id": "buc", "label": "Directeur BUC"},
            {"poste_id": "sato", "label": "Service Acquisitions et Traitement des Ouvrages (SATO)"},
            {"poste_id": "sd", "label": "Service de la Documentation (SD)"},
            {"poste_id": "dpu", "label": "Directeur Presses Universitaires (DPU)"},
            {"poste_id": "smc", "label": "Service Impression et Mise en Page (SMC)"},
            {"poste_id": "se", "label": "Service de l'Edition (SE)"},
        ],
    },
]


def seed():
    db = SessionLocal()
    try:
        for g in GROUPES:
            groupe = db.query(GroupeService).filter_by(role_code=g["role_code"]).first()
            if not groupe:
                groupe = GroupeService(
                    role_code=g["role_code"], label=g["label"],
                    description=g["description"], branche=g["branche"],
                    couleur=g["couleur"],
                )
                db.add(groupe)
                db.flush()
                print(f"[CREE] Groupe {g['role_code']}")
            else:
                groupe.label = g["label"]
                groupe.description = g["description"]
                groupe.branche = g["branche"]
                groupe.couleur = g["couleur"]
                print(f"[MAJ]  Groupe {g['role_code']} (deja existant)")

            for m in g["membres"]:
                membre = db.query(GroupeServiceMembre).filter_by(poste_id=m["poste_id"]).first()
                if not membre:
                    membre = GroupeServiceMembre(
                        groupe_id=groupe.id, poste_id=m["poste_id"],
                        label=m.get("label"),
                        branche_supervisee=m.get("branche_supervisee"),
                    )
                    db.add(membre)
                else:
                    membre.groupe_id = groupe.id
                    membre.label = m.get("label")
                    membre.branche_supervisee = m.get("branche_supervisee")
            db.commit()
        print("\nSeed des groupes de service termine avec succes.")
        print("IMPORTANT : aucun code de securite n'est defini par defaut.")
        print("Un administrateur doit definir un code pour chaque groupe via :")
        print("  PUT /auth/groupes-service/{groupe_id}/code   { \"code\": \"...\" }")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
