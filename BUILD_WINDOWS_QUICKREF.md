# 🚀 CV_Studio - Construction .exe Windows - Carte de Référence Rapide

## ⚡ Méthode la Plus Simple (Script Automatique)

### Pour Windows avec Batch File:
```
1. Téléchargez: build_windows.bat
2. Double-cliquez dessus
3. Attendez 5-15 minutes
4. Lancez: dist\CV_Studio\CV_Studio.exe
```

### Pour Windows avec PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File build_windows.ps1
```

## 📋 Prérequis Minimum

| Logiciel | Version | Téléchargement |
|----------|---------|----------------|
| Python   | 3.7+    | https://www.python.org/downloads/ |
| Git      | Récent  | https://git-scm.com/download/win |
| Espace   | 3 GB    | - |

**Important**: Cochez "Add Python to PATH" lors de l'installation de Python!

## 🛠️ Commandes Manuelles (Alternative)

```bash
# 1. Cloner
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio

# 2. Installer
pip install -r requirements.txt
pip install pyinstaller

# 3. Construire
python build_exe.py --clean

# 4. Trouver l'exe
# Emplacement: dist\CV_Studio\CV_Studio.exe
```

## 🎯 Options du Script build_exe.py

| Option | Description |
|--------|-------------|
| `--clean` | Nettoie avant de construire (recommandé) |
| `--windowed` | Cache la console (mode GUI pur) |
| `--icon fichier.ico` | Ajoute une icône personnalisée |
| `--debug` | Mode debug pour diagnostiquer |

## 📦 Résultat

```
dist/CV_Studio/
├── CV_Studio.exe  ← VOTRE EXÉCUTABLE
├── node/          ← Nœuds et modèles ONNX
├── node_editor/   ← Interface
└── _internal/     ← Dépendances Python
```

**Taille**: ~800 MB - 1.5 GB (tout inclus)

## 🚨 Problèmes Courants

### "Python n'est pas reconnu"
```
✓ Solution: Installez Python et cochez "Add to PATH"
```

### "Git n'est pas reconnu"
```
✓ Solution: Installez Git depuis git-scm.com
```

### L'exe ne démarre pas
```
✓ Solution: Installez Visual C++ Redistributable
   https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### "Module not found" après build
```
✓ Solution: Vérifiez que toutes les dépendances sont installées
   pip install -r requirements.txt
```

### Script PowerShell bloqué
```
✓ Solution: Utilisez le bypass
   powershell -ExecutionPolicy Bypass -File build_windows.ps1
```

## ☁️ Alternative: Build GitHub Actions

```
1. Allez sur: github.com/hackolite/CV_Studio/actions
2. Cliquez: "Build Windows Executable"
3. Cliquez: "Run workflow"
4. Attendez: 10-15 minutes
5. Téléchargez: CV_Studio-Windows-Executable.zip
```

**Avantage**: Pas besoin d'installer Python/Git localement!

## 📊 Durées Approximatives

| Étape | Durée |
|-------|-------|
| Installation dépendances | 2-5 min |
| Build PyInstaller | 3-10 min |
| **Total** | **5-15 min** |

*Varie selon connexion Internet et puissance machine*

## ✅ Checklist Rapide

- [ ] Python 3.7+ installé (avec PATH)
- [ ] Git installé
- [ ] 3 GB d'espace libre
- [ ] Script téléchargé ou repo cloné
- [ ] Lancé le script / commandes
- [ ] Patienté 5-15 minutes
- [ ] Trouvé l'exe dans dist\CV_Studio\
- [ ] Testé le lancement

## 📚 Documentation Complète

- **Guide Complet**: [BUILD_EXE_GUIDE_FR.md](BUILD_EXE_GUIDE_FR.md)
- **Script Guide**: [BUILD_WINDOWS_SCRIPT.md](BUILD_WINDOWS_SCRIPT.md)
- **Comment Obtenir**: [COMMENT_OBTENIR_EXE.md](COMMENT_OBTENIR_EXE.md)
- **README**: [README.md](README.md)

## 💡 Conseils

- ✅ Utilisez `--clean` pour un build propre
- ✅ Fermez antivirus temporairement si problème
- ✅ Testez l'exe sur votre machine avant distribution
- ✅ Distribuez tout le dossier `dist\CV_Studio`, pas juste l'exe
- ✅ Compression ZIP recommandée pour partage

## 🆘 Support

**Issues GitHub**: https://github.com/hackolite/CV_Studio/issues

---

**Version**: 1.0 | **Date**: 2026-01 | **Projet**: CV_Studio
