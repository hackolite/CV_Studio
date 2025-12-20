# YouTube Timestamp Management Implementation

## Résumé / Summary

**FR**: Implémentation de la gestion des timestamps basés sur le FPS pour le noeud d'entrée YouTube. Les timestamps sont générés automatiquement (frame_number / fps) et se propagent automatiquement à travers les noeuds de traitement et de vision vers le VideoWriter qui utilise le FPS configuré (24 FPS par défaut).

**EN**: Implementation of FPS-based timestamp management for the YouTube input node. Timestamps are automatically generated (frame_number / fps) and automatically propagate through processing and vision nodes to VideoWriter which uses the configured FPS (default 24 FPS).

## Problème Résolu / Problem Solved

### Demande Originale / Original Request
"rajoute la gestion du timestamp sur les frame en input sur le node d'input youtube, cette donnée non modifiée doit suivre sur les noeuds de type visionprocessing et visionmodele, et vérifie que le fps lors de la création de la video est adaptée au fps choisi par default 24 FPS, aide toi du timestamp. et utilise la méthode la plus robuste pour la stabilité du software"

### Traduction / Translation
Add timestamp management on input frames in the YouTube input node, this unmodified data must follow through vision processing and vision model nodes, and verify that the FPS during video creation is adapted to the chosen FPS by default 24 FPS, use the timestamp. Use the most robust method for software stability.

## Solution Implémentée / Implemented Solution

### 1. Gestion des Timestamps YouTube / YouTube Timestamp Management

**Ajout d'État / State Added:**
```python
self._frame_count = {}      # Track frame number per node
self._stream_fps = {}       # Track FPS from stream
self._stream_start_time = {} # Track stream start time
```

**Génération de Timestamp / Timestamp Generation:**
```python
# Calculate FPS-based timestamp
frame_timestamp = frame_count / stream_fps

# Example at 24 FPS:
# Frame 1 = 0.0417 seconds
# Frame 24 = 1.0 second
# Frame 48 = 2.0 seconds
```

**Retour des Données / Data Return:**
```python
return {
    "image": frame,
    "json": None,
    "audio": None,
    "timestamp": frame_timestamp  # FPS-based timestamp
}
```

### 2. Propagation Automatique / Automatic Propagation

Les timestamps se propagent automatiquement via `main.py` (lignes 161-188):

**Pour les noeuds d'entrée avec timestamp explicite / For input nodes with explicit timestamp:**
```python
node_provided_timestamp = data.get("timestamp", None)
if node_provided_timestamp is not None:
    node_image_dict.set_with_timestamp(node_id_name, data["image"], node_provided_timestamp)
```

**Pour les noeuds de traitement / For processing nodes:**
```python
if has_data_input and source_timestamp is not None:
    # Preserve source timestamp automatically
    node_image_dict.set_with_timestamp(node_id_name, data["image"], source_timestamp)
```

### 3. VideoWriter et FPS / VideoWriter and FPS

**Configuration FPS / FPS Configuration:**
```python
# VideoWriter uses configured FPS (default 24 FPS)
writer_fps = self._FPS_MAP.get(fps_text, 24)

video_writer = cv2.VideoWriter(
    file_path,
    cv2.VideoWriter_fourcc(*codec),
    writer_fps,  # Uses configured FPS
    (writer_width, writer_height)
)
```

**Note Importante / Important Note:**
Selon `TIMESTAMP_REMOVAL_CHANGES.md`, les timestamps sont à titre indicatif seulement. La création vidéo est basée sur l'accumulation des frames et le FPS configuré, pas sur les timestamps.

According to `TIMESTAMP_REMOVAL_CHANGES.md`, timestamps are informational only. Video creation is based on frame accumulation and configured FPS, not timestamps.

## Architecture Robuste / Robust Architecture

### 1. Isolation d'État / State Isolation
Chaque instance de noeud a son propre état (dictionnaire par node_id).
Each node instance has its own state (dictionary by node_id).

### 2. Gestion des Erreurs / Error Handling
```python
try:
    stream_fps = self.cap.get(cv2.CAP_PROP_FPS)
    if stream_fps > 0:
        self._stream_fps[node_id] = stream_fps
    else:
        self._stream_fps[node_id] = 24.0  # Fallback
except (cv2.error, AttributeError) as e:
    self._stream_fps[node_id] = 24.0  # Fallback
```

### 3. Nettoyage Approprié / Proper Cleanup
```python
def close(self, node_id):
    # Clean up all state
    node_id_str = str(node_id)
    self._frame_count.pop(node_id_str, None)
    self._stream_start_time.pop(node_id_str, None)
    self._stream_fps.pop(node_id_str, None)
    # ... etc
```

