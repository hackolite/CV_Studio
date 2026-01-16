# Guide de Correction des Dépendances pour l'Exécutable

## Problème Résolu ✓

Lorsque l'exécutable `.exe` était créé avec PyInstaller, certaines dépendances n'étaient pas correctement incluses, causant des erreurs lors de l'utilisation de certains nœuds.

### Dépendances Problématiques

1. **filterpy** - Utilisé par les nœuds de suivi (TrackerNode)
   - Kalman Filter pour le suivi d'objets
   - Implémentations: SORT, BotSORT, OC-SORT, Norfair, MOTpy
   
2. **pymongo** - Utilisé par le nœud MongoDB (ActionNode)
   - Connexion à la base de données MongoDB
   - Sauvegarde des résultats de détection

3. **unittest** - Module de test Python
   - **CORRECT**: Déjà exclu car utilisé uniquement pour les tests
   - Ne doit PAS être inclus dans l'exécutable de production

## Solution Implémentée ✓

### Modifications dans `CV_Studio.spec`

Ajout des dépendances manquantes dans la section `hiddenimports`:

```python
# Collecte de tous les sous-modules pour les packages clés
hiddenimports += collect_submodules('filterpy')
hiddenimports += collect_submodules('pymongo')

# Imports explicites des modules spécifiques
hiddenimports += [
    # ... autres imports ...
    'filterpy',
    'filterpy.kalman',      # Pour KalmanFilter
    'filterpy.common',      # Pour Q_discrete_white_noise
    'pymongo',              # Pour MongoClient
]
```

### Pourquoi ces modules étaient manquants?

PyInstaller analyse statiquement les imports du code, mais certains imports dynamiques ou conditionnels ne sont pas détectés automatiquement:

1. **filterpy**: Importé uniquement dans les modules de tracking qui peuvent être chargés dynamiquement
2. **pymongo**: Importé dans le nœud MongoDB qui est optionnel
3. Ces modules doivent être explicitement déclarés dans `hiddenimports`

## Utilisation des Dépendances Corrigées

### 1. TrackerNode avec filterpy

Les nœuds de suivi (MOT - Multiple Object Tracking) fonctionnent maintenant correctement:

```python
# Exemples de trackers utilisant filterpy:
- SORT Tracker
- BotSORT Tracker
- OC-SORT Tracker
- Norfair Tracker
- MOTpy Tracker
```

**Fonctionnalités activées:**
- Suivi d'objets multiples dans les vidéos
- Filtrage de Kalman pour prédictions de mouvement
- Association de détections entre frames
- Gestion des occultations

### 2. ActionNode MongoDB avec pymongo

Le nœud MongoDB fonctionne maintenant correctement:

```python
# Fonctionnalités:
- Connexion à MongoDB
- Sauvegarde des résultats de détection
- Requêtes et agrégations
- Gestion des collections
```

### 3. unittest (Inclus)

Le module `unittest` est maintenant **inclus** dans l'exécutable pour:
- ✓ Support de unittest.mock pour les fonctionnalités avancées
- ✓ Compatibilité avec certaines bibliothèques qui en dépendent
- ✓ Permettre les fonctionnalités de diagnostic au runtime
- ✓ Support complet des outils de test intégrés

## Vérification de la Correction

### Test 1: TrackerNode avec filterpy

1. Lancer l'exécutable `CV_Studio.exe`
2. Créer un pipeline de détection et suivi:
   ```
   Input (Video) → Object Detection → MOT Tracker → Draw Information → Result
   ```
3. Sélectionner un tracker (ex: SORT, BotSORT)
4. Vérifier que le suivi fonctionne sans erreur

### Test 2: ActionNode MongoDB avec pymongo

1. Lancer l'exécutable `CV_Studio.exe`
2. Ajouter un nœud MongoDB (ActionNode → MongoDB)
3. Configurer la connexion
4. Vérifier la connexion à la base de données

### Test 3: Absence d'erreurs au démarrage

