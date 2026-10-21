---
name: publication-projection
description: Routine - publie les pages d'avancement (gh-pages) puis republie le meme HTML sur les artefacts Claude, aligne les objectifs des sprints du tracker sur le JSON editorial, et signale explicitement tout texte de sprint perime. Lecture Jira pour construire ; ecritures gh-pages, artefacts et objectifs de sprint uniquement. Aucune notification.
schedule: config   # voir routines.yml > routines.<mission>-publish-projection.schedule
---

**Publier, aligner les objectifs, signaler la derive.** Les pages d'avancement melangent deux sources :
les chiffres et les listes de tickets suivent le tracker a chaque generation ; le **texte des sprints**
(objectif, « ce que l'utilisateur peut faire », « non disponible », texte par pole) est editorial, tenu a
la main dans les JSON de mission (`routines.yml > ...reads.editorial`). Ce texte ne se met jamais a jour
seul : la routine doit donc **dire** quand il ne colle plus au tracker. Reponds dans la langue du profil.

## Deroule

1. **Publier** : lance `commands.publish` (depuis la racine projet). **Garde** : push uniquement s'il y a
   une evolution ; le jeton du tracker n'apparait jamais dans les pages.
2. **Artefacts (regle gh-pages + artefact)** : pour chaque entree de `artifacts` (`url`, `ghpages_path`),
   recupere le HTML publie (`git show origin/gh-pages:<ghpages_path>` dans le checkout `ghpages_repo`) et
   publie-le tel quel sur son `url`. Jamais une page sans son artefact. Si « aucune evolution », rien a
   republier pour cette page.
3. **Objectifs des sprints** (si `commands.objectifs` est defini) : lance-le. Il n'ecrit que le champ
   objectif des sprints qui different du JSON ; aucun ticket touche, aucune notification. Rapporte les
   sprints realignes.
4. **Controle de derive** (si `commands.drift_check` est defini, lecture seule) : lance-le et lis ses
   sections « Objectifs des sprints » et « Narratif du plan a revoir ». S'il signale un ticket qui a change
   de sprint, un objectif different, ou un sprint sans texte, **alerte explicitement** :
   « ⚠ texte du sprint N perime : <tickets deplaces> », sprint par sprint, avec une proposition de phrase.
   **Ne reecris jamais le texte toi-meme** dans cette routine : c'est editorial, l'utilisateur valide.
   Si le controle plante, le dire (jamais en silence) et continuer.

## Alertes a relayer (jamais en silence)

- **Reliquat de fin de sprint** : quand la generation imprime `⚠ reliquat de fin de sprint`, le relayer
  (dashboard uniquement, aucune ecriture dans le tracker).
- **Texte de sprint perime** : etape 4.
- Toute autre entree de `routines.yml > ...alerts`.

## Garde-fous

- `notifies: none`. Artefacts prives ; l'objectif de sprint est un champ texte qui ne notifie personne.
- **Aucun ticket deplace ni modifie** par cette routine. Pas de tracker (autre routine), pas d'Office.
- Respecte chaque `routines.yml > ...writes[].guard`.

## Regle associee (hors routine)

Quiconque deplace des tickets entre sprints (Claude compris, en session) reecrit dans le **meme passage**
le texte des sprints concernes (JSON editoriaux), lance `commands.objectifs`, puis republie. La routine
n'est que le filet de securite.
