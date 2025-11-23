# ESC-50 Classification - Reference Amplitude Fix

## Problème Résolu ✅

L'utilisateur a signalé que la classification ESC-50 ne fonctionnait toujours pas bien malgré les corrections précédentes. Après une analyse approfondie du code d'entraînement fourni, j'ai identifié **une différence critique dans l'amplitude de référence** utilisée pour la conversion en décibels.

## Cause Racine

### Le Problème

Le code d'entraînement de l'utilisateur (qui fonctionne parfaitement) utilise :

```python
ims = 20.*np.log10(np.abs(sshow)/10e-6)
```

Mais le code du dépôt utilisait :

```python
REFERENCE_AMPLITUDE = 1e-6  # INCORRECT !
ims = 20. * np.log10(np.abs(S_log) / REFERENCE_AMPLITUDE)
```

### Impact de cette Différence

**Valeurs numériques :**
- `1e-6` = 0.000001
- `10e-6` = 0.00001 (10 fois plus grand)

**Décalage en décibels :**
```
20 * log10(10e-6 / 1e-6) = 20 * log10(10) = 20 dB
```

**Conséquence :** Un décalage de **20 dB** sur tout le spectrogramme !

### Pourquoi c'est Critique

1. **Le modèle YOLO-cls a été entraîné** sur des spectrogrammes générés avec `10e-6`
2. **L'échelle d'amplitude affecte** la luminosité et le contraste du spectrogramme
3. **Un décalage de 20 dB** change radicalement l'apparence visuelle
4. **Les modèles CNN** (comme YOLO-cls) sont sensibles à ces changements de contraste
5. **Résultat :** Le modèle reçoit des données avec une échelle différente de celle de l'entraînement → mauvaise précision

## Solution Appliquée

### Changement de Code

**Fichier : `node/InputNode/spectrogram_utils.py`**

```python
# AVANT (INCORRECT)
# Reference amplitude for dB conversion (1 micropascal)
REFERENCE_AMPLITUDE = 1e-6

# APRÈS (CORRECT)
# Reference amplitude for dB conversion (matching ESC-50 training code)
# Note: Using 10e-6 (which equals 1e-5) to match the original ESC-50 training implementation
REFERENCE_AMPLITUDE = 10e-6
```

Cette constante est importée et utilisée dans :
- `node/AudioProcessNode/node_spectrogram.py`
- `node/InputNode/spectrogram_utils.py` (fonction `create_spectrogram_from_audio`)

### Paramètres Validés

Tous les paramètres correspondent maintenant **exactement** au code d'entraînement ESC-50 :

| Paramètre | Code Entraînement | Code Repo (Après Fix) | Status |
|-----------|-------------------|----------------------|--------|
| Sample Rate | 44100 Hz | 44100 Hz | ✅ |
| FFT Window | 1024 | 1024 | ✅ |
| Log Scale Factor | 1.0 | 1.0 | ✅ |
| **Reference Amplitude** | **10e-6** | **10e-6** | ✅ **CORRIGÉ** |
| Colormap | JET | JET | ✅ |
| Format Image | BGR | BGR | ✅ |

## Tests et Validation ✅

### Test Créé

**`tests/test_reference_amplitude_fix.py`**

Ce test vérifie :
1. ✅ `REFERENCE_AMPLITUDE = 10e-6` (valeur correcte)
2. ✅ Différence de 20 dB entre ancienne et nouvelle valeur
3. ✅ Import correct dans `spectrogram_utils.py`
4. ✅ Import correct dans `node_spectrogram.py`
5. ✅ Génération de spectrogrammes fonctionnelle
6. ✅ Compatibilité complète avec le code d'entraînement

### Test Mis à Jour

**`tests/test_node_video_spectrogram.py`**
- Mis à jour pour vérifier `sr=44100` au lieu de `sr=22050`

### Résultats des Tests

```bash
$ python tests/test_reference_amplitude_fix.py
✓ ALL REFERENCE AMPLITUDE TESTS PASSED!

$ python tests/test_esc50_bgr_format.py
✓ ALL ESC-50 CLASSIFICATION TESTS PASSED!

$ python tests/test_node_video_spectrogram.py
✓ All tests passed successfully!
```

## Impact Attendu

### Avant le Fix
- **Amplitude de référence** : `1e-6` (INCORRECT)
- **Échelle dB** : Décalée de -20 dB par rapport à l'entraînement
- **Spectrogrammes** : Trop sombres/contrastés différemment
- **Précision de classification** : MAUVAISE ❌
- **Raison** : Le modèle voit des données d'échelle différente

### Après le Fix
- **Amplitude de référence** : `10e-6` (CORRECT)
- **Échelle dB** : Correspond exactement à l'entraînement
- **Spectrogrammes** : Apparence identique aux données d'entraînement
- **Précision de classification** : DEVRAIT ÊTRE BONNE ✅
- **Raison** : Le modèle voit des données d'échelle identique à l'entraînement

### Explication Visuelle de l'Impact

