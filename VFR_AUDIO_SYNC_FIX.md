# Fix pour les problèmes Audio/Vidéo après traitement FFmpeg + OpenCV

## Problème identifié (Symptômes)

### 1. Vidéo finale légèrement plus lente que l'originale
**Cause racine** : Utilisation d'un FPS incorrect lors de la reconstruction
- OpenCV (`cv2.CAP_PROP_FPS`) retourne un FPS non fiable pour les vidéos VFR
- Le FPS incorrect est utilisé pour reconstruire la vidéo avec `cv2.VideoWriter`
- Résultat : vidéo ralentie

### 2. Audio métallique, pâteux, étiré (effet "robot/glaire")
**Cause racine** : Découpage audio basé sur un FPS incorrect
- Le chunking audio utilise : `samples_per_frame = sample_rate / fps`
- Si le FPS est incorrect, les chunks audio sont mal dimensionnés
- Résultat : audio dégradé, effet métallique

### 3. Désynchronisation audio/vidéo progressive
**Cause racine** : Décalage cumulatif dû au FPS incorrect
- Chaque frame d'erreur s'accumule
- Plus la vidéo est longue, plus le décalage est important

## Solution implémentée

### 1. Extraction du FPS réel avec ffprobe

**Avant (INCORRECT)** :
```python
# OpenCV retourne un FPS non fiable pour VFR
fps = cap.get(cv2.CAP_PROP_FPS)  # ❌ Peut être faux pour VFR
```

**Après (CORRECT)** :
```python
# Utiliser ffprobe pour obtenir le avg_frame_rate réel
fps = self._get_accurate_fps(movie_path)  # ✓ FPS fiable
```

### 2. Nouvelle méthode `_get_accurate_fps()`

Cette méthode utilise ffprobe pour extraire le `avg_frame_rate` précis :

```python
def _get_accurate_fps(self, video_path):
    """
    Extrait le FPS précis avec ffprobe (avg_frame_rate).
    Plus fiable que OpenCV, surtout après conversion VFR→CFR.
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate",
            "-of", "csv=p=0",
            video_path
        ],
        capture_output=True,
        text=True,
        check=True
    )
    
    output = result.stdout.strip()
    if '/' in output:
        num, den = output.split('/')
        fps = float(num) / float(den)
    else:
        fps = float(output)
    
    return fps
```

### 3. Pipeline complète VFR → CFR correcte

#### Étape 1 : Détection VFR
```python
# Comparer r_frame_rate et avg_frame_rate
is_vfr = self._detect_vfr(movie_path)
```

#### Étape 2 : Conversion VFR → CFR
```python
if is_vfr:
    cfr_video_path = self._convert_vfr_to_cfr(movie_path, target_fps=target_fps)
    movie_path = cfr_video_path
```

#### Étape 3 : Extraction FPS précis
```python
# Utiliser ffprobe (pas OpenCV) pour obtenir le FPS réel
fps = self._get_accurate_fps(movie_path)
```

#### Étape 4 : Chunking audio correct
```python
# Maintenant le FPS est correct, le chunking sera précis
samples_per_frame = sample_rate / fps  # ✓ Correct
```

#### Étape 5 : Reconstruction avec FPS correct
```python
# VideoWriter utilisera le FPS correct depuis les métadonnées
video_writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
```

## Commandes FFmpeg recommandées (Production)

### Commande de conversion VFR → CFR (CORRECTE)

```bash
ffmpeg -i input_vfr.mp4 \
  -vsync cfr \              # Force constant frame rate
  -r 24 \                   # Target FPS (utiliser avg_frame_rate de la source)
  -c:v libx264 \            # Codec H.264
  -preset fast \            # Vitesse d'encodage
  -crf 18 \                 # Qualité (18 = visuellement lossless)
  -c:a copy \               # Copie audio SANS ré-encodage (CRITIQUE)
  output_cfr.mp4
```

**Points critiques** :
- `-vsync cfr` : Force CFR en dupliquant/supprimant frames si nécessaire
- `-r 24` : Utiliser le `avg_frame_rate` de la source (obtenu avec ffprobe)
- `-c:a copy` : **NE PAS ré-encoder l'audio** (préserve qualité)
- `-crf 18` : Qualité visuelle lossless (18-23 recommandé)

### Extraction du FPS réel (avg_frame_rate)

```bash
# Obtenir avg_frame_rate (le plus fiable)
ffprobe -v error -select_streams v:0 \
  -show_entries stream=avg_frame_rate \
  -of csv=p=0 input.mp4

# Exemple de sortie : "24000/1001" (23.976 fps)
# ou "30/1" (30 fps)
```

### Reconstruction vidéo avec audio (CORRECTE)

```bash
ffmpeg -i video.mp4 -i audio.wav \
  -map 0:v -map 1:a \
  -c:v copy \                        # Copie codec vidéo (pas de ré-encodage)
  -c:a aac \                         # Encoder audio en AAC
  -b:a 192k \                        # Bitrate audio élevé (qualité)
  -avoid_negative_ts make_zero \    # Aligne timestamps au début (CRITIQUE)
  -vsync cfr \                       # Force CFR
  -shortest \                        # Arrête à la fin du flux le plus court
  output.mp4
```

