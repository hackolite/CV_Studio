# 📉 Loss de distillation *set-based* (DETR-style) pour la détection d'objets

> Méthode de comparaison de deux ensembles de bounding boxes (teacher ↔ student)
> utilisée à la fois par le nœud **IoU** (affichage dans le nœud **Chart**) et par
> le nœud **OnlineTraining** (distillation).

Implémentation : `node/DLNode/online_training/distillation_loss.py`
(`hungarian_match_boxes`, `compute_set_distillation_loss`).

---

## Vue d'ensemble

Comparer la sortie de deux modèles de détection ne se réduit pas à un IoU
moyen : les deux modèles peuvent produire un **nombre différent de boxes**, dans
un **ordre différent**, avec des **classes différentes**. Il faut donc :

1. **apparier** les boxes de façon optimale (matching bipartite),
2. mesurer séparément les **erreurs de localisation**, de **classe**, de
   **cardinalité** (nombre de boxes) et les **boxes en trop / manquantes**,
3. combiner le tout en une **loss unique** (entraînement) tout en exposant des
   **métriques lisibles** (chart) et un **score de benchmark** (comparaison de
   modèles).

Cette approche combine plusieurs idées de l'état de l'art : matching de **DETR**
(Hongrois), assignation dynamique de **YOLOX SimOTA**, dense matching de
**NanoDet** et imitation de **CenterNet** (extension heatmap possible).

---

## Étape 1 — Matching global (sans confidence)

On construit une matrice de coût entre chaque box *teacher* `t` et chaque box
*student* `s`, **sans utiliser le score de confiance** :

```
cost(t, s) = λ_iou * IoU_cost(t, s) + λ_class * class_cost(t, s)

IoU_cost(t, s)   = 1 - IoU(t, s)
class_cost(t, s) = 0   si class_id_t == class_id_s
                   1   sinon
```

Le matching optimal (coût total minimal) est résolu par l'**algorithme
hongrois** (`scipy.optimize.linear_sum_assignment`). En l'absence de SciPy, un
repli **glouton** (paires de coût croissant) est utilisé.

> Un terme L1 optionnel (`λ_l1`, désactivé par défaut) peut être ajouté au coût
> pour départager les cas où plusieurs boxes se recouvrent identiquement.

## Étape 2 — Assignation

Le matching produit :

| Résultat | Signification |
|----------|---------------|
| `matched_pairs` | correspondances optimales teacher ↔ student |
| `unmatched_teacher` | **faux négatifs** (objets ratés par le student) |
| `unmatched_student` | **faux positifs** (objets en trop côté student) |

Les coordonnées des boxes sont normalisées par la plus grande extension présente
dans les deux ensembles avant le calcul des distances L1, afin que la loss reste
**indépendante de la résolution** (comme les boxes normalisées de DETR).

## Étape 3 — Loss SOTA

### 1. Box regression loss (paires appariées uniquement)

```
L_box = moyenne_paires [ L1(box_s, box_t) + (1 - IoU(box_s, box_t)) ]
```

### 2. Class distillation loss (paires appariées uniquement)

- **Sans logits** (labels durs) : la cross-entropy one-hot se réduit à un coût
  de mismatch `0/1`, moyenné sur les paires.
- **Avec logits** (si le teacher les fournit) : divergence
  `KL(softmax(logits_t) || softmax(logits_s))`.

```
L_class = moyenne_paires CrossEntropy(class_s, class_t)   # ou KL(logits)
```

### 3. Cardinality loss (TRÈS IMPORTANT)

Pénalise la différence de nombre de boxes :

```
L_card = |N_student - N_teacher|
```

### 4. Pénalités des non-appariées

```
L_fp = Σ_{s ∈ unmatched_student} ( 1 - max_t IoU(s, t) )   # faux positifs
L_fn = fn_constant * count(unmatched_teacher)              # faux négatifs
```

### 5. Pénalité explicite de mismatch de classe

```
L_cls_mismatch = Σ_{paires} [ class_s != class_t ]
```

### Loss totale

```
L_total =   λ_box  * L_box
          + λ_class * L_class
          + λ_card  * L_card
          + λ_fp    * L_fp
          + λ_fn    * L_fn
          + λ_cls   * L_cls_mismatch
```

Tous les poids `λ_*` sont des paramètres de `compute_set_distillation_loss`
(valeur par défaut `1.0`). `L_total >= 0`, et `0` signifie une correspondance
parfaite avec le teacher.

---

## 📊 Métriques pour le nœud Chart

`compute_set_distillation_loss` retourne un dictionnaire **plat et numérique**
directement consommable par le nœud **Chart** (qui moyenne chaque série dans le
temps, comme pour les autres métriques) :

| Clé | Description |
|-----|-------------|
| `loss` / `loss_total` | loss totale `L_total` |
| `loss_box` | terme de régression de box |
| `loss_class` | terme de distillation de classe |
| `loss_cardinality` | `L_card = |N_s - N_t|` |
| `loss_fp` / `loss_fn` | pénalités faux positifs / faux négatifs |
| `loss_cls_mismatch` | pénalité explicite de mismatch de classe |
| `cardinality_error` | `|N_s - N_t|` (entier) |
| `fp_count` | nombre de boxes student non appariées |
| `fn_count` | nombre de boxes teacher non appariées |
| `iou_mean_matched` | IoU moyen des paires appariées |
| `class_mismatch_rate` | `mismatch / matched` |
| `detection_score` | score global de benchmark (voir ci-dessous) |

---

## 📈 Score global (non-loss)

Pour comparer directement deux modèles en live (benchmark), un score
**à maximiser** (et non une loss) est aussi fourni :

```
detection_score =   mean_IoU_matched
                  - α * fp_count
                  - β * fn_count
                  - γ * class_mismatch_rate
                  - δ * cardinality_error
```

(`α, β, γ, δ` = `score_alpha, score_beta, score_gamma, score_delta`).

---

## Utilisation

### Dans le nœud IoU (comparaison + chart)

Le nœud **IoU** prend deux sorties JSON d'`ObjectDetection` (Detection A =
référence/teacher, Detection B = student), calcule la loss *set-based* et expose
toutes les métriques ci-dessus dans sa sortie JSON. En connectant cette sortie au
nœud **Chart**, la `loss` (et n'importe quelle composante) devient traçable dans
le temps.

### Dans le nœud OnlineTraining (distillation)

Le nœud **OnlineTraining** récupère la sortie d'`ObjectDetection` du teacher,
calcule en interne la même sortie sur le student, puis appelle la même loss
via `compute_distillation_score`. Les métriques sont exposées sous
`distillation_losses` et peuvent être affichées dans le nœud **Chart**. Lorsque
`onnxruntime-training` est disponible, `L_total` sert de signal de
rétropropagation pour mettre à jour les poids du student.

---

## 🚀 Notes SOTA & extension (optionnel)

Si le teacher fournit des **heatmaps** (détecteurs type CenterNet), on peut
étendre la loss par imitation directe :

```
L_hm = || H_student - H_teacher ||²          # heatmaps
+ distillation des regression maps (wh / reg)
```

### But final

Cette loss permet :

- un **entraînement student stable**,
- une **comparaison directe de modèles** (`detection_score`),
- une **visualisation claire des erreurs** : objets manquants (`fn_count`),
  objets en trop (`fp_count`), erreurs de classe (`class_mismatch_rate`) et
  mauvaise localisation (`loss_box`, `iou_mean_matched`).
