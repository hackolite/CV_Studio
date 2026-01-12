# Guide d'Installation de CV Studio sous Windows

> Guide complet d'installation de CV Studio pour les utilisateurs Windows

<img src="https://user-images.githubusercontent.com/37477845/172011014-23fb025e-68a5-4cb7-925f-c4417029966c.gif" loading="lazy" width="100%">

## 📋 Table des Matières

- [Vue d'ensemble](#-vue-densemble)
- [Configuration Requise](#-configuration-requise)
- [Méthode 1 : Exécutable Windows (RECOMMANDÉ)](#méthode-1--exécutable-windows-recommandé)
- [Méthode 2 : Installation Python Directe](#méthode-2--installation-python-directe)
- [Méthode 3 : Environnement Virtuel Python](#méthode-3--environnement-virtuel-python)
- [Méthode 4 : Installation via Pip](#méthode-4--installation-via-pip)
- [Vérification de l'Installation](#-vérification-de-linstallation)
- [Dépannage](#-dépannage)
- [Prochaines Étapes](#-prochaines-étapes)

---

## 🎯 Vue d'ensemble

CV Studio est une application professionnelle de traitement d'image basée sur un système de nœuds pour le développement, la vérification et la comparaison de vision par ordinateur.

Ce guide vous accompagne à travers toutes les méthodes d'installation disponibles sous Windows, de la plus simple (exécutable autonome) à la plus avancée (installation depuis les sources).

---

## 💻 Configuration Requise

### Configuration Minimale
- **Système d'exploitation** : Windows 10 ou Windows 11 (64-bit)
- **Processeur** : Intel Core i5 ou équivalent
- **Mémoire RAM** : 8 GB minimum (16 GB recommandés)
- **Espace disque** : 3 GB d'espace libre
- **Carte graphique** : Compatible OpenGL 3.0+

### Configuration Recommandée
- **Système d'exploitation** : Windows 11 (64-bit)
- **Processeur** : Intel Core i7 ou AMD Ryzen 7
- **Mémoire RAM** : 16 GB ou plus
- **Espace disque** : 5 GB d'espace libre
- **Carte graphique** : NVIDIA GPU avec support CUDA (pour l'accélération GPU)

### Logiciels Requis (selon la méthode)
- **Pour l'exécutable** : Aucun ! Tout est inclus
- **Pour l'installation Python** : 
  - Python 3.7 ou supérieur (Python 3.12 recommandé)
  - Git pour Windows (optionnel mais recommandé)

---

## Méthode 1 : Exécutable Windows (RECOMMANDÉ)

### ✅ Avantages
- ✅ **Aucune installation de Python requise**
- ✅ **Prêt à l'emploi** - Téléchargez et lancez
- ✅ **Tous les modèles inclus** - Modèles ONNX pour la détection d'objets
- ✅ **Idéal pour les débutants** - Aucune configuration nécessaire

### 📥 Option A : Construction Automatique via GitHub Actions (PLUS SIMPLE)

**Aucun outil de build local n'est requis !** Déclenchez simplement une construction sur GitHub :

#### Étapes

1. **Accédez à l'onglet Actions**
   - Allez sur : https://github.com/hackolite/CV_Studio/actions
   
2. **Cliquez sur "Build Windows Executable"** dans la barre latérale gauche

3. **Cliquez sur "Run workflow"**
   - Sélectionnez la branche (généralement `main`)
   - Cliquez sur le bouton vert "Run workflow"
   
4. **Attendez 10-15 minutes** que la construction se termine
   - Une coche verte ✓ apparaîtra lorsque c'est terminé
   
5. **Téléchargez l'exécutable**
   - Cliquez sur le workflow terminé
   - Descendez à la section "Artifacts"
   - Téléchargez `CV_Studio-Windows-Executable.zip` (environ 800 MB - 1.5 GB)
   
6. **Extrayez et Lancez**
   - Décompressez le fichier ZIP
   - Ouvrez le dossier `CV_Studio`
   - Double-cliquez sur `CV_Studio.exe`
   - C'est fait ! 🎉

### 📦 Option B : Télécharger depuis une Release

Si une release est disponible, téléchargez directement l'exécutable pré-construit :

1. Allez sur la page des Releases : https://github.com/hackolite/CV_Studio/releases
2. Téléchargez `CV_Studio-Windows.zip` depuis la dernière release
3. Extrayez le fichier ZIP
4. Lancez `CV_Studio.exe`

### 🔧 Option C : Construire Localement sur Votre Machine Windows

Si vous préférez construire l'exécutable vous-même :

#### Prérequis
- Python 3.7+ installé (testé avec Python 3.12)
- Git pour Windows
- Windows 10/11

#### Étapes de Construction

**Étape 1 : Installer Python**

1. Téléchargez Python depuis https://www.python.org/downloads/
2. **Important** : Cochez "Add Python to PATH" lors de l'installation
3. Vérifiez l'installation :
   ```cmd
   python --version
   ```

**Étape 2 : Cloner le Dépôt**

```cmd
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
```

**Étape 3 : Installer les Dépendances Principales**

```cmd
pip install -r requirements.txt
```

**Étape 4 : Installer les Dépendances de Build**

```cmd
pip install -r requirements-build.txt
```

**Étape 5 : Construire l'Exécutable**

```cmd
:: Build standard avec nettoyage
python build_exe.py --clean

:: Ou : Build sans fenêtre console (GUI uniquement)
python build_exe.py --clean --windowed

:: Ou : Avec une icône personnalisée
python build_exe.py --clean --icon votre_icone.ico
```

Le processus de build va :
1. ✅ Vérifier que toutes les dépendances sont installées
2. ✅ Nettoyer les artefacts de build précédents (si --clean est utilisé)
3. ✅ Empaqueter toutes les dépendances Python
4. ✅ Inclure tous les nœuds (Input, Process, DL, Audio, etc.)
5. ✅ Intégrer tous les modèles ONNX pour la détection d'objets
6. ✅ Créer l'exécutable autonome

**Temps de build** : Environ 5-15 minutes selon votre système.

**Étape 6 : Localiser Votre Exécutable**

Votre fichier .exe est prêt dans :
```
dist/CV_Studio/CV_Studio.exe
```

Le dossier `dist/CV_Studio/` contient :
- `CV_Studio.exe` - Exécutable principal
- `node/` - Toutes les implémentations de nœuds et modèles ONNX
- `node_editor/` - Noyau de l'éditeur et paramètres
- `src/` - Utilitaires sources
- `_internal/` - Runtime Python et dépendances

**Étape 7 : Tester l'Exécutable**

```cmd
cd dist\CV_Studio
CV_Studio.exe

:: Ou avec sortie de débogage
CV_Studio.exe --use_debug_print
```

### 📋 Contenu de l'Exécutable

- ✅ Tous les nœuds (Input, Process, DL, Audio, etc.)
- ✅ Tous les modèles ONNX pour la détection d'objets (YOLOX, YOLO, FreeYOLO, etc.)
- ✅ Runtime Python complet (aucune installation Python séparée nécessaire)
- ✅ Toutes les bibliothèques requises (OpenCV, DearPyGUI, ONNX Runtime, etc.)
- ✅ Fichiers de configuration et polices

**Taille** : Environ 800 MB - 1.5 GB

---

## Méthode 2 : Installation Python Directe

### ✅ Avantages
- ✅ **Installation rapide**
- ✅ **Modifications du code possibles**
- ✅ **Mises à jour faciles**
- ✅ **Idéal pour le développement**

### Prérequis

**Installer Python**

1. Téléchargez Python 3.7 ou supérieur depuis https://www.python.org/downloads/
2. **IMPORTANT** : Cochez "Add Python to PATH" lors de l'installation
3. Vérifiez l'installation :
   ```cmd
   python --version
   pip --version
   ```

**Installer Git (Optionnel)**

1. Téléchargez Git depuis https://git-scm.com/download/win
2. Installez avec les options par défaut

### Étapes d'Installation

**Étape 1 : Cloner ou Télécharger le Dépôt**

**Option A : Avec Git**
```cmd
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
```

**Option B : Téléchargement Manuel**
1. Allez sur https://github.com/hackolite/CV_Studio
2. Cliquez sur le bouton vert "Code"
3. Cliquez sur "Download ZIP"
4. Extrayez le ZIP dans un dossier de votre choix
5. Ouvrez un terminal dans ce dossier

**Étape 2 : Installer les Dépendances**

```cmd
pip install -r requirements.txt
```

Cette commande installe :
- opencv-contrib-python (≥4.5.5.64) - Traitement d'image
- onnxruntime-gpu - Inférence de modèles ML
- dearpygui (≥1.11.0) - Interface graphique
- mediapipe - Solutions ML
- protobuf (≥3.20.0) - Sérialisation de données
- filterpy (≥1.4.5) - Filtrage et suivi
- Et d'autres dépendances...

**Temps d'installation** : 5-10 minutes selon votre connexion Internet.

**Étape 3 : Lancer l'Application**

```cmd
python main.py
```

### Options de Ligne de Commande

```cmd
:: Utiliser un fichier de configuration personnalisé
python main.py --setting custom_config.json

:: Activer la sortie de débogage
python main.py --use_debug_print

:: Désactiver le dessin asynchrone (pour le débogage)
python main.py --unuse_async_draw

:: Combiner les options
python main.py --setting custom_config.json --use_debug_print
```

---

## Méthode 3 : Environnement Virtuel Python

### ✅ Avantages
- ✅ **Environnement isolé** - Pas de conflits avec d'autres projets Python
- ✅ **Gestion des dépendances** - Contrôle précis des versions
- ✅ **Meilleure pratique de développement**
- ✅ **Recommandé pour le développement**

### Prérequis

- Python 3.7+ installé (avec "Add to PATH" coché)
- Git pour Windows (optionnel)

### Étapes d'Installation

**Étape 1 : Cloner le Dépôt**

```cmd
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
```

**Étape 2 : Créer un Environnement Virtuel**

```cmd
python -m venv venv
```

Cela crée un dossier `venv` contenant un environnement Python isolé.

**Étape 3 : Activer l'Environnement Virtuel**

```cmd
:: Sur Windows (Command Prompt)
venv\Scripts\activate

:: Sur Windows (PowerShell)
venv\Scripts\Activate.ps1
```

**Note** : Si vous obtenez une erreur de politique d'exécution dans PowerShell :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Vous devriez voir `(venv)` au début de votre invite de commande, indiquant que l'environnement virtuel est actif.

**Étape 4 : Installer les Dépendances**

```cmd
pip install -r requirements.txt
```

**Étape 5 : Lancer l'Application**

```cmd
python main.py
```

**Désactiver l'Environnement Virtuel** (quand vous avez terminé)

```cmd
deactivate
```

### Utilisation Quotidienne

**Chaque fois que vous voulez utiliser CV Studio :**

```cmd
cd CV_Studio
venv\Scripts\activate
python main.py
```

**Pour quitter :**
- Fermez l'application
- Tapez `deactivate` dans le terminal

---

## Méthode 4 : Installation via Pip

### ✅ Avantages
- ✅ **Installation système**
- ✅ **Commande globale disponible**
- ✅ **Pas besoin de cloner le dépôt**

### Prérequis

**Installer les Outils de Build**

1. **Télécharger Visual Studio Build Tools**
   - Allez sur : https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Téléchargez "Build Tools for Visual Studio"
   - Lors de l'installation, sélectionnez "Desktop development with C++"

2. **Vérifier l'Installation**
   ```cmd
   cl
   ```
   Vous devriez voir des informations sur le compilateur Microsoft C/C++.

### Étapes d'Installation

**Étape 1 : Installer les Packages Requis**

```cmd
pip install Cython numpy wheel
```

**Étape 2 : Installer CV Studio depuis GitHub**

```cmd
pip install git+https://github.com/hackolite/CV_Studio.git
```

**Étape 3 : Lancer l'Application**

```cmd
ipn-editor
```

**Note** : Cette méthode peut nécessiter plus de temps de configuration et peut rencontrer des problèmes de dépendances. Nous recommandons la Méthode 2 ou 3 pour la plupart des utilisateurs.

---

## ✅ Vérification de l'Installation

### Test de Base

Après l'installation, vérifiez que CV Studio fonctionne correctement :

**1. Lancer l'Application**
   - L'interface graphique devrait s'ouvrir sans erreurs

**2. Tester un Pipeline Simple**

   a. **Ajouter un nœud Image**
      - Cliquez sur le menu : `Input → Image`
      - Cliquez sur la toile pour placer le nœud
   
   b. **Charger une Image**
      - Cliquez sur "Select Image" dans le nœud
      - Sélectionnez n'importe quelle image (jpg, png, bmp)
   
   c. **Ajouter un Nœud de Résultat**
      - Cliquez sur le menu : `Visual → Result Image`
      - Cliquez sur la toile pour placer le nœud
   
   d. **Connecter les Nœuds**
      - Glissez depuis la sortie du nœud Image vers l'entrée du nœud Result Image
      - Vous devriez voir votre image s'afficher !

**3. Tester un Nœud de Traitement**

   a. **Ajouter un nœud Blur**
      - Menu : `VisionProcess → Blur`
   
   b. **Connecter** : Image → Blur → Result Image
   
   c. **Ajuster les Paramètres**
      - Utilisez le curseur dans le nœud Blur
      - Vous devriez voir l'effet en temps réel

### Vérification Avancée

**Tester la Détection d'Objets**

1. Ajouter un nœud WebCam ou Image
2. Ajouter un nœud Object Detection (`VisionModel → Object Detection`)
3. Sélectionner un modèle (ex: YOLOX-Nano)
4. Ajouter un nœud Draw Information
5. Ajouter un nœud Result Image
6. Connecter : Input → Object Detection → Draw Information → Result Image

Si la détection fonctionne, votre installation est complète !

---

## 🔧 Dépannage

### Problème : Python n'est pas reconnu

**Erreur** : `'python' n'est pas reconnu en tant que commande interne`

**Solution** :
1. Réinstallez Python et **cochez "Add Python to PATH"**
2. Ou ajoutez manuellement Python au PATH :
   - Recherchez "Variables d'environnement" dans Windows
   - Cliquez sur "Variables d'environnement"
   - Dans "Variables système", trouvez "Path"
   - Ajoutez : `C:\Users\VotreNom\AppData\Local\Programs\Python\Python3X`
   - Ajoutez : `C:\Users\VotreNom\AppData\Local\Programs\Python\Python3X\Scripts`
3. Redémarrez votre terminal

### Problème : L'application ne démarre pas

**Solution 1 : Installer Visual C++ Redistributable**
- Téléchargez : https://aka.ms/vs/17/release/vc_redist.x64.exe
- Installez et redémarrez votre ordinateur

**Solution 2 : Vérifier les Dépendances**
```cmd
pip install -r requirements.txt --upgrade
```

**Solution 3 : Utiliser le Mode Debug**
```cmd
python main.py --use_debug_print
```
Cela affichera les messages d'erreur détaillés.

### Problème : Erreur d'Installation de Pip

**Erreur** : `Could not install packages due to an OSError`

**Solution** :
```cmd
:: Utiliser les droits administrateur
pip install -r requirements.txt --user

:: Ou mettre à jour pip
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Problème : La Webcam n'est pas détectée

**Solution** :
1. Fermez les autres applications utilisant la webcam
2. Vérifiez les permissions de la webcam dans Windows
3. Essayez différents numéros de périphérique dans le nœud WebCam (0, 1, 2...)

### Problème : Erreur GPU / CUDA

**Erreur** : Messages d'erreur liés à CUDA ou GPU

**Solution** :
1. Vérifiez si vous avez une carte NVIDIA : `nvidia-smi`
2. Si pas de GPU NVIDIA, utilisez la version CPU :
   ```cmd
   pip uninstall onnxruntime-gpu
   pip install onnxruntime
   ```
3. Dans l'application, décochez l'option "GPU" dans les nœuds DL

### Problème : Erreur MediaPipe

**Erreur** : `No module named 'mediapipe'` ou erreur protobuf

**Solution** :
```cmd
pip install mediapipe
pip install protobuf==3.20.0
```

### Problème : L'Exécutable ne Démarre pas

**Solution 1 : Vérifier l'Antivirus**
- Votre antivirus peut bloquer l'exécutable
- Ajoutez CV_Studio.exe à la liste blanche

**Solution 2 : Lancer depuis la Ligne de Commande**
```cmd
cd dist\CV_Studio
CV_Studio.exe --use_debug_print
```

**Solution 3 : Reconstruire l'Exécutable**
```cmd
python build_exe.py --clean
```

### Problème : FPS Faible / Traitement Lent

**Solutions** :
1. **Réduire la Résolution**
   - Ajoutez un nœud Resize au début de votre pipeline
   - Utilisez une résolution plus petite (ex: 640x480)

2. **Activer le GPU** (si vous avez une carte NVIDIA)
   - Cochez "GPU" dans les nœuds DL
   - Assurez-vous d'avoir `onnxruntime-gpu` installé

3. **Fermer les Applications Inutiles**
   - Libérez de la mémoire RAM
   - Fermez les autres applications gourmandes

### Problème : Erreur lors de l'Importation/Exportation

**Solution** :
1. Vérifiez que vous écrivez dans un dossier accessible
2. Assurez-vous que le fichier JSON est valide
3. Essayez un chemin sans caractères spéciaux

### Obtenir de l'Aide

Si vous rencontrez toujours des problèmes :

1. **GitHub Issues** : https://github.com/hackolite/CV_Studio/issues
   - Recherchez si votre problème existe déjà
   - Sinon, créez une nouvelle issue avec :
     - Version de Windows
     - Version de Python
     - Message d'erreur complet
     - Étapes pour reproduire le problème

2. **GitHub Discussions** : https://github.com/hackolite/CV_Studio/discussions
   - Pour les questions générales
   - Partage d'expériences avec d'autres utilisateurs

---

## 🚀 Prochaines Étapes

### Apprendre à Utiliser CV Studio

1. **Guide de Démarrage Rapide**
   - Voir la section "Usage" dans [README.md](README.md)
   - Essayez les exemples de pipeline

2. **Explorer les Nœuds**
   - Parcourez les différentes catégories de nœuds
   - Testez les nœuds de traitement d'image
   - Essayez les nœuds de Deep Learning

3. **Exemples**
   - Consultez le dossier [examples/](examples/)
   - Essayez les exemples de code

### Développement Avancé

1. **Créer des Nœuds Personnalisés**
   - Voir [src/README.md](src/README.md)
   - Consultez [src/nodes/examples/](src/nodes/examples/)

2. **Architecture et Tests**
   - Lisez [TIMESTAMPED_QUEUE_SYSTEM.md](TIMESTAMPED_QUEUE_SYSTEM.md)
   - Exécutez les tests : `python -m pytest tests/ -v`

3. **Contribuer**
   - Fork le dépôt
   - Créez vos améliorations
   - Soumettez une Pull Request

### Ressources Utiles

- **Documentation Complète** : [README.md](README.md)
- **Guide de Build d'Exécutable** : [BUILD_EXE_GUIDE_FR.md](BUILD_EXE_GUIDE_FR.md)
- **Comment Obtenir l'Exécutable** : [COMMENT_OBTENIR_EXE.md](COMMENT_OBTENIR_EXE.md)
- **Architecture Technique** : [src/README.md](src/README.md)

---

## 📞 Support et Communauté

- **Issues** : https://github.com/hackolite/CV_Studio/issues
- **Discussions** : https://github.com/hackolite/CV_Studio/discussions
- **Documentation** : Consultez les fichiers .md dans ce dépôt

---

<div align="center">

**Fait avec ❤️ pour la Communauté de Vision par Ordinateur**

⭐ Donnez une étoile à ce dépôt si vous le trouvez utile !

**Profitez de CV Studio ! 🎨**

</div>
