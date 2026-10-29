# Audit et améliorations — 29 octobre 2026

Périmètre : révision initiale `7a74651`, backend Django, frontend React,
intégrations et configuration de livraison. L'objectif est de corriger les
problèmes démontrables et de rendre leur vérification reproductible. Ce document
ne constitue ni une certification de sécurité, ni une attestation WCAG/RGPD.

## Correctifs livrés

| Domaine | Problème observé | Correction |
| --- | --- | --- |
| API | Références vers des sessions/calendriers appartenant à autrui | Relations filtrées par utilisateur, validations et tests négatifs |
| Confidentialité | API et profils legacy exposés malgré un profil privé ; caches persistants | Contrôle propriétaire/public et suppression des caches sensibles |
| Cercles | Créateur sans rôle administrateur ; tenant mutable ; jetons exposés | Création atomique, tenant immuable, réponses sans jetons membres |
| Invitations | Route frontend inexistante et promesse d'envoi mail non implémentée | Lien copiable et page d'acceptation ; aucun envoi mail annoncé |
| SSO | Liaison par email et privilèges issus d'identités externes | Identité explicite issuer/sub, validation des claims, invitations atomiques |
| Sessions | Cookies signés non révocables côté serveur ; déconnexion GET | Sessions PostgreSQL et déconnexion POST avec CSRF |
| Webhooks | Secret facultatif ; émissions avant commit et après chaque édition | Secret obligatoire, validation du payload, émission après commit sur transition |
| Intégrations | Accès réseau et fichiers serveur choisis par l'utilisateur | Origines/fichiers approuvés explicitement par l'opérateur ; refus des redirections |
| Calendriers | Lecture seule contournable, paramètres invalides, import JSON cassé | Validation REST/CalDAV, dates 400, import fonctionnel |
| CalDAV | UTC/export incorrects, ETag périmé, mots de passe applicatifs ignorés | Sérialisation réparée, ETag recalculé, authentification IAM intégrée |
| Minuteur | Free Flow terminé immédiatement, courses réseau, pauses incorrectes | Compteur libre, transitions robustes et tests du worker/hook |
| Contrats JSON | snake_case/camelCase incohérents, réglages ignorés, URL playlists erronée | Types et transport alignés ; clés de modes préservées |
| Formulaires | Saisie d'événement perdue après erreur ; calendrier remplacé lors d'un PATCH | Saisie conservée, erreurs affichées, relations préservées |
| Accessibilité | Modal, focus et navigation mobile perfectibles | Dialog accessible, focus clavier, réduction des animations |
| Performance | Toutes les pages dans le bundle initial | Routes chargées à la demande : environ 496 → 338 ko JS initial |
| Livraison | Aucun test effectif, dépendances vulnérables, secrets/debug préproduction | Tests et CI, versions verrouillées, Django 5.2 LTS, Node 24, secrets obligatoires |

## Vérifications exécutées

- **86 tests backend** réussis sur PostgreSQL 16 et Python 3.12.
- **23 tests frontend** réussis avec Vitest/jsdom.
- `manage.py check` : aucune erreur ; `makemigrations --check --dry-run` :
  aucune migration manquante.
- Migrations complètes exécutées sur une base PostgreSQL vide.
- `pip check`, `pip-audit -r requirements.lock`, `npm audit` : dépendances
  cohérentes et **aucune vulnérabilité connue signalée** lors de l'exécution.
- Build TypeScript/Vite et image Docker multi-stage réussis.
- Démarrage Uvicorn réel ; HTTP 200 pour health, SPA, assets, login et signup.
- WebSocket réel : anonyme refusé (403), membre authentifié accepté.
- `check --deploy --fail-level ERROR` sans erreur ; deux avertissements HSTS
  intentionnels (préchargement et sous-domaines non imposés).
- `git diff --check` propre.

Les tests couvrent notamment accès inter-utilisateurs, rollback de transaction,
confidentialité après changement de préférence, paramètres malformés, parcours
local inscription/connexion, SSO avec claims contrôlés, expiration des mots de
passe applicatifs et erreurs réseau simulées.

## Migration et limites

Lire [MAINTENANCE.md](MAINTENANCE.md) avant déploiement : nouvelle migration
`iam.0002_oidcidentity`, liaison explicite des anciens comptes SSO, invalidation
des sessions précédentes, renouvellement des secrets et allowlists d'intégration.

- Le SSO, Google Calendar, les fournisseurs IA et les adaptateurs n'ont pas été
  validés contre des comptes réels : aucun identifiant de service n'était fourni.
- Les tests UI utilisent jsdom ; aucun audit visuel navigateur, lecteur d'écran
  complet, test de charge ou pentest externe n'a été réalisé.
- Les liens d'invitation de cercle restent réutilisables selon le comportement
  existant ; leur révocation et l'envoi d'emails nécessitent un chantier dédié.
- La fédération multi-IdP et une compatibilité CalDAV exhaustive restent à
  compléter, notamment les UID externes non UUID.
- Les notifications de fin de session restent best effort : une outbox durable
  serait nécessaire pour une livraison garantie et une déduplication concurrente.
- Les domaines d'intégration autorisés doivent être fiables ; l'isolation réseau
  reste nécessaire en complément des restrictions applicatives.
- Les fichiers statiques sont encore servis par Django : envisager un serveur
  statique/CDN adapté si la charge le justifie.

La configuration de CI est ajoutée au dépôt ; ses résultats GitHub dépendent
encore de l'exécution des workflows sur la branche proposée. Aucun déploiement
sur l'installation existante n'est effectué par cet audit.
