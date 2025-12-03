# Node SyncQueue - Guide Visuel (Français)

## Description

Le node SyncQueue est un node système qui permet de synchroniser des données provenant de plusieurs queues. Chaque "Add Slot" crée une entrée et un point de sortie associé.

## Fonctionnalités

### Ajout Dynamique de Slots
- Bouton "Add Slot" pour créer des paires entrée/sortie dynamiquement
- Maximum de 10 slots par instance de node
- Chaque slot supporte les types IMAGE, JSON et AUDIO

### Synchronisation des Queues
- Récupère les éléments des queues connectées
- Synchronise les données basées sur les timestamps
- Intégration avec le système de queues horodatées existant

## Apparence du Node

### État Initial (0 slots)
```
┌─────────────────────────┐
│      SyncQueue          │
├─────────────────────────┤
│  [Add Slot]  Slots: 0   │
└─────────────────────────┘
```

### Après Ajout de 1 Slot
```
┌─────────────────────────┐
│      SyncQueue          │
├─────────────────────────┤
│ ○ In1: Image      ○     │  ← Entrée/Sortie IMAGE
│ ○ In1: JSON       ○     │  ← Entrée/Sortie JSON
│ ○ In1: Audio      ○     │  ← Entrée/Sortie AUDIO
├─────────────────────────┤
│  [Add Slot]  Slots: 1   │
└─────────────────────────┘
```

### Après Ajout de 3 Slots
```
┌─────────────────────────┐
│      SyncQueue          │
├─────────────────────────┤
│ ○ In1: Image      ○     │  ← Slot 1
│ ○ In1: JSON       ○     │
│ ○ In1: Audio      ○     │
│ ○ In2: Image      ○     │  ← Slot 2
│ ○ In2: JSON       ○     │
│ ○ In2: Audio      ○     │
│ ○ In3: Image      ○     │  ← Slot 3
│ ○ In3: JSON       ○     │
│ ○ In3: Audio      ○     │
├─────────────────────────┤
│  [Add Slot]  Slots: 3   │
└─────────────────────────┘
```

## Localisation dans le Menu

Le node SyncQueue se trouve dans le menu principal :

```
Barre de Menu CV_STUDIO
├── File
│   ├── Export
│   └── Import
├── Input
├── VisionProcess
├── VisionModel
├── AudioProcess
├── AudioModel
├── DataProcess
├── DataModel
├── Trigger
├── Router
├── Action
├── Overlay
├── Tracking
├── Visual
├── Video
└── System              ← NOUVELLE CATÉGORIE
    └── SyncQueue       ← NOUVEAU NODE
```

## Utilisation

### Création d'un Slot
1. Cliquez sur "Add Slot"
2. Trois entrées sont créées (IMAGE, JSON, AUDIO)
3. Trois sorties correspondantes sont créées
4. Le compteur de slots s'incrémente

### Connexion des Données
1. Connectez les nodes sources aux entrées du slot
2. Les données circulent et apparaissent sur les sorties correspondantes
3. Chaque entrée a une sortie associée pour le routage

### Exemple : Synchronisation Multi-Caméras
```
┌──────────┐           ┌─────────────────┐         ┌──────────┐
│ Caméra 1 │──IMAGE──→ │ ○ In1: Image  ○ │──IMAGE→ │ Affichage│
└──────────┘           │ ○ In1: JSON   ○ │         └──────────┘
                       │ ○ In1: Audio  ○ │
┌──────────┐           │                 │         ┌──────────┐
│ Caméra 2 │──IMAGE──→ │ ○ In2: Image  ○ │──IMAGE→ │ Sauveg.  │
└──────────┘           │ ○ In2: JSON   ○ │         └──────────┘
                       │ ○ In2: Audio  ○ │
┌──────────┐           │   SyncQueue     │
│ Caméra 3 │──IMAGE──→ │ ○ In3: Image  ○ │──IMAGE→ ...
└──────────┘           │ ○ In3: JSON   ○ │
                       │ ○ In3: Audio  ○ │
                       │  [Add Slot]     │
                       └─────────────────┘
```

