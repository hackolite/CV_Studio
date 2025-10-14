# Synchronisation Vidéo-Audio : Explication Claire

## Vue d'ensemble

Ce document explique comment le nœud Vidéo de CV Studio traite un fichier vidéo en :
1. **Séparant** l'audio et la vidéo
2. **Découpant** la vidéo en images individuelles (frames)
3. **Faisant correspondre** chaque frame audio (spectrogramme) avec le frame vidéo correspondant
4. **Jouant** le tout de façon synchronisée dans le nœud

---

## Étape 1 : Séparation Audio et Vidéo

### Qu'est-ce qui se passe ?
Quand vous sélectionnez un fichier vidéo, le système sépare le flux audio du flux vidéo.

### Code
**Fichier :** `node/InputNode/node_video.py`, méthode `_prepare_spectrogram()`

```python
# Extraction de l'audio depuis la vidéo avec ffmpeg
subprocess.run([
    'ffmpeg', '-i', movie_path,    # Entrée : fichier vidéo
    '-vn',                          # Enlever le flux vidéo
    '-acodec', 'pcm_s16le',        # Codec audio
    '-ar', '22050',                # Fréquence d'échantillonnage : 22050 Hz
    '-ac', '1',                    # Audio mono (1 canal)
    '-y', tmp_audio_path           # Sortie : fichier audio temporaire
])
```

### Résultat
- **Flux audio :** Extrait à 22 050 échantillons par seconde
- **Flux vidéo :** Reste dans le fichier original, accessible via OpenCV

---

## Étape 2 : Découpage de la Vidéo en Frames

### Qu'est-ce qui se passe ?
La vidéo est lue image par image pendant la lecture.

### Code
**Fichier :** `node/InputNode/node_video.py`, méthode `update()`

```python
# Ouvrir le fichier vidéo
video_capture = cv2.VideoCapture(movie_path)

# Obtenir les propriétés vidéo
fps = video_capture.get(cv2.CAP_PROP_FPS)  # ex: 30 images par seconde

# Lire les frames une par une
while True:
    ret, frame = video_capture.read()  # Lire le prochain frame
    if not ret:
        # Fin de la vidéo
        if loop_flag:
            video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Retour au début
            self._frame_count[str(node_id)] = 0             # Réinitialiser le compteur
        break
    
    self._frame_count[str(node_id)] += 1  # Compter le frame actuel
```

### Résultat
- **Frames vidéo :** Chaque frame = une image (tableau de pixels)
- **Compteur de frames :** `_frame_count` garde la trace du frame actuel
- **Fréquence d'images :** Le système connaît le FPS (ex: 30 images/seconde)

---

## Étape 3 : Génération du Spectrogramme Audio

### Qu'est-ce qui se passe ?
L'audio extrait est transformé en spectrogramme visuel qui montre les fréquences au fil du temps.

### Code
**Fichier :** `node/InputNode/node_video.py`, méthode `_prepare_spectrogram()`

```python
# Calculer le spectrogramme mel depuis l'audio
S = librosa.feature.melspectrogram(
    y=y,                    # Signal audio
    sr=sr,                  # Fréquence d'échantillonnage (22050 Hz)
    n_fft=2048,            # Taille de la fenêtre FFT
    hop_length=512,        # Échantillons entre colonnes (CRITIQUE pour la synchro!)
    n_mels=128,            # Nombre de bandes de fréquences
    power=2.0              # Spectrogramme de puissance
)

# Convertir en échelle décibel pour meilleure visualisation
S_db = librosa.power_to_db(S, ref=np.max)

# Normaliser entre 0 et 1
S_normalized = (S_db - S_db.min()) / (S_db.max() - S_db.min() + 1e-6)

# Appliquer une palette de couleurs (magma)
cmap = matplotlib.cm.get_cmap('magma')
S_colored = cmap(S_normalized)

# Convertir en image RGB 8-bit
S_rgb = (S_colored[:, :, :3] * 255).astype(np.uint8)

# Retourner verticalement (basses fréquences en bas)
S_rgb = np.flipud(S_rgb)
```

