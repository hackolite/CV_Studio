# CV_Studio - Restructuration pour PyInstaller

## Résumé des Changements / Summary of Changes

### Structure du Projet / Project Structure

Le projet a été restructuré pour faciliter la création d'un exécutable Windows avec PyInstaller.

The project has been restructured to facilitate building a Windows executable with PyInstaller.

#### Nouvelle structure / New structure:

```
CV_Studio/
├── internal/              # Tout le code source / All source code
│   ├── main.py           # Point d'entrée principal / Main entry point
│   ├── src/              # Utilitaires et modules / Core utilities and modules
│   ├── node/             # Implémentations des nœuds / Node implementations
│   └── node_editor/      # Composants UI / UI components
├── run.py                # Script de lancement depuis la racine / Launch script from root
├── CV_Studio_new.spec    # Spécification PyInstaller / PyInstaller specification
├── build_simple.bat      # Script de build Windows / Windows build script
├── BUILD_INSTRUCTIONS.md # Guide de build détaillé / Detailed build guide
└── README.md             # Documentation principale / Main documentation
```

### Changements Principaux / Main Changes

#### 1. Nettoyage des fichiers MD / Cleanup of MD files
- Supprimé ~50 fichiers markdown inutiles / Removed ~50 unnecessary markdown files
- Conservé uniquement README.md et LICENSE / Kept only README.md and LICENSE
- Créé BUILD_INSTRUCTIONS.md pour les instructions de build / Created BUILD_INSTRUCTIONS.md for build instructions

#### 2. Nouvelle structure "internal" / New "internal" structure
- Tout le code source déplacé dans `internal/` / All source code moved to `internal/`
- Facilite la séparation entre code et build / Facilitates separation between code and build
- Structure conforme aux attentes de PyInstaller / Structure compliant with PyInstaller expectations

#### 3. Scripts de build simplifiés / Simplified build scripts
- `build_simple.bat`: Script simple pour Windows / Simple script for Windows
- `CV_Studio_new.spec`: Configuration PyInstaller mise à jour / Updated PyInstaller configuration
- Build produit l'exe dans `dist/CV_Studio/` / Build produces exe in `dist/CV_Studio/`

#### 4. Imports corrigés / Fixed imports
- Tous les imports fonctionnent depuis `internal/` / All imports work from `internal/`
- Support du mode frozen (PyInstaller) et normal / Support for frozen (PyInstaller) and normal mode
- `run.py` permet de lancer depuis la racine / `run.py` allows launching from root

## Utilisation / Usage

### Pour les développeurs / For developers

Lancer l'application depuis la source / Run the application from source:

```bash
python run.py
```

Ou depuis le répertoire internal / Or from the internal directory:

```bash
cd internal
python main.py
```

### Pour créer l'exécutable / To build the executable

Sur Windows / On Windows:

```batch
build_simple.bat
```

L'exécutable sera créé dans / The executable will be created in:
```
dist/CV_Studio/CV_Studio.exe
```

## Avantages de cette structure / Benefits of this structure

1. **Séparation claire** / **Clear separation**: Code source dans `internal/`, build dans `dist/`
2. **Imports propres** / **Clean imports**: Plus de problèmes d'imports relatifs / No more relative import issues
3. **Build simplifié** / **Simplified build**: Un seul script pour tout / Single script for everything
4. **Documentation claire** / **Clear documentation**: BUILD_INSTRUCTIONS.md détaille tout / BUILD_INSTRUCTIONS.md details everything
5. **Compatibilité PyInstaller** / **PyInstaller compatibility**: Structure optimisée pour PyInstaller / Structure optimized for PyInstaller

## Vérification / Verification

Pour vérifier que tout fonctionne / To verify everything works:

1. Tester les imports / Test imports:
   ```bash
   cd internal
   python -c "from src.utils.logging import setup_logging; print('OK')"
   ```

2. Builder l'exe / Build the exe:
   ```batch
   build_simple.bat
   ```

3. Tester l'exe / Test the exe:
   ```batch
   dist\CV_Studio\CV_Studio.exe
   ```

## Notes Importantes / Important Notes

- Le répertoire `internal/` contient TOUT le code source / The `internal/` directory contains ALL source code
- Ne pas supprimer les fichiers dans `internal/` / Do not delete files in `internal/`
- Le build copie automatiquement tout dans `dist/` / The build automatically copies everything to `dist/`
- L'exe est autonome et portable / The exe is standalone and portable

## Dépannage / Troubleshooting

Voir / See: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) pour plus de détails / for more details