## Flux de Données

```
Source Externe
      ↓
   [Queue] ← Système de Queues Horodatées
      ↓
Attribut d'Entrée (○)
      ↓
Traitement du Node SyncQueue
  - Récupération depuis la queue
  - Synchronisation des timestamps
  - Transmission des données
      ↓
Attribut de Sortie (○)
      ↓
Node Suivant
```

## Types de Connexion

### Connexions IMAGE
- Entrée : Accepte les données image depuis caméra, processeur, ou modèle
- Sortie : Fournit les données image synchronisées avec aperçu texture
- Affichage : Miniature dans le node

### Connexions JSON
- Entrée : Accepte les métadonnées JSON de toute source
- Sortie : Fournit les données JSON synchronisées
- Affichage : Aperçu texte tronqué

### Connexions AUDIO
- Entrée : Accepte les flux de données audio
- Sortie : Fournit les données audio synchronisées
- Affichage : Étiquette texte uniquement

## Caractéristiques Techniques

### Propriétés du Node
- **Label** : SyncQueue
- **Tag** : SyncQueue
- **Slots Maximum** : 10
- **Types Supportés** : IMAGE, JSON, AUDIO

### Méthodes Principales
- `update()` : Traite les connexions et synchronise les données
- `close()` : Nettoyage à la suppression du node
- `_add_slot()` : Ajoute une nouvelle paire entrée/sortie
- `get_setting_dict()` : Sauvegarde la configuration
- `set_setting_dict()` : Restaure la configuration

## Cas d'Usage

1. **Synchronisation Multi-Caméras**
   - Synchronise les frames de plusieurs entrées caméra
   - Assure l'alignement temporel des flux vidéo

2. **Agrégation de Données**
   - Collecte les données JSON de plusieurs nodes d'analyse
   - Centralise les métadonnées pour traitement ultérieur

3. **Mixage Audio**
   - Route plusieurs flux audio à travers un point central
   - Permet la synchronisation audio multi-sources

4. **Gestion de Workflow**
   - Coordonne le flux de données entre pipelines de traitement
   - Gère les dépendances complexes de graphes de nodes

## Limitations

- Maximum 10 slots par instance de node
- Les données sont transmises sans modification
- La synchronisation est basée sur le système de queues horodatées

## Éléments Interactifs

1. **Bouton Add Slot**
   - Étiquette : "Add Slot"
   - Action : Crée une nouvelle paire de slots entrée/sortie
   - Actif : Quand slots < 10
   - Inactif : Quand slots = 10 (maximum atteint)

2. **Texte de Statut**
   - Format : "Slots: N"
   - Mise à jour : Après chaque ajout de slot
   - Plage : 0-10

3. **Connecteurs d'Entrée (○)**
   - Côté gauche du node
   - Point de connexion pour les données entrantes
   - Trois par slot (IMAGE, JSON, AUDIO)

4. **Connecteurs de Sortie (○)**
   - Côté droit du node
   - Point de connexion pour les données sortantes
   - Trois par slot (IMAGE, JSON, AUDIO)

## Implémentation

Le node SyncQueue utilise le système de queues horodatées existant pour :
- Récupérer les données avec leurs timestamps
- Synchroniser les flux de données multiples
- Maintenir l'ordre temporel des événements

Chaque slot créé génère automatiquement :
- 3 attributs d'entrée (un par type de données)
- 3 attributs de sortie (un par type de données)
- Un point de sortie associé à chaque entrée

Cette implémentation répond exactement à l'exigence :
> "créer une tab système dans laquelle on met un node sync_queue, cette queue fait du add slot, 
> va chercher les éléments dans les queues et synchronise chaque add slot crée une entrée, 
> et on doit avoir un point de sortie associé"
