# Guide Visuel : DearPyGui Node Editor avec Combo Coloré

## Vue d'ensemble

Ce document présente visuellement les fonctionnalités de l'exemple **dearpygui_node_editor_colored_combo_example.py**.

## Architecture du Code

```
main()
│
├─ dpg.create_context()
│   └─ Initialise DearPyGui
│
├─ setup_gui()
│   ├─ Créer thèmes pour tous les domaines
│   │   ├─ create_combo_theme("Vision", blue)
│   │   ├─ create_combo_theme("Audio", purple)
│   │   └─ create_combo_theme("Network", orange)
│   │
│   ├─ Créer fenêtre principale
│   │   ├─ Combo box de sélection
│   │   ├─ Texte d'information
│   │   └─ Node Editor (avec minimap)
│   │
│   └─ update_node_display()
│       └─ Créer 3 nodes avec thème du domaine actuel
│
├─ dpg.create_viewport()
│   └─ Fenêtre 1024x768
│
├─ dpg.start_dearpygui()
│   └─ Boucle principale
│
└─ dpg.destroy_context()
    └─ Nettoyage
```

## Flux de Données

```
Utilisateur sélectionne domaine
           ↓
    on_domain_change()
           ↓
    ┌──────┴──────┐
    ↓             ↓
Créer nouveau  update_node_display()
   thème            ↓
    ↓          Supprimer anciens nodes
    ↓               ↓
Appliquer      Créer nouveaux nodes
au combo            ↓
              Appliquer thème nodes
```

## Fonction brighter()

Transforme une couleur en version plus claire :

```python
# Entrée : (70, 130, 180, 255)  # Bleu
# Sortie : (91, 169, 234, 255)  # Bleu plus clair

Calcul : R_new = min(255, int(R * 1.3))
         G_new = min(255, int(G * 1.3))
         B_new = min(255, int(B * 1.3))
         A_new = A (inchangé)
```

### Exemple pour le domaine Vision

```
Base   : (70,  130, 180, 255) ████ Bleu standard
Hover  : (84,  156, 216, 255) ████ Bleu plus clair (hover)
Active : (98,  182, 251, 255) ████ Bleu très clair (actif)
Dark   : (49,   91, 125, 255) ████ Bleu foncé (fond node)
```

## Thèmes Combo Box

Chaque domaine a son propre thème pour le combo box :

```python
with dpg.theme(tag="combo_theme_Vision"):
    with dpg.theme_component(dpg.mvCombo):
        # Fond du combo (base color)
        mvThemeCol_FrameBg → (70, 130, 180, 255)
        
        # Fond au survol (hover color)
        mvThemeCol_FrameBgHovered → (84, 156, 216, 255)
        
        # Fond actif (active color)
        mvThemeCol_FrameBgActive → (98, 182, 251, 255)
        
        # Fond du popup (liste déroulante)
        mvThemeCol_PopupBg → (70, 130, 180, 255)
        
        # Texte blanc pour contraste
        mvThemeCol_Text → (255, 255, 255, 255)
```

## Thèmes Nodes

Chaque node utilise la couleur de son domaine :

```python
with dpg.theme(tag="node_theme_Vision"):
    with dpg.theme_component(dpg.mvNode):
        # Fond du node (dark color)
        mvNodeCol_NodeBackground → (49, 91, 125, 255)
        
        # Fond au survol
        mvNodeCol_NodeBackgroundHovered → (70, 130, 180, 255)
        
        # Fond sélectionné
        mvNodeCol_NodeBackgroundSelected → (70, 130, 180, 255)
        
        # Barre de titre
        mvNodeCol_TitleBar → (70, 130, 180, 255)
        
        # Barre de titre survol
        mvNodeCol_TitleBarHovered → (84, 156, 216, 255)
        
        # Barre de titre sélection
        mvNodeCol_TitleBarSelected → (91, 169, 234, 255)
```

## Domaines et Couleurs

### 1. Vision (Bleu Acier)

```
Couleur : (70, 130, 180, 255) ████

Nodes :
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Camera Input    │  │ Image Processing │  │ Object Detection │
├─────────────────┤  ├──────────────────┤  ├──────────────────┤
│ ● Input 1       │  │ ● Input 2        │  │ ● Input 3        │
│               ● │  │                ● │  │                ● │
│ Output 1        │  │ Output 2         │  │ Output 3         │
└─────────────────┘  └──────────────────┘  └──────────────────┘
```

### 2. Audio (Violet)

```
Couleur : (144, 70, 180, 255) ████

Nodes :
┌──────────────────┐  ┌───────────────────┐  ┌──────────────┐
│ Microphone Input │  │ Audio Processing  │  │ Spectrogram  │
├──────────────────┤  ├───────────────────┤  ├──────────────┤
│ ● Input 1        │  │ ● Input 2         │  │ ● Input 3    │
│                ● │  │                 ● │  │            ● │
│ Output 1         │  │ Output 2          │  │ Output 3     │
└──────────────────┘  └───────────────────┘  └──────────────┘
```

### 3. Network (Orange/Marron)

