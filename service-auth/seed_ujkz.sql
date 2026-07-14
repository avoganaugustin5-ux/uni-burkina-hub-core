-- ==============================================================================
-- seed_ujkz.sql — UniBurkina Hub — Seed UFR/Filières Université Joseph KI-ZERBO
-- AVOGAN Koudjo Augustin Sandaogo
--
-- ATTENTION : ce script ne fait QUE des INSERT.
-- Aucun UPDATE, aucun DELETE. Les id_univ=1 (Thomas SANKARA) et les
-- id_ufr 2,3,4 / id_filiere 3 à 11 déjà existants ne sont jamais touchés.
--
-- Pré-requis vérifié via /auth/universites : id_univ=2 = Joseph KI-ZERBO existe déjà.
-- Si ce n'est pas le cas chez toi, adapte la variable :univ_id ci-dessous.
--
-- Source : infos_ujkz.txt (contenu officiel des pages UFR de l'université)
-- ==============================================================================

BEGIN;

-- Sécurité : on vérifie qu'on insère bien pour la bonne université.
-- Remplace '2' par le véritable id_univ de Joseph KI-ZERBO si différent.
DO $$
DECLARE
    v_univ_id INTEGER := 2;
    v_exists  BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM universites WHERE id_univ = v_univ_id) INTO v_exists;
    IF NOT v_exists THEN
        RAISE EXCEPTION 'id_univ=% introuvable dans la table universites — seed annulé', v_univ_id;
    END IF;
END $$;

-- ──────────────────────────────────────────────────────────────────────────
-- 1. UFR / INSTITUTS — Université Joseph KI-ZERBO (id_univ = 2)
-- ──────────────────────────────────────────────────────────────────────────
INSERT INTO ufrs (nom_ufr, code_ufr, id_univ) VALUES
    ('UFR Sciences de la Vie et de la Terre',                                              'UFR-SVT-UJKZ',    2),
    ('UFR Sciences Exactes et Appliquées',                                                  'UFR-SEA-UJKZ',    2),
    ('UFR Sciences de la Santé',                                                            'UFR-SDS-UJKZ',    2),
    ('UFR Lettres, Arts et Communication',                                                  'UFR-LAC-UJKZ',    2),
    ('UFR Sciences Humaines',                                                               'UFR-SH-UJKZ',     2),
    ('Institut Burkinabè des Arts et Métiers',                                              'IBAM-UJKZ',       2),
    ('Institut Panafricain d''Etude et de Recherches sur les Médias, l''Information et la Communication', 'IPERMIC-UJKZ', 2),
    ('Institut Supérieur des Sciences de la Population',                                    'ISSP-UJKZ',       2),
    ('Institut de Génie de l''Environnement et du Développement Durable',                   'IGEDD-UJKZ',      2),
    ('Institut de Formation Ouverte et à Distance',                                         'IFOAD-UJKZ',      2),
    ('Institut Supérieur des Sciences de la Santé Humaine',                                 'ISSDH-UJKZ',      2)
ON CONFLICT (code_ufr) DO NOTHING;

-- ──────────────────────────────────────────────────────────────────────────
-- 2. FILIÈRES — rattachées via sous-requête sur code_ufr (évite de coder
--    les id_ufr en dur, qui pourraient varier selon ce qui existe déjà)
-- ──────────────────────────────────────────────────────────────────────────

-- UFR SVT : Chimie, Biologie, Géologie, Sciences et Technologies (ST)
INSERT INTO filieres (nom_filiere, description, id_ufr)
SELECT v.nom_filiere, v.description, f.id_ufr
FROM (VALUES
    ('Chimie',                     'Licence en Chimie — UFR SVT / Université Joseph KI-ZERBO'),
    ('Biologie',                   'Licence en Biologie — UFR SVT / Université Joseph KI-ZERBO'),
    ('Géologie',                   'Licence en Géologie — UFR SVT / Université Joseph KI-ZERBO'),
    ('Sciences et Technologies (ST)', 'Licence en Sciences et Technologies — UFR SVT / Université Joseph KI-ZERBO')
) AS v(nom_filiere, description)
CROSS JOIN (SELECT id_ufr FROM ufrs WHERE code_ufr = 'UFR-SVT-UJKZ') f;

