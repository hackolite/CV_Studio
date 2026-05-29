# CV Studio — Guide Utilisateur : Création de Workflows

## Table des matières

1. [Introduction](#introduction)
2. [Démarrage de l'application](#démarrage-de-lapplication)
3. [Interface de l'éditeur de nœuds](#interface-de-léditeur-de-nœuds)
4. [Créer un workflow](#créer-un-workflow)
5. [Catalogue des nœuds](#catalogue-des-nœuds)
6. [Connexions et types de données](#connexions-et-types-de-données)
7. [Sauvegarder et charger un workflow](#sauvegarder-et-charger-un-workflow)
8. [Configuration](#configuration)
9. [Exemples de workflows](#exemples-de-workflows)

---

## Introduction

**CV Studio** est un environnement de programmation visuelle (node-based) dédié à la vision par ordinateur, au traitement audio et à l'intelligence artificielle. Il permet de construire des pipelines de traitement en temps réel en connectant des nœuds graphiques entre eux, sans écrire de code.

L'application repose sur **DearPyGui** pour l'interface graphique et **OpenCV** / **ONNX Runtime** pour le traitement.

---

## Démarrage de l'application

### Lancement standard

```bash
python main.py
```

### Options de lancement

| Option | Description |
|--------|-------------|
| `--setting chemin/config.json` | Utiliser un fichier de configuration personnalisé |
| `--unuse_async_draw` | Mode synchrone (debug) |
| `--use_debug_print` | Activer les messages de débogage |

### Exemple

```bash
python main.py --setting node_editor/setting/setting.json --use_debug_print
```

Au lancement, un **splash screen** s'affiche pendant le chargement des modules, puis l'éditeur de nœuds apparaît en plein écran.

---

## Interface de l'éditeur de nœuds

### Disposition générale

L'interface se compose de :

- **Barre de menu** (en haut) : Menus File, Input, VisionProcess, VisionModel, etc.
- **Canvas** (zone principale) : Espace de travail où l'on place et connecte les nœuds
- **Minimap** (coin inférieur droit) : Vue miniature de l'ensemble du graphe

### Contrôles souris

| Action | Effet |
|--------|-------|
| **Clic gauche** | Sélectionner un nœud ou un lien |
| **Glisser un nœud** | Déplacer le nœud sur le canvas |
| **Clic droit + glisser** | Panoramique du canvas |
| **Molette** | Zoom avant/arrière (10% – 500%) |
| **Glisser depuis un port de sortie** | Créer une connexion vers un port d'entrée |

### Contrôles clavier

| Touche | Effet |
|--------|-------|
| **Suppr / Delete** | Supprimer le nœud ou le lien sélectionné |

### Sélection visuelle

Lorsqu'un nœud est sélectionné, sa couleur de titre est automatiquement intensifiée (+15% saturation, +20% luminosité) pour le distinguer visuellement.

---

## Créer un workflow

### Étape 1 : Ajouter des nœuds

1. Cliquez sur un **menu de catégorie** dans la barre de menu (ex. : *Input*, *VisionProcess*, *VisionModel*…)
2. Sélectionnez le nœud souhaité dans le sous-menu
3. Le nœud apparaît sur le canvas à la dernière position cliquée (décalé de +30px à chaque ajout)

### Étape 2 : Connecter les nœuds

1. Identifiez le **port de sortie** (côté droit du nœud source) — marqué par un cercle coloré
2. **Glissez** depuis ce port vers le **port d'entrée** (côté gauche du nœud destination)
3. La connexion est établie si les types sont compatibles

> ⚠️ Un port d'entrée ne peut recevoir qu'une seule connexion à la fois.

### Étape 3 : Configurer les paramètres

Chaque nœud possède des contrôles internes :
- **Sliders** : Ajuster des valeurs numériques (seuils, tailles…)
- **Combo-box** : Sélectionner un modèle, un mode, un device…
- **Boutons** : Actions spécifiques (charger un fichier, ajouter un modèle…)
- **Champs texte** : URLs, chemins, paramètres

### Étape 4 : Observer les résultats

Les nœuds affichent un **aperçu en temps réel** de leur sortie image directement dans leur corps. Le pipeline s'exécute automatiquement en continu (cycle de 10 ms).

### Étape 5 : Supprimer un élément

- Sélectionnez un nœud ou un lien en cliquant dessus
- Appuyez sur la touche **Suppr** pour le supprimer
- Les connexions associées sont automatiquement nettoyées

---

## Catalogue des nœuds

CV Studio intègre **85+ nœuds** répartis en **16 catégories** :

---

### 🟢 Input (Sources d'entrée)

Nœuds permettant d'acquérir des données (images, vidéos, audio, flux réseau).

| Nœud | Description |
|------|-------------|
| **Webcam** | Capture vidéo depuis la webcam avec sortie audio optionnelle |
| **Image** | Charge une image depuis un fichier (PNG, JPG, BMP…) |
| **Video** | Lecture d'un fichier vidéo avec extraction audio via FFmpeg |
| **RTSP** | Flux vidéo RTSP en temps réel (caméras IP) |
| **HLS** | Flux HTTP Live Streaming avec audio |
| **YouTube** | Streaming vidéo depuis YouTube via pafy |
| **WebRTC** | Flux WebRTC pour streaming basse latence |
| **ScreenCapture** | Capture de l'écran en temps réel |
| **Microphone** | Entrée audio depuis le microphone (16 kHz par défaut) |
| **API** | Entrée via requête REST (image/JSON) |
| **MQTT** | Réception de messages via le protocole MQTT |
| **WebSocket** | Connexion WebSocket (données AIS, streaming…) |
| **Weather** | Données météo via l'API OpenWeather (température, JSON) |
| **JsonBoolean** | Sortie booléenne JSON configurable (checkbox) |
| **CoordinateExamples** | Coordonnées GPS prédéfinies pour la visualisation Map |

---

### 🔵 VisionProcess (Traitement d'image)

Nœuds de traitement classique d'image avec OpenCV.

| Nœud | Description |
|------|-------------|
| **Blur** | Flou gaussien, médian ou bilatéral |
| **BilateralFilter** | Filtre bilatéral (préserve les contours) |
| **NLMDenoise** | Débruitage Non-Local Means |
| **SimpleFilter** | Filtres de convolution personnalisés |
| **KernelSharpen** | Renforcement de la netteté par noyau |
| **UnsharpMask** | Masque flou pour la netteté |
| **Brightness** | Ajustement de la luminosité |
| **Contrast** | Ajustement du contraste |
| **GammaCorrection** | Correction gamma |
| **CLAHE** | Égalisation adaptative de l'histogramme |
| **IlluminationCorrect** | Correction de l'éclairage non uniforme |
| **EqualizeHist** | Égalisation d'histogramme classique |
| **Canny** | Détection de contours Canny |
| **Morphology** | Opérations morphologiques (érosion, dilatation, ouverture, fermeture) |
| **Threshold** | Seuillage binaire / Otsu / Triangle |
| **AdaptiveThreshold** | Seuillage adaptatif (gaussien, mean) |
| **Grayscale** | Conversion en niveaux de gris |
| **ColorSpace** | Conversion d'espace colorimétrique (RGB, HSV, LAB, YUV…) |
| **ApplyColorMap** | Application d'une palette de couleurs (jet, hot, cool…) |
| **Crop** | Recadrage d'une région d'intérêt (ROI) |
| **Resize** | Redimensionnement de l'image |
| **Flip** | Retournement horizontal / vertical |
| **Zoom** | Zoom numérique sur une zone |
| **ImageAlphaBlend** | Fusion alpha de deux images |
| **OmnidirectionalViewer** | Visualisation d'images omnidirectionnelles / 360° |

---

### 🟣 VisionModel (Modèles de Vision IA)

Nœuds d'inférence Deep Learning basés sur ONNX Runtime.

| Nœud | Description |
|------|-------------|
| **ObjectDetection** | Détection d'objets (YOLOX, YOLO11, FreeYOLO, ONNX custom). Supporte l'ajout de modèles personnalisés via le registre |
| **Classification** | Classification d'images (MobileNetV3, EfficientNet, ResNet50, YoloCls) |
| **FaceDetection** | Détection de visages (YuNet, MediaPipe, ONNX custom) |
| **PoseEstimation** | Estimation de pose (MoveNet, MediaPipe Hands/Pose, keypoints Tennis) |
| **SemanticSegmentation** | Segmentation sémantique (DeepLabV3, YOLOv8-seg, MediaPipe Selfie) |
| **MonocularDepthEstimation** | Estimation de profondeur monoculaire (FSRE_Depth, HR_Depth, ONNX custom) |
| **LLIE** | Amélioration d'images en basse lumière (TBEFN, SCI, AGLLNet) |

#### Ajouter un modèle ONNX personnalisé

1. Cliquez sur le bouton **"Add Model"** (jaune) dans le nœud ObjectDetection
2. Sélectionnez votre fichier `.onnx` via la boîte de dialogue
3. Une fenêtre de prévisualisation affiche les métadonnées du modèle
4. Confirmez pour enregistrer le modèle dans le registre
5. Le modèle apparaît dans la combo-box de sélection

---

### 🟠 AudioProcess (Traitement Audio)

| Nœud | Description |
|------|-------------|
| **Spectrogram** | Visualisation spectrogramme (mel, STFT, chromagramme) — convertit AUDIO → IMAGE |
| **Decibel** | Calcul du niveau en décibels (RMS) depuis le flux audio |
| **Equalizer** | Égaliseur 5 bandes avec contrôle de gain |

---

### 🔴 AudioModel (Modèles Audio IA)

| Nœud | Description |
|------|-------------|
| **AudioClassification** | Classification audio par modèle ONNX (ex. : YAMNet). Entrée mel-spectrogramme, sortie classes + passthrough audio. Supporte l'ajout de modèles personnalisés |

---

### 📊 DataProcess (Traitement de données)

| Nœud | Description |
|------|-------------|
| **Histogram** | Histogramme de visualisation pour données JSON |
| **Homography** | Transformation homographique de coordonnées keypoints |
| **DistanceTracker** | Suivi de distance entre keypoints transformés |
| **DataProcessingKeypoints** | Traitement de données de keypoints de terrain |
| **BAR** | Graphique en barres (nœud interne, masqué du menu) |

---

### 📈 DataModel (Modèles de données)

| Nœud | Description |
|------|-------------|
| **PositionPrediction** | Prédiction de position par filtre de Kalman |

---

### 📝 NLPModel (Modèles NLP)

| Nœud | Description |
|------|-------------|
| **TinyBertVigilance** | Classification de vigilance par TinyBERT (vectorisation de phrases) |

---

### ⚡ Trigger (Déclencheurs)

Nœuds de logique conditionnelle pour activer/désactiver des actions.

| Nœud | Description |
|------|-------------|
| **Trigger** | Déclencheur générique basé sur des conditions |
| **ObjDetCount** | Déclencheur basé sur le nombre d'objets détectés (filtrage par classe COCO) |
| **DbDetCount** | Déclencheur basé sur la variation du nombre de détections (moyenne glissante) |
| **OnOffSwitch** | Interrupteur booléen ON/OFF |
| **BooleanInverter** | Inverseur de signal booléen JSON |
| **CourtKeypointDeviation** | Déclencheur sur déviation de keypoints (clustering KMeans) |

---

### 🔀 Router (Routage)

| Nœud | Description |
|------|-------------|
| **SimpleRouter** | Distribue les données vers plusieurs sorties avec effet visuel de clignotement |

---

### 🎬 Action (Actions de sortie)

Nœuds qui exécutent des actions concrètes sur le monde extérieur.

| Nœud | Description |
|------|-------------|
| **VideoRecorder** | Enregistrement vidéo contrôlé par trigger JSON avec métadonnées |
| **Buzzer** | Alerte sonore configurable (durée, fréquence) |
| **MongoDB** | Connexion et stockage de données dans MongoDB |
| **VLM** | Requête vers un modèle Vision-Language (captioning d'image via API HTTP) |

---

### 🖌️ Overlay (Superposition)

Nœuds pour dessiner des annotations sur les images.

| Nœud | Description |
|------|-------------|
| **Overlay** | Superposition des résultats JSON sur l'image (bounding boxes, labels) |
| **OverlayImage** | Superposition d'une image avec contrôle de position, échelle et alpha |
| **PutText** | Ajout de texte sur l'image (couleur, position, taille configurable) |
| **DrawInformation** | Dessin d'informations détaillées (classes, scores) |

---

### 🏃 Tracking (Suivi multi-objets)

| Nœud | Description |
|------|-------------|
| **MultiObjectTracking** | Suivi multi-objets (ByteTrack, Norfair, SORT, CenterTrack, OC-SORT, BotSORT) |
| **ReId** | Ré-identification d'objets par clustering KMeans |

---

### 📺 Visual (Visualisation avancée)

Nœuds de visualisation et représentation graphique des résultats.

| Nœud | Description |
|------|-------------|
| **HeatMap** | Carte de chaleur configurable (colormap, flou gaussien) |
| **ObjHeatMap** | Carte de chaleur des détections d'objets (filtrage par classe, alpha) |
| **Chart** | Graphique temporel des détections d'objets |
| **Map** | Carte interactive avec tuiles OSM (contextily + matplotlib) |
| **TennisCourt** | Visualisation de terrain de tennis avec keypoints transformés |
| **VigilanceGauge** | Jauge de niveau de vigilance (5 niveaux, code couleur) |
| **WordCloud** | Nuage de mots depuis la sortie texte VLM (multiples palettes) |

---

### 🎥 Video (Production vidéo)

| Nœud | Description |
|------|-------------|
| **VideoWriter** | Encodage et écriture vidéo avec FFmpeg (sync audio/vidéo) |
| **ImageConcat** | Concaténation de multiples flux images en une mosaïque |
| **DynamicPlay** | Lecture dynamique de médias avec contrôle gestuel |
| **ScreenCapture** | Capture d'écran comme source vidéo |

---

### ⚙️ System (Système)

| Nœud | Description |
|------|-------------|
| **SyncQueue** | Synchronisation de données depuis plusieurs files d'attente (timestamps) |

---

## Connexions et types de données

### Types de données supportés

| Type | Couleur | Description |
|------|---------|-------------|
| `IMAGE` | — | Image OpenCV (numpy array BGR) |
| `AUDIO` | — | Données audio (dict avec waveform, sample_rate, chunk_index…) |
| `JSON` | — | Résultats structurés (détections, classifications, métriques) |
| `FLOAT` | — | Valeur flottante |
| `INT` | — | Valeur entière |
| `BOOLEAN` | — | Valeur booléenne (true/false) |
| `TEXT` | — | Chaîne de caractères |
| `TIME_MS` | — | Timestamp en millisecondes |

### Règles de connexion

- **IMAGE → IMAGE** : Connexion standard d'images
- **AUDIO → AUDIO** : Connexion standard audio
- **AUDIO → IMAGE** : Conversion possible (spectrogramme)
- Les types doivent être compatibles entre la sortie et l'entrée
- Un port d'entrée n'accepte qu'une seule connexion
- Un port de sortie peut alimenter plusieurs entrées

### Ordre d'exécution

Les nœuds sont automatiquement triés par **ordre topologique** selon le graphe de connexions. Cela garantit que chaque nœud reçoit les données les plus récentes de ses sources avant de s'exécuter.

---

## Sauvegarder et charger un workflow

### Exporter un workflow

1. Menu **File** → **Export**
2. Une boîte de dialogue s'ouvre (nom par défaut : date du jour `YYYYMMDD`)
3. Choisissez un emplacement et un nom de fichier
4. Le workflow est sauvegardé en **format JSON**

#### Structure du fichier exporté

```json
{
  "node_list": ["1:Webcam", "2:Blur", "3:ResultImage"],
  "link_list": [
    ["1:Webcam:IMAGE:Output01", "2:Blur:IMAGE:Input01"],
    ["2:Blur:IMAGE:Output01", "3:ResultImage:IMAGE:Input01"]
  ],
  "1:Webcam": {
    "id": "1",
    "name": "Webcam",
    "setting": {
      "ver": "0.0.1",
      "pos": [100, 150],
      "1:Webcam:INT:Input01Value": 0
    }
  }
}
```

### Importer un workflow

1. Menu **File** → **Import**
2. Sélectionnez un fichier `.json` précédemment exporté
3. Le workflow est recréé automatiquement (nœuds, positions, paramètres, connexions)

> ⚠️ **Limitation** : L'importation ne fonctionne que si le canvas est **vide** (aucun nœud présent). Si des nœuds existent, un message d'avertissement apparaît.

### Bonnes pratiques

- Sauvegardez fréquemment vos workflows pendant la construction
- Utilisez des noms de fichiers explicites (ex. : `detection_personnes_rtsp.json`)
- Les fichiers JSON sont lisibles et versionnables (Git)
- Partagez vos workflows entre collègues en partageant le fichier `.json`

---

## Configuration

Le fichier de configuration principal se trouve dans `node_editor/setting/setting.json` :

```json
{
  "webcam_width": 1280,
  "webcam_height": 720,
  "editor_width": 1280,
  "editor_height": 720,
  "input_window_width": 240,
  "input_window_height": 135,
  "process_width": 240,
  "process_height": 135,
  "result_width": 480,
  "result_height": 600,
  "video_writer_width": 1280,
  "video_writer_height": 720,
  "video_writer_fps": 30,
  "video_writer_directory": "./_VideoWriter",
  "use_pref_counter": true,
  "draw_info_on_result": true,
  "use_gpu": true,
  "use_serial": false,
  "use_multiprocessing_rtsp": true,
  "use_multiprocessing_hls": true,
  "audio_chunk_duration": 5.0,
  "audio_chunk_step": 1.0
}
```

### Paramètres principaux

| Paramètre | Description |
|-----------|-------------|
| `webcam_width/height` | Résolution de capture webcam |
| `editor_width/height` | Taille de la fenêtre de l'éditeur |
| `process_width/height` | Taille des aperçus de traitement |
| `result_width/height` | Taille de la fenêtre de résultat |
| `video_writer_*` | Paramètres d'encodage vidéo (résolution, FPS, dossier) |
| `use_gpu` | Activer l'accélération GPU pour l'inférence |
| `use_pref_counter` | Afficher le compteur de performances |
| `draw_info_on_result` | Dessiner les labels sur les résultats |
| `audio_chunk_duration` | Durée des chunks audio en secondes |
| `audio_chunk_step` | Pas de glissement des chunks audio |

---

## Exemples de workflows

### Exemple 1 : Détection d'objets en temps réel

```
┌──────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────┐
│  Webcam  │────▶│ ObjectDetection │────▶│ DrawInformation │────▶│ VideoWriter │
└──────────┘     └─────────────────┘     └─────────────────┘     └─────────────┘
```

1. **Input → Webcam** : Capture le flux vidéo
2. **VisionModel → ObjectDetection** : Détecte les objets (YOLO)
3. **Overlay → DrawInformation** : Dessine les boîtes englobantes
4. **Video → VideoWriter** : Enregistre la vidéo annotée

---

### Exemple 2 : Surveillance avec alerte

```
┌──────────┐     ┌─────────────────┐     ┌─────────────┐     ┌────────┐
│   RTSP   │────▶│ ObjectDetection │────▶│ ObjDetCount │────▶│ Buzzer │
└──────────┘     └─────────────────┘     └─────────────┘     └────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │VideoRecorder │
                                         └──────────────┘
```

1. **Input → RTSP** : Flux caméra IP
2. **VisionModel → ObjectDetection** : Détecte les personnes
3. **Trigger → ObjDetCount** : Déclenche si nombre > seuil
4. **Action → Buzzer** : Émet une alerte sonore
5. **Action → VideoRecorder** : Enregistre le clip

---

### Exemple 3 : Traitement d'image avancé

```
┌──────────┐     ┌────────┐     ┌───────┐     ┌──────────┐
│  Image   │────▶│  CLAHE │────▶│ Canny │────▶│ Overlay  │
└──────────┘     └────────┘     └───────┘     └──────────┘
```

1. **Input → Image** : Charge une image
2. **VisionProcess → CLAHE** : Améliore le contraste
3. **VisionProcess → Canny** : Détecte les contours
4. **Overlay → Overlay** : Superpose le résultat

---

### Exemple 4 : Classification audio en temps réel

```
┌────────────┐     ┌─────────────────────┐     ┌─────────────┐
│ Microphone │────▶│ AudioClassification │────▶│ ImageConcat │
└────────────┘     └─────────────────────┘     └─────────────┘
                           │
                           ▼ (image: spectrogramme)
                   ┌─────────────┐
                   │  HeatMap    │
                   └─────────────┘
```

1. **Input → Microphone** : Capture audio 16 kHz
2. **AudioModel → AudioClassification** : Classifie les sons (YAMNet)
3. **Visual → HeatMap** : Affiche la carte de chaleur du spectrogramme
4. **Video → ImageConcat** : Combine les visualisations

---

### Exemple 5 : Suivi multi-objets avec analyse

```
┌──────────┐     ┌─────────────────┐     ┌─────────────────────┐     ┌─────────┐
│  Video   │────▶│ ObjectDetection │────▶│ MultiObjectTracking │────▶│ Overlay │
└──────────┘     └─────────────────┘     └─────────────────────┘     └─────────┘
                                                    │
                                                    ▼
                                            ┌────────────┐
                                            │ ObjHeatMap │
                                            └────────────┘
```

1. **Input → Video** : Lecture d'un fichier vidéo
2. **VisionModel → ObjectDetection** : Détecte les objets
3. **Tracking → MultiObjectTracking** : Assigne des IDs et suit les trajectoires
4. **Overlay → Overlay** : Affiche les résultats avec IDs
5. **Visual → ObjHeatMap** : Visualise les zones de concentration

---

### Exemple 6 : Pipeline sport (Tennis)

```
┌──────────┐     ┌────────────────┐     ┌───────────────┐     ┌──────────────┐
│  Video   │────▶│ PoseEstimation │────▶│  Homography   │────▶│ TennisCourt  │
└──────────┘     └────────────────┘     └───────────────┘     └──────────────┘
                                                │
                                                ▼
                                     ┌───────────────────────┐
                                     │   PositionPrediction  │
                                     └───────────────────────┘
```

---

## Conseils pour la création de workflows efficaces

### Organisation

- **Placez les nœuds sources à gauche** et les nœuds de sortie à droite
- **Alignez les nœuds** pour une meilleure lisibilité du flux
- **Regroupez les nœuds** par fonction logique

### Performance

- Activez **use_gpu: true** pour l'inférence Deep Learning
- Utilisez **Resize** avant les modèles lourds pour réduire la résolution
- Limitez le nombre de modèles simultanés si la mémoire GPU est contrainte
- Le mode **multiprocessing** est recommandé pour les flux RTSP/HLS

### Débogage

- Lancez avec `--use_debug_print` pour voir le flux de données
- Connectez un nœud **Overlay** à n'importe quel point pour visualiser l'état intermédiaire
- Vérifiez les connexions dans la minimap pour les workflows complexes

### Extensibilité

- Ajoutez vos propres modèles ONNX via le bouton **"Add Model"**
- Les fichiers de workflow `.json` sont portables entre machines
- Créez des workflows de référence pour chaque cas d'usage

---

## Résumé des catégories de menu

| Menu | Icône | Nombre | Usage |
|------|-------|--------|-------|
| Input | 🟢 | 15 | Sources de données (caméra, fichier, réseau, audio) |
| VisionProcess | 🔵 | 25 | Traitement d'image classique (filtres, couleurs, géométrie) |
| VisionModel | 🟣 | 7 | Inférence Deep Learning (détection, segmentation, pose) |
| AudioProcess | 🟠 | 3 | Traitement du signal audio |
| AudioModel | 🔴 | 1 | Classification audio par IA |
| DataProcess | 📊 | 5 | Statistiques et transformations de données |
| DataModel | 📈 | 1 | Modèles de prédiction (Kalman) |
| NLPModel | 📝 | 1 | Traitement du langage naturel |
| Trigger | ⚡ | 6 | Logique conditionnelle et événements |
| Router | 🔀 | 1 | Distribution de données |
| Action | 🎬 | 4 | Actions concrètes (enregistrement, alertes, DB) |
| Overlay | 🖌️ | 4 | Annotations et superpositions |
| Tracking | 🏃 | 2 | Suivi multi-objets |
| Visual | 📺 | 7 | Visualisations avancées |
| Video | 🎥 | 4 | Production et encodage vidéo |
| System | ⚙️ | 1 | Synchronisation système |

---

*Documentation générée pour CV Studio v0.0.1*
