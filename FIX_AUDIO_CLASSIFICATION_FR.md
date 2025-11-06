# Correction du Problème de Classification Audio

## Problème Original

**Question de l'utilisateur** : "Pourquoi je ne détecte que du snore comme classe alors le son est des aboiements, ? est ce qu'il manque de la coloration ?"

**Symptôme** : Les aboiements de chien étaient classifiés comme "Snoring" (ronflement - classe 28) au lieu de "Dog" (chien - classe 0) par le modèle Yolo-cls avec les classes ESC-50.

## Cause du Problème

Le problème était un **décalage entre l'entraînement et l'inférence** :

1. **Modèle entraîné sur** : Spectrogrammes en niveaux de gris (grayscale)
   - Les valeurs de pixels représentent directement l'amplitude/énergie du son
   - Un pixel gris foncé = faible amplitude
   - Un pixel gris clair = forte amplitude

2. **Système utilisait** : Spectrogrammes colorés (colormap INFERNO)
   - Les valeurs de pixels sont transformées en couleurs (violet → jaune)
   - Un pixel peut avoir des valeurs BGR complètement différentes
   - Le modèle ne reconnaît plus les motifs qu'il a appris

3. **Conséquence** : Mauvaise classification
   - L'aboiement de chien devient un motif de couleurs que le modèle n'a jamais vu
   - Le modèle tente de deviner → classe "Snoring" (incorrect!)

## Solution Implémentée

### Changement Principal

**Avant** :
```python
DEFAULT_SPECTROGRAM_COLORMAP = 'INFERNO'  # Coloré (violet-jaune)
```

**Après** :
```python
DEFAULT_SPECTROGRAM_COLORMAP = 'GRAYSCALE'  # Niveaux de gris (noir-blanc)
```

### Logique de Traitement

Ajout d'un mode GRAYSCALE dans `node/InputNode/node_video.py` :

```python
if self._spectrogram_colormap == 'GRAYSCALE':
    # Mode niveaux de gris pour classification audio
    # Normalise à 0-255 (noir à blanc)
    ims_norm = cv2.normalize(ims_transposed, None, 0, 255, cv2.NORM_MINMAX)
    ims_gray = np.clip(ims_norm, 0, 255).astype(np.uint8)
    
    # Retourne en bas, hautes fréquences en haut
    ims_gray = np.flipud(ims_gray)
    
    # Convertit en BGR (3 canaux avec même valeur) pour compatibilité
    S_bgr = cv2.cvtColor(ims_gray, cv2.COLOR_GRAY2BGR)
else:
    # Mode coloré pour visualisation
    S_rgb = apply_colormap_to_spectrogram(...)
    # ...
```

## Réponse à Votre Question

**"Est ce qu'il manque de la coloration ?"**

Excellente intuition ! Mais c'était **l'inverse** du problème :