-- UFR SEA : Mathématique, Physique, Chimie, Informatique
INSERT INTO filieres (nom_filiere, description, id_ufr)
SELECT v.nom_filiere, v.description, f.id_ufr
FROM (VALUES
    ('Mathématique',  'Licence en Mathématique — UFR SEA / Université Joseph KI-ZERBO'),
    ('Physique',       'Licence en Physique — UFR SEA / Université Joseph KI-ZERBO'),
    ('Chimie',         'Licence en Chimie — UFR SEA / Université Joseph KI-ZERBO'),
    ('Informatique',   'Licence en Informatique — UFR SEA / Université Joseph KI-ZERBO')
) AS v(nom_filiere, description)
CROSS JOIN (SELECT id_ufr FROM ufrs WHERE code_ufr = 'UFR-SEA-UJKZ') f;

-- UFR SDS : Médecine, Pharmacie, Technicien Supérieur de Santé, Psychiatrie
INSERT INTO filieres (nom_filiere, description, id_ufr)
SELECT v.nom_filiere, v.description, f.id_ufr
FROM (VALUES
    ('Médecine',                              'Doctorat en Médecine — UFR SDS / Université Joseph KI-ZERBO'),
    ('Pharmacie',                              'Doctorat en Pharmacie — UFR SDS / Université Joseph KI-ZERBO'),
    ('Technicien Supérieur de Santé (TSS)',    'Formation TSS — UFR SDS / Université Joseph KI-ZERBO'),
    ('Psychiatrie',                            'Spécialisation Psychiatrie — UFR SDS / Université Joseph KI-ZERBO')
) AS v(nom_filiere, description)
CROSS JOIN (SELECT id_ufr FROM ufrs WHERE code_ufr = 'UFR-SDS-UJKZ') f;

-- UFR LAC : Allemand, Anglais, Lettres Modernes, Linguistique
INSERT INTO filieres (nom_filiere, description, id_ufr)
SELECT v.nom_filiere, v.description, f.id_ufr
FROM (VALUES
    ('Allemand',         'Licence en Allemand — UFR LAC / Université Joseph KI-ZERBO'),
    ('Anglais',          'Licence en Anglais — UFR LAC / Université Joseph KI-ZERBO'),
    ('Lettres Modernes', 'Licence en Lettres Modernes — UFR LAC / Université Joseph KI-ZERBO'),
    ('Linguistique',     'Licence en Linguistique — UFR LAC / Université Joseph KI-ZERBO')
) AS v(nom_filiere, description)
CROSS JOIN (SELECT id_ufr FROM ufrs WHERE code_ufr = 'UFR-LAC-UJKZ') f;

-- UFR SH : Géographie, Histoire et Archéologie, Philosophie, Psychologie, Sociologie
INSERT INTO filieres (nom_filiere, description, id_ufr)
SELECT v.nom_filiere, v.description, f.id_ufr
FROM (VALUES
    ('Géographie',               'Licence en Géographie — UFR SH / Université Joseph KI-ZERBO'),
    ('Histoire et Archéologie',  'Licence en Histoire et Archéologie — UFR SH / Université Joseph KI-ZERBO'),
    ('Philosophie',               'Licence en Philosophie — UFR SH / Université Joseph KI-ZERBO'),
    ('Psychologie',               'Licence en Psychologie — UFR SH / Université Joseph KI-ZERBO'),
    ('Sociologie',                'Licence en Sociologie — UFR SH / Université Joseph KI-ZERBO')
) AS v(nom_filiere, description)
CROSS JOIN (SELECT id_ufr FROM ufrs WHERE code_ufr = 'UFR-SH-UJKZ') f;

-- IBAM : CCA, ABF, MG, ADB, MIAGE (licences professionnelles)
INSERT INTO filieres (nom_filiere, description, id_ufr)
SELECT v.nom_filiere, v.description, f.id_ufr
FROM (VALUES
    ('Comptabilité-Contrôle-Audit (CCA)',                 'Licence professionnelle — IBAM / Université Joseph KI-ZERBO'),
    ('Assurance-Banque-Finance (ABF)',                    'Licence professionnelle — IBAM / Université Joseph KI-ZERBO'),
    ('Marketing et Gestion (MG)',                         'Licence professionnelle — IBAM / Université Joseph KI-ZERBO'),
    ('Assistance de Direction Bilingue (ADB)',             'Licence professionnelle — IBAM / Université Joseph KI-ZERBO'),
    ('Méthodes Informatiques Appliquées à la Gestion (MIAGE)', 'Licence professionnelle — IBAM / Université Joseph KI-ZERBO')
) AS v(nom_filiere, description)
CROSS JOIN (SELECT id_ufr FROM ufrs WHERE code_ufr = 'IBAM-UJKZ') f;

