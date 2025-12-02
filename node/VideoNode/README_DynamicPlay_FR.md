# Documentation du Nœud DynamicPlay

## Aperçu

Le nœud **DynamicPlay** est un nœud vidéo interactif qui vous permet de :
- Afficher plusieurs flux vidéo/image
- Basculer entre les flux en utilisant des gestes de pointage de la main
- Zoomer/dézoomer en utilisant des gestes de pincement avec le pouce et l'index

Ce nœud combine la vision par ordinateur (MediaPipe Hands) avec des contrôles interactifs pour créer une interface de lecteur vidéo sans les mains.

## Fonctionnalités

### Flux d'Entrée Multiples
- Supporte jusqu'à 9 flux vidéo/image simultanés
- Ajout dynamique de slots (comme le nœud ImageConcat)
- La disposition en grille s'ajuste automatiquement selon le nombre de flux

### Contrôles par Gestes de la Main

#### Sélection de Flux
- Utilisez votre **geste de pointage avec l'index** pour sélectionner un flux
- Pointez sur le bouton numéroté superposé à l'écran
- Le flux sélectionné est surligné en vert
- Les autres flux sont affichés avec des bordures blanches

#### Pincement pour Zoomer
- Utilisez le **pincement pouce et index** pour zoomer
- Doigts rapprochés = moins de zoom (1x)
- Doigts écartés = plus de zoom (jusqu'à 3x)
- Le centre du zoom suit la position de votre index

## Interface du Nœud

### Entrées
- **Input01-Input09** : Entrées d'images BGR multiples (ajoutez des slots selon besoin)
- Chaque entrée peut recevoir un flux vidéo ou une image statique

### Sorties
- **Output01** : Le flux vidéo actuellement sélectionné et zoomé avec superposition

### Contrôles
- **Bouton Add Slot** : Cliquez pour ajouter plus de slots d'entrée (jusqu'à 9)

## Exemple d'Utilisation

### Configuration de Base
1. Ajoutez le nœud DynamicPlay depuis le menu **Video**
2. Connectez des sources vidéo aux slots d'entrée
   - Exemple : Connectez des nœuds WebCam, Video, ou tout nœud produisant des images
3. Le nœud affichera une grille de boutons numérotés de 1 à 9

### Contrôles par Gestes
1. **Sélection d'un Flux** :
   - Étendez votre index
   - Pointez sur le bouton numéroté correspondant au flux que vous souhaitez voir
   - Le flux sélectionné sera affiché en plein écran avec les contrôles de zoom

2. **Zoom** :
   - Faites un geste de pincement avec le pouce et l'index
   - Ajustez la distance entre vos doigts :
     - Rapprochés : Zoom arrière (1x)
     - Écartés : Zoom avant (jusqu'à 3x)
   - Déplacez votre index pour changer le centre du zoom

## Indicateurs Visuels

### Affichage à l'Écran
- **Numéro de Flux** : Affiche le flux actuel (ex : "Stream: 1/4")
- **Niveau de Zoom** : Affiche le facteur de zoom actuel (ex : "Zoom: 2.5x")
- **Grille de Boutons** : Superposition de boutons numérotés (1-9)
  - Bordure verte : Flux actuellement sélectionné
  - Bordure blanche : Flux disponibles
  - Bordure rouge : Bouton pointé

### Visualisation de la Main
- **Cercles jaunes** : Bout du pouce et de l'index (points de suivi clés)
- **Cercles verts** : Autres points de repère de la main

## Détails Techniques

### Disposition de la Grille
La grille de boutons s'ajuste automatiquement selon le nombre de flux d'entrée :

| Flux | Disposition |
|------|-------------|
| 1    | 1x1         |
| 2    | 2x1         |
| 3-4  | 2x2         |
| 5-6  | 3x2         |
| 7-9  | 3x3         |

### Paramètres de Zoom
- **Zoom Minimum** : 1.0x (pas de zoom)
- **Zoom Maximum** : 3.0x
- **Distance de Pincement de Base** : 100 pixels (pour zoom 1x)
- Le zoom est proportionnel à la distance de pincement

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
[WebCam] → [DynamicPlay]
[Video1] → [Input01]   
[Video2] → [Input02]    → [Output] → [Display/VideoWriter]
[Video3] → [Input03]    
```

Cette configuration vous permet de :
1. Sélectionner entre la webcam et plusieurs sources vidéo
2. Zoomer dans des zones d'intérêt spécifiques
3. Enregistrer la sortie sélectionnée et zoomée

## Limitations

- Maximum 9 flux d'entrée
- Suivi d'une seule main
- Plage de zoom limitée à 1x-3x
- Nécessite l'installation de MediaPipe

## Améliorations Futures

Les améliorations potentielles pourraient inclure :
- Support de gestes multi-mains
- Mappage de gestes personnalisés
- Limites de zoom ajustables
- Mode picture-in-picture
- Rotation basée sur les gestes
- Zoom à deux mains (comme le pincement sur écran tactile)

## Licence

Ce nœud fait partie du projet CV_Studio et suit les mêmes termes de licence.
