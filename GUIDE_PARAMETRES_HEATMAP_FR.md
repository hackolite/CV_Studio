# Guide d'Utilisation des Nouveaux Paramètres de Heatmap

## Vue d'ensemble

Cette amélioration ajoute des contrôles configurables pour personnaliser l'apparence des heatmaps dans CV Studio. Les utilisateurs peuvent maintenant ajuster en temps réel les paramètres de visualisation via des sliders et des menus déroulants.

## Nouveaux Paramètres Disponibles

### 1. Curseur "Blur" (Flou)
**Plage**: 1 à 99  
**Valeur par défaut**: 25

**Effet**: Contrôle la taille du noyau de flou gaussien pour lisser la heatmap.
- **Valeurs basses** (1-15): Heatmap nette avec des bordures bien définies
- **Valeurs moyennes** (15-35): Lissage équilibré
- **Valeurs hautes** (35-99): Aspect très lisse et diffus

**Exemple d'utilisation**:
- Pour détecter des zones précises → Utiliser blur = 5-10
- Pour une visualisation générale → Utiliser blur = 25-35
- Pour des tendances larges → Utiliser blur = 50-99

### 2. Menu "Colormap" (Palette de Couleurs)
**Options**: JET, HOT, COOL, RAINBOW, VIRIDIS, TURBO  
**Valeur par défaut**: JET

**Description des palettes**:
- **JET**: Bleu → Cyan → Jaune → Rouge (palette thermique classique)
- **HOT**: Noir → Rouge → Jaune → Blanc (basée sur la chaleur)
- **COOL**: Cyan → Magenta (tons froids)
- **RAINBOW**: Spectre complet arc-en-ciel
- **VIRIDIS**: Palette uniforme perceptuellement (scientifique)
- **TURBO**: Arc-en-ciel amélioré avec meilleure uniformité

**Recommandations**:
- **Visualisation générale**: JET ou TURBO
- **Analyse scientifique**: VIRIDIS (meilleure pour daltoniens)
- **Présentation**: RAINBOW ou HOT

### 3. Curseur "Blend Alpha" (Transparence)
**Plage**: 0.0 à 1.0  
**Valeur par défaut**: 0.6

**Effet**: Contrôle la transparence de la heatmap superposée sur l'image originale.
- **0.0**: Image originale uniquement (pas de heatmap visible)
- **0.3**: Overlay subtil, image originale dominante
- **0.6**: Mélange équilibré (recommandé)
- **1.0**: Heatmap uniquement (pas d'image originale)

**Cas d'usage**:
- **Analyse de mouvement**: 0.7-1.0 (heatmap dominante)
- **Contexte + détection**: 0.4-0.6 (équilibré)
- **Annotation légère**: 0.2-0.3 (subtil)

### 4. Curseur "Memory" (Mémoire)
**Plage**: 0.80 à 0.995  
**Valeur par défaut**: 0.98

**Effet**: Contrôle la durée de persistance des valeurs de heatmap (taux de décroissance).
- **Valeurs hautes** (0.99+): Persistance longue, idéal pour tracker des mouvements dans le temps
- **Valeurs basses** (0.80-0.90): Décroissance rapide, mieux pour l'état en temps réel

## Comment Utiliser

### Dans l'Interface CV Studio

1. **Ajouter un nœud Heatmap ou ObjHeatmap** à votre flux de travail
2. **Connecter** les sources d'image et de détection
3. **Ajuster les paramètres** en temps réel avec les contrôles:
   - Déplacer le curseur **Blur** pour modifier le lissage
   - Sélectionner une **Colormap** dans le menu déroulant
   - Ajuster **Blend Alpha** pour la transparence
   - Modifier **Memory** pour la persistance

4. **Observer les changements** immédiatement dans la sortie

### Exemples de Configuration

#### Configuration pour Analyse de Zones Chaudes
```
Blur: 35-51
Colormap: TURBO ou VIRIDIS
Blend Alpha: 0.8
Memory: 0.98
```
Idéal pour: Analyse de zones d'intérêt, cartes de chaleur d'activité

#### Configuration pour Détection Précise
```
Blur: 5-15
Colormap: JET
Blend Alpha: 0.5
Memory: 0.90
```
Idéal pour: Suivi d'objets, détection en temps réel

#### Configuration pour Présentation
```
Blur: 25
Colormap: RAINBOW ou HOT
Blend Alpha: 0.6
Memory: 0.95
```
Idéal pour: Démonstrations, visualisations grand public

## Compatibilité

- **Rétrocompatible**: Les configurations existantes fonctionnent avec les valeurs par défaut
- **Sauvegarde**: Tous les paramètres sont sauvegardés dans les fichiers de configuration
- **Performance**: Aucun impact sur les performances, les calculs restent optimisés

## Conseils d'Optimisation

1. **Pour des vidéos en temps réel**: Utiliser blur ≤ 25 pour maintenir la performance
2. **Pour l'analyse**: Expérimenter avec différentes colormaps pour identifier celle qui révèle le mieux les patterns
3. **Pour le debugging**: Commencer avec blend_alpha = 0.5 pour voir à la fois l'image et la heatmap

## Support Technique

Pour des questions ou des problèmes:
- Consulter la documentation technique: `HEATMAP_PARAMETERS_ENHANCEMENT.md`
- Exécuter les tests: `python tests/test_heatmap_parameters.py`

---

**Note**: Cette amélioration répond à la demande "rajoute sous forme de slide ou autre la capacité de changer les paramètres de la fonction qui défini la heatmap, mémoire, etc ..."
