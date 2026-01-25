# Diagramme du Flux d'Adaptation du Dropdown d'Exclusion

## Vue d'Ensemble

Le dropdown d'exclusion s'adapte automatiquement au modèle sélectionné dans trois scénarios clés :

```
┌─────────────────────────────────────────────────────────────────┐
│                  SCENARIOS D'ADAPTATION                         │
└─────────────────────────────────────────────────────────────────┘

1. CRÉATION DU NODE
   ↓
   ┌──────────────────────────────────────────┐
   │ add_node() est appelé                    │
   │ ├─ Récupère le modèle par défaut         │
   │ ├─ Charge les labels du modèle           │
   │ └─ Crée le dropdown avec ces labels      │
   └──────────────────────────────────────────┘
   ↓
   Dropdown initialisé avec: "0: person", "1: bicycle", etc.


2. CHANGEMENT DE MODÈLE (Runtime)
   ↓
   ┌──────────────────────────────────────────┐
   │ Utilisateur change le modèle via UI      │
   │         ↓                                 │
   │ on_model_change() callback déclenché     │
   │ ├─ Récupère les labels du nouveau modèle │
   │ ├─ Met à jour les items du dropdown      │
   │ └─ Vide la sélection actuelle            │
   └──────────────────────────────────────────┘
   ↓
   Dropdown mis à jour avec les labels du nouveau modèle


3. CHARGEMENT DE CONFIGURATION SAUVEGARDÉE
   ↓
   ┌──────────────────────────────────────────┐
   │ set_setting_dict() est appelé            │
   │ ├─ Charge le modèle depuis les settings  │
   │ ├─ Récupère les labels de ce modèle      │
   │ ├─ Met à jour les items du dropdown      │
   │ └─ Applique la sélection sauvegardée     │
   └──────────────────────────────────────────┘
   ↓
   Dropdown adapté au modèle chargé
```

## Fonction Centrale

```
get_class_rejection_dropdown_items(class_name_dict)
    ↓
┌─────────────────────────────────────────┐
│ Entrée: {0: 'person', 1: 'bicycle', ...}│
│         ↓                                │
│ Trie les class_id                       │
│         ↓                                │
│ Formate: "class_id: class_name"         │
│         ↓                                │
│ Retourne: ["0: person", "1: bicycle"]   │
└─────────────────────────────────────────┘
```

## Modèles Supportés et Leurs Labels

```
┌──────────────────────────────────────────────────────────┐
│ MODÈLE                        │ LABELS                   │
├──────────────────────────────────────────────────────────┤
│ YOLOX-Nano/Tiny/S             │ coco_class_names         │
│ FreeYOLO-Nano                 │ (80 classes: person,     │
│ YOLO11Nano                    │  bicycle, car, ...)      │
├──────────────────────────────────────────────────────────┤
│ Light-Weight Person Detector  │ coco_class_names_        │
│ FreeYOLO-Nano-CrowdHuman     │ only_person              │
│                               │ (1 classe: person)       │
├──────────────────────────────────────────────────────────┤
│ YOLOTENNIS                    │ coco_class_names_tennis  │
│                               │ (3 classes: player1,     │
│                               │  player2, ball)          │
└──────────────────────────────────────────────────────────┘
```

## Flux de Validation

```
Détection d'objets
    ↓
┌──────────────────────────────────────┐
│ Récupère rejected_classes_str        │
│ Format: "0: person" ou "0,1,2"       │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ Parse les class_ids rejetés          │
│ Extrait: {0, 1, 2}                   │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ Valide contre le modèle actuel       │
│ valid_class_ids = {0, 1, 2}          │
│ (pour tennis model)                  │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ Filtre les class_ids invalides       │
│ rejected_classes &= valid_class_ids  │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ Applique le filtre d'exclusion       │
│ keep_mask = class_id not in rejected │
└──────────────────────────────────────┘
    ↓
Détections filtrées transmises au reste du workflow
```

## Exemple Complet: Passage de COCO à Tennis

```
ÉTAT INITIAL: YOLOX-Nano (COCO, 80 classes)
┌────────────────────────────────────────────┐
│ Dropdown d'exclusion:                      │
│ ┌────────────────────────────────────────┐ │
│ │ "0: person"                            │ │
│ │ "1: bicycle"                           │ │
│ │ "2: car"                               │ │
│ │ ...                                    │ │
│ │ "79: toothbrush"                       │ │
│ └────────────────────────────────────────┘ │
│ Sélectionné: "0: person, 1: bicycle"       │
└────────────────────────────────────────────┘

↓ Utilisateur change le modèle → YOLOTENNIS

CALLBACK: on_model_change() déclenché
┌────────────────────────────────────────────┐
│ 1. selected_model = "YOLOTENNIS"           │
│ 2. class_names = coco_class_names_tennis   │
│    {0: 'player1', 1: 'player2', 2: 'ball'} │
│ 3. class_items = get_class_rejection_      │
│    dropdown_items(class_names)             │
│    → ["0: player1", "1: player2",          │
│       "2: ball"]                            │
│ 4. dpg.configure_item(..., items=...)      │
│ 5. dpg_set_value(..., "")  # Vide sélection│
└────────────────────────────────────────────┘

↓

ÉTAT FINAL: YOLOTENNIS (3 classes)
┌────────────────────────────────────────────┐
│ Dropdown d'exclusion:                      │
│ ┌────────────────────────────────────────┐ │
│ │ "0: player1"                           │ │
│ │ "1: player2"                           │ │
│ │ "2: ball"                              │ │
│ └────────────────────────────────────────┘ │
│ Sélectionné: (vide)                        │
└────────────────────────────────────────────┘
```

## Points Clés de l'Implémentation

1. **Synchronisation Automatique**: Le dropdown se met à jour automatiquement
2. **Validation des Classes**: Les class_ids invalides sont filtrés
3. **Réinitialisation Intelligente**: La sélection est vidée lors du changement de modèle
4. **Formats Supportés**: 
   - Format dropdown: "0: person"
   - Format legacy: "0,1,2"
5. **Gestion d'Erreurs**: Try/except pour gérer les cas où l'UI n'existe pas encore

## Fichiers Impliqués

```
node/DLNode/node_object_detection.py
├─ get_class_rejection_dropdown_items()  [ligne 27]
├─ on_model_change()                     [ligne 80]
├─ add_node() - Initialisation           [ligne 206]
└─ set_setting_dict() - Chargement       [ligne 587]

node/DLNode/object_detection/
├─ coco_class_names.py          (80 classes)
├─ coco_class_names_only_person.py  (1 classe)
└─ coco_class_names_tennis.py   (3 classes)

tests/
└─ test_exclusion_dropdown_model_adaptation.py
```