- ❌ Il y avait **TROP** de coloration (application d'une colormap)
- ✅ Il fallait **MOINS** de coloration (niveaux de gris)

### Pourquoi ?

Les modèles de classification audio (ESC-50, UrbanSound8K, etc.) sont entraînés sur des spectrogrammes en **niveaux de gris**, pas en couleur. Quand on applique une colormap :

1. **Amplitude 50 dB** → Sans colormap : pixel gris (128, 128, 128)
2. **Amplitude 50 dB** → Avec INFERNO : pixel orange (128, 80, 20)

Le modèle a appris que l'aboiement = motif de valeurs autour de 128 (gris moyen) à certaines fréquences. Quand il reçoit (128, 80, 20), il ne reconnaît pas le motif !

## Résultats Attendus

### Avant la Correction
- ❌ Aboiement de chien → Classifié "Snoring" (classe 28)
- ❌ Autres sons aussi mal classifiés
- ❌ Spectrogrammes colorés confondent le modèle

### Après la Correction
- ✅ Aboiement de chien → Devrait être classifié "Dog" (classe 0)
- ✅ Autres sons devraient être correctement classifiés
- ✅ Spectrogrammes en niveaux de gris correspondent aux données d'entraînement

## Utilisation

### Pour la Classification Audio (Par Défaut)

Aucun changement nécessaire ! Le système utilise maintenant des spectrogrammes en niveaux de gris par défaut :

```python
# Connectez simplement la sortie audio du nœud Video au nœud Classification
# Le spectrogramme sera automatiquement en niveaux de gris
```

### Pour la Visualisation (Optionnel)

Si vous préférez des spectrogrammes colorés pour la visualisation :

```python
from node.InputNode.node_video import VideoNode

node = VideoNode()
# Changez pour n'importe quelle colormap pour visualisation
node._spectrogram_colormap = 'INFERNO'  # ou 'VIRIDIS', 'JET', 'MAGMA', etc.
```

## Fichiers Modifiés

1. **`node/InputNode/node_video.py`**
   - Changé `DEFAULT_SPECTROGRAM_COLORMAP` de `'INFERNO'` à `'GRAYSCALE'`
   - Ajouté logique de traitement en niveaux de gris
   - Mis à jour les commentaires

2. **`tests/test_grayscale_spectrogram.py`** (NOUVEAU)
   - Suite de tests complète pour les spectrogrammes en niveaux de gris

3. **`FIX_AUDIO_CLASSIFICATION.md`** (NOUVEAU)
   - Documentation détaillée en anglais

4. **`FIX_AUDIO_CLASSIFICATION_FR.md`** (CE FICHIER)
   - Documentation en français

5. **`tests/demo_grayscale_classification.py`** (NOUVEAU)
   - Script de démonstration

## Test de la Correction

Pour vérifier que la correction fonctionne :

```bash
python tests/test_grayscale_spectrogram.py
```

Tous les tests devraient passer ✓

## Compatibilité

Cette modification est **rétrocompatible** :

- ✅ **Classification Audio** : Précision améliorée (c'était cassé avant)
- ✅ **Visualisation** : Toujours disponible en définissant la colormap
- ⚠️ **Apparence par Défaut** : Les spectrogrammes apparaissent maintenant en niveaux de gris par défaut au lieu de colorés

## Explication Technique

### Classes ESC-50

Le fichier `node/DLNode/classification/esc50_class_names.py` définit 50 classes :

- **Classe 0** : "Dog" (aboiement de chien) ← **Classe correcte**
- **Classe 28** : "Snoring" (ronflement) ← **Classe incorrecte obtenue avant**

### Pourquoi la Mauvaise Classification ?

Le modèle Yolo-cls (`son.onnx`) a été entraîné sur des spectrogrammes ESC-50 en niveaux de gris. Quand on lui donne un spectrogramme coloré :

1. **Apprentissage** : "Dog" = motif de pixels gris avec certaines valeurs à certaines fréquences
2. **Inférence avec colormap** : Pixels transformés en couleurs → motif méconnaissable
3. **Résultat** : Le modèle devine → "Snoring" (mauvais!)

### Avec la Correction

1. **Apprentissage** : "Dog" = motif de pixels gris
2. **Inférence avec niveaux de gris** : Même motif de pixels gris
3. **Résultat** : Le modèle reconnaît → "Dog" (correct!) ✓

## Conclusion

La correction change la représentation par défaut des spectrogrammes de colorée (colormap INFERNO) à niveaux de gris pour correspondre à ce qu'attendent les modèles de classification audio.

**Votre intuition était bonne** - vous avez posé la bonne question sur la "coloration". Le problème était qu'il y avait **trop** de coloration (application d'une colormap) alors que le modèle attendait des **niveaux de gris** !

---

**Mis à jour** : Novembre 2024  
**Problème** : Aboiement de chien mal classifié comme ronflement  
**Solution** : Utiliser des spectrogrammes en niveaux de gris pour la classification audio
