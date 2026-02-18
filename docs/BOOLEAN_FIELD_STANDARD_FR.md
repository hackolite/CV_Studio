# Standard du Champ Booléen pour les Nœuds CV Studio

## Vue d'ensemble

Ce document décrit le format standardisé du champ booléen utilisé dans les nœuds CV Studio pour les nœuds de déclenchement, de routage et d'action.

## Format Standard

Tous les nœuds de déclenchement et de routage **DOIVENT** produire du JSON dans le format suivant :

```json
{
  "BOOL": true
}
```

ou

```json
{
  "BOOL": false
}
```

### Exigences Clés

1. **Nom du Champ**: Le champ DOIT s'appeler `"BOOL"` (tout en majuscules)
2. **Type de Valeur**: La valeur DOIT être un booléen (`true` ou `false`), pas :
   - Entier (0 ou 1)
   - Chaîne ("true" ou "false")
   - None/null
   - Tout autre type
3. **Présence**: Le champ DOIT être présent dans le JSON de sortie

## Catégories de Nœuds

### Nœuds de Déclenchement (Producteurs)

Les nœuds de déclenchement détectent des conditions et produisent des signaux booléens.

**Nœuds Standardisés:**
- **ObjDetCount**: Produit `{"BOOL": trigger_active}` basé sur les seuils de comptage d'objets
- **Boolean Inverter**: Produit `{"BOOL": not input_bool}` pour inverser l'entrée
- **Keypoint Deviation**: Ajoute `output_json['BOOL'] = trigger_state` à sa sortie

**Exemple d'Implémentation:**
```python
# Dans la méthode update() du nœud de déclenchement
trigger_active = self.check_condition()  # Retourne True ou False
output_json = {"BOOL": trigger_active}
return {"image": None, "json": output_json, "audio": None}
```

### Nœuds de Routage (Processeurs)

Les nœuds de routage reçoivent des signaux booléens, appliquent une logique et produisent des signaux booléens.

**Nœuds Standardisés:**
- **SimpleRouter**: Produit `{"BOOL": trigger_active}` basé sur la logique de combinaison

**Exemple d'Implémentation:**
```python
# Dans la méthode update() du nœud de routage
# Lire le BOOL d'entrée
input_bool = False
if node_result and isinstance(node_result, dict):
    if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
        input_bool = node_result['BOOL']

# Appliquer la logique du routeur
trigger_active = self.apply_logic(input_bool)
output_json = {"BOOL": trigger_active}
return {"image": None, "json": output_json, "audio": None}
```

### Nœuds d'Action (Consommateurs)

Les nœuds d'action reçoivent des signaux booléens et effectuent des actions lorsqu'ils sont déclenchés.

**Nœuds Standardisés:**
- **VideoRecorder**: Vérifie le champ `BOOL` pour démarrer/arrêter l'enregistrement
- **Buzzer**: Vérifie le champ `BOOL` pour jouer un son

**Ordre de Priorité pour VideoRecorder:**
1. Champ `BOOL` (standard, priorité la plus élevée)
2. Champ `record` (support hérité)
3. Champ `trigger` (support hérité)
4. N'importe quel champ booléen avec la valeur `true` (solution de repli)

**Exemple d'Implémentation:**
```python
# Dans la méthode update() du nœud d'action
should_activate = False
if trigger_json and isinstance(trigger_json, dict):
    # Priorité: BOOL > champs hérités
    if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
        should_activate = trigger_json['BOOL']
    elif 'record' in trigger_json and isinstance(trigger_json['record'], bool):
        # Compatibilité ascendante
        should_activate = trigger_json['record']
    # ... autres champs hérités

if should_activate:
    self.perform_action()
```

## Avantages de la Standardisation

