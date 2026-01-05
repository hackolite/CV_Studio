# Comment Obtenir l'Exécutable Windows (.exe)

## 🎯 Méthode Automatique - GitHub Actions (RECOMMANDÉ)

L'exécutable Windows est maintenant créé automatiquement via GitHub Actions !

### Option 1 : Construction Manuelle (La Plus Simple)

1. **Aller dans l'onglet Actions** de ce dépôt GitHub
   - URL : https://github.com/hackolite/CV_Studio/actions

2. **Cliquer sur le workflow "Build Windows Executable"** dans la liste à gauche

3. **Cliquer sur "Run workflow"** (bouton à droite)
   - Sélectionner la branche `main` ou celle de votre choix
   - Cliquer sur le bouton vert "Run workflow"

4. **Attendre la fin de la construction** (environ 10-15 minutes)
   - Vous verrez une icône verte ✓ quand c'est terminé

5. **Télécharger l'exécutable**
   - Cliquer sur le workflow terminé
   - Descendre à la section "Artifacts"
   - Télécharger `CV_Studio-Windows-Executable.zip`
   - Extraire le ZIP et lancer `CV_Studio.exe`

### Option 2 : Construction Automatique sur Release

Quand vous créez une nouvelle release sur GitHub, l'exécutable est automatiquement construit et attaché à la release.

1. **Créer une nouvelle release** :
   - Aller dans "Releases" → "Create a new release"
   - Créer un nouveau tag (ex: `v1.0.0`)
   - Publier la release

2. **L'exécutable sera automatiquement construit** et ajouté aux assets de la release

3. **Télécharger depuis la page de release** : `CV_Studio-Windows.zip`

### Option 3 : Construction Automatique sur Push de Tag

Chaque fois que vous poussez un tag qui commence par `v` (ex: `v1.0.0`), un build automatique est déclenché :

```bash
git tag v1.0.0
git push origin v1.0.0
```

L'exécutable sera disponible dans l'onglet Actions comme artifact.

## 🖥️ Méthode Manuelle - Build Local sur Windows

Si vous préférez construire l'exécutable vous-même sur votre machine Windows :

### Prérequis
- Windows 10/11
- Python 3.7+ installé
- Git installé

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio

# 2. Installer les dépendances
pip install -r requirements.txt
pip install pyinstaller

# 3. Construire l'exécutable
python build_exe.py --clean

# 4. L'exécutable est dans dist/CV_Studio/
cd dist/CV_Studio
CV_Studio.exe
```

## 📦 Contenu de l'Exécutable

Une fois téléchargé et extrait, vous aurez :

```
CV_Studio/
├── CV_Studio.exe           # ← Exécutable principal à lancer
├── README.txt              # Documentation
├── node/                   # Tous les nœuds (Input, Process, DL, Audio...)
│   └── DLNode/            
│       └── object_detection/
│           ├── YOLOX/model/*.onnx      # Modèles ONNX
│           ├── YOLO/model/*.onnx
│           └── ...
├── node_editor/           # Éditeur de nœuds
└── _internal/            # Dépendances Python
```

## 🚀 Utilisation

Double-cliquez simplement sur `CV_Studio.exe` !

Aucune installation de Python requise. Tout est inclus.

## ❓ Questions Fréquentes

### Combien de temps prend la construction ?
- Environ 10-15 minutes sur GitHub Actions
- Environ 5-10 minutes en local selon votre machine

### Quelle est la taille de l'exécutable ?
- Environ 800 MB - 1.5 GB (inclut tous les modèles ONNX et dépendances)

### Puis-je construire pour Linux ou macOS ?
- Oui, modifiez `.github/workflows/build-exe.yml` pour utiliser `ubuntu-latest` ou `macos-latest`
- Sur Linux, l'exécutable s'appellera `CV_Studio` (sans .exe)
- Sur macOS, ce sera une application `.app`

### L'exécutable ne démarre pas ?
1. Installer Visual C++ Redistributable : https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Lancer depuis la ligne de commande pour voir les erreurs :
   ```bash
   cd dist\CV_Studio
   CV_Studio.exe --use_debug_print
   ```

## 🔗 Documentation Complète

Pour plus de détails sur la construction et la personnalisation :
- [Guide complet en français](BUILD_EXE_GUIDE_FR.md)
- [Guide complet en anglais](BUILD_EXE_GUIDE.md)
- [Référence rapide](BUILD_EXE_QUICKREF.md)

## 📞 Support

Des questions ? Ouvrez une issue sur GitHub :
https://github.com/hackolite/CV_Studio/issues

---

**Profitez de CV_Studio ! 🎨**
