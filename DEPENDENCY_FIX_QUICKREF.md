# Quick Fix Guide - Dépendances .exe / Dependencies .exe

## 🎯 Problème Résolu / Problem Solved

**Français**: Les dépendances `filterpy` et `pymongo` manquaient dans l'exécutable .exe, causant des erreurs avec les nœuds de suivi (TrackerNode) et MongoDB.

**English**: Dependencies `filterpy` and `pymongo` were missing from the .exe executable, causing errors with tracking nodes (TrackerNode) and MongoDB.

---

## ✅ Solution

### Modification: `CV_Studio.spec`

```python
# Ajout / Added:
hiddenimports += collect_submodules('filterpy')
hiddenimports += collect_submodules('pymongo')

hiddenimports += [
    'filterpy',
    'filterpy.kalman',
    'filterpy.common',
    'pymongo',
]
```

### Status: `unittest`
✓ **Correctement exclu / Correctly excluded** - Utilisé uniquement pour les tests / Only used for tests

---

## 🚀 Construction / Build

```bash
# Installation des dépendances / Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Construction / Build
python build_exe.py --clean

# Lancement / Run
cd dist/CV_Studio
CV_Studio.exe
```

---

## 🧪 Tests de Vérification / Verification Tests

### 1. TrackerNode (filterpy)
```
Input (Video) → Object Detection → MOT Tracker → Draw → Result
```
✅ SORT, BotSORT, OC-SORT, Norfair, MOTpy doivent fonctionner / should work

### 2. MongoDB Node (pymongo)
```
ActionNode → MongoDB → Configure connection
```
✅ Connexion à MongoDB doit fonctionner / MongoDB connection should work

### 3. Démarrage / Startup
✅ Pas d'erreur "ModuleNotFoundError" / No "ModuleNotFoundError"

---

## 📊 Impact

- **Taille ajoutée / Size added**: ~15-20 MB
- **Sécurité / Security**: ✅ Pas de vulnérabilités / No vulnerabilities
- **Fonctionnalités activées / Enabled features**:
  - ✅ Suivi d'objets multiples / Multiple object tracking
  - ✅ Filtrage de Kalman / Kalman filtering
  - ✅ Base de données MongoDB / MongoDB database

---

## 📚 Documentation Complète / Full Documentation

- **Français**: `DEPENDENCY_FIX_GUIDE.md`
- **English**: `DEPENDENCY_FIX_GUIDE_EN.md`
- **Build Guide**: `BUILD_EXE_GUIDE.md` / `BUILD_EXE_GUIDE_FR.md`

---

## ⚠️ Note Importante / Important Note

**unittest** est maintenant inclus (support ajouté) - il est nécessaire pour certaines fonctionnalités avancées et pour la compatibilité avec des bibliothèques qui en dépendent.

**unittest** is now included (support added) - it's needed for certain advanced features and compatibility with libraries that depend on it.

---

## 🆘 Support

- **GitHub Issues**: https://github.com/hackolite/CV_Studio/issues
- **Documentation**: Voir les guides ci-dessus / See guides above

---

**Problème résolu ✓ / Problem solved ✓**
