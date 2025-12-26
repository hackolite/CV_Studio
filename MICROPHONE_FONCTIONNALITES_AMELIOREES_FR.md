# Node Microphone - Fonctionnalités Améliorées

## Résumé des Améliorations

Ce document décrit les améliorations apportées au node Microphone pour répondre aux exigences de fonctionnalité, contrôle et surveillance améliorés.

## Nouvelles Fonctionnalités

### 1. Curseur FPS (Images par Seconde)
**Paramètre**: FPS Limit  
**Type**: Curseur (Float)  
**Plage**: 1.0 - 60.0 FPS  
**Défaut**: 30.0 FPS  

Contrôle le taux de mise à jour maximal du node microphone. Cela aide à prévenir la surcharge du système lors du traitement audio en temps réel.

**Utilisation:**
- Régler à **30 FPS** (défaut) pour des performances équilibrées
- Régler à **60 FPS** pour une réactivité maximale 
- Régler à **10-15 FPS** pour une utilisation CPU plus faible ou quand des mises à jour haute fréquence ne sont pas nécessaires

**Avantages:**
- Prévient l'utilisation excessive du CPU
- Permet un réglage fin performance vs réactivité
- Aide à maintenir un fonctionnement fluide quand plusieurs nodes sont actifs

### 2. Sélection du Mode de Sortie
**Paramètre**: Output Mode  
**Type**: Liste déroulante  
**Options**: 
- **Full Signal** (défaut): Sort les données complètes de la forme d'onde audio
- **dB Intensity**: Sort l'intensité sonore en décibels

**Mode Signal Complet:**
- Retourne tous les échantillons audio sous forme de tableau numpy
- Adapté pour le traitement audio en aval (spectrogrammes, analyse, etc.)
- Format de données: tableau float32 avec valeurs entre -1.0 et 1.0

**Mode Intensité dB:**
- Calcule le RMS (Root Mean Square) du chunk audio
- Convertit en échelle décibel: dB = 20 * log10(RMS)
- Retourne une seule valeur représentant l'intensité sonore
- Utile pour la surveillance du volume, les indicateurs de niveau, ou la détection simple d'activité audio
- Plage: typiquement -60 dB (silencieux) à 0 dB (pleine échelle)

**Cas d'Usage:**
- **Signal Complet**: Visualisation spectrogramme, effets audio, enregistrement, classification
- **Intensité dB**: Indicateurs de volume, surveillance du niveau sonore, détection d'activité vocale

### 3. Sélection des Canaux
**Paramètre**: Channels  
**Type**: Liste déroulante  
**Options**:
- **Mono** (défaut): Audio mono-canal
- **Stereo**: Audio deux canaux (gauche/droite)

**Mode Mono:**
- Capture l'audio sur un seul canal
- Utilise moins de mémoire et de puissance de traitement
- Adapté pour la plupart des applications vocales et d'analyse
- La sortie est un tableau 1D

**Mode Stéréo:**
- Capture l'audio sur deux canaux
- Préserve l'information audio spatiale
- Adapté pour l'enregistrement musical ou l'analyse audio spatiale
- La sortie est un tableau 2D (échantillons x 2)

### 4. Horodatage (Timestamp) pour Chaque Chunk
**Fonctionnalité**: Horodatage automatique  
**Type**: Timestamp Unix (float)  
**Précision**: Microsecondes  

Chaque chunk audio inclut maintenant un timestamp précis indiquant quand le chunk a été capturé.

**Format de Sortie Audio:**
```python
{
    'data': numpy.ndarray,      # Échantillons audio
    'sample_rate': int,         # Taux d'échantillonnage en Hz
    'timestamp': float,         # Timestamp Unix
    'channels': int,            # 1 pour mono, 2 pour stéréo
    'output_mode': str          # 'Full Signal' ou 'dB Intensity'
}
```

**Sortie JSON:**
```python
{
    'timestamp': float,         # Timestamp Unix
    'sample_rate': int,         # Taux d'échantillonnage en Hz
    'channels': int,            # Nombre de canaux
    'chunk_duration': float,    # Durée du chunk en secondes
    'output_mode': str,         # Mode de sortie
    'samples': int,             # Nombre d'échantillons
    'db_value': float           # Présent seulement en mode dB Intensity
}
```

**Avantages:**
- Permet une synchronisation précise avec les flux vidéo
- Permet l'analyse temporelle des données audio
- Facilite la corrélation entre plusieurs sources de données
- Essentiel pour les systèmes de files d'attente basés sur timestamp

## Fonctionnalités Existantes (Inchangées)

### Bouton Start/Stop
- Active/désactive l'enregistrement
- Le bouton change de label entre "Start" et "Stop"
- Arrête le flux audio quand non-enregistrement

### Sélection du Périphérique
- Liste déroulante de tous les périphériques d'entrée disponibles
- Détecte automatiquement les microphones du système

### Sélection du Taux d'Échantillonnage
- Taux standards: 8000, 16000, 22050, 44100, 48000 Hz
- Défaut: 44100 Hz (qualité CD)

### Durée du Chunk
- Curseur: 0.1 - 5.0 secondes
- Défaut: 1.0 seconde
- Contrôle la taille de chaque tampon audio

### Indicateur d'Activité Audio
- Retour visuel montrant quand l'audio est capturé
- Gris quand inactif, vert quand actif