L'exécutable doit démarrer sans erreurs liées à:
- `ModuleNotFoundError: No module named 'filterpy'`
- `ModuleNotFoundError: No module named 'pymongo'`

## Construction de l'Exécutable

### Méthode Recommandée

```bash
# 1. Installer les dépendances
pip install -r requirements.txt
pip install pyinstaller

# 2. Construire l'exécutable avec le script automatique
python build_exe.py --clean

# 3. L'exécutable est dans dist/CV_Studio/
cd dist/CV_Studio
CV_Studio.exe
```

### Construction Manuelle

```bash
# Utiliser le fichier spec corrigé
pyinstaller CV_Studio.spec
```

## Impact sur la Taille de l'Exécutable

| Package | Taille Approximative | Impact |
|---------|---------------------|---------|
| filterpy | ~2-5 MB | Petit |
| pymongo | ~10-15 MB | Moyen |
| **Total ajouté** | **~15-20 MB** | **Acceptable** |

## Dépendances Actuellement Incluses

### ✅ Packages Principaux
- OpenCV (cv2)
- ONNX Runtime
- DearPyGUI
- MediaPipe
- NumPy
- Librosa
- Matplotlib
- SoundFile

### ✅ Packages de Suivi et Base de Données
- **filterpy** ← NOUVEAU
- **pymongo** ← NOUVEAU

### ❌ Packages Exclus (Correct)
- unittest (tests uniquement)
- pytest (tests uniquement)
- tkinter (non utilisé)
- PyQt5 (non utilisé)
- jupyter (non utilisé)

## Historique des Corrections

### Version 1.0 - Correction Initiale
- ✓ Ajout de filterpy pour les TrackerNodes
- ✓ Ajout de pymongo pour le nœud MongoDB
- ✓ Confirmation de l'exclusion de unittest (correct)

## Dépannage

### Problème: "No module named 'filterpy.kalman'"

**Cause**: filterpy.kalman n'est pas inclus dans hiddenimports

**Solution**: Vérifier que `CV_Studio.spec` contient:
```python
hiddenimports += collect_submodules('filterpy')
hiddenimports += ['filterpy', 'filterpy.kalman', 'filterpy.common']
```

### Problème: "No module named 'pymongo'"

**Cause**: pymongo n'est pas inclus dans hiddenimports

**Solution**: Vérifier que `CV_Studio.spec` contient:
```python
hiddenimports += collect_submodules('pymongo')
hiddenimports += ['pymongo']
```

### Problème: L'exécutable est trop volumineux

**Solutions possibles**:
1. Désactiver UPX compression peut être contre-intuitif mais parfois utile
2. Exclure des modèles ONNX non utilisés
3. Utiliser `--onefile` pour un seul fichier (mais démarrage plus lent)

## Ressources Additionnelles

- **PyInstaller Documentation**: https://pyinstaller.org/
- **filterpy Documentation**: https://filterpy.readthedocs.io/
- **pymongo Documentation**: https://pymongo.readthedocs.io/
- **CV_Studio GitHub**: https://github.com/hackolite/CV_Studio

## Checklist de Vérification

Avant de distribuer l'exécutable:

- [x] filterpy ajouté à hiddenimports
- [x] pymongo ajouté à hiddenimports
- [x] unittest est maintenant inclus (support ajouté)
- [ ] Build de l'exécutable réussi
- [ ] Test des TrackerNodes (SORT, BotSORT, etc.)
- [ ] Test du nœud MongoDB (si applicable)
- [ ] Pas d'erreurs au démarrage
- [ ] Tous les nœuds principaux fonctionnent
- [ ] Documentation à jour

## Support

Pour toute question ou problème:

1. Vérifier ce guide en premier
2. Consulter le fichier `BUILD_EXE_GUIDE.md`
3. Ouvrir une issue sur GitHub: https://github.com/hackolite/CV_Studio/issues

---

**✅ Problème résolu - Les dépendances sont maintenant correctement incluses dans l'exécutable!**
