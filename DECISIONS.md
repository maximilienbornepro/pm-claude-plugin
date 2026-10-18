# Journal de décisions - pm-framework

Les décisions de conception du framework, **numérotées** (`DM-xxx`). On **cite `DM-xxx`** dans les
messages de commit et les commentaires de code quand une ligne existe à cause d'une décision : la trace
du *pourquoi* évite de défaire plus tard ce qui était un choix.

Règles du journal : on **ajoute en bas**, on ne réécrit pas ; une décision périmée est marquée
« révisée par DM-yyy », pas supprimée. Les premières entrées sont **documentées rétroactivement**
(18/10/2026) à partir de l'état du code ; les suivantes sont datées du jour où elles ont été prises.

---

## DM-001 - Une mission = un profil ; le moteur est générique  *(rétro)*
Les données d'une mission vivent dans `profiles/<mission>/` (dans le projet de l'utilisateur) ; le moteur
(`framework/`) n'embarque aucune donnée de mission. **Pourquoi :** un dispositif générique qui embarquerait
les décisions d'un projet réel n'est plus clonable. Le profil réel (ex. `profiles/sinbad`) est **exclu de
la publication** (`publish.sh` + `.gitignore`).

## DM-002 - Garde-fous en hooks, jamais dans la logique métier  *(rétro)*
Les règles de sûreté sont des hooks (`garde_office` : refuse une écriture Office brute ; `garde_suppression` :
refuse suppression/déplacement d'un fichier synchronisé ou d'une page Notion ; `pas_ecraser_jira` :
anti-écrasement d'une description Jira). **Pourquoi :** un garde-fou dans le code d'un générateur se contourne
en changeant de chemin ; un hook s'applique quel que soit l'appelant.

## DM-003 - Générateurs = livrables, lecture seule par défaut, écriture GARDÉE  *(rétro)*
Un générateur **produit du contenu** et n'écrit rien ; l'écriture se fait en session, après avoir montré le
contenu (ou un `--dry-run`) et reçu le oui. Le registre `GEN` (pm.py) porte le drapeau « lecture seule ».

## DM-004 - Multi-compte : registre au niveau POSTE, routage au niveau MISSION  *(rétro)*
Les comptes (chemins des config dirs Claude) vivent dans `~/.pm-accounts.yml` / `config/accounts.yml`
(gitignore) ; le routage par commande dans `profiles/<mission>/routing.yml`. Une délégation (`pm run agent`)
retire l'auth hôte injectée par l'app desktop pour vraiment basculer de compte. (Voir aussi DM-010.)

## DM-010 - Routage de compte DÉRIVÉ des métadonnées (A1)  *(17/10/2026)*
Le compte d'une commande se **dérive** de son bloc `meta` (`cost`, `mcp_deps`) selon
`orchestration.routing_policy` du profil ; `routing.yml` ne garde que les **exceptions**. **Pourquoi :**
31 lignes de routage à la main → oublis et incohérences (un générateur facturé au mauvais compte). Deux
politiques selon la topologie : `by-connector` (comptes différenciés par connecteur) et `by-cost` (tous les
comptes ont tous les connecteurs, ex. SINBAD : le coût tranche). Code : `generator_meta.derive_account`,
`profile.account_for` (exception explicite → dérivé → défaut). Déployé sur SINBAD le 17/10 (31 entrées → 6).

## DM-011 - by-cost envoie aussi le PUREMENT LOCAL sur perso  *(17/10/2026)*
Révélé par le dry-run SINBAD : `reset` (léger, sans connecteur) ne doit pas partir sur safran. `by-cost`
→ perso si `cost: heavy-local` **OU** aucun `mcp_deps` ; safran seulement pour le léger qui touche un
connecteur. (Affine DM-010.)

## DM-012 - Plugin auto-vérifiant : lint + tests gardent la publication (A3)  *(17/10/2026)*
`framework/harness/verifier.py` (GEN↔scripts, alias valides, meta bien formées, routing→commandes réelles)
et `framework/harness/test_a1.py` tournent **dans `publish.sh`** : refus de publier si rouge. **Pourquoi :**
fin des « skills en double / dérive » découverts trop tard.

## DM-013 - Déroulé d'écriture Office factorisé (A2)  *(17/10/2026)*
`framework/generators/_deroule-office.md` écrit la procédure d'écriture Office **une seule fois** ;
`deck-gate`/`risks`/`raci` y pointent (meta `writes: office`) au lieu de la dupliquer. Le lint **refuse** un
`writes: office` qui ne renvoie pas au déroulé (anti-dérive). **Pourquoi :** corriger un garde-fou d'écriture
à un seul endroit.

## DM-014 - notion-planning est un générateur SKILL-only  *(18/10/2026)*
`notion-planning` est du **pur connecteur** (construire un Gantt Notion), sans script `pm run` : il n'a pas
d'entrée `GEN`. Déclaré `exec: skill` dans sa meta ; le lint exempte les skill-only de l'avertissement
d'orphelin tout en validant leur meta.

## DM-015 - Trace d'usage par hook (A7)  *(18/10/2026)*
`framework/hooks/journal_usage.py` (PreToolUse sur `Skill|Agent|Task`) journalise chaque invocation de skill
et d'agent dans `<projet>/.claude/usage.log` (JSON par ligne), sans jamais bloquer. **Pourquoi :** savoir plus
tard ce qui n'est plus utilisé. Les runs de générateurs via `pm run` sont le plus souvent déclenchés par un
skill/une routine, donc déjà couverts.

## DM-016 - Les portes (gates) sont une DONNÉE ; le script compte, il ne valide pas (A6)  *(18/10/2026)*
Générateur `gate` : les portes d'une mission vivent dans `profiles/<mission>/gate.yml` sous `gates:` (une liste
- le standard GTF = 7 portes, Gate 0 à Gate 6 ; gabarit `gtf.sample.yml`). Chaque porte porte ses critères
(0 / 0,5 / 1), son seuil, l'`acte_humain` de franchissement et des `waivers` datés. `gate.py` **compte et
recommande**, il n'écrit rien. Doctrine, en dur dans `evaluate()` :
- **aucun franchissement automatique** : seuil atteint ≠ franchie ; il faut un `acte_humain` (approbateur, date,
  motif) tracé dans `gate.yml` ;