**Points critiques** :
- `-c:v copy` : Ne pas ré-encoder la vidéo (déjà en CFR)
- `-c:a aac -b:a 192k` : Qualité audio élevée
- `-avoid_negative_ts make_zero` : **CRITIQUE** pour synchro audio/vidéo
- `-vsync cfr` : Maintient CFR constant
- `-shortest` : Évite audio/vidéo de longueurs différentes

## Commandes FFmpeg à ÉVITER (Erreurs courantes)

### ❌ ERREUR 1 : Placer `-r` en entrée
```bash
# INCORRECT - Ne fait rien ou casse la synchro
ffmpeg -r 24 -i input.mp4 ...  # ❌ -r en INPUT ne force pas CFR
```

**Pourquoi c'est faux** : `-r` en input dit juste à ffmpeg à quelle vitesse LIRE, mais ne force pas CFR.

**Correct** :
```bash
ffmpeg -i input.mp4 -r 24 -vsync cfr ...  # ✓ -r en OUTPUT avec -vsync cfr
```

### ❌ ERREUR 2 : Ré-encoder l'audio inutilement
```bash
# INCORRECT - Dégrade l'audio
ffmpeg -i input.mp4 -c:a aac output.mp4  # ❌ Ré-encode audio sans raison
```

**Pourquoi c'est faux** : Chaque encodage dégrade la qualité audio (perte de données).

**Correct** :
```bash
# Pour conversion VFR→CFR, l'audio reste intact
ffmpeg -i input.mp4 -vsync cfr -r 24 -c:v libx264 -c:a copy output.mp4  # ✓
```

### ❌ ERREUR 3 : Double encodage audio
```bash
# INCORRECT - Encode puis ré-encode
ffmpeg -i input.mp4 -c:a aac temp.mp4
ffmpeg -i temp.mp4 -i audio.wav -c:a aac final.mp4  # ❌ Audio encodé 2 fois
```

**Pourquoi c'est faux** : Perte de qualité cumulative à chaque encodage.

**Correct** :
```bash
# Encoder une seule fois à la fin
ffmpeg -i temp.mp4 -i audio.wav -c:v copy -c:a aac -b:a 192k final.mp4  # ✓
```

### ❌ ERREUR 4 : Utiliser `-async 1` pour "corriger" la synchro
```bash
# INCORRECT - Étire/compresse l'audio
ffmpeg -i video.mp4 -i audio.wav -async 1 output.mp4  # ❌ Audio distordu
```

**Pourquoi c'est faux** : `-async` étire ou compresse l'audio pour correspondre à la durée vidéo, ce qui change le pitch et crée l'effet "robot".

**Correct** :
```bash
# Utiliser -avoid_negative_ts pour aligner les timestamps
ffmpeg -i video.mp4 -i audio.wav \
  -avoid_negative_ts make_zero \
  -vsync cfr -shortest output.mp4  # ✓ Synchro sans déformation
```

### ❌ ERREUR 5 : Oublier `-vsync cfr` lors de la reconstruction
```bash
# INCORRECT - Peut recréer du VFR
ffmpeg -i frames%04d.png -r 24 output.mp4  # ❌ Peut être VFR
```

**Pourquoi c'est faux** : Sans `-vsync cfr`, ffmpeg peut créer du VFR si les frames ne sont pas régulières.

**Correct** :
```bash
ffmpeg -framerate 24 -i frames%04d.png -vsync cfr -r 24 \
  -c:v libx264 -crf 18 output.mp4  # ✓ Force CFR
```

## Résumé des paramètres FFmpeg critiques

### Pour conversion VFR → CFR
| Paramètre | Valeur | Rôle | Obligatoire |
|-----------|--------|------|-------------|
| `-vsync` | `cfr` | Force constant frame rate | ✓ OUI |
| `-r` | `24` (avg_fps) | Target FPS en sortie | ✓ OUI |
| `-c:v` | `libx264` | Codec vidéo (ré-encodage nécessaire) | ✓ OUI |
| `-c:a` | `copy` | NE PAS ré-encoder audio | ✓ OUI |
| `-crf` | `18` | Qualité (18-23 = lossless) | Recommandé |
| `-preset` | `fast`/`medium` | Vitesse encodage | Recommandé |

### Pour merge audio/vidéo
| Paramètre | Valeur | Rôle | Obligatoire |
|-----------|--------|------|-------------|
| `-avoid_negative_ts` | `make_zero` | Aligne timestamps au début | ✓ OUI |
| `-vsync` | `cfr` | Maintient CFR | ✓ OUI |
| `-c:v` | `copy` | Pas de ré-encodage vidéo | Recommandé |
| `-c:a` | `aac` | Encoder audio en AAC | ✓ OUI |
| `-b:a` | `192k` | Bitrate audio (qualité) | ✓ OUI |
| `-shortest` | (flag) | Arrête au plus court | Recommandé |

## Workflow complet (Production)

