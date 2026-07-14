-- A executer AVANT toute nouvelle commande alembic upgrade/stamp.
-- Aucune de ces requetes n'ecrit quoi que ce soit — lecture pure.

-- A) Etat reel d'Alembic en base (deux tables possibles selon si le correctif
--    version_table a deja ete applique ou non)
SELECT * FROM alembic_version;
SELECT * FROM alembic_version_auth;  -- peut renvoyer une erreur "n'existe pas", c'est une info utile en soi

-- B) Schema REEL actuel des tables concernees, a comparer colonne par colonne
--    avec ce que chaque migration attend
\d document_circuits
\d circuit_historique
\d documents
\d groupes_service          -- peut ne pas exister si b7f3c1a9d2e4 n'a jamais tourne
\d groupes_service_membres  -- idem