- **un bloquant (critère à 0) se lève par un waiver à 8 champs dont une `echeance`** ; un waiver **expiré
  redevient un bloquant** (fail-closed), un waiver **incomplet ne lève rien** ;
- **un bloquant valablement waivé sort du score** (son risque est suivi par `surveillance`/`remediation`, pas
  porté par la moyenne) et le verdict devient **WAIVÉ** - « waivé n'est pas recommandé », le verdict change de
  nom, pas de nature ;
- un critère **sans score est « non évalué »** (exclu du calcul, ≠ 0) ; une porte sans aucun score est « non entamée ».
**Parseur :** `gate.yml` est imbriqué (gates → criteria/waivers), au-delà de ce que `profile._mini_parse` sait
lire ; nouveau `framework/lib/yamlmin.py` (sous-ensemble YAML, 0 dépendance, blocs + maps/listes en ligne), **sans
toucher** à `profile.py` (risque pour les profils). Tests : `framework/harness/test_gate.py` (10 cas), ajoutés à
`publish.sh`.

## DM-017 - La méthode est une DONNÉE : `method.yaml` par mission (A4)  *(18/10/2026)*
« Ce qui se calcule ne se raconte pas. » Ce qui relève de la méthode et se calcule - barèmes de cotation,
seuils-pivots, trames de livrables, chaîne de traçabilité - vit dans `profiles/<mission>/method.yaml`, pas dans
la prose d'un skill ni en dur dans un script. Lecteur commun `framework/lib/method.py` (`seuil`/`bareme`/`trame`/
`section`, fail-soft : section absente → défaut, rien ne casse). Générateur `method` : montre la méthode en
clair et signale ce qui reste en prose. **Migration incrémentale**, livrable par livrable (pas de big-bang) :
premier consommateur câblé, `gate` lit `seuils.gate_defaut` au lieu du 90 en dur. **Pourquoi :** des résultats
reproductibles et **opposables** (COPIL, OTAN), pas « calculés par un modèle ». `method.yaml` porte le
**transverse** ; les configs spécifiques d'un générateur (`risks.yml`, `gate.yml`) restent à elles. Tests :
`framework/harness/test_method.py` (7 cas), ajoutés à `publish.sh`. Prépare A5 (bloc `tracabilite`).

## DM-018 - Chaîne de traçabilité en donnée + audit de ruptures (A5)  *(18/10/2026)*
La chaîne besoin/TR → ticket → POC → test est déclarée **une fois**, en donnée : `method.yaml` > `tracabilite`
porte la **définition** (`phases`, `ordre` des maillons, `proprietaire` et `exigible_des` de chacun, `facultatif`
optionnel) ; `profiles/<mission>/tracabilite.yml` porte les **items** (`phase_courante`, et par besoin les `liens`
reliés). Générateur **lecture seule** `trace-audit` : à la phase courante, un maillon **exigible** (`exigible_des`
≤ phase), **non facultatif** et **non relié** est une **rupture** ; il calcule les ruptures et dit **où aller**
(propriétaire du premier maillon manquant). **Pourquoi :** unifier ce que disent la matrice IADT et le périmètre,
et détecter les trous tôt, sans qu'un modèle « décide » - il mesure sur une chaîne déclarée. En mission réelle,
`tracabilite.yml` est **produit par la synchro** (matrice + `perimetre_scope.json` + Jira), l'audit reste le même.
Dépend de A4 (lit `method.section(..., "tracabilite")`). Tests : `framework/harness/test_trace.py` (8 cas),
ajoutés à `publish.sh`.
