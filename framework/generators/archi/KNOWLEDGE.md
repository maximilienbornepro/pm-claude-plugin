# SINBAD - connaissance architecture (schéma interactif)

Faits et décisions qui font foi pour le schéma d'architecture interactif. Le QUOI structuré est dans
[`model.json`](model.json) ; ici, le pourquoi et les nuances. Tout élément inconnu se marque « à confirmer ».

## Règles de production (harness)

- **Sous-titres : jamais automatiques.** Un sous-titre de nœud (texte secondaire sous le libellé,
  `<text class="s">`) n'est ajouté QUE sur **demande explicite** de l'utilisateur. En générer un de sa
  propre initiative est un **défaut à reverter**. Même principe pour tout nouveau nœud/flux non demandé :
  on applique le périmètre demandé, rien de plus.
- Contrôle : `validate.py <fichier> --golden <ref.golden.html>` liste tout sous-titre **ajouté** depuis le
  golden (ECHEC), pour revue consciente ; les sous-titres légitimement demandés s'acquittent en recalant le
  golden après validation. Sans `--golden`, le harness garde ses 7 invariants structurels (flux normal).

## Les trois acteurs (qui possède quoi)

- **CIP** (entité externe) : provisionne et gère le **cluster EKS partagé** et le **réseau** (Terraform CIP).
- **Devs Sinbad** (interne Safran) : développent l'app, provisionnent **namespace / PostgreSQL / S3**
  (Terraform Sinbad) et **déploient via Argo CD**. Terraform Sinbad et Argo CD ont le **même owner**.
- **Enix** (infogérance) : **déploient la plateforme via Flux** (Prometheus, Keycloak, Teleport), font la
  **supervision**, et disposent de l'**accès Zero Trust** (Teleport).

Dans la vue exploitation, ces trois acteurs sont des **encarts colorés** (CIP rouge, Devs bleu, Enix vert).
Comme l'encart porte le nom de l'équipe, les outils dedans n'ont ni suffixe ni logo d'appartenance
(« Terraform », « Argo CD », « Flux », sans « CIP »/« Sinbad » ni logo Safran/Enix).

## Le cluster et la base (projection cible)

- **Un seul cluster EKS partagé**, géré par CIP (namespace-as-a-service).
- **AIFA et l'app Sinbad tournent dans le MÊME namespace** (déployé par Argo CD).
- **Une seule PostgreSQL**, partagée par AIFA et l'app : `bff_sessions`, détections, alertes.
- Terraform est **scindé** : CIP (cluster + réseau) / Sinbad (namespace + PostgreSQL + S3).
- **S3 et PostgreSQL sont hors cluster** (services managés AWS).

## Supervision et accès (corrections importantes)

- **Les métriques partent de l'applicatif vers Prometheus** (scrape). Ce n'est **pas** Enix qui « pousse »
  des métriques. Flèche : namespace -> Prometheus, « métriques ».
- **Teleport fournit l'accès Zero Trust** au cluster ; l'acteur qui s'en sert est **Enix**. Flèche :
  Enix -> Teleport, « accès Zero Trust ». Teleport ne fait que donner la capacité.

## Chaîne AIFA

- Chaîne de traitement des images : **Scan -> GeoCheck -> GeoConvert -> GeoFence -> DEC**, puis vers les
  services applicatifs (GeoDetections).
- L'entrée (images depuis le bucket S3) arrive **par le haut** en flèche tiretée ; le bucket S3 **n'est pas
  une étape**. GeoConvert écrit le raster (COG) dans S3 /outbox ; le DEC écrit les détections dans PostgreSQL.
- **Ne jamais écrire « lit »** pour AIFA : on dit « traitement des images », « récupère », « lecture / écriture ».

## Services applicatifs et exposition (BFF)

- Pipeline alertes : GeoDetections -> Alert V2 -> Alert Aggregation ; les events partenaires (KSAT/Airbus)
  sont récupérés et normalisés par l'**ETL Alert** vers Alert Aggregation.
- **Le BFF TIRE la donnée** : il récupère détections et alertes dans les services. On modélise ça en
  **double flèche** (demande « récupère » / donnée en retour « détections / alertes », « alertes »).
- **Le Frontend appelle le BFF** (double flèche : « appelle » / « GeoJSON / alertes »). Dans la vue
  Exposition BFF, le Frontend n'est pas un bloc : c'est un appel entrant par le haut + un retour.
- Le BFF est le **point d'exposition unique**. Il enregistre la **session dans PostgreSQL** (`bff_sessions`,
  les tokens ne quittent jamais le BFF). La partie **auth est à droite** : Keycloak (broker OIDC) -> IDP OTAN.

## Identité / auth

- Flux : **User -> SAI app (React) -> API Gateway/BFF -> Keycloak (broker) -> NATO IDP**.
- Protocole **OIDC Auth Code + PKCE S256**. SSO : la session Keycloak est réutilisée pour les apps
  partenaires (Geo Warning ADS, Vake KSAT). Le diagramme de séquence complet est **maintenu par Pierre**.
- IDP OTAN = aujourd'hui Safran.AI Entra.

## Vue d'ensemble

- Encart **Safran.AI** (compte/VPC) contenant le cluster EKS ; **Exploitation** opère le cluster (« opère »).
- Acquisitions (Airbus EO, ICEYE SAR) déposent dans le Bucket S3 ; AIFA traite ; l'app sert Utilisateur et
  Systèmes IT. Apps partenaires à droite (Change Monitoring Airbus, Maritim Awareness KSAT).
- Vue Frontend : **Services applicatifs** (pas « Acquisitions ») pointe vers **Site Monitoring** (nos
  détections), sous-ensemble de l'Analytics Portal.

## Où est publié (3 cibles, toujours synchronisées)

- Source canonique : [`architecture_sinbad.html`](architecture_sinbad.html) (ce dossier).
- Artefact Claude (thème original) : <artefact Claude de la mission>
- Artefact Claude (Light) : <artefact Claude de la mission>
- GitHub Pages : <URL GitHub Pages de la mission>
  (repo `<repo gh-pages de la mission>`, branche `gh-pages`, chemin `architecture/index.html`).

À chaque modification : éditer la source canonique, `python3 validate.py architecture_sinbad.html`, puis
publier **les trois** (voir [`README.md`](README.md)) et recaler `reference/architecture_sinbad.golden.html`.

## Nav commune aux 3 pages gh-pages

Les trois pages publiées (rapport de projection, plan de sprints, architecture) partagent une **top-nav
commune** : un menu déroulant listant les 3 pages + un switch de thème (dark par défaut, light = adservio
pour l'archi), mémorisé dans `localStorage['sinbad-theme']` (même origine gh-pages). La source unique est
`scan-jira/projection/chrome.py` (`XNAV`, `XNAV_CSS`, `LIGHT_CSS`, `EARLY_THEME`, `CHROME_JS`) :
`build_report.py` et `build_plan.py` l'importent. La page **architecture** a ce chrome **inliné** (fichier
artisanal) : si `chrome.py` change, réinjecter les chaînes dans `architecture_sinbad.html`. Les liens de nav
sont en **URL absolue gh-pages** (pour fonctionner aussi depuis les artefacts Claude). Déploiement :
`sync_pages.sh` (rapport) et `sync_plan.sh` (plan) ; l'archi via ses 3 cibles habituelles.
