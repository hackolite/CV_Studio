# Verification MOT Node - CID et TID en JSON

## Résumé

Ce document vérifie que le nœud MOT (Module de Tracking / Multiple Object Tracking) fonctionne correctement et effectue le suivi des objets en affichant les **CID** (Class ID) et **TID** (Track ID) avec les données servies en output au format **JSON**.

## Vérification Effectuée

✅ **Le nœud MOT fonctionne correctement**  
✅ **Le tracking est opérationnel**  
✅ **Les CID et TID sont inclus dans l'output JSON**  
✅ **Le format JSON est correct et complet**

## Structure de l'Output JSON

Le nœud MOT (fichier: `node/TrackerNode/node_mot.py`) retourne un JSON via **Output03** avec la structure suivante:

```json
{
  "track_ids": ["0_1", "0_2"],          // TID: Track IDs (identifiants de tracking)
  "bboxes": [[100, 100, 200, 250], ...], // Boîtes englobantes [x1, y1, x2, y2]
  "scores": [0.95, 0.88],                // Scores de confiance
  "class_ids": [0, 0],                   // CID: Class IDs (identifiants de classe)
  "class_names": ["person", "person"],   // Noms des classes
  "track_id_dict": {"0_1": 0, "0_2": 1}  // Mapping des track IDs
}
```

### Champs du JSON

| Champ | Description | Type |
|-------|-------------|------|
| **`track_ids`** | **TID** - Identifiants de tracking persistants pour chaque objet tracké | `List[str/int]` |
| **`class_ids`** | **CID** - Identifiants de classe pour chaque objet (0=person, 1=ball, etc.) | `List[int]` |
| `bboxes` | Coordonnées des boîtes englobantes `[x1, y1, x2, y2]` | `List[List[float]]` |
| `scores` | Scores de confiance de détection | `List[float]` |
| `class_names` | Noms lisibles des classes | `List[str]` |
| `track_id_dict` | Mapping des track IDs vers les indices d'affichage | `Dict[int, int]` |

## Fonctionnalités Vérifiées

### 1. Tracking Persistant (TID)

Les **Track IDs (TID)** restent constants à travers les frames pour le même objet:

```
Frame 1: TID = [0_1, 0_2]  (2 personnes détectées)
Frame 2: TID = [0_1, 0_2]  (mêmes personnes, TIDs maintenus) ✓
Frame 3: TID = [0_1, 0_2, 0_3]  (nouvelle personne = nouveau TID)
```

### 2. Identification des Classes (CID)

Les **Class IDs (CID)** identifient le type d'objet détecté:

```json
{
  "class_ids": [0, 0, 1, 1],
  "class_names": ["person", "person", "ball", "ball"]
}
```

- CID=0 → person
- CID=1 → ball
- etc.

### 3. Multi-Class Tracking

Le nœud MOT supporte le tracking multi-classes:

```
Objet 1: TID=0, CID=0 (person)
Objet 2: TID=1, CID=0 (person)
Objet 3: TID=2, CID=1 (ball)
Objet 4: TID=3, CID=1 (ball)
```

## Scripts de Vérification

Deux scripts ont été créés pour vérifier le fonctionnement:

### 1. Script de Vérification Complet
```bash
python tests/verify_mot_tracking_json.py
```

Ce script vérifie:
- ✅ Fonctionnement correct du tracking MOT
- ✅ Persistence des TIDs à travers les frames
- ✅ Inclusion des CIDs dans le JSON
- ✅ Format JSON complet et correct
- ✅ Tracking multi-classes

### 2. Démonstration Interactive
```bash
python tests/demo_mot_json_cid_tid.py
```

Ce script démontre:
- Le tracking sur plusieurs frames
- L'affichage des TID et CID pour chaque objet
- Le format JSON complet de l'output

## Affichage Visuel

En plus de l'output JSON, le nœud MOT affiche visuellement sur l'image:

```python
# Sur l'image, chaque objet tracké affiche:
TID:0(0.95)     # Track ID avec score
CID:0(person)   # Class ID avec nom de classe
```

Cette information est dessinée via la méthode `draw_multi_object_tracking_info()` dans `node/basenode.py` (lignes 926-984).

## Logging Ajouté

Un logging debug a été ajouté dans `node_mot.py` pour afficher l'output JSON:

```python
logger.debug(f"MOT JSON Output - Node {node_id}:")
logger.debug(f"  Track IDs (TID): {track_ids}")
logger.debug(f"  Class IDs (CID): {class_ids}")
logger.debug(f"  Class Names: {class_names}")
```

Pour activer le logging debug:
```bash
export LOG_LEVEL=DEBUG
```

## Tests Existants

Les tests suivants vérifient déjà le fonctionnement:

- `tests/test_mot_json_output.py` - Vérifie la structure JSON
- `tests/test_mot_json_input.py` - Vérifie les entrées JSON
- `tests/test_tracking_nodes.py` - Vérifie tous les trackers

## Conclusion

✅ **VÉRIFIÉ**: Le nœud MOT fonctionne correctement et effectue le suivi des objets  
✅ **VÉRIFIÉ**: Les CID (Class ID) sont inclus dans l'output JSON  
✅ **VÉRIFIÉ**: Les TID (Track ID) sont inclus dans l'output JSON  
✅ **VÉRIFIÉ**: Le format JSON est correct et complet  
✅ **VÉRIFIÉ**: L'affichage visuel montre TID et CID sur l'image  

Le module de tracking MOT est opérationnel et fournit bien les données CID et TID au format JSON via Output03.
