# Cartographie des notifications - generateur `scaffold`

Regle : le scaffold ne doit **jamais** declencher un mail. Avant toute ecriture, cette carte liste,
par cible, ce qui **notifie** (interdit) et ce qui **ne notifie pas** (autorise en creer-si-absent).

## Drive (SharePoint / OneDrive consortium)

| Action | Notifie ? | Verdict |
|---|---|---|
| Creer un dossier vide absent (via synchro locale) | non | ✅ autorise, creer-si-absent |
| Supprimer / deplacer / renommer un dossier synchronise | - | ❌ jamais (regle consortium + casse la synchro) |
| Partager / inviter sur un dossier | **oui** | ❌ jamais |

- Le connecteur M365 est **lecture seule** (Files.Read / Sites.Read) : il ne peut pas creer de dossier.
  Toute creation passe donc par un `mkdir` local d'un dossier **absent**, qui remonte par la synchro.
- Pour SINBAD : les 18 dossiers de Project Management existent deja -> le scaffold ne cree **rien**.

## Notion

| Action | Notifie ? | Verdict |
|---|---|---|
| Creer une page **privee (draft)** : `notion-create-pages` + `creation_mode:"draft"` | **non** (page workspace-level, `ancestor-path` vide, aucun abonne) | ✅ **PROUVE 09/10** : zero notification. Voie sure pour fabriquer une page avant placement. |
| Creer une page sous une page existante de Project Management | pas de mail ; **residuel** : un abonne de la page parent peut voir une notif in-app « nouvelle sous-page » | ✅ creer-si-absent, mais le residuel existe -> preferer : creer en draft prive, puis placer en connaissance de cause |
| Deplacer une page vers un autre conteneur ou la racine | **oui** (droits explicites recrees -> « Vous avez ete invite(e) dans... », cause des 31 mails du 23/09/2026) | ❌ jamais |
| @mention d'une personne | **oui** | ❌ jamais ; noms en texte simple |
| Commentaire | **oui** | ❌ jamais |
| Partage / invitation | **oui** | ❌ jamais |
| Attribution d'une tache a une personne | **oui** | ❌ jamais |
| Supprimer une page | non | on ne le fait pas ; on **propose** la suppression, Maximilien la fait dans Notion |

## Protocole de securite (tout generateur qui ecrit dehors)

1. `--dry-run` par defaut : montre ce qui serait cree, ne cree rien.
2. Creer-si-absent uniquement : on compare l'existant, on ne recree ni ne remplace jamais.
3. Aucune action de la colonne « notifie » n'est emise.
4. Premiere vraie ecriture : sur une **cible jetable**, validee avec Maximilien, avant toute campagne.
5. Jamais de deplacement de page Notion ; jamais de delete/move/rename Drive.