1. **Cohérence**: Tous les nœuds utilisent le même nom de champ et type
2. **Sécurité de Type**: La validation booléenne prévient les erreurs dues à des valeurs non-booléennes
3. **Clarté**: Signification sémantique claire (BOOL pour l'état de déclenchement booléen)
4. **Compatibilité Ascendante**: Les nœuds d'action supportent toujours les noms de champs hérités
5. **Intégration Facile**: Les nœuds de différentes catégories fonctionnent ensemble de manière transparente

## Tests

### Tests Unitaires

Chaque type de nœud doit avoir des tests vérifiant :
- La sortie contient le champ `BOOL`
- La valeur `BOOL` est de type booléen
- La valeur `BOOL` reflète correctement l'état du nœud

### Tests d'Intégration

Les tests de pipeline doivent vérifier :
- Le flux Déclenchement → Routeur → Action fonctionne correctement
- `BOOL=true` déclenche les actions
- `BOOL=false` ne déclenche pas les actions
- Sécurité de type (les valeurs non-booléennes sont rejetées)

**Exemple de Test:**
```python
def test_trigger_router_recorder_pipeline():
    # Le déclencheur produit
    trigger_output = {"BOOL": True}
    
    # Le routeur traite et produit
    router_output = {"BOOL": True}
    
    # L'enregistreur reçoit et agit
    should_record = False
    if 'BOOL' in router_output and isinstance(router_output['BOOL'], bool):
        should_record = router_output['BOOL']
    
    assert should_record == True
```

## Guide de Migration

### Pour les Développeurs de Nœuds de Déclenchement/Routage

Si votre nœud produit actuellement un format différent :

**Ancien Format:**
```python
return {"image": None, "json": {"trigger": True}, "audio": None}
```

**Nouveau Format:**
```python
return {"image": None, "json": {"BOOL": True}, "audio": None}
```

### Pour les Développeurs de Nœuds d'Action

Ajoutez le support du champ `BOOL` avec la priorité la plus élevée :

```python
should_activate = False
if trigger_json and isinstance(trigger_json, dict):
    # NOUVEAU: Vérifier d'abord le champ BOOL
    if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
        should_activate = trigger_json['BOOL']
    # HÉRITÉ: Conserver le support des anciens champs
    elif 'your_legacy_field' in trigger_json:
        should_activate = trigger_json['your_legacy_field']
```

## Pièges Courants

### ❌ Incorrect: Utiliser un entier au lieu d'un booléen
```python
output_json = {"BOOL": 1}  # FAUX!
```

### ✅ Correct: Utiliser un booléen
```python
output_json = {"BOOL": True}  # CORRECT!
```

### ❌ Incorrect: Utiliser une chaîne
```python
output_json = {"BOOL": "true"}  # FAUX!
```

### ✅ Correct: Utiliser un booléen
```python
output_json = {"BOOL": True}  # CORRECT!
```

### ❌ Incorrect: Ne pas vérifier le type
```python
if trigger_json['BOOL']:  # FAUX! Pourrait être non-booléen
    activate()
```

### ✅ Correct: Vérifier le type
```python
if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
    if trigger_json['BOOL']:  # CORRECT! Sécurisé en type
        activate()
```

## Problème Résolu

Ce standard résout le problème de cohérence entre :
- **Le booléen JSON sorti par le trigger** : ✅ Utilise `{"BOOL": true/false}`
- **Le booléen JSON sorti par le router** : ✅ Utilise `{"BOOL": true/false}`
- **Les actionneurs (notamment le video recorder)** : ✅ Comprend et active correctement quand `BOOL` est `true`

**Vérification:**
Quand `BOOL` est `true`, le video recorder :
1. ✅ Détecte le champ `BOOL`
2. ✅ Vérifie que la valeur est un booléen
3. ✅ Active l'enregistrement quand la valeur est `true`
4. ✅ N'active pas l'enregistrement quand la valeur est `false`

## Tests Associés

- `tests/test_bool_field_standardization.py` - Tests unitaires pour la gestion du champ booléen
- `tests/test_trigger_router_recorder_integration.py` - Tests d'intégration pour le pipeline complet
- `test_bool_consistency.py` - Vérification complète de la cohérence

## Questions?

Pour des questions sur le standard du champ booléen, veuillez consulter :
- Cette documentation
- Les fichiers de tests listés ci-dessus
- Les implémentations d'exemple dans les nœuds standardisés
