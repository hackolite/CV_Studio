# Méthodes de Suivi Ultra-Rapides pour le Tennis et les Sports

## Vue d'ensemble
Ce document décrit les deux nouvelles méthodes de suivi ultra-rapides ajoutées à CV_Studio, spécifiquement optimisées pour le tennis et les scénarios sportifs rapides : **OC-SORT** et **BoT-SORT**.

## Nouvelles Méthodes de Suivi

### 1. OC-SORT (SORT Centré sur l'Observation)

**Caractéristiques principales :**
- **Momentum centré sur l'observation** : Gère mieux les occlusions en utilisant l'historique des observations
- **Trajectoire virtuelle** : Prédit les positions des objets pendant les occlusions temporaires
- **Traitement rapide** : Optimisé pour le suivi en temps réel avec un minimum de calculs
- **Idéal pour le tennis** : Gère les balles et les joueurs en mouvement rapide avec des changements de direction rapides

**Détails techniques :**
- Basé sur l'article : "Observation-Centric SORT: Rethinking SORT for Robust Multi-Object Tracking" (2022)
- Utilise le filtrage de Kalman avec l'historique des observations pour une meilleure prédiction
- Le paramètre delta_t (défaut : 3) contrôle combien d'observations passées sont utilisées pour le calcul du momentum
- Un max_age plus élevé (défaut : 30) maintient les pistes actives plus longtemps pendant les occlusions

**Utilisation dans CV_Studio :**
Sélectionnez "OC-SORT" dans le menu déroulant des méthodes de suivi du nœud MultiObjectTracking.

**Paramètres :**
- `max_age` : Nombre maximum d'images pour garder une piste active sans détection (défaut : 30)
- `min_hits` : Minimum de détections avant de confirmer une piste (défaut : 3)
- `iou_threshold` : Seuil IoU pour la correspondance (défaut : 0.3)
- `delta_t` : Pas de temps pour le momentum centré sur l'observation (défaut : 3)

**Avantages pour le tennis :**
- Gère les changements de direction rapides (services, volées)
- Maintient le suivi pendant les occlusions brèves (passage du filet, chevauchement de joueurs)
- Faible latence pour le suivi en temps réel
- Robuste aux vitesses de balle rapides

### 2. BoT-SORT (Suivi Multi-Piétons à Associations Robustes)

**Caractéristiques principales :**
- **Correspondance GIoU** : Utilise l'IoU généralisé pour une meilleure association des boîtes non chevauchantes
- **Association en deux étapes** : Sépare les détections à haute et basse confiance
- **Lissage de la vélocité** : Utilise une vélocité lissée pour des prédictions stables
- **Suivi de confiance** : Maintient les scores de confiance des pistes au fil du temps

**Détails techniques :**
- Basé sur l'article : "BoT-SORT: Robust Associations Multi-Pedestrian Tracking" (2022)
- Implémente une correspondance en cascade à deux étapes pour une meilleure précision
- Utilise GIoU au lieu d'IoU pour une meilleure correspondance des boîtes non chevauchantes
- La dégradation de confiance pendant l'occlusion aide à gérer la qualité des pistes

**Utilisation dans CV_Studio :**
Sélectionnez "BoT-SORT" dans le menu déroulant des méthodes de suivi du nœud MultiObjectTracking.

**Paramètres :**
- `max_age` : Nombre maximum d'images pour garder une piste active sans détection (défaut : 30)
- `min_hits` : Minimum de détections avant de confirmer une piste (défaut : 3)
- `iou_threshold` : Seuil IoU pour la correspondance (défaut : 0.3)
- `use_giou` : Utiliser GIoU au lieu d'IoU (défaut : True)

**Avantages pour le tennis :**
- Gère mieux les joueurs à différentes positions sur le court (non chevauchants)
- La correspondance en deux étapes améliore la précision pour le suivi de la balle et des joueurs
- Les prédictions de vélocité lissées réduisent les tremblements
- Le filtrage basé sur la confiance réduit les faux positifs

## Comparaison des Performances

| Fonctionnalité | OC-SORT | BoT-SORT | SORT | ByteTrack |
|----------------|---------|----------|------|-----------|
| Vitesse | ⚡⚡⚡ Très rapide | ⚡⚡⚡ Très rapide | ⚡⚡⚡ Très rapide | ⚡⚡ Rapide |
| Gestion des occlusions | ⭐⭐⭐ Excellent | ⭐⭐⭐ Excellent | ⭐⭐ Bon | ⭐⭐⭐ Excellent |
| Objets non chevauchants | ⭐⭐ Bon | ⭐⭐⭐ Excellent | ⭐⭐ Bon | ⭐⭐ Bon |
| Mouvement rapide | ⭐⭐⭐ Excellent | ⭐⭐⭐ Excellent | ⭐⭐ Bon | ⭐⭐ Bon |
| Suivi de balle de tennis | ⭐⭐⭐ Excellent | ⭐⭐⭐ Excellent | ⭐⭐ Bon | ⭐⭐ Bon |
| Suivi de joueur | ⭐⭐⭐ Excellent | ⭐⭐⭐ Excellent | ⭐⭐ Bon | ⭐⭐⭐ Excellent |

## Quand Utiliser Chaque Tracker

### Utilisez OC-SORT quand :
- Vous suivez des objets en mouvement rapide (balles de tennis, volants)
- Les objets changent fréquemment de direction
- Les occlusions brèves sont courantes
- Vous avez besoin d'une latence minimale
- La mémoire des observations passées est importante

### Utilisez BoT-SORT quand :
- Vous suivez plusieurs joueurs/objets à des distances variées
- Les objets ne se chevauchent pas beaucoup
- Vous voulez une gestion de piste basée sur la confiance
- Besoin d'une association robuste avec des boîtes non chevauchantes
- Suivi d'objets petits (balle) et grands (joueurs) simultanément

## Détails d'Implémentation

Les deux trackers sont implémentés comme des wrappers multi-classes, ce qui signifie qu'ils peuvent suivre différentes classes d'objets simultanément (par exemple, balle, joueur 1, joueur 2).

**Structure des fichiers :**
```
node/TrackerNode/mot/
├── ocsort/
│   ├── __init__.py
│   ├── ocsort_tracker.py      # Algorithme OC-SORT de base
│   └── mc_ocsort.py            # Wrapper multi-classe
└── botsort/
    ├── __init__.py
    ├── botsort_tracker.py      # Algorithme BoT-SORT de base
    └── mc_botsort.py            # Wrapper multi-classe
```

## Intégration

Les trackers sont automatiquement disponibles dans le nœud MultiObjectTracking après l'implémentation. Aucune dépendance supplémentaire n'est requise au-delà du package `filterpy` existant.

Pour utiliser :
1. Ajoutez un nœud MultiObjectTracking à votre workflow
2. Connectez-le à un nœud ObjectDetection
3. Sélectionnez "OC-SORT" ou "BoT-SORT" dans le menu déroulant
4. Traitez votre vidéo

## Références

1. **OC-SORT** : Cao, J., et al. (2022). "Observation-Centric SORT: Rethinking SORT for Robust Multi-Object Tracking." arXiv:2203.14360
2. **BoT-SORT** : Aharon, N., et al. (2022). "BoT-SORT: Robust Associations Multi-Pedestrian Tracking." arXiv:2206.14651

## Licence

Les deux implémentations sont publiées sous licence MIT, conformément aux articles originaux et à la licence de CV_Studio.
