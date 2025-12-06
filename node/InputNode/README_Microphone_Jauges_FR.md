# Jauges de Volume pour le Nœud Microphone

## Vue d'ensemble

Le nœud Microphone comprend maintenant des jauges de volume visuelles en temps réel qui vous permettent de voir si l'enregistrement fonctionne correctement.

## Nouvelles Fonctionnalités

### Indicateurs de Niveau de Volume

Deux barres de progression ont été ajoutées au nœud Microphone :

1. **Jauge RMS (Root Mean Square)**
   - Affiche le niveau de volume moyen
   - Utile pour surveiller le niveau sonore général
   - Se met à jour en temps réel pendant l'enregistrement
   - Plage : 0.00 à 1.00

2. **Jauge Peak (Crête)**
   - Affiche le niveau de volume maximal
   - Utile pour surveiller l'écrêtage et l'amplitude maximale
   - Se met à jour en temps réel pendant l'enregistrement
   - Plage : 0.00 à 1.00

## Comment Utiliser les Jauges

### Vérifier que l'Enregistrement Fonctionne

1. Ajoutez un nœud **Microphone** (Input → Microphone)
2. Sélectionnez votre périphérique audio dans le menu déroulant
3. Cliquez sur le bouton **Start**
4. Parlez ou faites du bruit près du microphone
5. Observez les jauges :
   - Si les barres bougent, l'enregistrement fonctionne ! ✓
   - Si les barres restent à 0.00, vérifiez votre microphone

### Interpréter les Niveaux

| Niveau | RMS | Peak | Signification |
|--------|-----|------|---------------|
| Silence | 0.00 | 0.00 | Aucun son détecté |
| Très faible | 0.01-0.10 | 0.05-0.20 | Son très faible, augmentez le gain |
| Faible | 0.10-0.30 | 0.20-0.50 | Son faible mais utilisable |
| Optimal | 0.30-0.70 | 0.50-0.90 | Niveau parfait pour l'enregistrement |
| Fort | 0.70-0.90 | 0.90-0.99 | Son fort, attention à l'écrêtage |
| Écrêtage | > 0.90 | 1.00 | Risque de distorsion, baissez le gain |

### Conseils pour un Bon Enregistrement

1. **Ajuster le Gain du Microphone**
   - Les jauges doivent idéalement être dans la zone verte (0.30-0.70)
   - Évitez que la jauge Peak atteigne 1.00 (écrêtage)
   - Un niveau RMS trop faible (< 0.10) indique un signal faible

2. **Position du Microphone**
   - Si les jauges sont trop faibles, rapprochez le microphone
   - Si les jauges saturent (1.00), éloignez le microphone
   - Expérimentez avec différentes distances et angles

3. **Environnement Sonore**
   - Vérifiez que les jauges ne bougent pas quand vous êtes silencieux
   - Si elles bougent en silence, il y a du bruit de fond
   - Fermez les fenêtres, éteignez les ventilateurs, etc.

## Calcul des Niveaux de Volume

### RMS (Root Mean Square)
```
RMS = √(moyenne(échantillons²))
```
- Représente le niveau moyen d'énergie du signal
- Pour une onde sinusoïdale à amplitude 1.0, RMS ≈ 0.707
- Bon indicateur du volume perçu

### Peak (Crête)
```
Peak = max(|échantillons|)
```
- Représente l'amplitude maximale du signal
- Pour une onde sinusoïdale à amplitude 1.0, Peak = 1.0
- Bon indicateur pour éviter l'écrêtage

## Exemples d'Utilisation

### Exemple 1 : Vérification Rapide du Microphone

```
1. Ajoutez un nœud Microphone
2. Cliquez sur Start
3. Tapez dans vos mains
4. Les jauges devraient montrer un pic élevé momentané
5. Si oui, votre microphone fonctionne ! ✓
```

### Exemple 2 : Enregistrement Vocal

```
1. Ajoutez un nœud Microphone
2. Ajoutez un nœud Spectrogram (AudioProcess → Spectrogram)
3. Ajoutez un nœud Result Image
4. Connectez : Microphone → Spectrogram → Result Image
5. Cliquez sur Start
6. Parlez normalement
7. Ajustez votre position jusqu'à ce que :
   - RMS soit entre 0.30 et 0.60
   - Peak reste en dessous de 0.90
```

### Exemple 3 : Enregistrement Musical

```
1. Configurez le nœud Microphone :
   - Sample Rate : 48000 Hz (qualité professionnelle)
   - Chunk : 1.0s (bon pour l'analyse spectrale)
2. Cliquez sur Start
3. Jouez de votre instrument
4. Surveillez les jauges :
   - Pour la musique dynamique, Peak peut aller jusqu'à 0.90
   - RMS devrait être entre 0.40 et 0.70
```

## Dépannage

### Les Jauges Restent à 0.00

**Causes possibles :**
- Le microphone n'est pas sélectionné
- Le bouton Start n'a pas été cliqué
- Le microphone est muet dans les paramètres système
- Le mauvais périphérique est sélectionné

**Solutions :**
1. Vérifiez que le bon périphérique est sélectionné
2. Cliquez sur le bouton Start
3. Vérifiez les paramètres audio de votre système
4. Testez le microphone dans une autre application

### Les Jauges Bougent Mais Pas de Son

**Note :** Le nœud Microphone capture l'audio mais ne le lit pas.
- C'est normal ! Les jauges montrent que l'audio est capturé.
- Pour entendre le son, utilisez les nœuds de traitement en aval
- Le nœud Spectrogram vous permet de visualiser l'audio

### Les Jauges Saturent Toujours à 1.00

**Causes possibles :**
- Gain du microphone trop élevé
- Microphone trop proche de la source sonore
- Source sonore trop forte

**Solutions :**
1. Baissez le gain du microphone dans les paramètres système
2. Éloignez le microphone de la source sonore
3. Réduisez le volume de la source sonore

### Les Jauges Fluctuent Beaucoup

**C'est normal !** L'audio est un signal dynamique.
- La jauge RMS montre le niveau moyen
- La jauge Peak montre les pics instantanés
- Les variations sont normales pour la parole et la musique

## Spécifications Techniques

### Format des Données Audio
- **Canaux** : Mono (1 canal)
- **Type de données** : float32 (-1.0 à 1.0)
- **Normalisation** : Automatique par sounddevice

### Calculs en Temps Réel
- Les calculs sont effectués à chaque chunk audio
- Temps de calcul négligeable (< 1ms)
- Pas d'impact sur les performances

### Compatibilité
- Compatible avec tous les nœuds AudioProcess
- Compatible avec le système de queue horodatée
- Fonctionne avec tous les taux d'échantillonnage

## Historique des Versions

- **v0.0.2** (Nouvelle Fonctionnalité)
  - Ajout des jauges de volume RMS et Peak
  - Mise à jour en temps réel pendant l'enregistrement
  - Documentation en français et anglais
  - Tests unitaires pour les calculs de volume

## Voir Aussi

- [README_Microphone.md](README_Microphone.md) - Documentation complète du nœud (en anglais)
- [Spectrogram Node](../AudioProcessNode/SPECTROGRAM_METHODS.md) - Traitement audio
- [CV Studio Main README](../../README.md) - Documentation principale
