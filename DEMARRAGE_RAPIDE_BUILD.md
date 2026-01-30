# 🚀 Guide de Démarrage Rapide - Construire un .exe

## ⚡ Vous voulez un .exe ? Voici les 3 méthodes les plus rapides !

### 🥇 Méthode 1 : GitHub Actions (0 installation locale)

**La PLUS SIMPLE - recommandée pour la plupart des utilisateurs**

```
1. Aller sur : https://github.com/hackolite/CV_Studio/actions
2. Cliquer : "Build Windows Executable" (menu gauche)
3. Cliquer : "Run workflow" (bouton à droite)
4. Attendre : 10-15 minutes ⏱️
5. Télécharger : "CV_Studio-Windows-Executable.zip"
6. Extraire et lancer : CV_Studio.exe ✓
```

**Temps total** : 15 minutes + téléchargement
**Avantage** : Aucune configuration locale, build dans le cloud

---

### 🥈 Méthode 2 : Script Local (pour développeurs)

**Rapide si vous avez Python installé**

```bash
# Étape 1 : Prérequis (une seule fois)
pip install -r requirements.txt
pip install pyinstaller

# Étape 2 : Build (à chaque fois)
python build_exe.py --clean

# Étape 3 : Tester
dist\CV_Studio\CV_Studio.exe
```

**Temps total** : 5-10 minutes
**Avantage** : Contrôle total, build local, modifications rapides

---

### 🥉 Méthode 3 : PyInstaller Direct (pour experts)

**Pour ceux qui connaissent PyInstaller**

```bash
pyinstaller CV_Studio.spec
```

**Temps total** : 3-5 minutes
**Avantage** : Le plus rapide, configuration déjà faite

---

## 📦 Résultat de la construction

Quelle que soit la méthode, vous obtiendrez :

```
dist/CV_Studio/
├── CV_Studio.exe          ← Lancez ce fichier !
├── _internal/             (dépendances Python)
├── node/                  (tous les nœuds + modèles ONNX)
└── node_editor/           (éditeur de nœuds)

Taille : ~830 Mo
Fichiers : 483 fichiers
```

## ✅ Vérification rapide

Pour vérifier que tout fonctionne AVANT le build :

```bash
python verify_dependencies.py
```

✓ Toutes les dépendances sont OK ? Vous êtes prêt à construire !

## 🎯 Quelle méthode choisir ?

| Situation | Méthode recommandée |
|-----------|-------------------|
| Je veux juste un .exe, pas coder | **GitHub Actions** 🥇 |
| Je développe CV_Studio | **Script Local** 🥈 |
| Je connais bien PyInstaller | **PyInstaller Direct** 🥉 |
| Je n'ai pas Python installé | **GitHub Actions** 🥇 |
| Je veux customiser le build | **Script Local** 🥈 |

## ⏱️ Temps de build comparés

- **GitHub Actions** : 10-15 min (cloud)
- **Script Local** : 5-10 min (selon PC)
- **PyInstaller Direct** : 3-5 min (selon PC)

## 💡 Trucs et astuces

### Build plus rapide
```bash
# Skip la vérification des packages (si déjà installés)
python build_exe.py --skip-package-check
```

### Build sans console
```bash
# Pour une application GUI pure
python build_exe.py --windowed
```

### Build avec votre icône
```bash
# Personnaliser l'icône
python build_exe.py --icon mon_icone.ico
```

## ❌ Problèmes courants

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "Module not found"
```bash
pip install -r requirements.txt
```

### Le .exe ne démarre pas
```bash
# Installer Visual C++ Redistributable
# https://aka.ms/vs/17/release/vc_redist.x64.exe
```

## 📚 Documentation complète

Pour en savoir plus :
- `REPONSE_BUILD_EXE.md` - Réponse détaillée à "est-ce que ce script permet de build un .exe ?"
- `BUILD_EXE_GUIDE_FR.md` - Guide complet en français
- `COMMENT_OBTENIR_EXE.md` - Instructions détaillées

## 🎉 En résumé

**OUI, ce repository permet de construire un .exe !**

Choisissez votre méthode et lancez-vous ! 🚀

---

**Questions ?** Ouvrez une issue sur GitHub
**Date** : 30 janvier 2026
