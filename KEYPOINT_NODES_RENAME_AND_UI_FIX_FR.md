# Résumé des Modifications - Nœuds Keypoint et Correctif UI

## Problèmes Résolus

Ce PR résout trois problèmes énoncés dans l'issue :

1. **Renommage `Trigger/KeypointDeviation` → `Court/KeypointDeviation`**
2. **Renommage `DataProcess/Keypoints` → `Court/KeypointData`**
3. **Correction du bug UI : impossible de créer de nouvelles fenêtres ou faire des liens pendant la lecture vidéo**

## Changements de Code

### 1. Renommage des Nœuds

**Fichier : `node/TriggerNode/node_trigger_keypoint_deviation.py`**
- Changement de `node_label = 'Trigger/KeypointDeviation'` 
- À `node_label = 'Court/KeypointDeviation'`

**Fichier : `node/StatsNode/node_dataprocessing_keypoints.py`**
- Changement de `node_label = 'DataProcess/Keypoints'`
- À `node_label = 'Court/KeypointData'`

**Tests Mis à Jour**
- `tests/test_keypoints_nodes.py` : Correction des imports et assertions

### 2. Correction du Bug de Threading UI

**Problème Identifié**
Lorsque la vidéo joue, deux threads accèdent simultanément à DearPyGUI :
- **Thread principal** : Traite les événements UI via `dpg.start_dearpygui()`
- **Thread worker** : Met à jour les nœuds en continu via `async_main()` dans un thread executor

Cela causait des conditions de course qui empêchaient l'UI de répondre aux actions utilisateur.

**Solution Implémentée**

Ajout d'un verrou thread-safe (`threading.RLock`) partagé pour sérialiser tous les accès à DearPyGUI :

**Fichier : `node_editor/util.py`**
```python
import threading
# Verrou global pour opérations thread-safe DearPyGUI
_dpg_lock = threading.RLock()

def dpg_set_value(tag, value):
    with _dpg_lock:
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, value)

def dpg_get_value(tag):
    value = None
    with _dpg_lock:
        if dpg.does_item_exist(tag):
            value = dpg.get_value(tag)
    return value
```

**Fichier : `node_editor/node_editor.py`**
- Import du verrou partagé : `from .util import _dpg_lock`
- Protection de `_callback_add_node` avec `with _dpg_lock:`
- Protection de `_callback_link` avec `with _dpg_lock:`

## Détails Techniques

### Pourquoi RLock au lieu de Lock ?

`RLock` (Reentrant Lock) permet au même thread d'acquérir le verrou plusieurs fois, ce qui est nécessaire quand des appels DearPyGUI imbriqués se produisent dans le même thread.

### Scénarios Protégés

1. **Ajout de nœuds** : Lorsque l'utilisateur clique sur un menu pour ajouter un nœud pendant que async_main met à jour les nœuds existants
2. **Création de liens** : Lorsque l'utilisateur crée des connexions entre nœuds pendant que les valeurs sont mises à jour
3. **Lecture/écriture de valeurs** : Tous les appels dpg_get_value/dpg_set_value sont maintenant thread-safe

## Tests

### Nouveau Test : `tests/test_threading_lock.py`
Vérifie que :
- ✅ Le verrou `_dpg_lock` existe et est de type RLock
- ✅ `dpg_set_value` utilise le verrou
- ✅ `dpg_get_value` utilise le verrou
- ✅ `_callback_add_node` utilise le verrou
- ✅ `_callback_link` utilise le verrou

### Validation
- ✅ Tous les tests passent
- ✅ Validation syntaxe Python
- ✅ CodeQL : 0 vulnérabilité détectée

## Impact

### Avant
- ❌ UI bloquée pendant la lecture vidéo
- ❌ Impossible d'ajouter des nœuds
- ❌ Impossible de créer des liens
- ❌ Conditions de course possibles

### Après
- ✅ UI responsive même pendant la lecture vidéo
- ✅ Ajout de nœuds possible en tout temps
- ✅ Création de liens sans blocage
- ✅ Accès thread-safe à DearPyGUI

## Rétrocompatibilité

Ces modifications sont 100% rétrocompatibles :
- Les `node_tag` restent inchangés (seuls les `node_label` sont modifiés)
- Les fichiers JSON existants continueront de fonctionner
- Aucun changement d'API
- Comportement identique, juste plus stable

## Résumé Sécurité

**CodeQL Scan** : 0 alerte
- Aucune vulnérabilité introduite
- Utilisation appropriée des primitives de synchronisation
- Pas de fuites de ressources
- Gestion d'erreurs préservée
