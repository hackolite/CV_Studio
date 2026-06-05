# 🧠 Distillation de connaissances — Nœud OnlineTraining

> Entraînement en temps réel par distillation teacher-student pour la détection d'objets.

---

## Table des matières

1. [Concept](#concept)
2. [Architecture](#architecture)
3. [Utilisation](#utilisation)
4. [Score de distillation](#score-de-distillation)
5. [Interface utilisateur](#interface-utilisateur)
6. [Fichiers source](#fichiers-source)
7. [Prérequis](#prérequis)
8. [FAQ](#faq)

---

## Concept

La **distillation de connaissances** (knowledge distillation) est une technique où un petit modèle (l'**élève** / student) apprend à reproduire les prédictions d'un modèle plus gros et plus performant (le **professeur** / teacher).

Dans CV Studio, le nœud **OnlineTraining** implémente cette technique en temps réel :

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   Image source  │──────▶│ ObjectDetection  │──────▶│ OnlineTraining  │
│  (Video/Caméra) │       │  (Professeur)    │       │   (Élève)       │
└─────────────────┘       └──────────────────┘       └─────────────────┘
         │                                                     │
         └──────────────── IMAGE ─────────────────────────────▶│
                                    JSON (prédictions prof.) ──▶│
                                                               │
                                              IMAGE (annotée) ◀─┘
                                              JSON (prédictions élève) ◀─┘
```

**Objectif** : L'élève converge progressivement vers les performances du professeur tout en restant plus léger et rapide.

---

## Architecture

### Composants principaux

| Fichier | Rôle |
|---------|------|
| `node/DLNode/node_online_training.py` | Nœud principal (UI DearPyGUI + logique de pipeline) |
| `node/DLNode/online_training/student_trainer.py` | Gestionnaire du cycle de vie de l'élève (inférence, scoring, entraînement) |
| `node/DLNode/online_training/distillation_loss.py` | Fonctions de perte et score de distillation (IoU, matching, F1) |
| `node/DLNode/online_training/models/` | Répertoire de stockage des modèles élèves |

### Flux de données par frame

```
1. Réception de l'image (input IMAGE)
2. Réception du JSON du professeur (input JSON) : {bboxes, scores, class_ids}
3. Inférence de l'élève sur l'image → prédictions student
4. Calcul du score de distillation (teacher vs student)
5. [Si ORT Training disponible] Rétropropagation et mise à jour des poids
6. Affichage : bounding boxes élève (vert) + professeur (bleu)
7. Sortie : IMAGE annotée + JSON des prédictions élève
```

### Modes de fonctionnement

| Mode | Condition | Comportement |
|------|-----------|--------------|
| **Inférence seule** | `onnxruntime` standard | L'élève infère et est scoré, mais ses poids ne changent pas |
| **Entraînement complet** | `onnxruntime-training` installé | Rétropropagation active, les poids sont mis à jour à chaque frame |

---

## Utilisation

### Pipeline minimal

1. **Ajouter un nœud source** (Video ou Caméra)
2. **Ajouter un nœud ObjectDetection** (professeur) — chargez un modèle performant (ex: YOLO11-L)
3. **Ajouter un nœud OnlineTraining**
4. **Connecter** :
   - Sortie IMAGE de la source → Entrée IMAGE de OnlineTraining
   - Sortie JSON de ObjectDetection → Entrée "Teacher JSON" de OnlineTraining
5. **Charger un modèle élève** : cliquez "Load Student ONNX" et sélectionnez un petit modèle ONNX (ex: YOLO11-N)
6. **Lancer** le pipeline — le score de distillation s'affiche en temps réel

### Exporter le modèle entraîné

Cliquez **"Export Student ONNX"** pour sauvegarder l'état courant du modèle élève. Ce fichier ONNX peut ensuite être utilisé directement dans le nœud ObjectDetection.

### Réinitialiser

Cliquez **"Reset Student"** pour restaurer les poids originaux du modèle élève.

---

## Score de distillation

Le score mesure la similarité entre les prédictions du professeur et celles de l'élève. Il est calculé à chaque frame.

### Métriques retournées

| Métrique | Description |
|----------|-------------|
| `score` | Score global [0, 1] — 1.0 = correspondance parfaite |
| `matched_count` | Nombre de détections correctement appariées |
| `missed_count` | Détections du professeur non trouvées par l'élève (faux négatifs) |
| `false_positive_count` | Détections de l'élève sans correspondance chez le professeur |
| `avg_iou` | IoU moyen des paires appariées |
| `avg_score_diff` | Différence moyenne de confiance entre paires |
| `class_accuracy` | Fraction des paires ayant la bonne classe |

### Algorithme de calcul

1. **Matching** : Les détections élève sont appariées aux détections professeur par IoU greedy (seuil par défaut : 0.5)
2. **Rappel** : `matched / total_teacher`
3. **Précision** : `matched / total_student`
4. **Qualité** : `avg_iou × class_accuracy`
5. **Score final** : `F1 × (0.7 + 0.3 × qualité)`

```python
F1 = 2 × precision × recall / (precision + recall)
score = F1 × (0.7 + 0.3 × quality)  # bonus qualité
```

### Loss de distillation *set-based* (DETR-style)

En complément du score `[0, 1]`, une **loss de distillation set-based** est
calculée : matching hongrois (`cost = (1-IoU) + class_cost`), puis box
regression (L1 + 1-IoU), distillation de classe, cardinalité `|N_s - N_t|`,
pénalités faux positifs / faux négatifs et mismatch de classe. Elle est exposée
sous `distillation_losses` (affichable dans le nœud **Chart**) et sert de signal
d'entraînement quand `onnxruntime-training` est disponible. Voir
**[`distillation_loss.md`](distillation_loss.md)** pour la description complète
de la méthode et des métriques.

---

## Interface utilisateur

Le nœud OnlineTraining expose les contrôles suivants :

| Contrôle | Description |
|----------|-------------|
| **score_th** (slider) | Seuil de confiance minimum pour les prédictions de l'élève (0.0–1.0) |
| **learning_rate** (slider) | Taux d'apprentissage (0.00001–0.01) |
| **Training Active** (checkbox) | Active/désactive l'entraînement (l'inférence continue) |
| **Score display** | Affiche : score courant, moyenne, meilleur score |
| **Stats display** | Affiche : nombre de frames traitées, état de l'entraînement |
| **Load Student ONNX** (bouton jaune) | Charger un modèle ONNX élève |
| **Export Student ONNX** (bouton vert) | Exporter le modèle courant |
| **Reset Student** (bouton) | Réinitialiser aux poids originaux |

### Visualisation

- **Vert** : Bounding boxes de l'élève (avec label et score)
- **Bleu** : Bounding boxes du professeur (référence)
- **Jaune (overlay)** : Score de distillation + statistiques

---

## Fichiers source

```
node/DLNode/
├── node_online_training.py          # Nœud principal
└── online_training/
    ├── __init__.py
    ├── student_trainer.py           # Classe StudentTrainer
    ├── distillation_loss.py         # Calcul du score de distillation
    └── models/                      # Modèles élèves stockés
```

### StudentTrainer — API principale

```python
class StudentTrainer:
    def __init__(self, model_path, input_width, input_height, output_format, num_classes, learning_rate, score_threshold, providers)
    def infer(self, frame) -> (bboxes, scores, class_ids)
    def train_step(self, frame, teacher_bboxes, teacher_scores, teacher_class_ids, score_threshold) -> dict
    def reset(self)              # Restaure les poids originaux
    def export_onnx(self, path)  # Exporte le modèle courant
    def get_stats(self) -> dict  # Statistiques d'entraînement
```

### distillation_loss — Fonctions

```python
def compute_iou(box_a, box_b) -> float
def match_detections(teacher_bboxes, teacher_scores, student_bboxes, student_scores, iou_threshold=0.5)
def compute_distillation_score(teacher_bboxes, teacher_scores, teacher_class_ids, student_bboxes, student_scores, student_class_ids, iou_threshold=0.5) -> dict
```

---

## Prérequis

### Minimum (inférence seule)

```bash
pip install onnxruntime numpy opencv-python
```

### Complet (avec entraînement)

```bash
pip install onnxruntime-training numpy opencv-python
```

> **Note** : Sans `onnxruntime-training`, le nœud fonctionne en mode inférence seule — l'élève est évalué mais ses poids ne sont pas mis à jour.

### Modèles compatibles

Le modèle élève doit être au format ONNX avec un format de sortie supporté :
- **yolo11** (YOLO v11 / Ultralytics)
- **yolox** (YOLOX)

Le modèle doit contenir les métadonnées suivantes (inspectées automatiquement) :
- Dimensions d'entrée (input_width × input_height)
- Nombre de classes
- Noms de classes (optionnel, sinon `class_0`, `class_1`, etc.)

---

## FAQ

### Comment choisir le professeur et l'élève ?

| Critère | Professeur | Élève |
|---------|-----------|-------|
| **Taille** | Grand (YOLO11-L, YOLO11-X) | Petit (YOLO11-N, YOLO11-S) |
| **Précision** | Haute | En cours d'apprentissage |
| **Vitesse** | Lente (acceptable) | Rapide (objectif) |

### Que signifie un score de 0.85 ?

Un score de 0.85 signifie que l'élève reproduit 85% de la qualité des détections du professeur, en tenant compte du rappel, de la précision et de la qualité des localisations.

### L'entraînement fonctionne-t-il sans GPU ?

Oui, le mode CPU est supporté. L'entraînement sera plus lent mais fonctionnel. Le provider par défaut est `CPUExecutionProvider`.

### Puis-je utiliser le modèle exporté dans ObjectDetection ?

Oui ! Le modèle exporté est un fichier ONNX standard. Il peut être importé directement via le bouton "Add Model" du nœud ObjectDetection.

### Que se passe-t-il si je ne connecte pas le JSON du professeur ?

Le nœud détecte l'absence de JSON et l'élève infère seul sans calcul de score ni entraînement. Les prédictions sont tout de même affichées.
