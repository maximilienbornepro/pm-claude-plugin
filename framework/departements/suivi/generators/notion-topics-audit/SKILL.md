---
name: notion-sujets
description: Cree / met a jour des sujets dans la base Sujets (Notion), au format Contexte / Action attendue, a la voix du profil. Ecriture via le connecteur, sous garde-fous Notion, RIEN sans validation. check_sujet.py valide le format avant d'ecrire.
meta:
  produces: null
  consumes: [notion]
  mcp_deps: [notion]
  cost: light
  status: stable
---

Gere les **sujets de suivi** (base Sujets Notion) : format **Contexte / Action attendue**, voix du profil
(`notion_sujets.yml > tone` = `voice-maximilien`). L'ecriture passe par le **connecteur** (pilote par
Claude) ; **rien n'est ecrit sans validation**.

## Deroule

1. **Perimetre** : ne traiter que les sujets `filter.field = filter.keep` (ici `Suivi projet = TPM`) ;
   jamais un sujet porte par le CDP (sa version fait foi).
2. **Rediger** le corps au format impose : **Contexte** (factuel, sans redire les colonnes statut/priorite/
   responsable), puis **Action attendue** rangee **par theme** (gras + sous-puces, **un seul niveau**).
3. **Valider le format** avec `check_sujet.py` (lecture seule) AVANT d'ecrire : sections presentes et dans
   l'ordre, pas de liste a plat de 3+ puces, pas de prose au-dela du seuil, pas de vraie mention `@`.
4. **Montrer** le contenu exact et **attendre le oui**. Ecriture **chirurgicale** (`notion-update-page`,
   `update_content` old/new ; jamais `replace_content`). Mentions en **texte simple**.
5. Relire (`notion-fetch`) : rendu correct, aucune sous-page/base perdue.

## Usage du validateur

```bash
python3 check_sujet.py --body sujet.md [--mission sinbad]   # exit 1 + liste des defauts si KO
```

Config : `profiles/<mission>/notion_sujets.yml` (data source, filtre TPM, ton, seuils de structure).

## Garde-fous

- **Rien sans validation** ; ecriture via connecteur uniquement, jamais de deplacement de page
  (hook `garde_suppression.py`), aucune mention `@`, **aucune notification**.
- **Ne rien inventer** (`à confirmer` pour l'inconnu). Les modifs manuelles de l'utilisateur sont
  prioritaires. Pour condenser l'existant : routine `revue-sujets`, mode `condensation`.