-- IPERMIC : Sciences et Techniques de l'Information et de la Communication (3 options)
INSERT INTO filieres (nom_filiere, description, id_ufr)
SELECT v.nom_filiere, v.description, f.id_ufr
FROM (VALUES
    ('Communication d''entreprise / Relation publique', 'Licence STIC, option Communication d''entreprise — IPERMIC / Université Joseph KI-ZERBO'),
    ('Communication pour le développement',              'Licence STIC, option Communication pour le développement — IPERMIC / Université Joseph KI-ZERBO'),
    ('Journalisme',                                       'Licence STIC, option Journalisme — IPERMIC / Université Joseph KI-ZERBO')
) AS v(nom_filiere, description)
CROSS JOIN (SELECT id_ufr FROM ufrs WHERE code_ufr = 'IPERMIC-UJKZ') f;

-- ISSP : Statistiques Sociales (licence) + Population et Santé (master)
INSERT INTO filieres (nom_filiere, description, id_ufr)
SELECT v.nom_filiere, v.description, f.id_ufr
FROM (VALUES
    ('Statistiques Sociales',           'Licence en Statistiques Sociales — ISSP / Université Joseph KI-ZERBO'),
    ('Population et Santé (Master)',    'Master professionnel en Population et Santé — ISSP / Université Joseph KI-ZERBO')
) AS v(nom_filiere, description)
CROSS JOIN (SELECT id_ufr FROM ufrs WHERE code_ufr = 'ISSP-UJKZ') f;

-- IGEDD : Génie de l'Environnement (licence pro, 2 spécialités) + masters MQSE/TES/EER + master spécialisé ADT
INSERT INTO filieres (nom_filiere, description, id_ufr)
SELECT v.nom_filiere, v.description, f.id_ufr
FROM (VALUES
    ('Génie de l''Environnement — Technologies de l''Eau et Assainissement (TEA)', 'Licence professionnelle — IGEDD / Université Joseph KI-ZERBO'),
    ('Génie de l''Environnement — Gestion des Pollutions et Aménagement du Territoire', 'Licence professionnelle — IGEDD / Université Joseph KI-ZERBO'),
    ('Management Qualité-Sécurité-Environnement (MQSE)', 'Master professionnel — IGEDD / Université Joseph KI-ZERBO'),
    ('Territoire-Environnement-Santé (TES)',              'Master professionnel — IGEDD / Université Joseph KI-ZERBO'),
    ('Energie et Energies Renouvelables (EER)',           'Master professionnel et recherche — IGEDD / Université Joseph KI-ZERBO'),
    ('Aménagement Durable du Territoire (ADT)',           'Master spécialisé — IGEDD / Université Joseph KI-ZERBO')
) AS v(nom_filiere, description)
CROSS JOIN (SELECT id_ufr FROM ufrs WHERE code_ufr = 'IGEDD-UJKZ') f;

-- IFOAD et ISSDH : aucune filière détaillée disponible dans la source.
-- Les UFR sont créées (cf. section 1) mais restent sans filière pour l'instant,
-- en attente d'informations complémentaires.

COMMIT;

-- ──────────────────────────────────────────────────────────────────────────
-- Vérification post-seed (à exécuter manuellement après le script)
-- ──────────────────────────────────────────────────────────────────────────
-- SELECT u.nom_univ, f.nom_ufr, f.code_ufr, COUNT(fil.id_filiere) AS nb_filieres
-- FROM universites u
-- JOIN ufrs f ON f.id_univ = u.id_univ
-- LEFT JOIN filieres fil ON fil.id_ufr = f.id_ufr
-- WHERE u.id_univ = 2
-- GROUP BY u.nom_univ, f.nom_ufr, f.code_ufr
-- ORDER BY f.nom_ufr;
