# Documentation du Nœud DynamicPlay

## Aperçu

Le nœud **DynamicPlay** est un nœud vidéo interactif qui vous permet de :
- Afficher un flux vidéo maître (background) avec détection de la main
- Activer des flux vidéo en overlay (picture-in-picture) avec des gestes de pointage
- Déplacer et redimensionner l'overlay en utilisant des gestes de pincement avec le pouce et l'index

Ce nœud combine la vision par ordinateur (MediaPipe Hands) avec des contrôles interactifs pour créer une interface de lecteur vidéo sans les mains avec gestion d'overlay.

## Fonctionnalités

### Architecture Flux Maître + Overlay
- **Flux Maître** (Input01) : Flux vidéo de fond qui exécute toujours la détection de la main
- **Flux Overlay** (Input02-Input09) : Flux vidéo qui peuvent être activés en picture-in-picture
- Jusqu'à 8 flux overlay simultanés disponibles
- La disposition en grille s'ajuste automatiquement selon le nombre de flux

### Contrôles par Gestes de la Main

#### Activation d'Overlay
- Utilisez votre **geste de pointage avec l'index** pour activer un flux overlay
- Pointez sur le bouton numéroté superposé à l'écran
- Le flux overlay activé apparaît en picture-in-picture sur le flux maître
- Pointez à nouveau sur le même bouton pour désactiver l'overlay

#### Déplacement de l'Overlay (Drag)
- Utilisez le **pincement pouce et index** pour saisir l'overlay
- Maintenez le pincement et déplacez votre main pour déplacer l'overlay
- L'overlay suit la position de votre main en temps réel

#### Redimensionnement de l'Overlay
- Utilisez la **distance pouce-index** pour redimensionner l'overlay
- Doigts rapprochés = overlay plus petit (100px minimum)
- Doigts écartés = overlay plus grand (800px maximum)
- Le redimensionnement maintient le rapport d'aspect de l'overlay

## Interface du Nœud

### Entrées
- **Input01** : Flux maître (background) - Toujours visible avec détection de la main
- **Input02-Input09** : Flux overlay (ajoutez des slots selon besoin)
- Chaque entrée peut recevoir un flux vidéo ou une image statique

### Sorties
- **Output01** : Le flux maître avec overlay incrusté et contrôles visuels

### Contrôles
- **Bouton Add Slot** : Cliquez pour ajouter plus de slots d'overlay (jusqu'à 8 overlays)

## Exemple d'Utilisation

### Configuration de Base
1. Ajoutez le nœud DynamicPlay depuis le menu **Video**
2. Connectez un flux maître au slot Input01 (par exemple, une WebCam)
3. Connectez des flux overlay aux slots Input02, Input03, etc. (par exemple, des nœuds Video)
4. Le nœud affichera une grille de boutons numérotés sur le flux maître

### Contrôles par Gestes
1. **Activation d'un Overlay** :
   - Étendez votre index
   - Pointez sur le bouton numéroté correspondant au flux overlay que vous souhaitez activer
   - L'overlay apparaîtra en picture-in-picture sur le flux maître
   - Pointez à nouveau sur le même bouton pour le désactiver

2. **Déplacement de l'Overlay** :
   - Pincez avec le pouce et l'index (rapprochez-les à moins de 40 pixels)
   - Maintenez le pincement et déplacez votre main
   - L'overlay suit votre main en temps réel
   - Relâchez le pincement pour arrêter le déplacement

3. **Redimensionnement de l'Overlay** :
   - Tout en maintenant le pincement, variez la distance entre le pouce et l'index
   - Écartez les doigts pour agrandir l'overlay (jusqu'à 800px)
   - Rapprochez les doigts pour rétrécir l'overlay (minimum 100px)
   - Le rapport d'aspect est maintenu automatiquement

## Indicateurs Visuels

### Affichage à l'Écran
- **Info Overlay** : Affiche l'overlay actif et sa taille (ex : "Overlay: 2 | Size: 320x240")
- **Grille de Boutons** : Superposition de boutons numérotés (1-8)
  - Bordure verte : Overlay actuellement actif
  - Bordure blanche : Overlays disponibles
  - Bordure rouge : Bouton pointé
