# Guide Complet de Construction de l'Exécutable CV Studio

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Installation des Dépendances](#installation-des-dépendances)
4. [Construction de l'Exécutable](#construction-de-lexécutable)
5. [Création de l'Installateur Windows](#création-de-linstallateur-windows)
6. [Distribution](#distribution)
7. [Dépannage](#dépannage)
8. [FAQ](#faq)

---

## 🎯 Vue d'ensemble

Ce guide explique comment créer un exécutable Windows autonome (.exe) et un installateur pour CV Studio. L'exécutable inclut :

- ✅ **Runtime Python complet** - Aucune installation Python requise
- ✅ **Toutes les dépendances** - OpenCV, DearPyGUI, ONNX Runtime, etc.
- ✅ **Modèles ONNX** - Tous les modèles de détection d'objets (YOLOX, YOLO, etc.)
- ✅ **Tous les nœuds** - Input, Process, DL, Audio, etc.
- ✅ **Accélération GPU** - Support ONNX Runtime GPU (CUDA)

**Taille finale :** Environ 800 MB - 1.5 GB

---

## 🔧 Prérequis

### Système d'exploitation

- **Windows 10/11** (64-bit) - Requis pour créer l'exécutable Windows
- **Windows 7 SP1** ou supérieur - Version minimale pour exécuter l'application

### Logiciels requis

#### 1. Python

**Version recommandée :** Python 3.8 à 3.12

**Installation :**

```bash
# Télécharger depuis python.org
https://www.python.org/downloads/

# Lors de l'installation :
# ☑ Cochez "Add Python to PATH"
# ☑ Cochez "Install pip"
```

**Vérification :**

```bash
python --version
# Devrait afficher : Python 3.x.x

pip --version
# Devrait afficher : pip x.x.x
```

#### 2. Git (optionnel mais recommandé)

```bash
# Télécharger depuis :
https://git-scm.com/download/win

# Ou utiliser GitHub Desktop :
https://desktop.github.com/
```

#### 3. Visual C++ Redistributable

**Important :** Requis pour l'exécution de l'application compilée.

```bash
# Télécharger et installer :
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

#### 4. Inno Setup (pour créer l'installateur)

**Version recommandée :** Inno Setup 6.2 ou supérieur

```bash
# Télécharger depuis :
https://jrsoftware.org/isdl.php

# Télécharger le fichier "innosetup-6.2.x.exe"
# Installer avec les options par défaut
```

### Configuration GPU (optionnel)

Pour activer l'accélération GPU avec ONNX Runtime :

**Prérequis GPU :**
- GPU NVIDIA compatible CUDA
- CUDA Toolkit 11.x
- cuDNN 8.x

**Installation CUDA :**

```bash
# 1. Télécharger CUDA Toolkit
https://developer.nvidia.com/cuda-downloads

# 2. Installer CUDA Toolkit 11.8 (recommandé)
# Suivre l'assistant d'installation

# 3. Vérifier l'installation
nvcc --version
```

**Note :** Si vous n'avez pas de GPU NVIDIA, l'application fonctionnera en mode CPU uniquement.

---

## 📦 Installation des Dépendances

### Étape 1 : Cloner le dépôt

```bash
# Avec Git
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio

# Ou télécharger le ZIP depuis GitHub
# Puis extraire et ouvrir le terminal dans le dossier
```

### Étape 2 : Créer un environnement virtuel (recommandé)

```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Sur Windows :
venv\Scripts\activate

# Vous devriez voir (venv) dans votre terminal
```

### Étape 3 : Installer les dépendances principales

```bash
# Mettre à jour pip
python -m pip install --upgrade pip

# Installer les dépendances principales
pip install -r requirements.txt
```

**Dépendances principales :**
- `opencv-contrib-python` - Traitement d'images
- `onnxruntime-gpu` - Inférence de modèles ONNX avec GPU
- `dearpygui` - Interface graphique
- `mediapipe` - Solutions ML
- `librosa` - Traitement audio
- `matplotlib` - Visualisation
- Et plus...

### Étape 4 : Installer les dépendances de build

```bash
pip install -r requirements-build.txt
```

**Dépendances de build :**
- `pyinstaller>=5.0.0` - Création d'exécutables

### Étape 5 : Vérifier l'installation

```bash
# Tester l'application
python main.py

# L'application devrait se lancer
# Si elle fonctionne, les dépendances sont correctement installées
```

---

## 🏗️ Construction de l'Exécutable

### Méthode 1 : Build Standard (Recommandé)

```bash
# Build avec nettoyage
python build_exe.py --clean

# Durée : 5-15 minutes selon votre système
```

**Ce que fait cette commande :**
1. ✅ Vérifie que toutes les dépendances sont installées
2. ✅ Nettoie les anciens artifacts de build
3. ✅ Package toutes les dépendances Python
4. ✅ Inclut tous les nœuds et modèles ONNX
5. ✅ Crée l'exécutable dans `dist/CV_Studio/`

### Méthode 2 : Build sans Console (Mode GUI)

```bash
# Build en mode fenêtré (sans console)
python build_exe.py --clean --windowed
```

**Utiliser cette option quand :**
- Vous voulez une interface propre sans fenêtre de console
- Pour la distribution finale aux utilisateurs
- **Note :** Plus difficile de voir les erreurs en mode fenêtré

### Méthode 3 : Build avec Icône Personnalisée

```bash
# Avec icône personnalisée
python build_exe.py --clean --icon votre_icone.ico

# L'icône doit être un fichier .ico
# Taille recommandée : 256x256 pixels
```

### Méthode 4 : Build de Débogage

```bash
# Build avec informations de débogage
python build_exe.py --clean --debug

# Utile pour diagnostiquer les problèmes
```

### Options de Build Avancées

```bash
# Combinaison d'options
python build_exe.py --clean --windowed --icon mon_icone.ico

# Options disponibles :
# --clean          : Nettoie les dossiers de build avant
# --windowed       : Cache la fenêtre console
# --debug          : Build avec informations de débogage
# --icon FICHIER   : Utilise une icône personnalisée
# --help           : Affiche l'aide
```

### Sortie du Build

Après un build réussi, vous trouverez :

```
CV_Studio/
├── dist/
│   └── CV_Studio/                    ← Dossier de distribution
│       ├── CV_Studio.exe            ← Exécutable principal
│       ├── README.txt               ← Documentation
│       ├── node/                    ← Tous les nœuds
│       │   ├── DLNode/             ← Nœuds Deep Learning
│       │   │   └── object_detection/
│       │   │       └── */model/*.onnx  ← Modèles ONNX
│       │   ├── InputNode/
│       │   ├── ProcessNode/
│       │   └── ...
│       ├── node_editor/             ← Éditeur de nœuds
│       ├── src/                     ← Utilitaires source
│       └── _internal/               ← Runtime Python et DLLs
│
├── build/                           ← Fichiers temporaires (peut être supprimé)
└── CV_Studio.spec                   ← Fichier de configuration PyInstaller
```

### Vérification du Build

```bash
# Naviguer vers le dossier de distribution
cd dist\CV_Studio

# Tester l'exécutable
CV_Studio.exe

# Ou avec sortie de débogage
CV_Studio.exe --use_debug_print
```

**Points de vérification :**
- ✅ L'application se lance sans erreurs
- ✅ Les nœuds sont visibles dans le menu
- ✅ Vous pouvez ajouter et connecter des nœuds
- ✅ Les nœuds de détection d'objets peuvent charger les modèles ONNX
- ✅ Les nœuds de traitement d'image fonctionnent correctement

---

## 📀 Création de l'Installateur Windows

### Pourquoi créer un installateur ?

Un installateur offre :
- ✅ Installation professionnelle dans Program Files
- ✅ Raccourcis dans le menu Démarrer et sur le Bureau
- ✅ Désinstallation propre via le Panneau de configuration
- ✅ Vérifications des prérequis système
- ✅ Expérience utilisateur améliorée

### Prérequis

1. **Build réussi** - `dist/CV_Studio/` doit exister
2. **Inno Setup installé** - Voir section Prérequis ci-dessus

### Étape 1 : Vérifier le script d'installation

Le fichier `installer.iss` est déjà fourni. Il configure :
- Nom de l'application et version
- Fichiers à inclure
- Icônes et raccourcis
- Vérifications des prérequis
- Messages en français et anglais

### Étape 2 : Compiler l'installateur

**Méthode A : Via l'interface graphique Inno Setup**

1. Ouvrir **Inno Setup Compiler**
2. Fichier → Ouvrir → Sélectionner `installer.iss`
3. Build → Compiler (ou F9)
4. L'installateur sera créé dans `installer_output/`

**Méthode B : Via la ligne de commande**

```bash
# Compiler avec ISCC (Inno Setup Command Line Compiler)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# Ou si Inno Setup est dans le PATH
iscc installer.iss
```

### Étape 3 : Localiser l'installateur

```bash
installer_output/
└── CV_Studio_Setup_v1.0.0.exe     ← Installateur Windows
```

**Taille :** Environ 800 MB - 1.5 GB (compressé)

### Étape 4 : Tester l'installateur

```bash
# Exécuter l'installateur
installer_output\CV_Studio_Setup_v1.0.0.exe

# L'assistant d'installation guidera l'utilisateur :
# 1. Bienvenue
# 2. Licence
# 3. Sélection du dossier d'installation
# 4. Sélection des composants
# 5. Création de raccourcis
# 6. Installation
# 7. Terminé
```

### Personnalisation de l'installateur

Éditer `installer.iss` pour personnaliser :

```pascal
; Informations de base
#define MyAppName "CV Studio"
#define MyAppVersion "1.0.0"        ; ← Changer la version
#define MyAppPublisher "hackolite"  ; ← Votre nom/organisation

; Icône de l'installateur
SetupIconFile=node_editor\setting\icon.ico  ; ← Votre icône .ico

; Dossier de sortie
OutputDir=installer_output
OutputBaseFilename=CV_Studio_Setup_v{#MyAppVersion}  ; ← Nom du fichier
```

---

## 📤 Distribution

### Format 1 : Dossier ZIP

**Avantages :**
- Simple à créer
- Pas d'installation requise
- Portable

**Création :**

```bash
# Naviguer vers dist
cd dist

# Créer une archive ZIP
# Avec PowerShell :
Compress-Archive -Path CV_Studio -DestinationPath CV_Studio_v1.0.0.zip

# Avec 7-Zip (si installé) :
7z a CV_Studio_v1.0.0.zip CV_Studio
```

**Instructions pour les utilisateurs :**
1. Télécharger le fichier ZIP
2. Extraire dans un dossier
3. Exécuter `CV_Studio.exe`

### Format 2 : Installateur Windows

**Avantages :**
- Installation professionnelle
- Intégration système (menu Démarrer, raccourcis)
- Désinstallation propre
- Vérification des prérequis

**Distribution :**
- Partager `CV_Studio_Setup_v1.0.0.exe`
- Les utilisateurs double-cliquent et suivent l'assistant

### Distribution sur GitHub

```bash
# 1. Créer une nouvelle release sur GitHub
https://github.com/votre-nom/CV_Studio/releases/new

# 2. Informations de la release :
Tag version: v1.0.0
Release title: CV Studio v1.0.0
Description:
  - Fonctionnalités principales
  - Corrections de bugs
  - Notes de version

# 3. Téléverser les fichiers :
- CV_Studio_Setup_v1.0.0.exe    (Installateur)
- CV_Studio_v1.0.0.zip           (Version portable)
- README.txt                     (Instructions)
- CHANGELOG.md                   (Historique des modifications)

# 4. Publier la release
```

### Informations à fournir aux utilisateurs

**Fichier README.txt pour la distribution :**

```markdown
# CV Studio v1.0.0

## Configuration Requise

- Windows 10/11 (64-bit) recommandé
- Windows 7 SP1 minimum
- 4 GB RAM minimum (8 GB recommandé)
- 2 GB espace disque
- GPU NVIDIA (optionnel, pour l'accélération)

## Installation

### Méthode 1 : Installateur (Recommandé)
1. Exécuter CV_Studio_Setup_v1.0.0.exe
2. Suivre l'assistant d'installation
3. Lancer depuis le menu Démarrer

### Méthode 2 : Version Portable
1. Extraire CV_Studio_v1.0.0.zip
2. Ouvrir le dossier CV_Studio
3. Double-cliquer sur CV_Studio.exe

## Prérequis

Si l'application ne démarre pas :
1. Installer Visual C++ Redistributable :
   https://aka.ms/vs/17/release/vc_redist.x64.exe

2. Pour l'accélération GPU :
   - GPU NVIDIA requis
   - Pilotes NVIDIA à jour

## Support

- Documentation : https://github.com/hackolite/CV_Studio
- Issues : https://github.com/hackolite/CV_Studio/issues
```

---

## 🔧 Dépannage

### Problème : PyInstaller non trouvé

```bash
# Solution :
pip install pyinstaller

# Ou :
pip install -r requirements-build.txt
```

### Problème : Dépendances manquantes

```bash
# Erreur lors du build mentionnant des packages manquants

# Solution :
pip install -r requirements.txt
pip install -r requirements-build.txt

# Vérifier :
python build_exe.py
# Suivre les suggestions affichées
```

### Problème : Build échoue avec erreur de mémoire

```bash
# Si vous obtenez "MemoryError" ou le build s'arrête

# Solution :
# 1. Fermer les autres applications
# 2. Désactiver UPX (compression)

# Éditer CV_Studio.spec :
exe = EXE(
    ...
    upx=False,  # ← Changer True en False
    ...
)

coll = COLLECT(
    ...
    upx=False,  # ← Changer True en False
    ...
)

# Puis rebuilder :
python build_exe.py --clean
```

### Problème : L'exe ne démarre pas

**Symptôme :** Double-clic sur l'exe ne fait rien

**Solutions :**

1. **Exécuter depuis la ligne de commande pour voir les erreurs :**

```bash
cd dist\CV_Studio
CV_Studio.exe --use_debug_print
```

2. **Installer Visual C++ Redistributable :**

```bash
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

3. **Vérifier l'antivirus :**
- Certains antivirus bloquent les exécutables PyInstaller
- Ajouter une exception pour CV_Studio.exe

4. **Vérifier les permissions :**
- Clic droit sur CV_Studio.exe
- Propriétés → Débloquer (si présent)

### Problème : Modèles ONNX non trouvés

```bash
# Erreur : "Model file not found"

# Solution :
# Vérifier que le dossier node/DLNode est intact

# Structure attendue :
dist/CV_Studio/node/DLNode/
├── object_detection/
│   ├── yolox/
│   │   └── model/
│   │       └── *.onnx
│   ├── yolo11/
│   │   └── model/
│   │       └── *.onnx
│   └── ...

# Si manquant, rebuilder :
python build_exe.py --clean
```

### Problème : GPU non détecté

**Symptôme :** L'application utilise le CPU même avec une GPU NVIDIA

**Solutions :**

1. **Vérifier CUDA :**

```bash
nvcc --version
nvidia-smi
```

2. **Vérifier onnxruntime-gpu :**

```bash
# Dans l'environnement de build :
pip list | grep onnx

# Devrait afficher :
# onnxruntime-gpu    x.x.x
```

3. **Tester le GPU dans l'application :**
- Ajouter un nœud Object Detection
- Cocher la case "GPU"
- Si erreur, le GPU n'est pas disponible

### Problème : Inno Setup ne compile pas

**Erreur :** "File not found" dans Inno Setup

**Solutions :**

1. **Vérifier que le build existe :**

```bash
# Le dossier dist/CV_Studio doit exister
dir dist\CV_Studio\CV_Studio.exe
```

2. **Vérifier les chemins dans installer.iss :**

```pascal
; Vérifier ces lignes :
Source: "dist\CV_Studio\*"; ...        ; ← Chemin correct ?
SetupIconFile=node_editor\setting\icon.ico  ; ← Fichier existe ?
LicenseFile=LICENSE                    ; ← Fichier existe ?
```

3. **Créer les dossiers manquants :**

```bash
mkdir installer_output
```

### Problème : Installateur trop gros

**Symptôme :** L'installateur fait plus de 2 GB

**Solutions :**

1. **Augmenter la compression dans installer.iss :**

```pascal
Compression=lzma2/ultra64     ; ← Compression maximale
SolidCompression=yes
```

2. **Retirer les modèles inutilisés :**
- Éditer `CV_Studio.spec`
- Exclure certains modèles ONNX lourds

### Problème : Application lente au démarrage

**Symptôme :** L'exe prend 30+ secondes à démarrer

**Solutions :**

1. **Désactiver la vérification antivirus en temps réel** pour le dossier
2. **Utiliser le mode dossier** (pas --onefile) - déjà le cas par défaut
3. **Ajouter une exception dans Windows Defender :**
   - Paramètres → Virus & threat protection
   - Gérer les paramètres
   - Ajouter une exclusion → Dossier
   - Sélectionner le dossier CV_Studio

---

## ❓ FAQ

### Q1 : PyTorch est-il nécessaire ?

**R :** Non, CV Studio utilise **ONNX Runtime** pour l'inférence des modèles. PyTorch n'est pas requis sauf si :
- Vous voulez entraîner de nouveaux modèles
- Vous voulez convertir des modèles PyTorch en ONNX
- Vous développez de nouveaux nœuds Deep Learning utilisant PyTorch

**Pour ajouter PyTorch (optionnel) :**

```bash
# Pour CPU uniquement :
pip install torch torchvision

# Pour GPU (CUDA 11.8) :
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**Note :** L'ajout de PyTorch augmentera la taille de l'exécutable d'environ 1-2 GB.

### Q2 : Quelle est la différence entre ONNX Runtime et PyTorch ?

**R :**
- **ONNX Runtime** : Moteur d'inférence léger et rapide (CV Studio l'utilise)
- **PyTorch** : Framework de deep learning complet pour l'entraînement et l'inférence

Pour la distribution, ONNX Runtime est préférable car :
- Plus léger (moins de dépendances)
- Plus rapide pour l'inférence
- Compatible avec de nombreux frameworks

### Q3 : Puis-je créer un exécutable plus petit ?

**R :** Oui, plusieurs options :

1. **Retirer les modèles ONNX inutilisés** (économise 200-500 MB)
2. **Utiliser onnxruntime au lieu de onnxruntime-gpu** (économise 100-200 MB)
3. **Retirer les nœuds inutilisés**
4. **Augmenter la compression UPX**

**Attention :** Un exe plus petit = moins de fonctionnalités

### Q4 : L'application fonctionne sans GPU ?

**R :** Oui ! L'application fonctionne en mode CPU par défaut. Le GPU est optionnel pour :
- Accélérer l'inférence des modèles ONNX
- Traitement vidéo plus rapide
- Détection d'objets en temps réel

### Q5 : Puis-je distribuer l'application commercialement ?

**R :** CV Studio est sous licence **Apache 2.0**, vous pouvez donc :
- ✅ Utiliser commercialement
- ✅ Modifier le code
- ✅ Distribuer
- ✅ Breveter

**Mais vous devez :**
- Inclure la licence Apache 2.0
- Mentionner les changements effectués
- Vérifier les licences des modèles ONNX individuels

### Q6 : Comment mettre à jour la version ?

**R :**

1. **Changer la version dans le code**

```python
# Dans main.py ou un fichier config
VERSION = "1.0.1"
```

2. **Changer dans installer.iss**

```pascal
#define MyAppVersion "1.0.1"
```

3. **Rebuilder**

```bash
python build_exe.py --clean
iscc installer.iss
```

### Q7 : Puis-je créer un installateur pour Linux/Mac ?

**R :** Ce guide est spécifique à Windows. Pour Linux/Mac :

**Linux :**
- Utiliser PyInstaller (similaire)
- Créer un paquet .deb (Debian/Ubuntu)
- Créer un paquet .rpm (RedHat/Fedora)
- Utiliser AppImage pour portabilité

**Mac :**
- Utiliser PyInstaller
- Créer une application .app
- Créer un .dmg pour distribution
- Signer l'application (requis pour macOS)

### Q8 : Comment déboguer l'application compilée ?

**R :**

1. **Build en mode debug :**

```bash
python build_exe.py --clean --debug
```

2. **Exécuter avec sortie debug :**

```bash
CV_Studio.exe --use_debug_print
```

3. **Vérifier les logs :**
- Les logs sont affichés dans la console
- Utiliser --console=True dans le spec file

4. **Utiliser un outil de monitoring :**
- Process Explorer
- Process Monitor
- DebugView

### Q9 : Puis-je inclure mes propres modèles ONNX ?

**R :** Oui !

1. **Ajouter le modèle dans le dossier approprié :**

```
node/DLNode/object_detection/mon_modele/model/mon_modele.onnx
```

2. **Créer le nœud correspondant** (voir documentation développement)

3. **Rebuilder :**

```bash
python build_exe.py --clean
```

Le modèle sera automatiquement inclus dans l'exe.

### Q10 : Combien de temps prend la construction ?

**R :** Temps approximatifs :

- **Première build complète :** 10-20 minutes
- **Rebuild (avec --clean) :** 5-10 minutes
- **Build incrémentale :** 2-5 minutes
- **Compilation installateur :** 1-3 minutes

**Facteurs influençant la durée :**
- Vitesse du CPU
- Vitesse du disque (SSD vs HDD)
- Antivirus (peut ralentir considérablement)
- Taille des modèles ONNX

---

## 📝 Résumé des Commandes

```bash
# 1. Installation initiale
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-build.txt

# 2. Tester l'application
python main.py

# 3. Construire l'exécutable
python build_exe.py --clean

# 4. Créer l'installateur
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# 5. Tester
dist\CV_Studio\CV_Studio.exe
installer_output\CV_Studio_Setup_v1.0.0.exe

# 6. Distribuer
# - Partager installer_output\CV_Studio_Setup_v1.0.0.exe
# - Ou créer un ZIP de dist\CV_Studio
```

---

## 🎓 Ressources Supplémentaires

### Documentation

- [README.md](README.md) - Documentation principale
- [BUILD_EXE_GUIDE.md](BUILD_EXE_GUIDE.md) - Guide en anglais
- [BUILD_EXE_QUICKREF.md](BUILD_EXE_QUICKREF.md) - Référence rapide

### Liens Utiles

- [PyInstaller Documentation](https://pyinstaller.org/)
- [Inno Setup Documentation](https://jrsoftware.org/ishelp/)
- [ONNX Runtime](https://onnxruntime.ai/)
- [Python Packaging Guide](https://packaging.python.org/)

### Support

- **GitHub Issues :** [https://github.com/hackolite/CV_Studio/issues](https://github.com/hackolite/CV_Studio/issues)
- **Discussions :** [https://github.com/hackolite/CV_Studio/discussions](https://github.com/hackolite/CV_Studio/discussions)

---

## ✅ Checklist de Distribution

Avant de distribuer votre application :

### Tests

- [ ] L'exe se lance sans erreurs
- [ ] Tous les nœuds sont accessibles
- [ ] Les nœuds de traitement d'image fonctionnent
- [ ] Les modèles ONNX se chargent correctement
- [ ] La détection d'objets fonctionne
- [ ] L'accélération GPU fonctionne (si applicable)
- [ ] La webcam peut être ouverte
- [ ] Les vidéos peuvent être lues
- [ ] Export/Import de graphes fonctionne

### Documentation

- [ ] README.txt inclus
- [ ] LICENCE incluse
- [ ] Instructions d'installation claires
- [ ] Configuration système requise documentée
- [ ] Liens de support fournis

### Distribution

- [ ] Fichiers signés (optionnel mais recommandé)
- [ ] Version testée sur une machine propre
- [ ] Taille du fichier acceptable (< 2 GB)
- [ ] Instructions de désinstallation
- [ ] Notes de version (CHANGELOG)

---

**🎉 Félicitations ! Vous avez maintenant un exécutable Windows professionnel de CV Studio !**

Pour toute question ou problème, n'hésitez pas à ouvrir une issue sur GitHub.