```
Couleur : (180, 100, 70, 255) ████

Nodes :
┌──────────────┐  ┌──────────────┐  ┌─────────────┐
│ HTTP Request │  │ WebSocket    │  │ Data Parser │
├──────────────┤  ├──────────────┤  ├─────────────┤
│ ● Input 1    │  │ ● Input 2    │  │ ● Input 3   │
│            ● │  │            ● │  │           ● │
│ Output 1     │  │ Output 2     │  │ Output 3    │
└──────────────┘  └──────────────┘  └─────────────┘
```

## Interactions Utilisateur

### Étape 1 : Sélection du domaine

```
┌──────────────────────────────────┐
│ Sélectionner : [Vision ▼] ← Clic │
└──────────────────────────────────┘
```

### Étape 2 : Affichage du menu

```
┌──────────────────────────────────┐
│ Sélectionner : [Vision  ]        │
│                ┌────────────────┐ │
│                │ Vision    ████ │ │ ← Bleu
│                │ Audio     ████ │ │ ← Violet
│                │ Network   ████ │ │ ← Orange
│                └────────────────┘ │
└──────────────────────────────────┘
```

### Étape 3 : Survol d'une option

```
┌──────────────────────────────────┐
│ Sélectionner : [Vision  ]        │
│                ┌────────────────┐ │
│                │ Vision    ████ │ │
│                │ Audio     ████ │ │ ← Plus clair
│                │ Network   ████ │ │
│                └────────────────┘ │
└──────────────────────────────────┘
```

### Étape 4 : Sélection confirmée

```
┌──────────────────────────────────┐
│ Sélectionner : [Audio ▼] ← Violet│
└──────────────────────────────────┘
                ↓
        Nodes changent !
```

## Système de Callbacks

```python
# 1. Utilisateur sélectionne "Audio"
dpg.add_combo(..., callback=on_domain_change)

# 2. Callback déclenché
def on_domain_change(sender, app_data, user_data):
    # app_data = "Audio"
    current_domain = app_data
    
    # 3. Créer nouveau thème
    domain_color = (144, 70, 180, 255)  # Violet
    theme_tag = create_combo_theme("Audio", domain_color)
    
    # 4. Appliquer au combo
    dpg.bind_item_theme("domain_combo", theme_tag)
    
    # 5. Mettre à jour les nodes
    update_node_display()
```

## Mise à Jour des Nodes

```python
def update_node_display():
    # 1. Nettoyer
    for old_node in existing_nodes:
        dpg.delete_item(old_node)
    
    # 2. Obtenir nouvelle config
    domain_color = DOMAINS[current_domain]["color"]
    nodes = DOMAINS[current_domain]["nodes"]
    
    # 3. Créer nouveau thème
    node_theme = create_node_theme(current_domain, domain_color)
    
    # 4. Créer nouveaux nodes
    for node_name in nodes:
        with dpg.node(label=node_name):
            # Attributs input/output
            ...
        dpg.bind_item_theme(node_tag, node_theme)
```

## Avantages de Cette Architecture

### ✅ Séparation des Préoccupations

- **Thèmes** : Gérés séparément (create_combo_theme, create_node_theme)
- **Données** : Centralisées dans DOMAINS
- **UI** : Construite dans setup_gui()
- **Logique** : Callbacks isolés

### ✅ Réutilisabilité

```python
# Facile d'ajouter un nouveau domaine
DOMAINS["MonDomaine"] = {
    "color": (R, G, B, 255),
    "nodes": ["Node1", "Node2", "Node3"]
}
# Tout le reste fonctionne automatiquement !
```

### ✅ Maintenabilité

- Un seul endroit pour modifier les couleurs (DOMAINS)
- Thèmes créés dynamiquement
- Pas de duplication de code

### ✅ Extensibilité

```python
# Ajouter plus de propriétés
DOMAINS["Vision"] = {
    "color": (70, 130, 180, 255),
    "nodes": [...],
    "icon": "🎥",           # Nouveau !
    "description": "..."    # Nouveau !
}
```

## Utilisations Potentielles

1. **Système de Catégories** : Différents types de nodes avec identification visuelle
2. **Filtrage Visuel** : Masquer/afficher nodes par domaine
3. **Workflow Guidé** : Suggérer nodes selon le contexte
4. **Documentation Interactive** : Expliquer chaque domaine
5. **Gestion de Complexité** : Organiser grands projets

## Exécution

```bash
# Depuis le répertoire racine
python examples/dearpygui_node_editor_colored_combo_example.py

# Ou tests unitaires
python tests/test_dearpygui_example.py
```

## Résultat Attendu

L'application affiche une fenêtre avec :
- ✅ Combo box coloré selon domaine sélectionné
- ✅ Liste déroulante avec items colorés
- ✅ Hover effect sur les items (plus clair)
- ✅ Node editor avec 3 nodes
- ✅ Nodes colorés selon domaine
- ✅ Minimap en bas à droite
- ✅ Changement dynamique lors de la sélection

---

**Note** : Ce guide est une documentation technique du code. Pour l'utilisation pratique, voir [examples/README.md](README.md).
