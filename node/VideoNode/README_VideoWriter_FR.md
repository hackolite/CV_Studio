# VideoWriter Node - Options de Format

## Vue d'ensemble

Le nœud VideoWriter vous permet d'exporter la sortie de votre pipeline de traitement vers des fichiers vidéo. Il prend en charge plusieurs formats vidéo avec différentes caractéristiques d'encodage.

## Options de Format

### 1. MP4 (Standard)
- **Extension:** `.mp4`
- **Codec:** MPEG-4 Part 2 (`mp4v`)
- **Type d'encodage:** Interframe (compression temporelle)
- **Caractéristiques:**
  - Utilise des P-frames et B-frames pour la compression
  - Tailles de fichiers plus petites grâce à la compression temporelle
  - **PAS frame par frame** - les frames dépendent d'autres frames
  - Idéal pour: Distribution finale, streaming, utilisation générale

### 2. MP4 (I-Frame) ✨ NOUVEAU
- **Extension:** `.mp4`
- **Codec:** H.264 (`libx264`) avec encodage intraframe uniquement
- **Type d'encodage:** Intraframe uniquement (toutes I-frames)
- **Caractéristiques:**
  - **Chaque frame est indépendante** (pas de P ou B frames)
  - Véritable encodage frame par frame
  - Meilleure compression que MJPEG avec les fonctionnalités des codecs modernes
  - Tailles de fichiers plus grandes que MP4 standard
  - Parfait pour: Montage précis au frame, analyse frame par frame, post-production professionnelle
- **Détails techniques:**
  - Utilise `keyint=1` pour forcer toutes les I-frames
  - Utilise `scenecut=0` pour désactiver la détection de scène
  - Réencodage lors de la fusion audio pour les paramètres appropriés

### 3. AVI
- **Extension:** `.avi`
- **Codec:** Motion JPEG (`MJPG`)
- **Type d'encodage:** Intraframe uniquement
- **Caractéristiques:**
  - Chaque frame est une image JPEG séparée
  - Véritable encodage frame par frame
  - Tailles de fichiers importantes
  - Compatibilité universelle
  - Idéal pour: Systèmes legacy, montage frame par frame simple

### 4. MKV
- **Extension:** `.mkv`
- **Codec:** FFV1 (sans perte)
- **Type d'encodage:** Intraframe uniquement
- **Caractéristiques:**
  - Encodage vidéo sans perte
  - Véritable encodage frame par frame
  - Prend en charge les pistes de métadonnées (audio et données JSON)
  - Idéal pour: Archivage, préservation, enregistrements riches en métadonnées

## Encodage Frame par Frame

**Question:** Est-ce que je peux faire du frame par frame avec l'option MP4 du VideoWriter ?

**Réponse:** Oui ! Utilisez le format **MP4 (I-Frame)** pour un véritable encodage frame par frame avec des conteneurs MP4.

### Qu'est-ce que l'encodage Frame par Frame ?

L'encodage frame par frame (intraframe) signifie que chaque frame est encodée indépendamment sans référence aux autres frames. Cela permet :

- **Précision parfaite au frame** pour le montage et l'analyse
- **Navigation instantanée** vers n'importe quelle frame
- **Pas d'artifacts temporels** provenant de la compression inter-frame
- **Extraction et manipulation de frames fiables**

### Comparaison des Formats pour Frame par Frame

| Format | Frame par Frame | Codec | Taille | Qualité | Cas d'usage |
|--------|----------------|-------|---------|---------|-------------|
| **MP4** | ❌ Non | MPEG-4 Part 2 | Petite | Bonne | Distribution |
| **MP4 (I-Frame)** | ✅ Oui | H.264 Intra | Moyenne | Excellente | Montage professionnel |
| **AVI** | ✅ Oui | Motion JPEG | Grande | Bonne | Compatibilité legacy |
| **MKV** | ✅ Oui | FFV1 | Grande | Sans perte | Archivage |

## Utilisation

1. **Sélectionner le Format:**
   - Dans le nœud VideoWriter, utilisez le menu déroulant **Format**
   - Choisissez votre format désiré dans la liste

2. **Démarrer l'Enregistrement:**
   - Cliquez sur le bouton **Start**
   - Le nœud commencera à enregistrer les frames de l'entrée

3. **Arrêter l'Enregistrement:**
   - Cliquez sur le bouton **Stop**
   - La vidéo sera encodée et sauvegardée dans le répertoire configuré

## Emplacement de Sortie

Les vidéos sont sauvegardées dans le répertoire spécifié dans `setting.json`:
- **Configuration:** `video_writer_directory`
- **Nommage des fichiers:** `YYYYMMDD_HHMMSS.<ext>`

## Support Audio

Tous les formats supportent la fusion audio:
- L'audio est capturé depuis les nœuds connectés
- Qualité audio: bitrate AAC 192k (haute qualité)
- La synchronisation audio-vidéo est automatique
- L'audio a la priorité - la durée vidéo s'adapte pour correspondre à la longueur audio

## Détails Techniques

### Mode Worker en Arrière-plan

Quand FFmpeg est disponible, le VideoWriter utilise un worker en arrière-plan pour de meilleures performances:
- Encodage non-bloquant (l'interface reste réactive)
- Suivi de progression avec ETA
- Contrôles Pause/Reprendre/Annuler
- Gestion efficace de la file d'attente

### Mode Legacy

Sans FFmpeg, le VideoWriter utilise l'encodage direct OpenCV:
- Écriture synchrone des frames
- Implémentation plus simple
- Fusion audio automatique à la fin

## Conseils

- **Pour le montage:** Utilisez MP4 (I-Frame), AVI, ou MKV
- **Pour la distribution:** Utilisez MP4 standard
- **Pour l'archivage:** Utilisez MKV avec FFV1
- **Pour la compatibilité:** Utilisez AVI avec MJPEG

## Prérequis

- **FFmpeg-python:** Requis pour la fusion audio et l'encodage MP4 (I-Frame)
- **Soundfile:** Requis pour le traitement audio
- **OpenCV:** Requis pour l'encodage vidéo de base

Installation:
```bash
pip install ffmpeg-python soundfile opencv-python
```

## Voir Aussi

- [Video Node Dynamic Play](README_DynamicPlay_FR.md)
- [README Principal](../../README.md)
