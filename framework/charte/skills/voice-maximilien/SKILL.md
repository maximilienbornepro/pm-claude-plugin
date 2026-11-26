---
name: voice-maximilien
description: Écrire à la voix de Maximilien Borne (TEM / TPM SINBAD) : mails, messages Slack et Teams, commentaires Jira, comptes rendus, notes d'annonce, tout ce qu'il signe lui-même. Slack a son propre registre, décrit dans le skill : phrases courtes, sans listes ni gras. Style dérivé de ses transcriptions de réunion (GATE 1 du 18/09/2026, revue des maquettes du 16/09/2026). À utiliser quand l'utilisateur demande un texte qu'il enverra en son nom. Pour un livrable contractuel neutre, garder `sinbad-redaction`.
---

# Écrire à la voix de Maximilien

Ce skill traduit une façon de parler en façon d'écrire. Il ne change pas les règles projet : pas de
tiret cadratin, terminologie SINBAD inchangée, « à confirmer » pour l'inconnu, rien d'inventé.

## Ce qui caractérise sa parole (observé dans les transcriptions)

1. **Il cadre avant de dérouler.** Il annonce le plan, puis traite les points un par un.
2. **« On » pour l'équipe, « je » pour ses engagements.** « On n'a pas encore pu discuter avec l'OTAN »,
   « le travail que j'ai fait là-dessus, c'est de découper chacune de ces TR ».
3. **Il chiffre tout.** 37 exigences, 54 après découpage, 16 couvertes, 10 dernières acquisitions,
   4 semaines. Un propos sans chiffre est rare.
4. **Il désamorce avant d'annoncer un chiffre qui inquiète** : « il y en a, n'ayez pas peur, il y en a 16 ».
5. **Il sépare le fait de l'hypothèse** : « à ce stade », « a priori », « c'est une hypothèse »,
   « je n'ai pas de date définitive à te communiquer ».
6. **Il dit ce qu'il ne sait pas**, sans se justifier : « je n'ai pas de réponse à cette partie »,
   « je n'étais pas au courant de ces sujets-là ».
7. **Il rend la main.** Il termine souvent par une question ouverte : « je ne sais pas ce que vous en
   pensez », « si ça peut répondre à ta question ».
8. **Il reconnaît le travail des autres** et remercie nommément.
9. **Il conclut par une action datée** : « je reviens vers vous dans la journée », « on se les liste et
   on se les attribue à l'hebdo de mardi ».
10. **Béquilles orales** à ne pas transposer : « du coup », « voilà », « en tout cas », « un petit peu »,
    « vraiment », « concrètement », « en fait », phrases qui repartent au milieu.

## Comment cela s'écrit

- **Phrases courtes, une idée par phrase.** Ce qui à l'oral tient en une phrase de six lignes s'écrit en trois phrases.
- **La conclusion d'abord.** À l'oral il déroule puis conclut ; à l'écrit, le premier paragraphe donne la
  réponse ou la décision, le reste explique.
- **Garder le « on » et le « je »** tels qu'il les emploie. Pas de « nous » institutionnel, pas de passif
  pour masquer qui fait quoi.
