# 🚀 Script de Build Windows - Guide Rapide

## Pour construire CV_Studio.exe depuis zéro

### Méthode 1: Script Batch (Simple - Recommandé pour débutants)

1. **Téléchargez le script** `build_windows.bat` depuis ce repository
2. **Double-cliquez** sur `build_windows.bat`
3. **Attendez** que le script termine (5-15 minutes)
4. **Lancez** `dist\CV_Studio\CV_Studio.exe`

**C'est tout !** Le script fait tout automatiquement :
- ✅ Clone le repository depuis GitHub
- ✅ Installe toutes les dépendances Python
- ✅ Construit l'exécutable .exe
- ✅ Vous indique où trouver le fichier

### Méthode 2: Script PowerShell (Plus moderne)

1. **Téléchargez** le script `build_windows.ps1`
2. **Ouvrez PowerShell** dans le dossier contenant le script
3. **Exécutez** :
   ```powershell
   powershell -ExecutionPolicy Bypass -File build_windows.ps1
   ```
4. **Attendez** la fin de la construction
5. **Lancez** `dist\CV_Studio\CV_Studio.exe`

## 📋 Prérequis

Avant de lancer le script, assurez-vous d'avoir :

1. **Python 3.7 ou supérieur**
   - Téléchargez depuis : https://www.python.org/downloads/
   - ⚠️ **Important** : Cochez "Add Python to PATH" lors de l'installation !

2. **Git**
   - Téléchargez depuis : https://git-scm.com/download/win
   - Installation par défaut convient

3. **Connexion Internet** (pour télécharger le code et les dépendances)

4. **Espace disque** : ~3 GB libre

## 📝 Instructions détaillées

### Option A : Utilisation du script depuis n'importe quel dossier

1. **Créez un dossier** pour votre build (ex: `C:\CV_Studio_Build`)
2. **Copiez le script** `build_windows.bat` dans ce dossier
3. **Double-cliquez** sur le script
4. Le script va automatiquement :
   - Cloner le repository dans un sous-dossier `CV_Studio`
   - Installer les dépendances
   - Construire l'exécutable

### Option B : Utilisation depuis un repository déjà cloné

Si vous avez déjà cloné le repository :

```bash
cd CV_Studio
build_windows.bat
```

Le script détectera automatiquement qu'il est dans le repository et ne clonera pas à nouveau.

## 🎯 Que fait le script ?

Le script effectue les étapes suivantes :

```
[1/6] Vérification de Python ✓
[2/6] Vérification de Git ✓
[3/6] Clonage du repository (ou détection du repo existant) ✓
[4/6] Installation des dépendances Python ✓
[5/6] Construction de l'exécutable avec PyInstaller ✓
[6/6] Vérification et résumé ✓
```

Durée totale : **5-15 minutes** selon votre machine et connexion Internet

## 📦 Résultat

Après l'exécution, vous obtiendrez :

```
CV_Studio/
└── dist/
    └── CV_Studio/
        ├── CV_Studio.exe  ← VOTRE EXÉCUTABLE !
        ├── README.txt
        ├── node/
        ├── node_editor/
        ├── src/
        └── _internal/
```

**Taille approximative** : 800 MB - 1.5 GB (inclut Python, OpenCV, ONNX Runtime, tous les modèles, etc.)

## 🚀 Utilisation de l'exécutable

### Lancement simple
```bash
cd dist\CV_Studio
CV_Studio.exe
```

Ou simplement **double-cliquez** sur `CV_Studio.exe`

### Options de ligne de commande
```bash
# Avec configuration personnalisée
CV_Studio.exe --setting mon_config.json

# Mode debug
CV_Studio.exe --use_debug_print
```

## 📤 Distribution

Pour partager votre exécutable :

1. **Compressez** le dossier `dist\CV_Studio` en ZIP
2. **Partagez** l'archive
3. Les utilisateurs **extraient** et lancent `CV_Studio.exe`

**Aucune installation de Python requise** pour les utilisateurs finaux ! 🎉

## ❓ Résolution de problèmes

### Le script ne démarre pas

**Erreur** : "Python n'est pas reconnu..."
- **Solution** : Installez Python et cochez "Add Python to PATH"
- Ou ajoutez manuellement Python au PATH

**Erreur** : "Git n'est pas reconnu..."
- **Solution** : Installez Git depuis https://git-scm.com/

### La construction échoue

**Erreur** : "Module not found..."
- **Solution** : Le script réinstalle les dépendances automatiquement
- Si le problème persiste, lancez manuellement :
  ```bash
  pip install -r requirements.txt
  pip install pyinstaller
  ```

**Erreur** lors de PyInstaller
- **Solution** : Vérifiez que vous avez assez d'espace disque (~3 GB)
- Désactivez temporairement l'antivirus (peut bloquer PyInstaller)

### L'exécutable ne démarre pas

1. **Installez Visual C++ Redistributable**
   - Téléchargez : https://aka.ms/vs/17/release/vc_redist.x64.exe
   - Installez et redémarrez

2. **Testez depuis la ligne de commande** pour voir les erreurs :
   ```bash
   cd dist\CV_Studio
   CV_Studio.exe --use_debug_print
   ```

3. **Vérifiez l'antivirus**
   - Certains antivirus bloquent les exécutables PyInstaller
   - Ajoutez une exception pour CV_Studio.exe

### Problème de permissions PowerShell

Si vous avez "script execution disabled" :

```powershell
# Méthode 1 : Bypass temporaire (recommandé)
powershell -ExecutionPolicy Bypass -File build_windows.ps1

# Méthode 2 : Activer pour la session
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 🔄 Commandes alternatives

Si vous préférez faire étape par étape manuellement :

```bash
# 1. Cloner
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio

# 2. Installer dépendances
pip install -r requirements.txt
pip install pyinstaller

# 3. Construire
python build_exe.py --clean

# 4. Lancer
dist\CV_Studio\CV_Studio.exe
```

## 📚 Documentation supplémentaire

Pour plus d'informations :
- **Guide complet (FR)** : [BUILD_EXE_GUIDE_FR.md](BUILD_EXE_GUIDE_FR.md)
- **Comment obtenir l'exe** : [COMMENT_OBTENIR_EXE.md](COMMENT_OBTENIR_EXE.md)
- **Guide rapide** : [BUILD_EXE_QUICKREF.md](BUILD_EXE_QUICKREF.md)

## ☁️ Alternative : Build sur GitHub Actions

Vous pouvez aussi construire automatiquement sur GitHub :
1. Allez dans l'onglet **Actions** du repository
2. Sélectionnez **"Build Windows Executable"**
3. Cliquez **"Run workflow"**
4. Téléchargez l'exécutable une fois terminé

Plus d'infos : [COMMENT_OBTENIR_EXE.md](COMMENT_OBTENIR_EXE.md)

## 🆘 Support

Des questions ? Problèmes ?
- **Issues GitHub** : https://github.com/hackolite/CV_Studio/issues
- **Documentation** : Consultez les guides dans le repository

---

**Bonne construction ! 🎉**
