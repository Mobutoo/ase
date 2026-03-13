# PRD — Ase v3.0 "Circle Flow"

> Human-Centric Flow Engine + Calendrier Familial Intelligent

**Produit** : Ase v3.0 — Flash Studio Circle OS
**Auteur** : Sekoul — Flash Studio
**Version** : 3.0.0-draft
**Date** : Mars 2026
**Statut** : Brouillon

---

## Table des matieres

1. [Resume executif](#1-resume-executif)
2. [Etat actuel (v2.0)](#2-etat-actuel-v20)
3. [Vision v3.0](#3-vision-v30)
4. [Architecture technique](#4-architecture-technique)
5. [Authentification et multi-tenancy](#5-authentification-et-multi-tenancy)
6. [Fonctionnalites — Calendrier](#6-fonctionnalites--calendrier)
7. [Fonctionnalites — Integration Taches-Calendrier](#7-fonctionnalites--integration-taches-calendrier)
8. [Fonctionnalites — Agents IA](#8-fonctionnalites--agents-ia)
9. [Fonctionnalites — UX et Mobile](#9-fonctionnalites--ux-et-mobile)
10. [Modele de donnees](#10-modele-de-donnees)
11. [Securite](#11-securite)
12. [Contraintes non-fonctionnelles](#12-contraintes-non-fonctionnelles)
13. [Migration v2 → v3](#13-migration-v2--v3)
14. [Phases de livraison](#14-phases-de-livraison)
15. [Criteres d'acceptation](#15-criteres-dacceptation)
16. [Risques et mitigations](#16-risques-et-mitigations)
17. [Hors scope (v3)](#17-hors-scope-v3)

---

## 1. Resume executif

### Probleme

Les groupes de personnes (familles, colocations, equipes, clubs, associations) n'ont pas d'outil unique pour :
- **Gerer leur temps** : focus, pomodoro, suivi d'energie
- **Coordonner leur vie** : calendrier partage, evenements dependants, bookings
- **Piloter par l'IA** : un agent qui anticipe, planifie, et reserve — le groupe valide

Les solutions existantes forcent a jongler entre une app de productivite (Todoist, Forest) et un calendrier (Google Calendar, Cozi) sans aucun lien entre les deux.

### Vision

**Ase v3 est le premier outil qui fusionne productivite personnelle et calendrier de groupe**, avec un agent IA souverain. Une tache avec pomodoro reserve automatiquement un creneau. Un evenement genere ses dependances (trajet, repas, accompagnement). Le groupe valide d'un tap.

Le concept central est le **Circle** : un groupe generique qui s'adapte au contexte — famille, colocation, equipe de travail, club sportif. Le preset du Circle determine les roles disponibles et les labels UI, mais la logique technique est identique.

### Positionnement dans Flash Studio

Ase est une application du Data Plane de chaque tenant Flash Studio. Il ne vit pas seul — il fait partie d'un ecosysteme :

```
Flash Studio (Control Plane)
├── Zitadel Global (admins tenants)
│
└── Data Plane Tenant (provisionne par flash-infra)
    ├── Ase v3 (Flow + Calendar + Circles)
    ├── Authelia + LLDAP (IAM par defaut) ou Zitadel (premium)
    ├── Cal.com (booking pro, optionnel)
    ├── Zimboo (budget personnel)
    └── Monitoring (Grafana)
```

---

## 2. Etat actuel (v2.0)

### Ce qui existe et fonctionne

| Module | Description | Modeles Django |
|--------|-------------|----------------|
| **Flow Engine** | 5 modes (Deep Work, Pomodoro, Kids, Sprint, Free Flow) | `Session`, `UserSettings` |
| **Taches** | Taches locales + adapteurs externes (Plane, GitHub, Super Productivity) | `LocalTask`, `TaskSourceConfig` |
| **Energie** | Suivi d'energie 1-5 avant/apres session | `EnergyReading` |
| **Musique** | YouTube playlists par mode, MiniPlayer global | `Playlist` |
| **Analytics** | Graphiques Recharts, focus score, streaks | `DailyPlan`, `Achievement` |
| **AI Copilot** | Suggestions IA via n8n/OpenClaw webhooks | `AISuggestion` |
| **Gamification** | Badges, leaderboard, rewards | `Rewards`, `Achievement` |
| **i18n** | 7 langues supportees | Frontend i18next |
| **Design** | Theme Afrofuturist + 6 autres themes | `UserSettings.theme` |

### Stack technique v2.0

| Composant | Technologie |
|-----------|-------------|
| Backend | Django 4.2 + DRF 3.15 |
| Frontend | React 18 + Vite 6 + Tailwind 3.4 + TypeScript |
| State | Zustand 5 |
| BDD | PostgreSQL |
| Cache | Redis |
| Auth | django-allauth (username/password) |
| Graphiques | Recharts |
| i18n | i18next |
| Icons | Lucide React |
| Deploiement | Docker multi-stage (single container) |

### Limites actuelles

1. **Pas de calendrier** : les taches n'ont qu'un `due_date`, pas de creneaux horaires
2. **Mono-utilisateur de fait** : pas de concept de circle/groupe/equipe
3. **Auth locale** : username/password django-allauth, pas de SSO
4. **Pas de PWA** : pas de service worker, pas de push, pas d'offline
5. **Pas de CalDAV** : pas de sync avec iPhone/Android calendriers natifs
6. **Agent IA limité** : suggestions passives, pas d'actions automatiques

---

## 3. Vision v3.0

### Les 4 piliers d'Ase v3

```
┌──────────────────────────────────────────────────┐
│                  Ase v3 "Circle Flow"              │
│                                                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────────┐ │
│  │   FLOW     │ │ CALENDRIER │ │   CIRCLE       │ │
│  │            │ │            │ │                │ │
│  │ Pomodoro   │ │ Jour/Sem/  │ │ Membres        │ │
│  │ Deep Work  │ │ Mois       │ │ Invitation     │ │
│  │ Energie    │ │ 3 couches  │ │ Roles/Presets  │ │
│  │ Musique    │ │ CalDAV     │ │ Visibilite     │ │
│  └─────┬──────┘ └─────┬──────┘ └───────┬────────┘ │
│        │              │                │           │
│        └──────────┬───┘                │           │
│                   │                    │           │
│  ┌────────────────┴────────────────────┴─────────┐ │
│  │              AGENT IA                          │ │
│  │                                                │ │
│  │  Event Graph · NLP · Booking · Digest hebdo    │ │
│  │  Human-in-the-loop (Telegram)                  │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### Killer features (ce que personne d'autre n'a)

| Feature | Description |
|---------|-------------|
| **Pomodoro → Creneau** | Une tache avec pomodoro reserve automatiquement un creneau dans le calendrier familial |
| **Event Graph** | Un evenement racine genere ses sous-evenements (trajet, accompagnement, repas) |
| **NLP naturel** | "Julia gym samedi 10h" → evenement parse + dependances creees |
| **Visibilite par role** | Adultes / Enfants / Prive — les enfants ne voient pas les RDV medicaux |
| **Magic Link + QR CalDAV** | Invitation famille sans mot de passe + setup CalDAV en 1 scan |
| **Digest IA hebdo** | Dimanche soir : resume de la semaine pour chaque membre |

---

## 4. Architecture technique

### Schema global

```
┌──────────────────────────────────────────────────────┐
│              Data Plane Tenant (Flash Studio)          │
│                                                        │
│  Authelia + LLDAP (~45MB)  ou  Zitadel (~512MB)       │
│       │ OIDC                                           │
│       ▼                                                │
│  ┌─── ASE v3 ──────────────────────────────────────┐  │
│  │                                                  │  │
│  │  Django 4.2 + DRF                                │  │
│  │  ├── app/             (Flow Engine existant)     │  │
│  │  ├── api/             (DRF existant)             │  │
│  │  ├── adapters/        (TaskSource existant)      │  │
│  │  ├── calendar/        (NOUVEAU — CalDAV + events)│  │
│  │  ├── circles/         (NOUVEAU — groupes, membres, roles) │  │
│  │  ├── iam/             (NOUVEAU — OIDC + UserProv)│  │
│  │  └── agents/          (NOUVEAU — Event Graph, IA)│  │
│  │                                                  │  │
│  │  PostgreSQL = SOURCE UNIQUE DE VERITE            │  │
│  │                                                  │  │
│  │  React 18 + Vite + Tailwind (PWA)                │  │
│  │  ├── pages/ existantes (Home, Tasks, Analytics…) │  │
│  │  ├── pages/Calendar    (NOUVEAU)                 │  │
│  │  ├── pages/Circle      (NOUVEAU)                 │  │
│  │  └── sw.js             (NOUVEAU — Service Worker)│  │
│  │                                                  │  │
│  └──────────────────────────────────────────────────┘  │
│       │ CalDAV (RFC 4791)       │ REST API             │
│       ▼                         ▼                      │
│  iPhones / Android          Cal.com (optionnel)        │
│  (auto-config QR)           webhook → Ase              │
│                                                        │
│  OpenClaw (agent IA)                                   │
│  ├── Token scope                                       │
│  ├── Audit log signe                                   │
│  └── Kill switch famille                               │
└────────────────────────────────────────────────────────┘
```

### Stack technique v3.0

| Composant | v2.0 | v3.0 | Changement |
|-----------|------|------|------------|
| Backend | Django 4.2 + DRF | Django 4.2 + DRF | Inchange |
| Frontend | React 18 + Vite | React 18 + Vite + **PWA** | Service Worker + manifest |
| Auth | django-allauth (password) | **OIDC** (Authelia ou Zitadel) | Migration auth |
| CalDAV | Aucun | **Integre** (`vobject` + `caldav`) | Nouvelle app Django |
| BDD | PostgreSQL | PostgreSQL (**source unique**) | Inchange |
| Cache | Redis | Redis | Inchange |
| State | Zustand | Zustand | Inchange |
| Booking pro | Aucun | **Cal.com** (optionnel, webhook) | Integration externe |
| Sync mobile | Aucun | **CalDAV natif** RFC 4791 | Serveur CalDAV integre |
| Agent IA | Suggestions passives | **Event Graph + actions** | Upgrade majeur |
| Notifications | Aucun | **Push (PWA) + Telegram** | Nouveau |

### Decisions architecturales cles

**D1 — Source unique de verite** : PostgreSQL (Ase) est le seul store d'evenements. Pas de Baikal externe. Ase expose directement CalDAV via une app Django dediee. Raison : zero latence de sync, zero conflit, une seule BDD a sauvegarder.

**D2 — Pas de VDIRSYNCER** : supprime. Si Cal.com est connecte, un webhook Cal.com → Ase cree l'evenement dans PostgreSQL. Ase ne sync pas — il est la source.

**D3 — OIDC generique** : Ase parle OIDC standard via `mozilla-django-oidc`. Le provider (Authelia ou Zitadel) est configure par variable d'environnement. Le code Ase ne connait pas le provider.

**D4 — PWA, pas de native** : React + Vite + Service Worker. Installable sur l'ecran d'accueil, push notifications, offline read. Pas d'app store, pas de review Apple/Google.

**D5 — UserProvider abstrait** : l'invitation famille passe par une interface `UserProvider` avec deux implementations (`LLDAPProvider`, `ZitadelProvider`), selectionnee par env var `IAM_BACKEND`.

**D6 — Guest federe cross-tenant** : un abonne Flash Studio peut etre membre d'une famille dans un autre tenant sans creer de compte local. Zitadel Global sert d'Identity Broker. L'IAM de chaque tenant fait confiance a Zitadel Global comme IdP externe OIDC. Les donnees du guest restent dans le tenant hote (isolation preservee).

**D7 — CalDAV implementation strategy** : Django expose directement CalDAV via des vues PROPFIND/REPORT/GET/PUT/DELETE sur `calendar/`. Pas de sidecar Radicale. La lib `vobject` genere/parse le iCalendar (RFC 5545). L'export `.ics` par calendrier est expose en URL publique signee (lecture seule, abonnement Google Agenda). L'approche full-Django evite un processus supplementaire, un second store, et une synchronisation.

**D8 — Real-time** : Django Channels (WebSocket) pour la propagation instantanee des modifications calendrier entre membres connectes. SSE en fallback si WebSocket non disponible (proxy restrictif). Redis sert de channel layer (deja present). Les clients CalDAV externes restent en polling standard CalDAV.

**D9 — Transactional email** : Brevo (ex-Sendinblue) comme provider email transactionnel initial (magic link, invitations, digest hebdo). Migration vers Stalwart Mail (self-hosted JMAP/SMTP, ~50MB RAM) quand le volume le justifie. L'abstraction `EmailBackend` Django rend le changement transparent.

---

## 5. Authentification et multi-tenancy

### Modele IAM

```
Control Plane (Flash Studio)
│
│  Zitadel Global
│  ├── Tenant admins (clients payants)
│  └── Identity Broker pour guest federes cross-tenant
│
└── Data Plane (par tenant)
    │
    ├── OPTION A (defaut) : Authelia + LLDAP (~45MB RAM)
    │   CX22 Hetzner (4GB) · Invite famille via LLDAP API
    │   Trust: Zitadel Global comme IdP externe OIDC
    │
    └── OPTION B (premium) : Zitadel dedie (~512MB RAM)
        CX32 Hetzner (8GB) · Invite famille via Zitadel Management API
        Trust: Zitadel Global comme IdP externe OIDC
```

### Flux d'authentification

```
Utilisateur → https://ase.tenant-kone.flash.studio
    │
    ├── Pas de session → redirect OIDC vers Authelia/Zitadel du tenant
    │   │
    │   ├── Magic Link (email) — defaut pour les invites locaux
    │   ├── Passkey (WebAuthn/FaceID) — recommande
    │   ├── Mot de passe (fallback)
    │   └── "Se connecter avec Flash Studio" — pour guest federes
    │   │
    │   └── Callback OIDC → Django cree/met a jour le User local
    │       Token dans cookie HttpOnly + Secure + SameSite=Strict
    │
    └── Session active → acces direct
```

### Types de membres

Ase supporte deux types de membres dans une famille :

| Type | Identite | Cas d'usage | Cout |
|------|----------|-------------|------|
| **local** | Creee dans le LLDAP/Zitadel du tenant | Enfants, conjoint sans abonnement | Gratuit (inclus) |
| **federated** | Authentifiee via Zitadel Global | Abonne Flash Studio membre d'une autre famille | Gratuit (a deja son abonnement) |

Un membre federe a **exactement les memes droits** qu'un membre local dans Ase (calendrier, taches, agent IA). La seule difference est la source d'authentification.

### Invitation famille — Membre local (nouveau)

```
Dr. Kone dans Ase → "Inviter un proche" (email)
    │
    ▼
Ase backend (Django)
├── Genere un token d'invite HMAC (expire 24h, usage unique)
├── UserProvider.invite_member("awa@email.com", "Awa", role="adult")
│   ├── LLDAP → cree user + groupe "family"
│   └── Zitadel → cree user + envoie email
├── Envoie email avec magic link
│
▼
Awa clique le lien → OIDC (IAM du tenant) → connectee a Ase
├── CircleMember(membership_type="local") cree
├── Voit le calendrier familial
├── Recoit un QR code pour configurer CalDAV sur son iPhone
└── Invisible du reste de Flash Studio
```

### Invitation famille — Guest federe (abonne Flash Studio)

```
Dr. Kone dans Ase → "Inviter un abonne Flash Studio" (email)
    │
    ▼
Ase backend (Django)
├── Verifie via Zitadel Global API : awa@email.com existe ?
│   ├── Oui → genere token d'invite, envoie email
│   └── Non → erreur "cet email n'est pas un abonne Flash Studio"
│
▼
Awa clique le lien → choisit "Se connecter avec Flash Studio"
    │
    ├── Redirect OIDC vers Zitadel Global (pas le LLDAP du tenant)
    ├── Awa s'authentifie avec son compte Flash Studio habituel
    ├── Callback OIDC → Django recoit le token Global
    │   sub: "awa-uuid-global"
    │   issuer: "https://global.flash.studio"
    │
    ▼
Ase backend
├── Cree un User Django local (auto-provision)
├── Cree CircleMember(membership_type="federated",
│     external_issuer="https://global.flash.studio",
│     external_sub="awa-uuid-global")
├── Awa voit le calendrier familial Kone
└── Awa garde aussi son propre tenant (contexte separe)
```

### Acces multi-famille pour un guest federe

```
Awa se connecte a Flash Studio (Zitadel Global)
    │
    ├── "Mon espace" → Tenant Awa (admin de son propre Data Plane)
    │   └── Son propre Ase, ses projets, son calendrier
    │
    └── "Famille Kone" → Tenant Kone (guest federe)
        └── Calendrier familial, taches partagees, agent IA familial
```

Le choix du contexte se fait :
- Soit via un **selecteur de famille** dans le header d'Ase
- Soit via des **URLs distinctes** : `ase.tenant-kone.flash.studio` vs `ase.tenant-awa.flash.studio`

### Cycle de vie des membres federes

| Evenement | Comportement |
|-----------|-------------|
| Awa prend un abonnement Flash Studio | Rien ne change dans le tenant Kone (elle reste locale) |
| Dr. Kone migre Awa de local → federe | Ancien compte LLDAP desactive, nouveau CircleMember federe cree, donnees conservees |
| Awa resilie son abonnement | Son tenant Awa est supprime, mais son membership federe chez Kone **reste actif** (son identite Global persiste tant que Flash Studio la maintient) |
| Dr. Kone supprime Awa du circle | CircleMember supprime, donnees Kone purgees, le compte Global d'Awa reste intact |
| Tenant Kone supprime | Tous les CircleMember (locaux et federes) supprimes, le compte Global d'Awa reste intact |

### Matrice de permissions RBAC

Les permissions dependent du **preset** du Circle et du **role** du membre. La matrice ci-dessous utilise le preset `family` comme reference. Les autres presets suivent le meme modele en remplacant les roles.

| Permission | `admin` | `adult` | `child` | `guest` |
|------------|:-------:|:-------:|:-------:|:-------:|
| Voir calendrier circle | O | O | O (filtre) | O (filtre) |
| Creer evenement | O | O | O (personnel) | X |
| Modifier evenement d'un autre | O | O (si assigne) | X | X |
| Supprimer evenement | O | O (ses propres) | X | X |
| Voir evenements `adults_only` | O | O | X | X |
| Voir evenements `private` d'un autre | X | X | X | X |
| Inviter un membre local | O | X | X | X |
| Inviter un guest federe | O | X | X | X |
| Changer le role d'un membre | O | X | X | X |
| Supprimer un membre | O | X | X | X |
| Configurer l'agent IA | O | O | X | X |
| Valider une action agent (Telegram) | O | O | X | X |
| Voir audit log agent | O | O | X | X |
| Creer/modifier un circle | O | X | X | X |
| Kill switch agent | O | X | X | X |
| Gerer app-specific passwords | O | O (les siennes) | X | X |
| Import .ics | O | O | X | X |
| Export .ics | O | O | O (ses calendriers) | X |

**Preset `colocation`** : remplacer `adult` par `roommate`, pas de role `child`.
**Preset `team`** : remplacer `adult` par `member`, ajouter `intern` (memes droits que `child`).
**Preset `club`** : remplacer `admin` par `admin`, `adult` par `coach`, `child` par `player`, ajouter `parent` (lecture seule calendrier joueur).

### Isolation

| Propriete | Garantie |
|-----------|----------|
| Membres locaux invisibles hors tenant | Users dans LLDAP/Zitadel du tenant uniquement |
| Membres federes : donnees dans le tenant hote | Les evenements/preferences d'Awa chez Kone vivent dans la BDD de Kone |
| Pas d'acces inverse | Kone ne voit rien du tenant Awa, et vice versa |
| Pas de conflit email cross-tenant | Chaque tenant a son propre store + Global est un store separe |
| Admin Flash Studio ne voit pas les membres locaux | Control Plane separe du Data Plane |
| Suppression tenant = suppression totale | `docker compose -p tenant-X down -v` (les comptes Global restent) |
| RGPD export | Dump PostgreSQL + LLDAP du tenant uniquement |

---

## 6. Fonctionnalites — Calendrier

### 6.1 Gestion des evenements

- Creation d'evenements avec granularite **5 minutes** (DTSTART/DTEND libres)
- Duree : de 5 minutes a plusieurs semaines
- Types d'evenements :

| Type | Description | Rendu visuel |
|------|-------------|-------------|
| `event` | Evenement ponctuel | Bloc pleine opacite, couleur membre |
| `recurring` | Evenement recurrent (RRULE RFC 5545) | Bloc + icone repetition |
| `background` | Contexte non-bloquant (compet gym, sortie scolaire) | Aplat semi-transparent pleine largeur |
| `task` | Tache planifiee (liee a `LocalTask`) | Bloc avec icone pomodoro si applicable |
| `dependent` | Genere par Event Graph (trajet, repas, accompagnement) | Bloc + lien visuel vers parent |

- Assignation a un ou plusieurs membres
- Relation parent/enfant via `parent_event_id` (equivalent RELATED-TO iCal)
- Recurrence : RRULE standard RFC 5545

### 6.2 Calendriers multiples par membre

- Chaque membre peut avoir plusieurs calendriers (Personnel, Famille, Pro, Ecole)
- Couleur et icone personnalisables par calendrier
- Visibilite configurable : `private` / `adults_only` / `family` / `custom`
- Vue agregee de tous les calendriers

### 6.3 Vues frontend

| Vue | Description |
|-----|-------------|
| **Jour** | Timeline verticale, granularite 5min, 3 couches visuelles |
| **Semaine** | 7 colonnes, scroll horizontal sur mobile |
| **Mois** | Grille classique, indicateurs de densite |
| **Agenda** | Liste chronologique (mobile-friendly) |
| **Multi-membres** | Colonnes par personne, evenements fond visibles partout |

3 couches visuelles superposees :

| Couche | Rendu | Usage |
|--------|-------|-------|
| **Fond** | Aplat semi-transparent pleine largeur | Evenement collectif (compet, sortie scolaire) |
| **Partage** | Bloc pleine opacite, couleur membre | Evenement impliquant 2+ membres |
| **Personnel** | Bloc couleur calendrier | Tache ou evenement d'un seul membre |

### 6.4 CalDAV integre (RFC 4791)

Ase expose un serveur CalDAV directement depuis Django :

```
https://ase.tenant.flash.studio/caldav/{username}/
├── calendrier-famille/
├── calendrier-personnel/
└── calendrier-pro/
```

- Compatible Apple Calendrier (iPhone, iPad, Mac) sans configuration
- Compatible Google Agenda via compte CalDAV custom
- Export iCal (.ics) par calendrier pour abonnement exterieur
- Propagation d'une modification < 5 secondes sur tous les clients
- App-specific passwords pour les clients CalDAV (pas le mot de passe principal)

### 6.5 Import .ics

Ase supporte l'import de fichiers `.ics` (iCalendar RFC 5545) :

- **Upload** : drag & drop ou bouton "Importer" dans les Settings du calendrier
- **Parsing** : `vobject` parse le fichier, gere VEVENT, VTODO, RRULE, VALARM
- **Mapping** : chaque VEVENT devient un `Event`, les RRULE deviennent des evenements recurrents
- **Deduplication** : par UID iCalendar — si un evenement avec le meme UID existe, il est mis a jour (pas duplique)
- **Previsualisation** : avant import, l'utilisateur voit les N evenements a importer et peut decocher
- **Sources** : Google Calendar export, Apple Calendar export, Outlook .ics, tout fichier RFC 5545

### 6.6 Edition d'evenements recurrents

Quand un membre modifie ou supprime une occurrence d'un evenement recurrent :

```
┌────────────────────────────────────────┐
│  Modifier l'evenement recurrent        │
│                                        │
│  "Gym Julia" — Samedi 10h (chaque sem) │
│                                        │
│  ○ Cette occurrence uniquement         │
│  ○ Cet evenement et les suivants       │
│  ○ Tous les evenements de la serie     │
│                                        │
│  [Confirmer]  [Annuler]                │
└────────────────────────────────────────┘
```

- **Cette occurrence** : cree un `EventException` avec `replacement_event` (ou `null` si suppression)
- **Cet evenement et les suivants** : tronque la RRULE de l'original (`UNTIL=date-1`), cree un nouvel evenement recurrent a partir de cette date
- **Tous** : modifie l'evenement parent directement

### 6.7 QR Code setup mobile

```
Ase → Settings → "Ajouter a mon telephone"
    │
    ├── iPhone : genere un .mobileconfig (Apple Configuration Profile)
    │   Scan QR → CalDAV auto-configure (serveur, login, app-password)
    │
    └── Android : genere un intent:// link
        Scan QR → ouvre l'app Calendrier → CalDAV pre-rempli
```

---

## 7. Fonctionnalites — Integration Taches-Calendrier

### 7.1 Pomodoro → Creneau automatique

C'est le killer feature d'Ase v3 — le pont entre productivite et calendrier.

```
Utilisateur cree une tache :
  "Rediger proposition client"
  estimated_minutes: 50 (= 2 pomodoros de 25min)
  due_date: mercredi 17h

Ase propose automatiquement :
  ┌──────────────────────────────┐
  │ Mercredi                      │
  │                               │
  │ 14:00 ┌─────────────────────┐ │
  │       │ Pomodoro 1/2        │ │
  │       │ Rediger proposition  │ │
  │ 14:25 └─────────────────────┘ │
  │ 14:25 ┌─────────────────────┐ │
  │       │ Pause 5min          │ │
  │ 14:30 └─────────────────────┘ │
  │ 14:30 ┌─────────────────────┐ │
  │       │ Pomodoro 2/2        │ │
  │       │ Rediger proposition  │ │
  │ 14:55 └─────────────────────┘ │
  │                               │
  └──────────────────────────────┘

Le creneau est visible sur le calendrier familial.
Le reste de la famille sait que Papa est occupe de 14h a 15h.
```

Logique :
1. L'utilisateur cree/modifie une tache avec `estimated_minutes` et `due_date`
2. Ase calcule le nombre de pomodoros (selon le mode du user)
3. Ase cherche un creneau libre dans le calendrier avant la `due_date`
4. Si conflit, propose des alternatives
5. Les creneaux pomodoro sont des evenements `task` dans le calendrier
6. Quand le pomodoro demarre, l'evenement passe en "en cours"
7. Quand le pomodoro finit, l'evenement est marque "termine"

### 7.2 DailyPlan → Planning calendrier

Le `DailyPlan` existant (Phase 3-4) genere un planning visuel :

```
DailyPlan du jour = [tache A (30min), tache B (50min), tache C (25min)]
                        │
                        ▼
Ase repartit sur la journee selon :
├── Creneaux deja pris (evenements existants)
├── Profil d'energie du user (historique EnergyReading)
│   → Tache difficile en pic d'energie (ex: matin)
│   → Tache legere en creux (ex: apres dejeuner)
└── Preferences horaires (UserSettings)
```

### 7.3 Adaptateurs externes → Calendrier

Les taches de sources externes (Plane, GitHub) qui ont un `due_date` et `estimated_minutes` generent aussi des creneaux calendrier si l'utilisateur active l'option.

---

## 8. Fonctionnalites — Agents IA

### 8.1 Event Graph (evenements dependants)

Un evenement racine genere automatiquement des sous-evenements contextuels.

**Exemple concret :**
```
Evenement racine : "Competition gym Julia — Samedi 10h, Gymnase Voltaire"
    │
    Agent IA detecte et propose :
    │
    ├── Trajet aller (Google Maps API)
    │   "Depart maison → Gymnase Voltaire"
    │   Samedi 9h20 (40min trajet) — assigne: Maman
    │
    ├── Accompagnement
    │   "Accompagner Julia a la compet"
    │   Samedi 9h20-12h30 — assigne: Maman
    │
    ├── Dejeuner post-compet
    │   "Restaurant famille apres la compet"
    │   Samedi 12h30 — assigne: toute la famille
    │   Suggestion: Chez Amadou (favori, 500m du gymnase)
    │
    └── Trajet retour
        "Gymnase Voltaire → Maison"
        Samedi 14h00 — assigne: Maman
```

**Flux :**
1. Evenement racine cree (manuellement ou via CalDAV)
2. Agent detecte via webhook interne
3. Agent identifie les membres concernes (profil famille + historique)
4. Agent calcule les dependances (trajet, pauses, repas)
5. Agent recherche restaurant/service (Google Places, preferences Qdrant)
6. Agent envoie proposition via **Telegram** (human-in-the-loop)
7. Famille valide ou modifie
8. Sur validation : creation dans PostgreSQL + booking externe confirme

### 8.2 Capacites de l'agent

| Capacite | Priorite | Detail |
|----------|----------|--------|
| Creation evenements dependants | P0 | Trajet, accompagnement, repas depuis evenement racine |
| Calcul de trajet | P0 | Google Maps API — duree + heure de depart |
| Recherche restaurant/service | P0 | Google Places / TheFork API, filtre preferences |
| Booking externe | P0 | Reservation restaurant/service via API partenaire |
| Human-in-the-loop | P0 | Validation Telegram avant toute action irreversible |
| Langage naturel | P0 | "Julia gym samedi 10h" → evenement parse |
| Rappels intelligents | P1 | Notification selon distance/contexte |
| Gestion conflits | P1 | Detection chevauchements, proposition alternatives |
| Taches recurrentes | P1 | Menage, courses — rotation entre membres |
| Digest hebdo | P1 | Resume dimanche soir pour chaque membre |
| Optimisation planning | P2 | Reorganisation si surcharge detectee |
| Templates auto | P2 | L'IA apprend les patterns apres 3 occurrences |

### 8.3 NLP — Langage naturel

L'entree en langage naturel est **P0**, pas une feature optionnelle. C'est le "wow moment" du produit.

**Entrees supportees :**
- Champ texte dans l'app : "Julia gym samedi 10h"
- Telegram bot : `/ajoute Julia dentiste mardi 14h`
- Vocal (Phase 2) : dictee → transcription → parsing

**Parsing :**
```
"Julia gym samedi 10h au gymnase Voltaire"
    │
    Agent NLP extrait :
    ├── Membre : Julia
    ├── Titre : Gym
    ├── Date : prochain samedi
    ├── Heure : 10h00
    ├── Lieu : Gymnase Voltaire
    └── Duree : estimee 2h (historique)
    │
    → Cree evenement + lance Event Graph
```

**Specification technique NLP :**

| Aspect | Choix | Justification |
|--------|-------|---------------|
| **Modele** | LLM via LiteLLM (meme provider que l'agent) | Pas de modele NLP custom a maintenir, multilangue natif |
| **Fallback** | Regex patterns pour formats courants (date/heure FR/EN) | Si LLM indisponible ou budget epuise |
| **Latence cible** | < 500ms (p95) pour le parsing inline | UX temps reel dans le champ texte |
| **Langues** | FR, EN (P0) — autres langues via LLM sans config | i18next deja present |
| **Entites extraites** | `member`, `title`, `date`, `time`, `duration`, `location`, `recurrence` | Mapping direct vers Event |
| **Ambiguite** | Si confiance < 80%, affiche les champs pre-remplis pour validation humaine | Pas de creation silencieuse |
| **Contexte circle** | Le parsing connait les noms des membres du circle pour le matching | Evite "Julia qui ?" |
| **Format sortie** | JSON structure : `{member_id, title, start_at, end_at, location, rrule}` | Consomme par le frontend |
| **Budget** | Eco models (Qwen3-coder, DeepSeek-v3) suffisent pour le parsing NLP | ~0.001$/requete |

### 8.4 Digest hebdomadaire IA

Chaque dimanche soir, l'agent genere un resume personnalise :

```
┌──────────────────────────────────────────┐
│  Semaine du 10 au 16 mars — Famille Kone  │
│                                           │
│  Dr. Kone :                               │
│  ├── 12 patients (Cal.com)                │
│  ├── 3h deep work planifiees              │
│  └── Conflit mercredi 14h : RDV + pomodoro│
│                                           │
│  Awa :                                    │
│  ├── 2 accompagnements Julia              │
│  └── Courses samedi matin                 │
│                                           │
│  Julia :                                  │
│  ├── Compet gym samedi (Event Graph actif) │
│  └── 5 pomodoros devoirs                  │
│                                           │
│  Suggestions :                            │
│  └── Deplacer pomodoro mercredi a jeudi ? │
└──────────────────────────────────────────┘
```

Envoye via push notification (PWA) + Telegram.

### 8.5 Securite de l'agent

| Mesure | Implementation |
|--------|---------------|
| **Token scope** | L'agent a un API token avec permissions explicites (`event:create`, `event:read`, `booking:propose` — pas `event:delete`, pas `user:manage`) |
| **Rate limit** | Max 20 actions/heure par tenant |
| **Audit log signe** | Chaque action : `{who, what, when, approved_by, hash}` en append-only |
| **Kill switch** | Le tenant admin peut desactiver l'agent a tout moment (Settings → Agent IA → Off) |
| **Budget par action** | Booking > 50 EUR requiert double validation (Telegram + in-app) |
| **Timeout** | Sans reponse humaine sous 30 minutes, l'agent annule et notifie |
| **Pas d'action irreversible** | L'agent ne peut JAMAIS supprimer, modifier ou envoyer sans validation humaine |

---

## 9. Fonctionnalites — UX et Mobile

### 9.1 PWA (Progressive Web App)

| Capacite | Implementation |
|----------|---------------|
| Installable | `manifest.json` + Service Worker |
| Push notifications | Web Push API (rappels, validations agent) |
| Offline | Cache-first pour lecture calendrier, queue pour ecritures |
| Icone ecran d'accueil | Logo Ase + badge notifications |
| Splash screen | Theme Afrofuturist |

### 9.2 Magic Link / Passkey

**Defaut pour les invites famille** : pas de mot de passe a retenir.

| Methode | Disponibilite | UX |
|---------|--------------|-----|
| **Magic Link** (email) | Authelia + Zitadel | Clic dans email → connecte |
| **Passkey** (WebAuthn) | Authelia + Zitadel | FaceID / empreinte → connecte |
| Mot de passe | Fallback | Formulaire classique |

### 9.3 Visibilite par role

Chaque evenement a un niveau de visibilite :

| Niveau | Qui voit | Exemple |
|--------|----------|---------|
| `family` | Tous les membres | "Diner en famille" |
| `adults_only` | Membres avec role `adult` uniquement | "RDV gynecologue" |
| `private` | Createur uniquement | "Entretien embauche" |
| `custom` | Membres selectionnes | "Surprise anniversaire Papa" (sans Papa) |

Les enfants avec role `child` ne voient **jamais** les evenements `adults_only`.

### 9.4 Creation rapide d'evenement

```
Tap sur creneau vide dans le calendrier
    │
    ▼
┌──────────────────────────────────┐
│  Nouveau evenement               │
│                                  │
│  [Titre ou phrase naturelle    ] │ ← NLP parsing en temps reel
│                                  │
│  👤 Membres : [Dr.K] [Awa] [+]  │ ← Avatars cliquables
│                                  │
│  ⏱  Duree : [5m] [15m] [30m]    │
│             [1h] [journee]       │ ← Presets
│                                  │
│  👀 Visibilite : [Famille ▾]     │
│                                  │
│  🍅 Pomodoro : [ ] Activer       │ ← Si tache
│                                  │
│  [Creer]  [+ Details]            │
└──────────────────────────────────┘

Le champ titre accepte le langage naturel :
"Julia gym samedi 10h" → pre-remplit les champs automatiquement
```

### 9.5 Gestion des conflits

Quand deux evenements se chevauchent :

```
┌──────────────────────────────────────────┐
│  Conflit detecte                          │
│                                           │
│  ┌──────────┐ ←→ ┌──────────────────┐    │
│  │ Pomodoro │    │ Accompagnement   │    │
│  │ 14h-14h25│    │ Julia 14h-15h    │    │
│  └──────────┘    └──────────────────┘    │
│                                           │
│  Suggestions IA :                         │
│  ○ Deplacer le pomodoro a 15h30           │
│  ○ Raccourcir a 1 pomodoro (25min→13h30) │
│  ○ Annuler le pomodoro                    │
│                                           │
│  [Choisir] [Ignorer le conflit]           │
└──────────────────────────────────────────┘
```

---

## 10. Modele de donnees

### Nouvelles apps Django

```
ase/
├── app/             # Existant — Flow Engine (Session, LocalTask, Energy…)
├── api/             # Existant — DRF viewsets
├── adapters/        # Existant — TaskSource adapters
├── calendar/        # NOUVEAU — Calendrier + CalDAV
├── circles/         # NOUVEAU — Groupes, membres, roles, invitation
├── iam/             # NOUVEAU — OIDC + UserProvider
└── agents/          # NOUVEAU — Event Graph, NLP, Telegram
```

### App `circles`

Le terme **Circle** est volontairement generique. Un Circle peut etre :

| Preset | Exemple | Roles typiques |
|--------|---------|----------------|
| `family` | Famille Kone | admin, adult, child, guest |
| `colocation` | Coloc Rue Voltaire | admin, roommate, guest |
| `team` | Cabinet Dr. Kone | admin, member, intern, guest |
| `club` | FC Abidjan U15 | admin, coach, player, parent |
| `custom` | Groupe projet X | admin, member, guest |

Le preset determine les **roles disponibles** et les **labels UI** (ex: "Membres" vs "Colocataires" vs "Joueurs") mais la logique technique est identique.

```python
CIRCLE_PRESET_CHOICES = (
    ("family", "Famille"),
    ("colocation", "Colocation"),
    ("team", "Equipe"),
    ("club", "Club / Association"),
    ("custom", "Personnalise"),
)

class Circle(Model):
    """Un groupe de personnes partageant un calendrier et des taches.
    N circles par tenant (ex: famille + club sport + projet pro).
    Peut representer une famille, une equipe, un club, etc."""
    name: str                          # "Famille Kone", "Coloc Voltaire", "FC Abidjan"
    preset: str                        # "family" | "colocation" | "team" | "club" | "custom"
    tenant_id: str                     # Identifiant tenant Flash Studio
    is_primary: bool                   # True = circle principal du tenant (cree automatiquement)
    timezone: str                      # "Africa/Abidjan"
    agent_enabled: bool                # Kill switch agent IA
    agent_budget_limit: Decimal        # Budget max booking auto (EUR)
    created_at: datetime

class CircleMember(Model):
    """Lien entre un User Django et un Circle."""
    user: FK(User)
    circle: FK(Circle)
    role: str                          # Roles dependant du preset :
                                       #   family: "admin" | "adult" | "child" | "guest"
                                       #   colocation: "admin" | "roommate" | "guest"
                                       #   team: "admin" | "member" | "intern" | "guest"
                                       #   club: "admin" | "coach" | "player" | "parent"
                                       #   custom: "admin" | "member" | "guest"
    display_name: str                  # "Awa", "Coach Diallo"
    avatar_color: str                  # "#E76F51"
    avatar_emoji: str                  # optionnel
    invite_token: str                  # HMAC signe, usage unique
    invite_accepted_at: datetime | None
    created_at: datetime

    # --- Guest federe cross-tenant ---
    membership_type: str               # "local" | "federated"
                                       # local = identite dans le LLDAP/Zitadel du tenant
                                       # federated = identite dans Zitadel Global
    external_issuer: str | None        # URL issuer OIDC externe (ex: "https://global.flash.studio")
                                       # null si membership_type="local"
    external_sub: str | None           # Subject ID dans l'issuer externe (UUID)
                                       # null si membership_type="local"

    class Meta:
        unique_together = [("user", "circle")]
        constraints = [
            # Un guest federe est identifie par son issuer+sub dans ce circle
            UniqueConstraint(
                fields=["circle", "external_issuer", "external_sub"],
                condition=Q(membership_type="federated"),
                name="unique_federated_member_per_circle",
            ),
        ]
```

### App `calendar`

```python
class Calendar(Model):
    """Un calendrier appartenant a un membre."""
    owner: FK(CircleMember)
    name: str                          # "Personnel", "Famille", "Pro"
    color: str                         # "#2D6A4F"
    icon: str                          # "briefcase" (lucide icon name)
    visibility: str                    # "private" | "adults_only" | "family" | "custom"
    caldav_enabled: bool               # Expose via CalDAV ?
    created_at: datetime

class Event(Model):
    """Un evenement dans un calendrier."""
    uid: UUID                          # iCal UID (RFC 5545)
    calendar: FK(Calendar)
    parent_event: FK("self", null)     # Event Graph — RELATED-TO
    title: str
    description: str
    location: str
    start_at: datetime                 # DTSTART
    end_at: datetime                   # DTEND
    all_day: bool
    event_type: str                    # "event" | "recurring" | "background"
                                       # | "task" | "dependent"
    display_mode: str                  # "normal" | "background" | "private" | "shared"
    visibility: str                    # "family" | "adults_only" | "private" | "custom"
    recurrence_rule: str               # RRULE string (RFC 5545), nullable
    members: M2M(CircleMember)         # Membres concernes
    linked_task: FK(LocalTask, null)   # Lien vers tache Ase (pomodoro→creneau)

    # Event Graph metadata
    dependent_type: str | None         # "transport" | "meal" | "accompany" | "break"
    booking_ref: JSON | None           # {provider, booking_id, amount, currency}
    validated_by: FK(CircleMember, null)
    validated_at: datetime | None

    # CalDAV sync
    etag: str                          # ETag pour sync CalDAV
    caldav_raw: str                    # iCal brut (cache pour CalDAV GET)

    created_at: datetime
    updated_at: datetime

    class Meta:
        indexes = [
            Index(fields=["calendar", "start_at", "end_at"]),
            Index(fields=["parent_event"]),
            Index(fields=["linked_task"]),
        ]

class EventException(Model):
    """Exception a un evenement recurrent (RFC 5545 EXDATE/modification)."""
    recurring_event: FK(Event)
    original_start: datetime           # Date d'occurrence modifiee
    replacement_event: FK(Event, null) # Evenement de remplacement (null = supprime)
    created_at: datetime

class EventReminder(Model):
    """Rappel associe a un evenement (RFC 5545 VALARM)."""
    event: FK(Event, related_name="reminders")
    member: FK(CircleMember, null)     # null = tous les membres de l'event
    offset_minutes: int                # Minutes avant l'evenement (ex: 15, 60, 1440)
    channel: str                       # "push" | "telegram" | "email"
    sent_at: datetime | None           # null = pas encore envoye
    created_at: datetime

    class Meta:
        unique_together = [("event", "member", "offset_minutes", "channel")]
```

### App `iam`

```python
class OIDCConfig(Model):
    """Configuration OIDC du tenant (singleton par tenant)."""
    issuer_url: str                    # https://auth.tenant.flash.studio
    client_id: str
    client_secret: str                 # Chiffre en BDD
    backend_type: str                  # "lldap" | "zitadel"
    api_url: str                       # URL API management du provider

class TrustedExternalIdP(Model):
    """IdP externe de confiance pour guest federes."""
    issuer_url: str                    # "https://global.flash.studio"
    client_id: str                     # Client OIDC enregistre aupres de l'IdP externe
    client_secret: str                 # Chiffre en BDD
    display_name: str                  # "Flash Studio" (affiche sur le bouton login)
    enabled: bool                      # Activer/desactiver la federation
    created_at: datetime

    class Meta:
        unique_together = [("issuer_url",)]

class AppSpecificPassword(Model):
    """Mot de passe applicatif pour CalDAV (pas le MDP principal)."""
    user: FK(User)
    name: str                          # "iPhone de Awa"
    password_hash: str                 # bcrypt hash
    last_used_at: datetime | None
    created_at: datetime
    expires_at: datetime | None        # Optionnel, defaut 1 an
```

### App `agents`

```python
class AgentAction(Model):
    """Audit log de chaque action de l'agent IA."""
    circle: FK(Circle)
    action_type: str                   # "event_create" | "booking_propose"
                                       # | "event_suggest" | "digest_send"
    payload: JSON                      # Details de l'action
    proposed_at: datetime
    approved_by: FK(CircleMember, null)
    approved_at: datetime | None
    rejected_at: datetime | None
    executed_at: datetime | None
    error: str                         # Si execution echouee
    integrity_hash: str                # SHA-256 du payload (append-only)

    class Meta:
        ordering = ["-proposed_at"]

class MemberPreference(Model):
    """Preferences d'un membre pour l'agent IA (restaurants, habitudes…)."""
    member: FK(CircleMember)
    category: str                      # "restaurant" | "transport" | "schedule"
    key: str                           # "favorite_restaurant_1"
    value: JSON                        # {name, address, cuisine, rating}
    confirmed: bool                    # Explicitement valide par le membre
    source: str                        # "manual" | "learned" | "imported"
    created_at: datetime
    updated_at: datetime

class NotificationPreference(Model):
    """Preferences de notification par membre (canaux, heures calmes, types)."""
    member: FK(CircleMember, unique=True)

    # Canaux actives
    push_enabled: bool                 # PWA push notifications
    telegram_enabled: bool             # Telegram bot
    email_enabled: bool                # Email (Brevo / Stalwart)

    # Heures calmes (pas de notification sauf urgence)
    quiet_start: time | None           # ex: 22:00
    quiet_end: time | None             # ex: 07:00

    # Preferences par type de notification
    notify_event_created: bool         # Nouvel evenement dans mes calendriers
    notify_event_modified: bool        # Modification d'un evenement ou je suis assigne
    notify_event_reminder: bool        # Rappels VALARM
    notify_agent_proposal: bool        # L'agent propose une action
    notify_agent_digest: bool          # Digest hebdomadaire
    notify_conflict: bool              # Conflit detecte sur mon planning
    notify_invitation: bool            # Invitation a rejoindre un circle

    updated_at: datetime
```

### Modifications aux modeles existants

Les modeles v2 ne sont **pas modifies**. Les nouvelles apps Django referencent les modeles existants par FK :
- `Event.linked_task → LocalTask` (pomodoro → creneau)
- `CircleMember.user → User` (lien auth)
- Les `Session`, `EnergyReading`, `DailyPlan`, `Achievement` restent inchanges

---

## 11. Securite

### 11.1 Authentification

| Mesure | Implementation |
|--------|---------------|
| OIDC tokens en cookie | `HttpOnly=True`, `Secure=True`, `SameSite=Strict` |
| Jamais de token en localStorage | XSS = pas de vol de session |
| Refresh token rotation | Nouveau refresh token a chaque utilisation |
| Session revocation | Suppression membre → blacklist token + invalidation sessions |

### 11.2 CalDAV

| Mesure | Implementation |
|--------|---------------|
| App-specific passwords | Generes par Ase, bcrypt, revocables, expiration 1 an |
| Pas le MDP principal | Le MDP OIDC n'est JAMAIS utilise pour CalDAV |
| TLS obligatoire | CalDAV uniquement sur HTTPS |
| Rate limiting | Max 100 requetes/minute par user CalDAV |

### 11.3 Invitation famille

| Mesure | Implementation |
|--------|---------------|
| Token HMAC signe | `HMAC-SHA256(secret, email + family_id + timestamp)` |
| Expiration 24h | Token invalide apres 24h |
| Usage unique | Token supprime apres utilisation |
| Rate limiting | Max 10 invitations/jour par tenant |
| Email verification | L'invite doit cliquer le magic link envoye a son email |

### 11.4 Agent IA

| Mesure | Implementation |
|--------|---------------|
| Token scope | Permissions explicites par action |
| Rate limit | 20 actions/heure par tenant |
| Audit log signe | SHA-256 hash, append-only, non modifiable |
| Kill switch | `Circle.agent_enabled = False` → agent desactive |
| Budget par action | Booking > seuil → double validation |
| Timeout | 30min sans reponse → annulation + notification |
| Pas de suppression | L'agent ne peut JAMAIS supprimer un evenement |

### 11.5 Isolation tenant

| Mesure | Implementation |
|--------|---------------|
| Namespace Docker | Chaque tenant = `docker compose -p tenant-X` |
| Reseau isole | Chaque tenant a son propre bridge Docker |
| BDD isolee | PostgreSQL par tenant (pas de schema partage) |
| IAM isole | LLDAP/Zitadel par tenant |
| Backup chiffre | Cle AES-256 par tenant, rotation trimestrielle |
| RGPD suppression | Suppression namespace = suppression totale |

### 11.6 Webhooks

| Source | Securite |
|--------|----------|
| Cal.com → Ase | HMAC signature + nonce + timestamp (anti-replay) |
| n8n → Ase | Header `X-Webhook-Secret` (existant, inchange) |
| Ase → Telegram | Bot token + chat_id valides |

---

## 12. Contraintes non-fonctionnelles

### Performance

| Metrique | Cible |
|----------|-------|
| Chargement initial PWA | < 2 secondes (reseau local / VPN) |
| Propagation CalDAV | < 5 secondes |
| Reponse API DRF | < 200ms (p95) |
| Agent IA proposition | < 10 secondes apres creation evenement |
| Offline → Online sync | < 3 secondes au retour de connexion |

### Compatibilite calendriers

| Plateforme | Statut | Mecanisme |
|------------|--------|-----------|
| Apple Calendrier (iOS/macOS) | P0 | CalDAV natif (RFC 4791) |
| Google Agenda (Android/Web) | P0 | CalDAV custom account |
| Cal.com (pro) | P1 | REST API + webhook |
| Thunderbird | P2 | CalDAV standard |
| Outlook | Hors scope v3 | Exchange CalDAV bridge |

### Ressources (par tenant)

| Profil | RAM totale | VPS |
|--------|-----------|-----|
| Famille (< 10 membres, Authelia) | ~300MB | CX22 (4GB) |
| Structure (10-50 membres, Zitadel) | ~800MB | CX32 (8GB) |

---

## 13. Migration v2 → v3

### 13.1 Migration des donnees

| Donnees v2 | Action v3 | Risque |
|------------|-----------|--------|
| `User` (django-allauth) | Conserve. Ajout champs OIDC via `mozilla-django-oidc`. Fallback allauth en dev | Faible |
| `Session`, `EnergyReading`, `Pomodoro` | Inchanges. FK vers `User` preservees | Aucun |
| `LocalTask` | Inchange. Nouveau FK optionnel `Event.linked_task` | Aucun |
| `TaskSourceConfig` | Inchange | Aucun |
| `DailyPlan`, `Achievement`, `Rewards` | Inchanges | Aucun |
| `UserSettings` | Inchange. Nouvelles preferences dans `NotificationPreference` (nouveau modele) | Aucun |
| `AISuggestion` | Conserve (legacy). Nouveau systeme via `AgentAction` | Aucun |

### 13.2 Migration de l'authentification

```
Phase A (backward-compatible) :
├── Installer mozilla-django-oidc
├── Ajouter OIDC comme backend AUTH supplementaire (pas remplacement)
├── Les users existants continuent avec allauth
├── Les nouveaux users passent par OIDC
└── Duree : Phase 0 du projet

Phase B (migration complete) :
├── Pour chaque User existant :
│   ├── Creer le user dans LLDAP/Zitadel du tenant (via UserProvider)
│   ├── Mapper le User Django existant au sub OIDC
│   └── Envoyer un email "Votre nouveau lien de connexion"
├── Desactiver allauth (retirer de AUTHENTICATION_BACKENDS)
└── Duree : fin Phase 0

Fallback :
├── Si OIDC echoue, re-activer allauth comme backend secondaire
├── Variable d'env : AUTH_FALLBACK_ALLAUTH=true
└── Jamais en production (dev/staging uniquement)
```

### 13.3 Migration de la base de donnees

- Nouvelles apps (`calendar/`, `circles/`, `iam/`, `agents/`) = nouvelles tables uniquement
- **Zero modification** des tables v2 existantes
- Migrations Django standard (`makemigrations` + `migrate`)
- Rollback possible : supprimer les nouvelles tables sans affecter v2

### 13.4 Checklist de migration par tenant

- [ ] Backup PostgreSQL du tenant
- [ ] Deployer Ase v3 (nouvelles apps + OIDC)
- [ ] Configurer variables OIDC (`OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, etc.)
- [ ] Executer `python manage.py migrate` (nouvelles tables)
- [ ] Creer le Circle primaire pour le tenant
- [ ] Migrer les users existants vers OIDC (script `migrate_users_to_oidc`)
- [ ] Verifier connexion OIDC pour chaque user
- [ ] Desactiver allauth
- [ ] Tester CalDAV, agent IA, notifications

---

## 14. Phases de livraison

### Phase 0 — Auth OIDC + Circles (3 semaines)

**Objectif** : Ase passe de django-allauth a OIDC. Concept de Circle (groupe generique) avec membres locaux et federes.

| Tache | Detail |
|-------|--------|
| App `iam/` | `mozilla-django-oidc`, config OIDC par env var, modeles `OIDCConfig` + `TrustedExternalIdP` |
| App `circles/` | Modeles Circle, CircleMember (avec `membership_type`, `external_issuer`, `external_sub`) |
| Migration auth | allauth → OIDC (backward-compatible: allauth reste en fallback dev) |
| Invitation locale | Token HMAC, magic link, UserProvider (LLDAP + Zitadel) |
| Invitation federee | Verification Zitadel Global API, bouton "Se connecter avec Flash Studio", mapping `external_sub` |
| Frontend | Page Circle (preset selector, invite local, invite abonne, liste membres, roles, badge "federe") |
| Tests | Auth OIDC mock, invitation local + federe, role permissions, isolation cross-tenant |

**Critere de sortie** : un utilisateur se connecte via OIDC, invite un membre local ET un abonne Flash Studio en guest federe, les deux se connectent et voient le calendrier.

### Phase 1 — Calendrier core (4 semaines)

**Objectif** : Calendrier fonctionnel avec 3 couches visuelles et CalDAV.

| Tache | Detail |
|-------|--------|
| App `calendar/` | Modeles Calendar, Event, EventException |
| CalDAV server | Django views CalDAV (GET/PUT/DELETE/PROPFIND/REPORT) via `vobject` |
| Frontend vues | Jour, Semaine, Mois, Agenda — composants React |
| 3 couches | Fond / Partage / Personnel — rendu CSS |
| CRUD evenements | Creation, edition, suppression, recurrence (RRULE) |
| Visibilite | Filtrage par role (`adults_only`, `private`, etc.) |
| Tests | CalDAV compliance RFC 4791, CRUD events, visibilite |

**Critere de sortie** : un evenement cree dans Ase apparait dans Apple Calendrier sous 5s.

### Phase 2 — Taches ↔ Calendrier + PWA (3 semaines)

**Objectif** : Le pont pomodoro → creneau. Ase devient une PWA.

| Tache | Detail |
|-------|--------|
| Pomodoro → creneau | `Event.linked_task` + logique de placement auto |
| DailyPlan → planning | Repartition basee sur profil d'energie |
| Conflits | Detection chevauchement + suggestions |
| PWA | Service Worker, manifest.json, offline cache, push |
| QR CalDAV | Generation .mobileconfig (Apple) + intent (Android) |
| App-specific passwords | Generation, revocation, UI dans Settings |
| Tests | Placement pomodoro, conflict detection, PWA offline |

**Critere de sortie** : une tache avec pomodoro cree un creneau visible sur l'iPhone du conjoint.

### Phase 3 — Agent IA v1 + NLP (4 semaines)

**Objectif** : Event Graph, langage naturel, human-in-the-loop.

| Tache | Detail |
|-------|--------|
| App `agents/` | AgentAction, MemberPreference |
| Event Graph | Detection racine → generation dependances |
| NLP parsing | Champ texte → extraction entites (membre, date, lieu) |
| Google Maps | API Directions pour calcul trajets |
| Telegram bot | Propositions, validations, commandes (`/planning`, `/ajoute`) |
| Audit log | Actions signees, append-only |
| Scoped tokens | Permissions agent explicites |
| Tests | Event Graph scenarios, NLP parsing, audit integrity |

**Critere de sortie** : "Julia gym samedi 10h" cree un evenement + trajet + proposition dejeuner via Telegram.

### Phase 4 — Cal.com + Booking + Digest (3 semaines)

**Objectif** : Integration pro et intelligence avancee.

| Tache | Detail |
|-------|--------|
| Cal.com integration | Webhook → Ase, vue unifiee pro+famille |
| Booking restaurant | Google Places / TheFork API, preferences |
| Digest hebdo | Generation dimanche soir, envoi push + Telegram |
| Templates auto | Detection patterns, creation templates apres 3 occurrences |
| Budget evenement | Montant sur l'evenement, total mensuel |
| Tests | Cal.com webhook, booking flow, digest generation |

**Critere de sortie** : un booking Cal.com apparait dans le calendrier familial. Digest envoye chaque dimanche.

### Phase 5 — Polish + Mobile + Observabilite (2 semaines)

**Objectif** : Production-ready.

| Tache | Detail |
|-------|--------|
| Mobile polish | Touch gestures, swipe, responsive fine-tuning |
| Accessibility | ARIA labels, keyboard navigation, screen reader |
| Grafana dashboards | Metriques CalDAV, agent actions, API latency |
| Documentation | Guide utilisateur, guide admin tenant |
| Performance | Optimisation queries, cache Redis calendrier |
| Ansible role | Role flash-infra pour deploiement Ase v3 |

**Critere de sortie** : Ase v3 deploye en production pour un tenant pilote.

---

## 15. Criteres d'acceptation

### P0 — Bloquants pour production

| # | Critere |
|---|---------|
| 1 | Un utilisateur se connecte via OIDC (Authelia ou Zitadel) |
| 2 | Un admin famille invite un membre par email (magic link) |
| 3 | Le membre invite accede a Ase sans creer de compte Flash Studio |
| 4 | Le membre invite est invisible du Control Plane |
| 5 | Un evenement cree dans Ase apparait dans Apple Calendrier sous 5 secondes |
| 6 | Un evenement cree dans Ase apparait dans Google Agenda sous 5 secondes |
| 7 | Un evenement peut etre cree avec une duree de 5 minutes exactement |
| 8 | La vue calendrier affiche les 3 couches (fond / partage / personnel) |
| 9 | Les enfants (`role=child`) ne voient pas les evenements `adults_only` |
| 10 | Une tache avec pomodoro + due_date cree automatiquement un creneau calendrier |
| 11 | "Julia gym samedi 10h" en champ texte cree un evenement correctement parse |
| 12 | L'agent ne pose JAMAIS une action irreversible sans validation Telegram |
| 13 | L'agent a un audit log signe pour chaque action |
| 14 | Ase est installable comme PWA sur mobile |
| 15 | Les tokens OIDC sont en cookie HttpOnly (jamais localStorage) |
| 16 | Un abonne Flash Studio peut etre invite comme guest federe dans une autre famille |
| 17 | Le guest federe se connecte via Zitadel Global, pas via le LLDAP du tenant hote |
| 18 | Les donnees du guest federe restent dans la BDD du tenant hote (isolation preservee) |
| 19 | La suppression du tenant hote ne supprime pas le compte Global du guest federe |

### P1 — Requis avant GA

| # | Critere |
|---|---------|
| 20 | QR code configure CalDAV sur iPhone en 1 scan |
| 21 | L'agent calcule l'heure de depart pour un accompagnement (±10 min) |
| 22 | Le digest hebdo est envoye chaque dimanche avec le planning personnalise |
| 23 | Un booking Cal.com cree un evenement dans le calendrier familial |
| 24 | Offline : le calendrier est consultable sans connexion (PWA cache) |
| 25 | Les taches recurrentes se repartissent entre membres selon rotation |
| 26 | Grafana affiche les metriques : CalDAV latency, agent actions, API errors |
| 27 | Backup Restic s'execute et est restaurable par tenant |
| 28 | L'import .ics parse correctement un export Google Calendar |
| 29 | L'edition d'un evenement recurrent propose "cette occurrence / suivants / tous" |
| 30 | Les rappels VALARM declenchent push + Telegram selon les preferences |
| 31 | Les modifications calendrier se propagent en temps reel (WebSocket) aux membres connectes |
| 32 | Les heures calmes de NotificationPreference sont respectees |

---

## 16. Risques et mitigations

| Risque | Probabilite | Impact | Mitigation |
|--------|-------------|--------|------------|
| CalDAV compliance Apple edge cases (recurrence, timezone) | Moyenne | Haut | Tests unitaires RFC 5545, lib `vobject` mature, suite de tests Apple CalDAV |
| API TheFork / booking restaurant instable | Haute | Moyen | Fallback Google Maps Places, liste manuelle en dernier recours |
| Agent IA hallucine preferences | Faible | Moyen | Preferences explicitement validees (`confirmed=True`), reset possible |
| Performance CalDAV sous charge (50+ membres) | Faible | Haut | Cache Redis par calendrier, pagination REPORT, index PostgreSQL |
| Migration auth allauth → OIDC casse les sessions existantes | Moyenne | Haut | Fallback allauth en mode dev, migration progressive, double auth temporaire |
| Complexite Event Graph (cascades infinies) | Faible | Moyen | Limite de profondeur (max 3 niveaux), timeout par sous-evenement |
| LLDAP pas assez riche pour cas complexes | Faible | Faible | Migration vers Zitadel premium si besoins avances |
| Push notifications PWA peu fiables sur iOS | Haute | Moyen | Telegram comme canal secondaire obligatoire, email fallback |
| Federation OIDC : Zitadel Global down = guests federes bloques | Faible | Moyen | Les membres locaux (LLDAP) ne sont pas affectes. Fallback : le tenant admin peut temporairement re-inviter le guest en local |
| Migration local → federe : perte de donnees | Faible | Haut | Script de migration qui transfere le CircleMember existant (preserve FK vers events, preferences) et desactive l'ancien compte LLDAP |

---

## 17. Hors scope (v3)

| Feature | Raison | Phase future |
|---------|--------|-------------|
| Application mobile native (iOS/Android) | PWA couvre 90% des besoins, evite app store friction | v4 si adoption le justifie |
| Integration Outlook / Exchange | Faible demande cible famille/TPE | v4 |
| Commande vocale integree | Necessite speech-to-text on-device, complexe | v4 |
| Gestion budgetaire liee aux evenements | Zimboo existe dans l'ecosysteme, pont optionnel | v3.1 |
| Marketplace de templates d'evenements | Premature avant adoption | v4 |
| Geolocalisation temps reel des membres | Implications vie privee majeures, opt-in complexe | v4 |
| Multi-tenant dans une seule instance Ase | Chaque tenant a sa propre instance Docker | Architecture decision |
| Partage public de calendriers (lien sans auth) | Risque securite, pas de cas d'usage famille | Non prevu |

---

## Annexes

### A. Standards et protocoles

| Standard | Reference |
|----------|-----------|
| CalDAV | RFC 4791 (IETF) |
| iCalendar | RFC 5545 (IETF) — DTSTART, DTEND, RELATED-TO, RRULE |
| CardDAV | RFC 6352 (optionnel v4) |
| OIDC | OpenID Connect Core 1.0 |
| WebAuthn | W3C Web Authentication |
| Web Push | RFC 8030 + VAPID (RFC 8292) |

### B. Dependances Python a ajouter (v3)

```
# Auth OIDC
mozilla-django-oidc==4.0.1

# CalDAV
vobject==0.9.7
icalendar==6.1.0

# Real-time
channels==4.1.0      # Django Channels (WebSocket)
channels-redis==4.2.1 # Redis channel layer

# Agent IA
httpx==0.27.0       # async HTTP pour Google Maps, TheFork
celery==5.4.0       # taches async (Event Graph, digest)
redis==5.0.0        # broker Celery (deja present)

# Email transactionnel
sib-api-v3-sdk==7.6.0  # Brevo (ex-Sendinblue) — phase initiale
                        # Migration Stalwart Mail (self-hosted JMAP) quand volume le justifie

# Securite
cryptography==43.0.0  # HMAC tokens, chiffrement
bcrypt==4.2.0        # App-specific passwords
```

### C. Dependances frontend a ajouter (v3)

```json
{
  "@fullcalendar/react": "^6.1.0",
  "@fullcalendar/daygrid": "^6.1.0",
  "@fullcalendar/timegrid": "^6.1.0",
  "@fullcalendar/interaction": "^6.1.0",
  "workbox-webpack-plugin": "^7.0.0",
  "qrcode.react": "^4.0.0"
}
```

### D. Variables d'environnement (nouvelles v3)

```env
# OIDC
OIDC_ISSUER_URL=https://auth.tenant.flash.studio
OIDC_CLIENT_ID=ase
OIDC_CLIENT_SECRET=xxx
OIDC_REDIRECT_URI=https://ase.tenant.flash.studio/oidc/callback/

# IAM Backend (famille)
IAM_BACKEND=lldap                         # ou "zitadel"
IAM_API_URL=http://lldap:17170            # ou http://zitadel:8080
IAM_API_KEY=xxx

# Federation — Guest federe cross-tenant
FEDERATION_ENABLED=true                   # Activer le bouton "Se connecter avec Flash Studio"
FEDERATION_GLOBAL_ISSUER=https://global.flash.studio
FEDERATION_GLOBAL_CLIENT_ID=ase-federation
FEDERATION_GLOBAL_CLIENT_SECRET=xxx

# CalDAV
CALDAV_EXTERNAL_URL=https://ase.tenant.flash.studio/caldav/

# Agent IA
AGENT_ENABLED=true
AGENT_RATE_LIMIT=20                       # actions/heure
AGENT_BOOKING_BUDGET_LIMIT=50.00          # EUR, double validation au-dessus
AGENT_TIMEOUT_MINUTES=30
GOOGLE_MAPS_API_KEY=xxx
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_FAMILY_CHAT_ID=xxx

# Cal.com (optionnel)
CALCOM_API_URL=http://calcom:3000
CALCOM_WEBHOOK_SECRET=xxx

# Email transactionnel (Brevo)
BREVO_API_KEY=xxx
EMAIL_FROM=noreply@tenant.flash.studio
EMAIL_BACKEND=brevo                   # ou "stalwart" apres migration

# Push notifications
VAPID_PUBLIC_KEY=xxx
VAPID_PRIVATE_KEY=xxx
VAPID_ADMIN_EMAIL=admin@flash.studio
```

---

*Fin du document PRD v3.0*