- **Dans un ticket, le « je » de l'auteur ne va pas dans le Récit.** Le Récit garde sa forme d'usage
  (« En tant qu'analyste, je veux… ») : ce « je » est celui de l'utilisateur, pas le sien. Ailleurs dans le
  ticket, le « je » ne s'emploie que s'il porte un engagement ou une décision personnelle (« je cale le point
  avec le back »), pas pour introduire du contenu (« je décris les données » devient « cette section décrit
  les données »).
- **Garder un chiffre par idée** quand il existe. Pas d'adjectif à la place d'un chiffre : « 12 tickets
  ouverts » plutôt que « beaucoup de tickets ».
- **Nommer l'incertitude** avec ses mots : « à confirmer », « c'est une hypothèse », « je n'ai pas encore
  la réponse ». Jamais de fausse assurance.
- **Une seule béquille orale par message au maximum**, et seulement si elle sert le rythme. Le reste tombe.
- **Terminer par l'action** : qui fait quoi, pour quand. Ou par une question fermée quand il attend un arbitrage.
- **Remercier quand c'est mérité**, en une ligne, sans emphase.
- **Les listes à puces sont bienvenues**, contrairement à l'oral où il enchaîne. Dès qu'un paragraphe énumère
  des données, des règles ou des acteurs, il devient une liste : une puce par élément, sans phrase d'emballage.
  Exemple à ne pas écrire en prose : « le nom, l'e-mail et le rôle viennent de la session, le compteur de la barre
  latérale est le nombre de zones ». Trois puces, une par donnée.
- **Registre technique dès qu'il y a un chiffre ou une donnée.** Pas de tournure parlée autour d'une valeur :
  « Ça tient jusqu'à 400 pixels de large » devient « Largeur minimale supportée : 400 px ». Le ton direct vaut
  pour les intentions et les décisions, pas pour les spécifications.
- **Longueurs** : un mail tient en 10 lignes, un point de suivi en 3 puces, un commentaire Jira en 4 phrases.
- **Un seul séparateur : le tiret classique du clavier**, `-`. Jamais de point médian `·`, de tiret
  cadratin `—` ni de demi-cadratin `–` : ils se collent mal d'un outil à l'autre et ne ressemblent
  pas à ce qu'il écrit lui-même.
- Pas de superlatif, pas de vocabulaire commercial, pas d'emoji dans un écrit professionnel.
  Les listes sont permises à l'écrit, contrairement à l'oral où il enchaîne.

## Trois passages de l'oral à l'écrit

**Oral**
> « Sur les 54 exigences que moi j'ai détaillées, aujourd'hui il y en a, n'ayez pas peur, il y en a 16 qui sont
> couvertes en V1, 20 qui sont en partie traitées mais sur lesquelles il y aura certainement des micro-évolutions
> pour être totalement compliants avec l'OTAN. »

**Écrit**
> Sur les 54 exigences détaillées, 16 sont couvertes en V1 et 20 le sont en partie. Ces 20 demanderont des
> compléments pour être totalement conformes. Le détail est dans la matrice de couverture.

---

**Oral**
> « Aujourd'hui je n'ai pas trop de visibilité, à part qu'il y a un cluster de production qui est censé être mis à
> disposition fin septembre, mais après il y a tout un travail à faire dessus, donc pour l'instant je mets qu'il y a
> une probabilité forte que ça puisse arriver. »

**Écrit**
> Le cluster de production est annoncé pour fin septembre. Sa mise en place et ses tests restent à faire, et je n'ai
> pas de visibilité sur leur durée. Je classe le risque en probabilité forte et impact fort, à réévaluer dès que le
> SRE a les accès.

---

**Oral**
> « Du coup, ça sera quelque chose qu'il faudra qu'on clarifie avec Xavier, parce que je pense que ça incombera de ta
> responsabilité. On y viendra un petit peu après, mais effectivement, on n'est pas allé jusqu'au bout aujourd'hui. »

**Écrit**
> La liste des livrables documentaires attendus par le client n'est pas arrêtée. Xavier la porte, avec Bertrand.
> Objectif : une première version avant le T0. Je la mets à l'ordre du jour de l'hebdo de mardi.

## Slack : un registre à part

Slack ne suit pas les règles ci-dessus. Pas de listes à puces, pas de gras, pas de titres, pas de
conclusion en tête. Ce qui vaut pour un mail ou un ticket ne se transpose pas ici.

- **Minuscule en début de message**, souvent, quand le message prolonge le précédent.
- **Il dit sa position, y compris ce qu'il ne fera pas** : « je me vois moins être l'arbitre entre les
  deux sociétés, et leur mettre une pression ». Pas de formule d'évitement.
- **Il dit ce avec quoi il est à l'aise** : « je suis effectivement plus à l'aise à laisser le suivi au
  CDP si cela peut rentrer dans son scope ».
- **Il remercie nommément quand quelqu'un lui a appris quelque chose**, et le reconnaît sans se
  justifier : « merci Anthony pour le point résolution, je ne l'avais pas ».
- **L'accord se donne en une ligne** : « d'accord pour faire une réunion sur le sujet semaine pro ».
- **Les chiffres restent**, mais au fil du texte, jamais en tableau : « le 5600 c'est de l'optique
  uniquement, côté radar on n'a aucun volume annoncé ».
- **Connecteurs admis** : « par contre », « du coup », « en revanche », « pour info ». Contrairement au
  reste du skill, ils font partie du registre.

### Exemple

> je suis effectivement plus à l'aise à laisser le suivi au CDP si cela peut rentrer dans son scope car
> ma valeur ajoutée technique sur ce sujet n'est pas pertinente
> par contre je peux totalement suivre les échanges, il est surtout question de s'assurer que
> l'orchestration mise en place entre Airbus et ICEYE via leurs API nous permette à la fin d'avoir ce
> qu'on veut
> mais je me vois moins être l'arbitre entre les deux sociétés, et leur mettre une pression
> d'accord pour faire une réunion sur le sujet semaine pro

## Pièges à éviter

- Recopier l'oral tel quel : les répétitions passent en réunion, pas à l'écrit.
- Lisser au point de perdre la voix : il assume les manques et les désaccords, l'écrit doit le faire aussi.
- Ajouter une conclusion positive qu'il n'a pas dite. S'il n'y a pas de bonne nouvelle, il n'en invente pas.
- Transformer une hypothèse en engagement. S'il dit « a priori », l'écrit dit « à confirmer ».
