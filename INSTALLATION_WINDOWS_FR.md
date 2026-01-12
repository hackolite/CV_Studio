# Guide d'Installation et d'Exécution de CV Studio sous Windows

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Prérequis](#prérequis)
- [Installation de Python](#installation-de-python)
- [Installation de CV Studio](#installation-de-cv-studio)
- [Lancement de l'application](#lancement-de-lapplication)
- [Vérification de l'installation](#vérification-de-linstallation)
- [Dépannage](#dépannage)
- [Alternative : Exécutable Windows](#alternative--exécutable-windows)

## Vue d'ensemble

Ce guide explique comment installer et exécuter CV Studio sous Windows pour le développement et l'utilisation quotidienne. Si vous souhaitez créer un exécutable autonome (.exe), consultez plutôt [BUILD_EXE_GUIDE_FR.md](BUILD_EXE_GUIDE_FR.md) ou [COMMENT_OBTENIR_EXE.md](COMMENT_OBTENIR_EXE.md).

## Prérequis

### Configuration minimale requise

- **Système d'exploitation** : Windows 10 ou supérieur (64 bits recommandé)
- **RAM** : 8 Go minimum, 16 Go recommandé
- **Espace disque** : 5 Go d'espace libre
- **Processeur** : Processeur multi-cœurs moderne
- **GPU** : Optionnel mais recommandé pour les nœuds Deep Learning (NVIDIA avec support CUDA)

### Logiciels requis

1. **Python 3.7 ou supérieur** (3.10 ou 3.11 recommandé)
2. **Git pour Windows** (optionnel mais recommandé)
3. **Microsoft Visual C++ Redistributable** (généralement déjà installé)

## Installation de Python

### Méthode 1 : Installation depuis python.org (RECOMMANDÉ)

1. **Téléchargez Python** depuis le site officiel :
   - Allez sur [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - Téléchargez la dernière version de Python 3.11 ou 3.10 pour Windows

2. **Lancez l'installateur** :
   - ⚠️ **IMPORTANT** : Cochez "Add Python to PATH" en bas de la fenêtre
   - Cliquez sur "Install Now"
   - Attendez la fin de l'installation

3. **Vérifiez l'installation** :
   ```cmd
   python --version
   ```
   Vous devriez voir quelque chose comme `Python 3.11.x` ou `Python 3.10.x`

   Si la commande `python` ne fonctionne pas, essayez :
   ```cmd
   python3 --version
   ```
   ou
   ```cmd
   py --version
   ```

### Méthode 2 : Installation via Microsoft Store

1. Ouvrez le **Microsoft Store**
2. Recherchez "Python"
3. Installez **Python 3.11** ou **Python 3.10**
4. Python sera automatiquement ajouté au PATH

## Installation de CV Studio

### Étape 1 : Ouvrir l'invite de commandes (PowerShell ou CMD)

**Option A - PowerShell (Recommandé)** :
- Appuyez sur `Windows + X`
- Sélectionnez "Windows PowerShell" ou "Terminal"

**Option B - Invite de commandes** :
- Appuyez sur `Windows + R`
- Tapez `cmd` et appuyez sur Entrée

### Étape 2 : Cloner le dépôt

Si vous avez **Git installé** :

```cmd
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
```

Si vous n'avez **pas Git** :

1. Allez sur [https://github.com/hackolite/CV_Studio](https://github.com/hackolite/CV_Studio)
2. Cliquez sur le bouton vert "Code" → "Download ZIP"
3. Extrayez le fichier ZIP dans un dossier de votre choix
4. Ouvrez l'invite de commandes dans ce dossier :
   - Dans l'Explorateur Windows, maintenez `Shift` + clic droit dans le dossier
   - Sélectionnez "Ouvrir PowerShell ici" ou "Ouvrir une fenêtre de commande ici"

### Étape 3 : Créer un environnement virtuel (Recommandé)

Un environnement virtuel isole les dépendances de CV Studio :

```cmd
python -m venv venv
```

Si la commande `python` ne fonctionne pas, essayez `python3` ou `py` :
```cmd
python3 -m venv venv
```
ou
```cmd
py -m venv venv
```

### Étape 4 : Activer l'environnement virtuel

**Dans PowerShell** :
```powershell
.\venv\Scripts\Activate.ps1
```

Si vous obtenez une erreur de politique d'exécution, exécutez d'abord :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Puis réessayez d'activer l'environnement.

**Dans CMD** :
```cmd
venv\Scripts\activate.bat
```

Vous devriez voir `(venv)` apparaître au début de votre ligne de commande.

### Étape 5 : Mettre à jour pip

```cmd
python -m pip install --upgrade pip
```

### Étape 6 : Installer les dépendances

```cmd
pip install -r requirements.txt
```

Cette commande installera toutes les bibliothèques nécessaires :
- OpenCV pour le traitement d'images
- DearPyGUI pour l'interface graphique
- ONNX Runtime pour les modèles de Deep Learning
- MediaPipe pour les modèles ML
- Et autres dépendances

⏱️ **L'installation peut prendre 5-10 minutes** selon votre connexion Internet.

## Lancement de l'application

Une fois l'installation terminée, vous pouvez lancer CV Studio :

### Méthode standard

```cmd
python main.py
```

### Avec options de débogage

```cmd
# Activer les messages de débogage
python main.py --use_debug_print

# Désactiver le dessin asynchrone (en cas de problème d'affichage)
python main.py --unuse_async_draw

# Utiliser un fichier de configuration personnalisé
python main.py --setting chemin\vers\config.json

# Combiner plusieurs options
python main.py --use_debug_print --unuse_async_draw
```

### À chaque fois que vous voulez utiliser CV Studio

1. Ouvrez l'invite de commandes dans le dossier CV_Studio
2. Activez l'environnement virtuel :
   - PowerShell : `.\venv\Scripts\Activate.ps1`
   - CMD : `venv\Scripts\activate.bat`
3. Lancez l'application : `python main.py`

## Vérification de l'installation

### Test rapide

Une fois l'application lancée :

1. **L'interface graphique devrait s'ouvrir** avec une zone de travail vide
2. **Ajoutez un nœud Image** :
   - Cliquez sur le menu "Input" → "Image"
   - Cliquez sur la zone de travail pour placer le nœud
3. **Ajoutez un nœud Result Image** :
   - Cliquez sur le menu "Visual" → "Result Image"
   - Placez-le à côté du premier nœud
4. **Connectez les nœuds** :
   - Glissez depuis la sortie du nœud Image vers l'entrée du nœud Result Image
5. **Chargez une image** :
   - Cliquez sur "Select Image" dans le nœud Image
   - Sélectionnez une image sur votre ordinateur
   - L'image devrait s'afficher dans le nœud Result Image

✅ Si tout fonctionne, votre installation est réussie !

## Dépannage

### Problème : "python n'est pas reconnu..."

**Solution 1** : Essayez `python3` ou `py` au lieu de `python`

**Solution 2** : Réinstallez Python en cochant "Add Python to PATH"

**Solution 3** : Ajoutez manuellement Python au PATH :
1. Recherchez "Variables d'environnement" dans le menu Démarrer
2. Cliquez sur "Variables d'environnement"
3. Dans "Variables système", trouvez "Path" et cliquez sur "Modifier"
4. Ajoutez le chemin vers Python (ex : `C:\Users\VotreNom\AppData\Local\Programs\Python\Python311`)
5. Ajoutez aussi `C:\Users\VotreNom\AppData\Local\Programs\Python\Python311\Scripts`
6. Redémarrez l'invite de commandes

### Problème : Erreur lors de l'installation de dépendances

**Erreur avec opencv-python** :
```cmd
pip install --upgrade pip setuptools wheel
pip install opencv-python
```

**Erreur avec dearpygui** :
- Assurez-vous d'utiliser Python 64 bits
- Essayez : `pip install dearpygui==1.11.0`

**Erreur "Microsoft Visual C++ 14.0 is required"** :
1. Téléchargez et installez [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. Relancez l'installation des dépendances

### Problème : L'application se bloque au démarrage

**Solution 1** : Désactivez le dessin asynchrone
```cmd
python main.py --unuse_async_draw
```

**Solution 2** : Vérifiez les pilotes de votre carte graphique
- Mettez à jour les pilotes depuis le site du fabricant (NVIDIA, AMD, Intel)

**Solution 3** : Essayez avec les logs de débogage
```cmd
python main.py --use_debug_print
```
Les messages d'erreur vous aideront à identifier le problème.

### Problème : La webcam n'est pas détectée

**Solutions** :
1. Fermez toutes les applications utilisant la webcam (Zoom, Teams, Skype, etc.)
2. Vérifiez les permissions de la caméra dans Windows :
   - Paramètres → Confidentialité → Caméra
   - Activez "Autoriser les applications de bureau à accéder à votre caméra"
3. Essayez différents numéros de périphérique dans le nœud WebCam (0, 1, 2...)

### Problème : Erreur "Cannot connect to GPU"

Si vous n'avez pas de GPU NVIDIA ou CUDA :
1. C'est normal, les nœuds Deep Learning utiliseront le CPU
2. Décochez simplement l'option "GPU" dans les nœuds Deep Learning
3. Le traitement sera plus lent mais fonctionnel

Si vous avez un GPU NVIDIA :
1. Installez [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
2. Installez onnxruntime-gpu : `pip install onnxruntime-gpu`
3. Vérifiez que vos pilotes NVIDIA sont à jour

### Problème : Erreur de politique d'exécution PowerShell

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problème : L'application est lente

**Solutions** :
1. Ajoutez un nœud **Resize** au début de votre pipeline pour réduire la résolution
2. Désactivez les nœuds gourmands avec un nœud **ON/OFF Switch**
3. Activez le GPU pour les nœuds Deep Learning (si disponible)
4. Réduisez le taux de FPS dans les nœuds vidéo/webcam

### Problème : "Module not found" après installation

**Solution** :
1. Vérifiez que l'environnement virtuel est activé (vous devez voir `(venv)`)
2. Réinstallez les dépendances :
   ```cmd
   pip install -r requirements.txt --force-reinstall
   ```

## Alternative : Exécutable Windows

Si vous ne souhaitez pas installer Python et préférez un exécutable autonome :

### Option 1 : Télécharger un exécutable pré-compilé

Consultez [COMMENT_OBTENIR_EXE.md](COMMENT_OBTENIR_EXE.md) pour obtenir un exécutable via GitHub Actions.

### Option 2 : Compiler votre propre exécutable

Consultez [BUILD_EXE_GUIDE_FR.md](BUILD_EXE_GUIDE_FR.md) pour créer votre propre fichier .exe.

**Avantages de l'exécutable** :
- ✅ Pas besoin d'installer Python
- ✅ Portable (peut être copié sur une clé USB)
- ✅ Plus simple pour les utilisateurs finaux

**Avantages de l'installation Python** :
- ✅ Plus facile pour le développement
- ✅ Modifications du code instantanées
- ✅ Moins d'espace disque utilisé
- ✅ Mises à jour plus rapides

## 💡 Conseils pour une utilisation optimale sous Windows

### Performance

1. **Fermez les applications inutiles** pour libérer de la RAM
2. **Utilisez un SSD** pour de meilleures performances I/O
3. **Activez le GPU** si vous avez une carte NVIDIA compatible CUDA
4. **Ajustez la résolution** des images/vidéos pour un traitement plus rapide

### Organisation

1. **Créez un raccourci** :
   - Créez un fichier `lancerCV_Studio.bat` avec le contenu :
     ```batch
     @echo off
     cd /d "%~dp0"
     call venv\Scripts\activate.bat
     python main.py
     pause
     ```
   - Double-cliquez sur ce fichier pour lancer CV Studio directement

2. **Sauvegardez vos configurations** :
   - Utilisez la fonction Export pour sauvegarder vos pipelines
   - Créez un dossier `mes_projets` pour vos fichiers JSON

### Sécurité

1. **Antivirus** : Si votre antivirus bloque l'application :
   - Ajoutez le dossier CV_Studio aux exceptions
   - C'est un faux positif courant avec les applications Python

2. **Pare-feu** : Si vous utilisez des flux RTSP ou des serveurs externes :
   - Autorisez Python dans le pare-feu Windows

## 📚 Ressources supplémentaires

- **README principal** : [README.md](README.md) - Documentation complète du projet
- **Guide d'utilisation** : Voir la section "Usage" dans [README.md](README.md)
- **Exemples** : Dossier [examples/](examples/) pour des exemples de code
- **Nœuds disponibles** : Liste complète dans [README.md](README.md)
- **Tests** : [tests/](tests/) pour les tests unitaires

## 🆘 Support

Si vous rencontrez des problèmes non couverts par ce guide :

1. **Vérifiez les Issues GitHub** : [https://github.com/hackolite/CV_Studio/issues](https://github.com/hackolite/CV_Studio/issues)
2. **Ouvrez une nouvelle Issue** : Décrivez votre problème avec :
   - Votre version de Windows
   - Votre version de Python
   - Le message d'erreur complet
   - Les étapes pour reproduire le problème
3. **Discussions** : [https://github.com/hackolite/CV_Studio/discussions](https://github.com/hackolite/CV_Studio/discussions)

---

**Bon développement avec CV Studio ! 🎉**
