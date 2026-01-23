# Fix pour les problèmes d'import dans l'exécutable .exe

## Problème résolu

Après avoir construit l'exécutable .exe avec PyInstaller, les erreurs suivantes se produisaient :

1. **pytz** - `ModuleNotFoundError: No module named 'pytz'`
2. **lap** - `ModuleNotFoundError: No module named 'lap'` ou erreur lors de l'utilisation
3. **PIL.ImageGrab** - Erreurs lors de l'utilisation de la capture d'écran

## Cause du problème

PyInstaller ne détecte pas automatiquement certaines dépendances spéciales :

- **pytz** : Les fichiers de données de timezone ne sont pas inclus automatiquement
- **lap** : Les extensions C compilées (.pyd/.so) ne sont pas détectées
- **PIL.ImageGrab** : Nécessite une inclusion explicite, surtout sur Windows

## Solution implémentée

### 1. Hooks PyInstaller personnalisés

Trois hooks ont été créés dans le répertoire `hooks/` :

#### `hooks/hook-pytz.py`
Collecte les fichiers de données de timezone de pytz et tous ses sous-modules.

**Node affecté :** `node.ActionNode.node_mongodb` (utilise pytz pour la gestion des fuseaux horaires UTC)

#### `hooks/hook-lap.py`
Collecte les bibliothèques dynamiques (extensions C compilées) et les sous-modules de lap.

**Node affecté :** `node.TrackerNode.mot.bytetrack.tracker.matching` (utilise lap pour le tracking d'objets)

#### `hooks/hook-PIL.py`
Assure que PIL.ImageGrab et toutes les dépendances PIL sont correctement incluses.

**Node affecté :** `node.VideoNode.node_screen_capture` (utilise PIL.ImageGrab pour la capture d'écran)

### 2. Modifications de CV_Studio.spec

Les modifications suivantes ont été apportées :

```python
# Ajout des fichiers de données pour pytz et PIL
datas += collect_data_files('pytz')  # CRITICAL pour pytz
datas += collect_data_files('PIL')

# Ajout des binaires compilés pour lap
from PyInstaller.utils.hooks import collect_dynamic_libs
binaries = []
binaries += collect_dynamic_libs('lap')  # CRITICAL pour lap

# Utilisation du répertoire hooks
a = Analysis(
    ...
    hookspath=['hooks'],  # Utilise les hooks personnalisés
    ...
)
```

### 3. Modifications de build_exe.py

Les mêmes modifications ont été appliquées au script de build pour garantir la cohérence.

## Comment utiliser

### Build standard
```bash
python build_exe.py --clean
```

### Build avec PyInstaller directement
```bash
pyinstaller CV_Studio.spec
```

### Tester les imports critiques
```bash
python test_critical_imports.py
```

## Vérification après build

1. **Construire l'exécutable**
   ```bash
   python build_exe.py --clean
   ```

2. **Exécuter l'exe**
   ```bash
   cd dist/CV_Studio
   CV_Studio.exe
   ```

3. **Tester les nodes problématiques**
   - Node MongoDB (teste pytz)
   - Node ByteTrack tracker (teste lap)
   - Node Screen Capture (teste PIL.ImageGrab)

## Structure des fichiers ajoutés

```
CV_Studio/
├── hooks/
│   ├── README.md           # Documentation des hooks
│   ├── hook-pytz.py        # Hook pour pytz
│   ├── hook-lap.py         # Hook pour lap
│   └── hook-PIL.py         # Hook pour PIL/Pillow
├── test_critical_imports.py # Script de test des imports
├── CV_Studio.spec          # Modifié
└── build_exe.py            # Modifié
```

## Dépannage

### Si les imports échouent encore après le build

1. **Nettoyer et reconstruire**
   ```bash
   python build_exe.py --clean
   ```

2. **Vérifier les warnings de PyInstaller**
   Pendant le build, cherchez des avertissements concernant pytz, lap ou PIL

3. **Vérifier que le répertoire hooks existe**
   ```bash
   ls -la hooks/
   ```

4. **Installer toutes les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

### Messages d'erreur courants et solutions

#### `ModuleNotFoundError: No module named 'pytz'`
- **Solution** : Le hook pytz n'a pas été utilisé. Vérifiez que `hookspath=['hooks']` est dans le spec.

#### `ModuleNotFoundError: No module named 'lap'` ou crash au runtime
- **Solution** : Les extensions C de lap ne sont pas incluses. Vérifiez `collect_dynamic_libs('lap')`.

#### `ImportError: cannot import name 'ImageGrab'`
- **Solution** : PIL.ImageGrab n'est pas disponible ou mal configuré. Vérifiez le hook PIL.

## Références techniques

- **PyInstaller Hooks** : https://pyinstaller.org/en/stable/hooks.html
- **pytz** : https://pypi.org/project/pytz/
- **lap** : https://pypi.org/project/lap/
- **Pillow** : https://pypi.org/project/Pillow/

## Changelog

### Version actuelle
- ✅ Ajout de hooks PyInstaller pour pytz, lap, et PIL
- ✅ Mise à jour de CV_Studio.spec avec hookspath et collections de données
- ✅ Mise à jour de build_exe.py pour cohérence
- ✅ Ajout de script de test test_critical_imports.py
- ✅ Documentation complète des fixes

## Support

Si vous rencontrez toujours des problèmes après avoir appliqué ces fixes :

1. Exécutez `python test_critical_imports.py` avant le build
2. Vérifiez les warnings PyInstaller pendant le build
3. Ouvrez une issue sur GitHub avec les logs d'erreur complets