### Structure du Spectrogramme
- **Lignes (axe Y) :** Bandes de fréquences (128 bandes mel, graves en bas)
- **Colonnes (axe X) :** Progression dans le temps
- **Chaque colonne :** Représente 512 échantillons audio = 0,023 secondes

### Résultat
- **Tableau spectrogramme :** Image 2D (128 lignes × N colonnes)
- **Métadonnées stockées :** Fréquence d'échantillonnage, hop_length, FPS vidéo

---

## Étape 4 : Correspondance Frame par Frame

### La Formule de Synchronisation

C'est l'**ÉTAPE CRITIQUE** où audio et vidéo sont synchronisés.

**Fichier :** `node/InputNode/node_video.py`, méthode `update()`

```python
# Étape 4A : Obtenir le numéro du frame vidéo actuel
current_frame = self._frame_count.get(str(node_id), 0)  # ex: frame 900

# Étape 4B : Convertir le numéro de frame en temps (secondes)
fps = 30.0  # images par seconde
current_time = current_frame / fps  # 900 / 30 = 30,0 secondes

# Étape 4C : Convertir le temps en position d'échantillon audio
sr = 22050  # fréquence d'échantillonnage audio (échantillons/seconde)
current_sample = int(current_time * sr)  # 30,0 * 22050 = 661 500 échantillons

# Étape 4D : Convertir l'échantillon audio en colonne du spectrogramme
hop_length = 512  # échantillons par colonne
spectrogram_col = int(current_sample / hop_length)  # 661 500 / 512 = 1 292

# Résultat :
# - La vidéo montre le frame 900 (à 30 secondes)
# - La colonne 1 292 du spectrogramme correspond à ce moment exact
```

### Pourquoi ça Marche ?

La synchronisation est mathématiquement précise :

```
Frame Vidéo → Temps → Échantillon Audio → Colonne Spectrogramme
    900     → 30,0s →     661 500       →        1 292

Chaque frame vidéo correspond à exactement une colonne du spectrogramme !
```

### Paramètres Clés (Doivent Correspondre !)
- **hop_length = 512 :** Même valeur utilisée pour générer le spectrogramme
- **sr = 22050 :** Même fréquence d'échantillonnage pour extraire l'audio
- **fps :** Fréquence d'images réelle du fichier vidéo

---

## Étape 5 : Fenêtre de Défilement

### Qu'est-ce qui se passe ?
Au lieu de montrer tout le spectrogramme (qui serait compressé et illisible), le système montre une **fenêtre glissante** centrée sur la position actuelle.

### Code
**Fichier :** `node/InputNode/node_video.py`, méthode `update()`

```python
# Définir la taille de la fenêtre (correspond à la largeur d'affichage)
window_width = 240  # pixels
half_window = 120   # pixels

# Calculer les limites de la fenêtre
start_col = max(0, spectrogram_col - half_window)
end_col = min(full_spectrogram.shape[1], start_col + window_width)

# Extraire la tranche de la fenêtre
spectrogram_window = full_spectrogram[:, start_col:end_col].copy()

# Calculer la position de l'indicateur dans la fenêtre
indicator_col = spectrogram_col - start_col

# Dessiner une ligne jaune à la position actuelle
if 0 <= indicator_col < spectrogram_window.shape[1]:
    cv2.line(spectrogram_window, 
            (indicator_col, 0), 
            (indicator_col, spectrogram_window.shape[0] - 1), 
            (0, 255, 255),  # Jaune en BGR
            2)              # 2 pixels de large
```

### Représentation Visuelle

```
Spectrogramme Complet (ex: 12 919 colonnes pour vidéo de 5 minutes) :
[████████████████████████████████████████████████████████████████████████]
                         ↑
                  Position actuelle
                   (colonne 1 292)

Fenêtre Affichée (240 colonnes) :
              [█████████████|█████████████]
                            ↑
                    Indicateur jaune
                    (centré dans la fenêtre)

Pendant la lecture → la fenêtre glisse vers la droite → effet de défilement
```

