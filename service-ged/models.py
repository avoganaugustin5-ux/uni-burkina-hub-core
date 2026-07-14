from sqlalchemy import (Column, String, Boolean, DateTime,
                        ForeignKey, Enum, Integer, Text, BigInteger)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid, enum

Base = declarative_base()

# ── Enums ──────────────────────────────────────────────────
class TypeRessourceEnum(str, enum.Enum):
    COURS         = "COURS"
    TD            = "TD"
    EXAMEN        = "EXAMEN"
    ARCHIVE       = "ARCHIVE"
    ADMINISTRATIF = "ADMINISTRATIF"  # AJOUT UTS — documents du circuit documentaire (Cabinet, SG, Directions...)

class StatutDocumentEnum(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE     = "VALIDE"
    REFUSE     = "REFUSE"

# ── AJOUT — Visibilité d'un document administratif ────────
class VisibiliteDocumentEnum(str, enum.Enum):
    PRIVE  = "PRIVE"   # restreint aux personnes concernées (auteur + acteurs du circuit)
    PUBLIC = "PUBLIC"  # visible par tous les utilisateurs du système

# ── AJOUT UTS — Statut d'un circuit documentaire ──────────
class StatutCircuitEnum(str, enum.Enum):
    EN_COURS   = "EN_COURS"    # circuit en progression
    EN_ATTENTE = "EN_ATTENTE"  # en attente d'action au niveau actuel
    VALIDE     = "VALIDE"      # validé définitivement par le dernier destinataire
    REJETE     = "REJETE"      # rejeté à une étape
    PUBLIE     = "PUBLIE"      # publié après validation finale

# ── AJOUT UTS — Actions possibles dans l'historique ───────
class ActionCircuitEnum(str, enum.Enum):
    ENVOYE     = "ENVOYE"
    RECU       = "RECU"
    MODIFIE    = "MODIFIE"
    REMPLACE   = "REMPLACE"
    TRANSMIS   = "TRANSMIS"
    VALIDE     = "VALIDE"
    REJETE     = "REJETE"
    RETOURNE   = "RETOURNE"
    COMMENTE   = "COMMENTE"

# ── Document ───────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id_doc           = Column(Integer, primary_key=True, autoincrement=True)
    titre            = Column(String(300), nullable=False)
    type_ressource   = Column(Enum(TypeRessourceEnum), nullable=False)
    chemin_fichier   = Column(String(500), nullable=False)
    nom_fichier      = Column(String(300), nullable=True)
    taille_fichier   = Column(BigInteger, nullable=True)
    type_mime        = Column(String(100), nullable=True)
    texte_ocr        = Column(Text, nullable=True)
    est_valide       = Column(Boolean, default=False)
    statut           = Column(Enum(StatutDocumentEnum),
                              default=StatutDocumentEnum.EN_ATTENTE)
    motif_refus      = Column(Text, nullable=True)
    date_soumission  = Column(DateTime, default=datetime.utcnow)
    date_publication = Column(DateTime, nullable=True)

    id_module        = Column(Integer, nullable=True)
    id_filiere       = Column(Integer, nullable=True)
    id_univ          = Column(Integer, nullable=True)
    uploaded_by      = Column(UUID(as_uuid=True), nullable=True)
    valide_par       = Column(UUID(as_uuid=True), nullable=True)
    # AJOUT SECURITE UTS — empreinte SHA-256 de la version courante du fichier
    # (miroir du dernier hash_fichier enregistré dans CircuitHistorique).
    hash_fichier     = Column(String(64), nullable=True)
    # AJOUT — uniquement pertinent pour type_ressource = ADMINISTRATIF.
    # nullable=True + defaut applicatif PRIVE : ne casse pas les documents deja en base
    # (COURS/TD/EXAMEN/ARCHIVE, ou visibilite n'a pas de sens et reste NULL).
    visibilite       = Column(Enum(VisibiliteDocumentEnum), nullable=True)

    # Relation vers les circuits documentaires
    circuits = relationship("DocumentCircuit", back_populates="document")

# ── Planning ───────────────────────────────────────────────
class Planning(Base):
    __tablename__ = "plannings"

    id_planning = Column(Integer, primary_key=True, autoincrement=True)
    semaine     = Column(String(50), nullable=False)
    titre       = Column(String(200), nullable=False)
    fichier_url = Column(String(500), nullable=True)
    date_envoi  = Column(DateTime, default=datetime.utcnow)
    id_filiere  = Column(Integer, nullable=True)
    id_univ     = Column(Integer, nullable=True)
    publie_par  = Column(UUID(as_uuid=True), nullable=True)
    est_publie  = Column(Boolean, default=False)

# ── Annonce ────────────────────────────────────────────────
class Annonce(Base):
    __tablename__ = "annonces"

    id_annonce      = Column(Integer, primary_key=True, autoincrement=True)
    titre           = Column(String(200), nullable=False)
    contenu         = Column(Text, nullable=False)
    date_creation   = Column(DateTime, default=datetime.utcnow)
    date_expiration = Column(DateTime, nullable=True)
    est_publiee     = Column(Boolean, default=False)
    id_univ         = Column(Integer, nullable=True)
    id_filiere      = Column(Integer, nullable=True)
    publie_par      = Column(UUID(as_uuid=True), nullable=True)


# ══════════════════════════════════════════════════════════
# AJOUT UTS — Circuit documentaire (Objectifs 1.1, 1.2 + Consignes 1-3)
# ══════════════════════════════════════════════════════════

class DocumentCircuit(Base):
    """
    Un circuit = un document en transit administratif.
    - circuit        : liste ordonnée des poste_id destinataires (JSON)
                       ex: ["ssm", "dsi", "vp-eip", "president"]
    - niveau_index   : index courant dans la liste circuit (commence à 0)
    - statut         : EN_COURS / EN_ATTENTE / VALIDE / REJETE / PUBLIE
    Consigne 1 : date_envoi, niveau_index, statut couvrent le suivi en temps réel.
    """
    __tablename__ = "document_circuits"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    document_id      = Column(Integer, ForeignKey("documents.id_doc"), nullable=False)
    auteur_id        = Column(UUID(as_uuid=True), nullable=False)  # user_id du créateur
    auteur_poste_id  = Column(String(50), nullable=True)           # poste_id du créateur
    circuit          = Column(JSONB, nullable=False)                # ["ssm","dsi","president"]
    niveau_index     = Column(Integer, default=0, nullable=False)
    statut           = Column(Enum(StatutCircuitEnum),
                              default=StatutCircuitEnum.EN_ATTENTE, nullable=False)
    objet            = Column(String(300), nullable=True)           # objet/sujet du document
    commentaire_init = Column(Text, nullable=True)                  # message d'accompagnement
    date_envoi       = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_derniere_action = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_cloture     = Column(DateTime, nullable=True)              # date validation finale
    # AJOUT SECURITE UTS — Point 3 : delai de traitement / echeance du circuit.
    # Date a laquelle le circuit doit avoir termine TOUTES ses etapes de validation.
    date_limite      = Column(DateTime, nullable=True)

    # Relations
    document    = relationship("Document", back_populates="circuits")
    historique  = relationship("CircuitHistorique", back_populates="circuit",
                               order_by="CircuitHistorique.date_action")


class CircuitHistorique(Base):
    """
    Une ligne par action sur le circuit.
    Consigne 2 : traçabilité complète — aucune information supprimée.
    Consigne 3 : chaque action (lire/modifier/remplacer/transmettre/valider)
                 génère une entrée ici.
    """
    __tablename__ = "circuit_historique"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    circuit_id      = Column(Integer, ForeignKey("document_circuits.id"), nullable=False)
    acteur_id       = Column(UUID(as_uuid=True), nullable=False)   # user_id de l'acteur
    acteur_poste_id = Column(String(50), nullable=True)            # poste_id de l'acteur
    acteur_nom      = Column(String(200), nullable=True)           # nom complet (snapshot)
    action          = Column(Enum(ActionCircuitEnum), nullable=False)
    niveau_avant    = Column(Integer, nullable=True)               # niveau avant l'action
    niveau_apres    = Column(Integer, nullable=True)               # niveau après l'action
    nouveau_fichier = Column(String(500), nullable=True)           # si REMPLACE
    commentaire     = Column(Text, nullable=True)
    date_action     = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Temps passé à cette étape depuis la dernière action (en secondes)
    duree_etape_secondes = Column(Integer, nullable=True)

    # ── AJOUT SECURITE UTS — Point 2 : traçabilité renforcée (validé) ──────
    # hash_fichier : empreinte SHA-256 du fichier AU MOMENT de cette action.
    # Calculé à chaque ENVOYE/REMPLACE pour prouver qu'aucune altération
    # silencieuse n'a eu lieu entre deux étapes (comparaison possible entre
    # deux lignes d'historique successives).
    hash_fichier    = Column(String(64), nullable=True)
    # Adresse IP de l'acteur au moment de l'action.
    ip_address      = Column(String(50), nullable=True)
    # User-Agent brut du navigateur/client ayant effectué l'action, pour
    # repérer une action faite depuis un appareil inhabituel.
    user_agent      = Column(String(500), nullable=True)

    # Relation
    circuit = relationship("DocumentCircuit", back_populates="historique")
