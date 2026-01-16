# Guide de Création de l'Exécutable - Problème Résolu ✓

## 📋 Résumé du Problème et de la Solution

### Problème Identifié
Le workflow GitHub Actions pour créer l'exécutable Windows échouait avec l'erreur suivante :
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 2: character maps to <undefined>
```

Cette erreur se produisait parce que le script `build_exe.py` utilisait des caractères Unicode (✓) qui ne pouvaient pas être encodés avec l'encodage Windows cp1252 par défaut.

### Solution Implémentée
Deux modifications ont été apportées pour résoudre ce problème :

#### 1. Modification de `build_exe.py`
Ajout d'un wrapper UTF-8 pour la console Windows :
```python
# Ensure UTF-8 encoding for Windows console output
if sys.platform == 'win32':
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

#### 2. Modification de `.github/workflows/build-exe.yml`
Ajout des variables d'environnement UTF-8 :
```yaml
env:
  PYTHONUTF8: '1'
  PYTHONIOENCODING: 'utf-8'
```

## 🚀 Comment Créer l'Exécutable Maintenant

### Méthode 1 : Déclenchement Manuel du Workflow (RECOMMANDÉ)

1. **Aller sur la page GitHub Actions** :
   - URL : https://github.com/hackolite/CV_Studio/actions

2. **Sélectionner le workflow "Build Windows Executable"** dans la liste à gauche

3. **Cliquer sur "Run workflow"** (bouton à droite)
   - Sélectionner la branche `copilot/create-executable-file` (ou `main` après le merge)
   - Cliquer sur le bouton vert "Run workflow"

4. **Attendre la fin de la construction** (environ 10-15 minutes)
   - Une icône verte ✓ apparaîtra quand c'est terminé

5. **Télécharger l'exécutable**
   - Cliquer sur le workflow terminé
   - Descendre à la section "Artifacts"
   - Télécharger `CV_Studio-Windows-Executable.zip`
   - Extraire le ZIP et lancer `CV_Studio.exe`

### Méthode 2 : Construction Automatique sur Tag

Créer un tag et le pousser :
```bash
git tag v1.0.0
git push origin v1.0.0
```

Le workflow se déclenchera automatiquement et l'exécutable sera disponible dans les artifacts.

### Méthode 3 : Construction Locale (Windows uniquement)

Si vous avez accès à une machine Windows :

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

## ✅ Vérification du Correctif

Pour vérifier que le correctif fonctionne :

1. Le workflow doit passer l'étape "Build executable with PyInstaller" avec succès
2. Aucune erreur `UnicodeEncodeError` ne doit apparaître dans les logs
3. Le fichier `dist/CV_Studio/CV_Studio.exe` doit être créé
4. L'étape "Verify build" doit confirmer la création de l'exécutable

## 🔧 Modifications Techniques Détaillées

### Avant (Code Problématique)
```python
print(f"  ✓ Python {sys.version.split()[0]}")  # Erreur sur Windows avec cp1252
```

### Après (Code Corrigé)
```python
# Configuration UTF-8 au début du script
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Maintenant les caractères Unicode fonctionnent
print(f"  ✓ Python {sys.version.split()[0]}")  # ✓ Fonctionne !
```

## 📝 Notes Importantes

1. **Encodage UTF-8** : Le correctif garantit que Python utilise UTF-8 sur Windows, ce qui est nécessaire pour les caractères Unicode modernes.

2. **Compatibilité** : Ces modifications n'affectent que Windows. Sur Linux/macOS, UTF-8 est l'encodage par défaut.

3. **Caractères Spéciaux** : Le script peut maintenant afficher correctement :
   - Checkmarks : ✓ ✅
   - Erreurs : ✗ ❌
   - Émojis : 🚀 📁 💻

4. **Variables d'Environnement** :
   - `PYTHONUTF8=1` : Force Python 3.7+ à utiliser UTF-8 sur Windows
   - `PYTHONIOENCODING=utf-8` : Configure l'encodage des I/O

## 🐛 Dépannage

### Le workflow échoue toujours ?
1. Vérifier que vous utilisez la branche avec le correctif
2. Vérifier les logs du workflow pour voir l'erreur exacte
3. S'assurer que les modifications de `build_exe.py` et `build-exe.yml` sont présentes

### L'exécutable ne démarre pas ?
1. Installer Visual C++ Redistributable : https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Lancer depuis la ligne de commande pour voir les erreurs :
   ```bash
   cd dist\CV_Studio
   CV_Studio.exe --use_debug_print
   ```

### Problèmes de dépendances ?
Vérifier que toutes les dépendances de `requirements.txt` sont installées correctement.

## 📞 Support

Des questions ? Ouvrez une issue sur GitHub :
https://github.com/hackolite/CV_Studio/issues

---

**✅ Problème résolu - L'exécutable peut maintenant être créé avec succès !**