```
Spectrogramme avec REFERENCE_AMPLITUDE = 1e-6 (ANCIEN):
┌────────────────────────────────────────┐
│ Valeurs dB trop basses (-20 dB offset) │
│ Image trop sombre                       │
│ Contraste différent                     │
│ ❌ Modèle confus                        │
└────────────────────────────────────────┘

Spectrogramme avec REFERENCE_AMPLITUDE = 10e-6 (NOUVEAU):
┌────────────────────────────────────────┐
│ Valeurs dB correctes                   │
│ Luminosité correcte                    │
│ Contraste identique à l'entraînement   │
│ ✅ Modèle performant                   │
└────────────────────────────────────────┘
```

## Pipeline de Génération Complet

```
Fichier Vidéo
    ↓
[FFmpeg] Extraction Audio à 44100 Hz
    ↓
Chunks de 5 secondes (WAV, 44100 Hz)
    ↓
[STFT] n_fft=1024, overlap=0.5
    ↓
[Log Scale] factor=1.0
    ↓
[Conversion dB] 20*log10(magnitude / 10e-6)  ← FIX ICI
    ↓
[Normalisation] 0-255
    ↓
[Colormap JET] BGR format
    ↓
Spectrogramme → YOLO-cls → Classification ✅
```

## Historique des Fixes ESC-50

### Fix #1 : Sample Rate (44100 Hz)
- **Problème** : Audio rééchantillonné à 22050 Hz
- **Solution** : Utiliser 44100 Hz (natif ESC-50)
- **Impact** : Préserve toute la bande de fréquence (0-22050 Hz)

### Fix #2 : Format Couleur (BGR)
- **Problème** : Conversion BGR→RGB inutile
- **Solution** : Retourner BGR directement (compatible OpenCV/YOLO)
- **Impact** : Canaux de couleur corrects pour le modèle

### Fix #3 : Amplitude de Référence (10e-6) ← **CE FIX**
- **Problème** : Référence `1e-6` au lieu de `10e-6`
- **Solution** : Changer `REFERENCE_AMPLITUDE = 10e-6`
- **Impact** : Échelle dB correcte, spectrogrammes identiques à l'entraînement

## Compatibilité

### Rétrocompatibilité

✅ **Compatible avec** :
- Toutes les sources vidéo (fichiers, webcam, RTSP)
- Tous les taux d'échantillonnage (ffmpeg rééchantillonne automatiquement)
- Autres modèles de classification (traitent les spectrogrammes comme des images)

⚠️ **Note pour les modèles personnalisés** :
Si vous avez entraîné des modèles sur des spectrogrammes générés avec `REFERENCE_AMPLITUDE = 1e-6`, vous devrez soit :
1. Les réentraîner avec `10e-6` (recommandé pour ESC-50)
2. Temporairement revenir à `1e-6` pour ces modèles spécifiques

Pour la classification ESC-50, ce fix est **essentiel et doit être conservé**.

## Fichiers Modifiés

| Fichier | Type | Changement |
|---------|------|-----------|
| `node/InputNode/spectrogram_utils.py` | Code | `1e-6` → `10e-6` (1 ligne) |
| `tests/test_reference_amplitude_fix.py` | Test | NOUVEAU (224 lignes) |
| `tests/test_node_video_spectrogram.py` | Test | Mise à jour (1 ligne) |
| `REFERENCE_AMPLITUDE_FIX.md` | Doc | NOUVEAU (ce fichier) |

**Total** : 1 ligne de code modifiée, 225 lignes de tests ajoutées

## Conclusion

Le problème de classification ESC-50 était causé par un **décalage de 20 dB dans l'échelle d'amplitude** des spectrogrammes. Le code d'entraînement utilisait `10e-6` comme amplitude de référence, mais le dépôt utilisait `1e-6`.

**Ce fix minimal (1 ligne)** aligne maintenant parfaitement le code du dépôt avec le code d'entraînement ESC-50.

### Récapitulatif des 3 Fixes Essentiels

```
1. Sample Rate:     22050 Hz → 44100 Hz  (Fix précédent)
2. Color Format:    RGB      → BGR       (Fix précédent)
3. Ref Amplitude:   1e-6     → 10e-6     (CE FIX)
```

Avec ces trois corrections, le pipeline de génération de spectrogrammes correspond **exactement** au code d'entraînement ESC-50 de l'utilisateur.

**La classification ESC-50 devrait maintenant fonctionner beaucoup mieux ! 🎵✨**

## Références

- Code d'entraînement ESC-50 de l'utilisateur
- Dataset ESC-50 : https://github.com/karoldvl/ESC-50
- Tutoriel de référence : https://mpolinowski.github.io/docs/IoT-and-Machine-Learning/ML/2023-09-23--yolo8-listen/2023-09-23/

## Auteurs

- Fix identifié et implémenté par : GitHub Copilot Agent
- Problème signalé par : hackolite
- Code d'entraînement de référence fourni par : hackolite