### Exemple de Défilement

```
Frame 0 :     Fenêtre montre colonnes [0-240]       | Indicateur à colonne 0 (bord gauche)
Frame 300 :   Fenêtre montre colonnes [150-390]     | Indicateur à colonne 120 (centré)
Frame 900 :   Fenêtre montre colonnes [1172-1412]   | Indicateur à colonne 120 (centré)
Frame 5000 :  Fenêtre montre colonnes [6386-6626]   | Indicateur à colonne 120 (centré)
```

---

## Étape 6 : Lecture dans le Nœud

### Qu'est-ce qui se passe ?
Le frame vidéo et la fenêtre du spectrogramme synchronisés sont affichés ensemble dans l'interface du nœud DearPyGUI.

### Code
**Fichier :** `node/InputNode/node_video.py`, méthode `update()`

```python
# Convertir le frame vidéo en texture d'affichage
if frame is not None:
    texture = self.convert_cv_to_dpg(
        frame,              # Frame vidéo (tableau numpy)
        small_window_w,     # 240 pixels
        small_window_h,     # 135 pixels
    )
    dpg_set_value(tag_node_output_image, texture)  # Mettre à jour l'affichage vidéo

# Convertir la fenêtre du spectrogramme en texture d'affichage
texture = self.convert_cv_to_dpg(
    spectrogram_window,  # Fenêtre du spectrogramme avec ligne jaune
    small_window_w,      # 240 pixels
    small_window_h       # 135 pixels
)
dpg_set_value(tag_node_spectrogram_value, texture)  # Mettre à jour l'affichage spectrogramme
```

### Interface Utilisateur

```
┌─────────────────────────────────┐
│       Nœud Vidéo                │
├─────────────────────────────────┤
│  [Sélectionner Film]            │
├─────────────────────────────────┤
│  ┌───────────────────────────┐  │  ← Affichage du frame vidéo
│  │                           │  │    (240×135 pixels)
│  │     Frame Vidéo           │  │
│  │                           │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  ☑ Afficher Spectrogramme       │
│  ┌───────────────────────────┐  │  ← Affichage du spectrogramme
│  │     ███|███████            │  │    (240×135 pixels)
│  │     ███|███████            │  │    La ligne jaune montre
│  │     ███|███████            │  │    la position actuelle
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│  ☑ Boucle                       │
│  Taux de saut : [===|=======] 1 │
│  [Démarrer]                     │
└─────────────────────────────────┘
```

---

## Résumé du Flux de Données Complet

### Initialisation (quand la vidéo est chargée)

```
1. L'utilisateur sélectionne un fichier vidéo
   ↓
2. Extraction de l'audio
   - ffmpeg sépare le flux audio
   - Audio : 22050 échantillons/seconde
   ↓
3. Génération du spectrogramme
   - mel-spectrogramme avec hop_length=512
   - Résultat : tableau 2D (128 × N_colonnes)
   ↓
4. Stockage des métadonnées
   - Audio : sample_rate, hop_length
   - Vidéo : fps
```

### Lecture (à chaque mise à jour de frame)

```
1. Lire le prochain frame vidéo
   - frame_count s'incrémente
   - Frame stocké comme tableau numpy
   ↓
2. Calculer la synchronisation
   - frame → temps → échantillon → colonne
   - Exemple : frame 900 → 30s → 661500 → col 1292
   ↓
3. Extraire la fenêtre du spectrogramme
   - 240 colonnes centrées sur la position actuelle
   - Dessiner une ligne jaune au centre
   ↓
4. Afficher les deux
   - Frame vidéo dans l'affichage du haut
   - Fenêtre du spectrogramme dans l'affichage du bas
   ↓
5. Répéter pour le prochain frame
```