### 1. Vérifier si VFR
```bash
# Comparer r_frame_rate et avg_frame_rate
ffprobe -v error -select_streams v:0 \
  -show_entries stream=r_frame_rate,avg_frame_rate \
  -of csv=p=0 input.mp4

# Si différents → VFR
# Si identiques → CFR
```

### 2. Obtenir avg_frame_rate
```bash
# Extraire avg_frame_rate précis
ffprobe -v error -select_streams v:0 \
  -show_entries stream=avg_frame_rate \
  -of csv=p=0 input.mp4

# Exemple : "24000/1001" → 23.976 fps
```

### 3. Conversion VFR → CFR (si nécessaire)
```bash
# Convertir avec FPS précis
ffmpeg -i input_vfr.mp4 \
  -vsync cfr \
  -r 23.976 \
  -c:v libx264 -preset fast -crf 18 \
  -c:a copy \
  output_cfr.mp4
```

### 4. Traitement avec OpenCV
```python
# Utiliser ffprobe pour FPS (pas OpenCV)
fps = get_accurate_fps(video_path)

# Ouvrir vidéo
cap = cv2.VideoCapture(video_path)

# Traiter frames...
while True:
    ret, frame = cap.read()
    if not ret:
        break
    # Process frame...
    processed_frames.append(processed_frame)

cap.release()

# Écrire avec FPS correct
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('temp_video.mp4', fourcc, fps, (width, height))
for frame in processed_frames:
    out.write(frame)
out.release()
```

### 5. Reconstruction avec audio
```bash
# Merger vidéo + audio avec synchro parfaite
ffmpeg -i temp_video.mp4 -i audio.wav \
  -c:v copy \
  -c:a aac -b:a 192k \
  -avoid_negative_ts make_zero \
  -vsync cfr \
  -shortest \
  final_output.mp4
```

## Vérification finale

### Vérifier le FPS
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=avg_frame_rate,r_frame_rate \
  -of default=noprint_wrappers=1:nokey=1 output.mp4

# Les deux doivent être identiques pour CFR
```

### Vérifier la durée
```bash
# Durée vidéo
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 output.mp4

# Durée audio
ffprobe -v error -select_streams a:0 \
  -show_entries stream=duration \
  -of default=noprint_wrappers=1:nokey=1 output.mp4

# Les deux doivent être identiques (±0.1s)
```

### Vérifier la synchro
```bash
# Jouer la vidéo et vérifier visuellement
ffplay output.mp4

# Vérifier que :
# - Audio et vidéo démarrent ensemble (pas de décalage au début)
# - Synchro maintenue jusqu'à la fin
# - Pas d'effet métallique sur l'audio
# - Vitesse de lecture normale (pas ralentie)
```

## Résumé des changements dans le code

### Fichier modifié : `node/InputNode/node_video.py`

#### 1. Nouvelle méthode `_get_accurate_fps()`
```python
def _get_accurate_fps(self, video_path):
    """Extrait FPS précis avec ffprobe (avg_frame_rate)"""
    # Utilise ffprobe au lieu de OpenCV
    # Retourne le avg_frame_rate réel
```

#### 2. Modification de `_preprocess_video()`
```python
# AVANT (ligne 586)
fps = cap.get(cv2.CAP_PROP_FPS)  # ❌ Non fiable pour VFR

# APRÈS
fps = self._get_accurate_fps(movie_path)  # ✓ FPS précis via ffprobe
if fps is None or fps <= 0:
    fps = cap.get(cv2.CAP_PROP_FPS)  # Fallback OpenCV
    if fps <= 0:
        fps = target_fps  # Ultimate fallback
```

## Impact de la correction

### Avant le fix
- ❌ FPS incorrect → audio chunking incorrect → audio dégradé
- ❌ Vidéo reconstruite avec mauvais FPS → vidéo ralentie
- ❌ Désynchronisation audio/vidéo progressive
- ❌ Audio métallique, effet "robot"

### Après le fix
- ✓ FPS précis extrait avec ffprobe
- ✓ Audio chunking correct → audio de qualité
- ✓ Vidéo reconstruite avec FPS correct → vitesse normale
- ✓ Synchro audio/vidéo parfaite
- ✓ Audio clair, sans distorsion

## Références

### Documentation FFmpeg
- [FFmpeg VFR to CFR](https://trac.ffmpeg.org/wiki/ChangingFrameRate)
- [FFmpeg vsync option](https://ffmpeg.org/ffmpeg.html#Advanced-Video-options)
- [FFmpeg avoid_negative_ts](https://ffmpeg.org/ffmpeg-formats.html#Format-Options)
- [FFprobe documentation](https://ffmpeg.org/ffprobe.html)

### Articles techniques
- [Understanding Variable Frame Rate](https://www.adobe.com/creativecloud/video/discover/variable-frame-rate.html)
- [Audio/Video Synchronization](https://en.wikipedia.org/wiki/Audio_to_video_synchronization)

---

**Date de création** : 2025-12-14  
**Version** : 1.0.0  
**Auteur** : CV Studio Development Team  
**Statut** : Production-ready
