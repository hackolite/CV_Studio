# Exemples DearPyGui

Ce dossier contient des exemples d'utilisation de DearPyGui dans le contexte de CV Studio.

## dearpygui_node_editor_colored_combo_example.py

### Description

Exemple complet qui démontre :

1. **Une fenêtre avec un node editor** - Interface de node editor pour visualiser et manipuler des nodes
2. **Un mvCombo (droplist)** - Permet de sélectionner un "domaine" parmi plusieurs options
3. **Couleurs par domaine** - Chaque domaine a une couleur spécifique pour ses nodes
4. **Background coloré** - Le background du combo reflète la couleur du domaine sélectionné
5. **Liste déroulante colorée** - Les éléments de la liste ont leur fond coloré avec éclaircissement au survol
6. **Thèmes dynamiques** - Création dynamique de thèmes pour chaque sélection
7. **Fonction brighter()** - Fonction utilitaire pour éclaircir les couleurs (effet hover)
8. **Trois domaines** - Trois domaines avec couleurs différentes et trois nodes fictifs par domaine

### Domaines disponibles

- **Vision** (Bleu acier) : Camera Input, Image Processing, Object Detection
- **Audio** (Violet) : Microphone Input, Audio Processing, Spectrogram
- **Network** (Orange/Marron) : HTTP Request, WebSocket, Data Parser

### Exécution

```bash
# Depuis le répertoire racine du projet
python examples/dearpygui_node_editor_colored_combo_example.py

# Ou directement
./examples/dearpygui_node_editor_colored_combo_example.py
```

### Prérequis

- Python 3.7+
- dearpygui >= 1.11.0

Si DearPyGui n'est pas installé :

```bash
pip install dearpygui
```

### Fonctionnalités démontrées

#### 1. Fonction `brighter(color_tuple)`

Cette fonction prend un tuple RGBA (0-255) et renvoie un tuple un peu plus clair :

```python
def brighter(color_tuple, factor=1.3):
    """
    Prend un tuple RGBA (0-255) et renvoie un tuple un peu plus clair.
    
    Args:
        color_tuple: Tuple de 4 entiers (R, G, B, A) entre 0-255
        factor: Facteur d'éclaircissement (> 1 pour éclaircir)
    
    Returns:
        Tuple RGBA plus clair, plafonné à 255
    """
    r, g, b, a = color_tuple
    r = min(255, int(r * factor))
    g = min(255, int(g * factor))
    b = min(255, int(b * factor))
    return (r, g, b, a)
```

#### 2. Thèmes pour combo box

La fonction `create_combo_theme()` crée un thème personnalisé pour le combo box avec :
- Couleur de fond correspondant au domaine
- Couleur hover (plus claire)
- Couleur active (encore plus claire)
- Couleur du popup (liste déroulante)
- Texte en blanc pour le contraste

#### 3. Thèmes pour nodes

La fonction `create_node_theme()` crée un thème pour les nodes avec :
- Couleur de fond (version sombre de la couleur du domaine)
- Couleur hover et selected (versions plus claires)
- Barre de titre colorée

#### 4. Callback de changement de domaine

Le callback `on_domain_change()` :
- Met à jour le domaine sélectionné
- Crée et applique un nouveau thème au combo box
- Met à jour l'affichage des nodes

#### 5. Mise à jour dynamique des nodes

La fonction `update_node_display()` :
- Supprime les nodes existants
- Crée de nouveaux nodes pour le domaine sélectionné
- Applique le thème correspondant à chaque node

### Structure du code

```
main()
├── dpg.create_context()
├── setup_gui()
│   ├── Créer les thèmes pour tous les domaines
│   ├── Créer la fenêtre principale
│   ├── Ajouter le combo box de sélection
│   ├── Ajouter le node editor
│   └── update_node_display()
├── dpg.create_viewport()
├── dpg.setup_dearpygui()
├── dpg.show_viewport()
├── dpg.start_dearpygui()
└── dpg.destroy_context()
```

### Aperçu visuel

Lorsque vous exécutez l'exemple, vous verrez :
- Une fenêtre avec un combo box en haut
- Le combo box a un fond coloré selon le domaine sélectionné
- En dessous, un node editor avec trois nodes
- Les nodes ont la même couleur que le domaine
- En changeant le domaine dans le combo box, les couleurs et les nodes changent

```
┌─────────────────────────────────────────────────────────────┐
│ Node Editor avec Combo Coloré                          [x]  │
├─────────────────────────────────────────────────────────────┤
│ Sélectionner un domaine : [Vision ▼]  ← Fond bleu          │
│─────────────────────────────────────────────────────────────│
│ Les nodes ci-dessous appartiennent au domaine sélectionné. │
│ Changez le domaine pour voir différentes couleurs.         │
│─────────────────────────────────────────────────────────────│
│                                                             │
│  ┌────────────────┐  ┌──────────────────┐  ┌──────────┐   │
│  │ Camera Input   │  │ Image Processing │  │ Object   │   │
│  │ (Bleu)         │  │ (Bleu)           │  │Detection │   │
│  ├────────────────┤  ├──────────────────┤  ├──────────┤   │
│  │ ● Input 1      │  │ ● Input 2        │  │ ● Input 3│   │
│  │              ● │  │                ● │  │        ● │   │
│  │ Output 1       │  │ Output 2         │  │ Output 3 │   │
│  └────────────────┘  └──────────────────┘  └──────────┘   │
│                                                             │
│                                            [Minimap]        │
└─────────────────────────────────────────────────────────────┘
```

**Interaction :**
- Cliquez sur le combo box pour voir les trois domaines (Vision, Audio, Network)
- Survolez les options : elles deviennent plus claires
- Sélectionnez un domaine : les nodes changent de nom et de couleur

### Personnalisation

Pour ajouter un nouveau domaine :

```python
DOMAINS = {
    "Vision": {
        "color": (70, 130, 180, 255),  # Steel Blue
        "nodes": ["Camera Input", "Image Processing", "Object Detection"]
    },
    # Ajoutez votre domaine ici
    "MonDomaine": {
        "color": (R, G, B, 255),  # Votre couleur
        "nodes": ["Node 1", "Node 2", "Node 3"]
    }
}
```

### Notes techniques

- Les couleurs sont définies en RGBA avec des valeurs de 0 à 255
- Les thèmes DearPyGui utilisent `dpg.mvThemeCat_Core` pour les widgets et `dpg.mvThemeCat_Nodes` pour les nodes
- Le node editor inclut une minimap en bas à droite pour la navigation
- Les nodes ont des attributs d'entrée et de sortie (non fonctionnels dans cet exemple)

## Licence

Ce code d'exemple est fourni sous la même licence que le projet CV Studio (Apache 2.0).
