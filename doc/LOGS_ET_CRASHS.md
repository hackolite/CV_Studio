# Logs et diagnostic des crashs

Quel que soit le mode de lancement — `python main.py`, exécutable Windows
(`CV_Studio.exe`, avec ou sans console), binaire Linux — un crash laisse
**toujours** une trace dans des fichiers faciles à trouver.

## 1. Où sont les logs ?

Le répertoire de logs est choisi au démarrage, dans cet ordre (premier
emplacement accessible en écriture) :

| Priorité | Emplacement | Cas |
|---|---|---|
| 1 | `$CV_STUDIO_LOG_DIR` | variable d'environnement, si définie |
| 2 | `CV_Studio_data/logs/` **à côté de l'exécutable** | `.exe` Windows et binaire Linux (PyInstaller) |
| 2 | `logs/` à la racine du dépôt | lancement `python main.py` |
| 3 | `%APPDATA%\CV_Studio\logs` / `~/.local/state/CV_Studio/logs` / `~/Library/Logs/CV_Studio` | si le dossier de l'application n'est pas inscriptible (ex. `Program Files`) |
| 4 | `<temp>/CV_Studio/logs` | dernier recours |

Le chemin retenu est écrit au démarrage dans le log et dans la console :

```
... - __main__ - INFO - Log directory: C:\Apps\CV_Studio\CV_Studio_data\logs
... - __main__ - INFO - Application log file: C:\Apps\CV_Studio\CV_Studio_data\logs\cv_studio.log
... - src.utils.fault_diagnostics - INFO - Fault diagnostics enabled (fault trace output: ...\cv_studio_fault.log) — crash signals: SIGSEGV, SIGABRT, SIGFPE, SIGBUS
```

## 2. Les deux fichiers

| Fichier | Contenu | Rotation |
|---|---|---|
| `cv_studio.log` | Journal applicatif (INFO, ou DEBUG avec `--use_debug_print`), **toutes les exceptions non rattrapées** : thread principal, threads de travail, callbacks DearPyGui, et même une erreur d'import survenue avant l'initialisation du logging (ligne `CRASH - Unhandled exception`). | 5 × 5 Mo |
| `cv_studio_fault.log` | Traces des **crashs durs** (segfault, abort, erreur dans une bibliothèque native : OpenCV, ONNX Runtime, pilote GPU…) écrites par `faulthandler` avec la pile de tous les threads, plus un instantané de tous les threads toutes les 30 s (watchdog). Une ligne `===== CV_STUDIO session started ... =====` sépare les sessions. | tronqué au-delà de 20 Mo |

En pratique :

* **L'application se ferme avec une erreur Python** → chercher `Traceback` dans `cv_studio.log`.
* **L'application disparaît sans message** (segfault) → ouvrir `cv_studio_fault.log`, aller à la dernière section `Fatal Python error:`.
* **L'application se fige** → envoyer `SIGUSR1` (Linux : `kill -USR1 <pid>`) ou `Ctrl+Break` (Windows, console) : la pile de tous les threads est ajoutée aux deux sorties ; sinon, le dernier instantané du watchdog dans `cv_studio_fault.log` montre où elle bloquait.

## 3. Exécutable Windows

* **Console visible (build par défaut)** : en cas d'erreur fatale, la console
  affiche l'emplacement des logs et attend `Entrée` avant de se fermer (désactiver
  avec `CV_STUDIO_NO_PAUSE=1`, automatiquement désactivé en `--smoke-test`).
* **Build `--windowed` (sans console)** : rien n'est affiché, mais les deux fichiers
  sont tout de même écrits dans `CV_Studio_data\logs\`.
* La trace d'un segfault n'apparaît **que** dans `cv_studio_fault.log`
  (`faulthandler` ne peut écrire que vers une seule destination) ; la console ne
  montre rien après un crash natif.

## 4. Options et variables

| Option / variable | Rôle |
|---|---|
| `--log-file CHEMIN` | fichier du journal applicatif (défaut : `<logs>/cv_studio.log`) |
| `--fault_log CHEMIN` ou `CV_STUDIO_FAULT_LOG` | fichier des crashs durs (défaut : `<logs>/cv_studio_fault.log`) |
| `--use_debug_print` | niveau DEBUG |
| `CV_STUDIO_LOG_DIR` | répertoire de logs |
| `CV_STUDIO_WATCHDOG_INTERVAL` | période du watchdog en secondes (défaut 30, `0` désactive) |
| `CV_STUDIO_NO_PAUSE` | ne pas attendre `Entrée` après une erreur fatale (exe Windows) |

## 5. À joindre à un rapport de bug

1. `cv_studio.log` (et `cv_studio.log.1` si le crash est ancien) ;
2. `cv_studio_fault.log` ;
3. la ligne `Platform: ... | Python: ... | Frozen: ...` du début du log.

## 6. Vérification

```bash
python -m pytest tests/test_utils/test_crash_logging.py -q
```

Les tests simulent, dans des sous-processus : une exception avant
`setup_logging`, une exception dans un thread, un segfault avec et sans console
(`sys.stderr = None`), et un chemin `--fault_log` explicite.