### 4. Valeurs par Défaut / Default Values
- **FPS par défaut / Default FPS:** 24.0
- **Comportement si FPS indisponible / Behavior if FPS unavailable:** Utilise 24.0 / Uses 24.0
- **Comportement si pas de frame / Behavior if no frame:** timestamp = None (main.py crée un nouveau / main.py creates new)

## Tests / Testing

### Tests Unitaires / Unit Tests (6/6 ✅)
- `test_timestamp_initialization`: Vérification de l'initialisation
- `test_timestamp_calculation`: Précision du calcul
- `test_different_fps_values`: Support de différents FPS
- `test_update_return_format`: Format de retour
- `test_cleanup_on_close`: Nettoyage approprié
- `test_timestamp_consistency`: Cohérence séquentielle

### Tests End-to-End (7/7 ✅)
- `test_youtube_generates_timestamp`: Génération YouTube
- `test_processing_node_format`: Format noeuds de traitement
- `test_vision_model_node_format`: Format noeuds de vision
- `test_videowriter_fps_configuration`: Configuration FPS VideoWriter
- `test_timestamp_propagation_logic`: Logique de propagation
- `test_fps_timestamp_relationship`: Relation FPS-timestamp
- `test_robustness_features`: Fonctionnalités de robustesse

### Tests Existants (6/6 ✅)
- Validation des URLs YouTube (tous passent)

**Total: 19/19 tests passent ✅**

## Vérification de Sécurité / Security Verification

**CodeQL Scan:** 0 alertes / 0 alerts ✅

Aucune vulnérabilité de sécurité détectée.
No security vulnerabilities detected.

## Flux de Données / Data Flow

```
┌─────────────────┐
│  YouTube Node   │
│  (Input)        │
│                 │
│ Generate:       │
│ timestamp =     │
│ frame_num / fps │
└────────┬────────┘
         │ timestamp: 0.0417s (frame 1 @ 24 FPS)
         ▼
┌─────────────────┐
│ ProcessNode     │
│ (e.g., Blur)    │
│                 │
│ main.py         │
│ preserves       │
│ source          │
│ timestamp       │
└────────┬────────┘
         │ timestamp: 0.0417s (preserved)
         ▼
┌─────────────────┐
│ DLNode          │
│ (e.g., YOLO)    │
│                 │
│ main.py         │
│ preserves       │
│ source          │
│ timestamp       │
└────────┬────────┘
         │ timestamp: 0.0417s (preserved)
         ▼
┌─────────────────┐
│ VideoWriter     │
│ (Output)        │
│                 │
│ Uses FPS: 24    │
│ (configured)    │
│ Timestamp:      │
│ informational   │
└─────────────────┘
```

## Avantages / Benefits

1. **Cohérence / Consistency:** Timestamps basés sur FPS, pas sur le temps d'exécution
2. **Robustesse / Robustness:** Gestion d'erreurs appropriée, valeurs par défaut
3. **Automatique / Automatic:** Propagation automatique via main.py
4. **Testé / Tested:** Couverture de tests complète (19/19)
5. **Sécurisé / Secure:** Aucune vulnérabilité (CodeQL: 0 alertes)
6. **Maintenable:** Code clair avec commentaires explicatifs

## Compatibilité / Compatibility

✅ **Rétrocompatible / Backward Compatible:** Tous les tests existants passent
✅ **Suit le Patron Existant / Follows Existing Pattern:** Même approche que le noeud Video
✅ **S'Intègre au Système / Integrates with System:** Utilise le système de propagation existant de main.py

## Fichiers Modifiés / Modified Files

1. **node/InputNode/node_youtube.py**
   - Ajout de la gestion des timestamps
   - Amélioration de la gestion des erreurs
   - Commentaires explicatifs

2. **tests/test_youtube_timestamp_management.py** (nouveau / new)
   - Tests unitaires complets

3. **tests/test_timestamp_propagation_e2e.py** (nouveau / new)
   - Tests end-to-end complets

## Documentation Additionnelle / Additional Documentation

Voir aussi / See also:
- `TIMESTAMP_REMOVAL_CHANGES.md`: Contexte sur l'utilisation des timestamps
- `node/InputNode/node_video.py`: Implémentation de référence similaire

## Conclusion

L'implémentation est complète, testée, sécurisée et robuste. Elle suit les meilleures pratiques du projet et s'intègre naturellement au système existant.

The implementation is complete, tested, secure and robust. It follows project best practices and integrates naturally with the existing system.
