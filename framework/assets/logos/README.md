# Bibliothèque de logos techno (partagée)

Logos des **technologies communes** à la plupart des missions : on retrouve les mêmes briques d'un
projet à l'autre (cloud, orchestration, auth, observabilité, IaC, GitOps, front). Ils sont **partagés**
ici pour qu'un schéma d'architecture démarre avec les logos déjà disponibles, sur n'importe quelle mission.

**Les logos de marque** (Safran, partenaires d'une mission : Airbus, KSAT, ICEYE, NATO, Enix...) ne sont
**pas** ici : ils vivent dans `profiles/<mission>/logos/`, parce qu'ils sont propres à la mission.

## Disponibles

| Fichier | Techno |
|---|---|
| `aws.webp` | AWS |
| `kubernetes.webp` | Kubernetes |
| `keycloak.png` | Keycloak (auth / OIDC) |
| `prometheus.webp` | Prometheus (métriques) |
| `redis.svg` | Redis |
| `terraform.webp` | Terraform (IaC) |
| `argocd.png` | Argo CD (GitOps) |
| `fluxcd.png` | Flux CD (GitOps) |
| `react.webp` | React (front) |
| `shadcn.png` | shadcn/ui (front) |
| `user.webp` | icône utilisateur / compte (UI générique) |
| `map-pin.png` | repère de carte (UI générique) |

## Usage

Dans un `model.json` de schéma d'archi, une entité référence un logo par son nom. On réutilise d'abord
cette bibliothèque ; on n'ajoute un logo que s'il manque vraiment.

**À compléter au fil des missions** (manquants fréquents, à ajouter quand une mission les apporte) :
PostgreSQL, NATS, RabbitMQ, Grafana, Entra ID, Vault. Ne pas inventer un logo : l'ajouter quand on l'a.