- **Bordure Cyan** : Bordure autour de l'overlay actif pour le rendre visible

### Visualisation de la Main
- **Cercles jaunes** : Bout du pouce et de l'index (points de suivi clés)
- **Cercles verts** : Autres points de repère de la main

## Détails Techniques

### Architecture
- **Slot 0 (Input01)** : Flux maître (toujours visible)
- **Slots 1-8 (Input02-09)** : Flux overlay (activables)
- Seul un overlay peut être actif à la fois

### Disposition de la Grille
La grille de boutons s'ajuste automatiquement selon le nombre de flux overlay :

| Overlays | Disposition |
|----------|-------------|
| 1        | 1x1         |
| 2        | 2x1         |
| 3-4      | 2x2         |
| 5-6      | 3x2         |
| 7-8      | 3x3         |

### Paramètres d'Overlay
- **Taille Minimum** : 100x100 pixels
- **Taille Maximum** : 800x800 pixels
- **Taille par Défaut** : 320x240 pixels
- **Distance de Pincement de Base** : 100 pixels (pour référence)
- **Seuil de Pincement** : 40 pixels (pour détecter le pincement)
- Le redimensionnement maintient le rapport d'aspect de la source

### Détection de la Main
- Utilise **MediaPipe Hands** (Complexité 0)
- Détecte jusqu'à 1 main
- Confiance minimale de détection : 0.7
- Confiance minimale de suivi : 0.5

## Prérequis

### Dépendances
- `mediapipe` : Pour l'estimation de la pose de la main
- `opencv-contrib-python` : Pour le traitement d'image
- `numpy` : Pour les opérations numériques
- `dearpygui` : Pour le rendu de l'interface

### Matériel
- Webcam ou dispositif d'entrée vidéo (pour la détection de la main)
- Éclairage suffisant pour le suivi de la main

## Considérations de Performance

- La détection de la main s'exécute sur chaque image du flux sélectionné
- Pour de meilleures performances :
  - Utilisez des flux d'entrée à résolution plus faible
  - Réduisez le nombre de flux simultanés
  - Assurez-vous de bonnes conditions d'éclairage pour le suivi de la main

## Dépannage

### Main Non Détectée
- **Vérifiez l'éclairage** : Assurez-vous d'un éclairage adéquat sur votre main
- **Vérifiez la caméra** : Assurez-vous que la main est visible dans le cadre de la caméra
- **Vérifiez la distance** : La main doit être à une distance raisonnable de la caméra (30cm-1m)

### Gestes Ne Répondent Pas
- **Pointez clairement** : Étendez complètement l'index pour pointer
- **Pincez clairement** : Faites un geste de pincement distinct avec le pouce et l'index
- **Évitez les mouvements rapides** : Gardez les mouvements de main fluides et constants

### Problèmes de Performance
- Réduisez la résolution du flux d'entrée
- Réduisez le nombre de flux d'entrée
- Fermez les autres applications gourmandes en ressources

## Exemple de Workflow

```
[WebCam]    → [Input01 - Flux Maître]
[Video1]    → [Input02]   
[Video2]    → [Input03]    → [DynamicPlay] → [Output] → [Display/VideoWriter]
[Video3]    → [Input04]    
```

Cette configuration vous permet de :
1. Voir en permanence le flux de la webcam (avec détection de la main)
2. Activer des vidéos en overlay avec des gestes de pointage
3. Déplacer et redimensionner l'overlay avec des gestes de pincement
4. Enregistrer la sortie composite (maître + overlay)

## Limitations

- Maximum 1 flux maître + 8 flux overlay
- Un seul overlay actif à la fois
- Suivi d'une seule main
- Taille d'overlay limitée à 100-800 pixels
- Nécessite l'installation de MediaPipe

## Améliorations Futures

Les améliorations potentielles pourraient inclure :
- Support de plusieurs overlays simultanés
- Gestes personnalisés pour différentes actions
- Mode picture-in-picture multiple
- Rotation de l'overlay basée sur les gestes
- Transparence d'overlay ajustable
- Zoom dans l'overlay lui-même

## Licence

Ce nœud fait partie du projet CV_Studio et suit les mêmes termes de licence.