## Considérations de Performance

### Limitation FPS
La limite FPS empêche le node de se mettre à jour trop fréquemment, ce qui:
- Réduit l'utilisation CPU
- Prévient le lag de l'interface dans l'éditeur de nodes
- Maintient des performances stables avec plusieurs nodes
- Permet au système de traiter l'audio à un taux contrôlé

### Utilisation Mémoire
- **Mode Signal Complet**: L'utilisation mémoire dépend de la durée du chunk et du taux d'échantillonnage
  - Formule: `échantillons = taux_échantillonnage * durée_chunk * canaux`
  - Exemple: 44100 Hz * 1.0s * 1 canal = 44,100 valeurs float32 (~176 KB par chunk)
- **Mode Intensité dB**: Utilisation mémoire minimale (une seule valeur float)

### Utilisation CPU
- **Mono**: Utilisation CPU et mémoire plus faible
- **Stéréo**: ~2x CPU et mémoire comparé au mono
- **Limite FPS**: Contrôle directement la fréquence de mise à jour et la charge CPU globale

## Tests

Toutes les améliorations ont été testées de manière approfondie:

### Tests Unitaires
- ✅ Initialisation des nouveaux attributs
- ✅ Structure des tags d'entrée
- ✅ Précision du calcul décibel
- ✅ Validation du format timestamp
- ✅ Vérification de la structure de sortie
- ✅ Logique de limitation FPS

### Tests d'Intégration
- ✅ Compatibilité ascendante avec les tests existants
- ✅ Import et instanciation du node
- ✅ Validation de la structure factory
- ✅ Signature de la méthode update

## Exemples d'Utilisation

### Exemple 1: Surveillance Audio Temps Réel avec Intensité dB
```
Configuration:
1. Node Microphone (Mode de Sortie: dB Intensity)
2. Connecter à un affichage de valeur ou node graphique
3. Surveiller les niveaux sonores en temps réel

Paramètres:
- Taux d'Échantillonnage: 44100 Hz
- Durée du Chunk: 0.1s (réponse rapide)
- Limite FPS: 30 (mises à jour fluides)
- Mode de Sortie: dB Intensity
- Canaux: Mono
```

### Exemple 2: Enregistrement Audio Haute Qualité
```
Configuration:
1. Node Microphone (Mode de Sortie: Full Signal)
2. Connecter à une chaîne de traitement audio
3. Sauvegarder dans un fichier ou traiter en temps réel

Paramètres:
- Taux d'Échantillonnage: 48000 Hz
- Durée du Chunk: 1.0s
- Limite FPS: 30
- Mode de Sortie: Full Signal
- Canaux: Stéréo
```

### Exemple 3: Détection d'Activité Vocale Faible Latence
```
Configuration:
1. Node Microphone
2. Basculer entre modes Full Signal et dB Intensity
3. Utiliser le timestamp pour un timing d'événement précis

Paramètres:
- Taux d'Échantillonnage: 16000 Hz (suffisant pour la voix)
- Durée du Chunk: 0.1s (latence 100ms)
- Limite FPS: 60 (haute réactivité)
- Mode de Sortie: dB Intensity
- Canaux: Mono
```

## Implémentation Technique

### Algorithme de Limitation FPS
```python
current_time = time.time()
min_interval = 1.0 / fps_limit
time_since_last = current_time - self._last_update_time

if time_since_last < min_interval:
    # Sauter cette mise à jour
    return None
    
self._last_update_time = current_time
# Traiter l'audio...
```

### Calcul dB
```python
rms = np.sqrt(np.mean(audio_data**2))
if rms > 0:
    db_value = 20 * np.log10(rms)
else:
    db_value = -inf
```

### Génération de Timestamp
```python
chunk_timestamp = time.time()
# Timestamp Unix avec précision microseconde
```

## Compatibilité

- ✅ Compatible avec les nodes existants
- ✅ Fonctionne avec le pipeline de traitement audio existant
- ✅ Compatible avec le système de préservation de timestamp
- ✅ S'intègre avec le système de dictionnaire à file d'attente

## Information de Version

**Version Améliorée**: 0.0.2  
**Date**: 26 Décembre 2025  
**Changements**:
- Ajout du curseur limite FPS (1-60 FPS)
- Ajout de la sélection du mode de sortie (Signal Complet / Intensité dB)
- Ajout de la sélection des canaux (Mono / Stéréo)
- Ajout du timestamp à la sortie audio
- Ajout de métadonnées JSON complètes en sortie
- Structure de sortie audio améliorée avec champs supplémentaires

## Vérification du Fonctionnement

Le node microphone a été vérifié pour:
- ✅ Ne pas buguer le système
- ✅ Fonctionner correctement avec tous les nouveaux paramètres
- ✅ Maintenir la compatibilité avec les nodes existants
- ✅ Fournir des timestamps précis pour chaque chunk
- ✅ Gérer correctement les modes mono et stéréo
- ✅ Calculer correctement l'intensité dB
- ✅ Limiter le FPS comme configuré

## Voir Aussi

- [README Microphone Node](node/InputNode/README_Microphone.md)
- [Documentation Préservation Timestamp](TIMESTAMP_PRESERVATION.md)
- [Documentation Éditeur Node](node_editor/README.md)