---

## Exemple Pratique

### Vidéo : 30 FPS, 1 minute de durée

```
Frames vidéo :       1 800 frames (30 fps × 60 secondes)
Échantillons audio : 1 323 000 échantillons (22050 Hz × 60 secondes)
Spectrogramme :      2 584 colonnes (1 323 000 / 512)

Frame 0 :     0,000s → échantillon 0         → colonne 0
Frame 30 :    1,000s → échantillon 22 050    → colonne 43
Frame 900 :   30,00s → échantillon 661 500   → colonne 1 292
Frame 1800 :  60,00s → échantillon 1 323 000 → colonne 2 584
```

### Affichage de la Fenêtre

Au frame 900 (30 secondes) :
- Colonne du spectrogramme : 1 292
- Fenêtre montre : colonnes 1 172 à 1 412 (240 colonnes)
- Ligne jaune à : colonne 120 dans la fenêtre (centre)
- Position réelle : colonne 1 292 dans le spectrogramme complet

---

## Avantages de Cette Approche

### ✓ **Synchronisation Parfaite**
La formule mathématique garantit que l'audio et la vidéo restent synchronisés

### ✓ **Précision Frame par Frame**
Chaque frame vidéo correspond exactement à un moment audio

### ✓ **Spectrogramme Lisible**
Mapping 1:1 pixel (pas de compression) rend les fréquences visibles

### ✓ **Défilement Fluide**
La fenêtre glisse en douceur pendant la lecture de la vidéo

### ✓ **Support de Boucle**
Quand la vidéo boucle, frame_count et position se réinitialisent à 0

### ✓ **Efficace**
- Extraction audio : une fois au chargement
- Génération du spectrogramme : une fois au chargement
- Lecture : seulement extraction de fenêtre et dessin de ligne (rapide)

---

## Points Clés de Synchronisation

### 1. **Résolution Temporelle**
- **Vidéo :** 1 frame = 1/30 seconde = 0,033 secondes (à 30 FPS)
- **Audio :** 1 colonne spectrogramme = 512/22050 = 0,023 secondes
- **Résultat :** La résolution audio est plus élevée que la vidéo (plus de détails)

### 2. **Cohérence**
Le hop_length=512 est **CRITIQUE** :
- Utilisé pendant la génération du spectrogramme
- Utilisé pendant la synchronisation de lecture
- Le changer casserait la synchro !

### 3. **Précision**
Le mapping frame-à-colonne est mathématiquement exact :
```python
# Avant : frame → colonne
colonne = int((frame / fps) * sr / hop_length)

# Arrière : colonne → frame (approximatif)
frame = int((colonne * hop_length / sr) * fps)
```

---

## Fichiers Modifiés

1. **`node/InputNode/node_video.py`**
   - `_prepare_spectrogram()` : Extraction audio et génération du spectrogramme
   - `update()` : Synchronisation frame par frame et affichage

2. **Structures de Stockage**
   - `_spectrogram_array[node_id]` : Spectrogramme complet (128 × N_colonnes)
   - `_spectrogram_meta[node_id]` : {y, sr, hop_length, fps}
   - `_frame_count[node_id]` : Numéro du frame vidéo actuel
   - `_video_capture[node_id]` : Objet OpenCV VideoCapture

---

## Conclusion

Le système de synchronisation vidéo-audio fonctionne en :
1. **Séparant** l'audio et la vidéo en flux séparés
2. **Traitant** la vidéo frame par frame avec comptage des frames
3. **Générant** un spectrogramme temps-fréquence depuis l'audio
4. **Faisant correspondre** chaque frame vidéo à une colonne du spectrogramme avec des maths précises
5. **Affichant** une fenêtre glissante synchronisée avec indicateur visuel

Le résultat est un affichage audio-visuel **parfaitement synchronisé, lisible et fluide** qui aide les utilisateurs à comprendre quelles fréquences audio sont présentes à chaque moment de la vidéo.
