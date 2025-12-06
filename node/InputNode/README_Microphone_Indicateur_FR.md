# Indicateur Audio pour le Nœud Microphone

## Vue d'ensemble

Le nœud Microphone comprend maintenant un indicateur visuel qui clignote en vert lorsque les décibels augmentent, vous permettant de voir facilement si l'enregistrement fonctionne.

## Nouvelle Fonctionnalité

### Indicateur d'Activité Audio

Un indicateur visuel simple a été ajouté au nœud Microphone :

- **"Audio: ○"** (gris) : Pas d'enregistrement ou audio très silencieux
- **"Audio: ●"** (vert brillant) : Clignote quand le niveau audio augmente
- **"Audio: ○"** (vert foncé) : Alterne avec le vert brillant pour créer l'effet de clignotement

L'indicateur clignote en vert chaque fois que le niveau audio (RMS) augmente par rapport au chunk précédent.

## Comment Utiliser l'Indicateur

### Vérifier que l'Enregistrement Fonctionne

1. Ajoutez un nœud **Microphone** (Input → Microphone)
2. Sélectionnez votre périphérique audio dans le menu déroulant
3. Cliquez sur le bouton **Start**
4. Parlez ou faites du bruit près du microphone
5. Observez l'indicateur :
   - Si l'indicateur clignote en vert, l'enregistrement fonctionne ! ✓
   - Si l'indicateur reste gris, vérifiez votre microphone

### Quand l'Indicateur Clignote

L'indicateur clignote quand :
1. Le niveau audio augmente par rapport au chunk précédent
2. Le niveau audio est au-dessus du seuil minimum (0.01) pour ignorer le bruit de fond

Cela vous aide à :
- Vérifier que le microphone capture activement du son
- Voir un retour visuel en temps réel quand vous parlez ou faites des sons
- Confirmer que l'entrée audio fonctionne sans avoir besoin de valeurs numériques
- Savoir quand le niveau de décibels augmente

### Conseils pour un Bon Enregistrement

1. **Position du Microphone**
   - Si l'indicateur ne clignote pas, rapprochez le microphone
   - Parlez clairement et à un volume normal
   - Expérimentez avec différentes distances et angles

2. **Environnement Sonore**
   - Enregistrez dans un endroit calme pour de meilleurs résultats
   - Réduisez le bruit ambiant (ventilateurs, circulation, etc.)
   - Fermez les fenêtres si le bruit extérieur est gênant

3. **Test Audio**
   - Faites un test avant l'enregistrement final
   - Parlez à votre volume normal d'enregistrement
   - Vérifiez que l'indicateur clignote régulièrement

## Exemples d'Utilisation

### Exemple 1 : Visualisation de Spectrogramme en Temps Réel

1. Ajoutez un nœud **Microphone** (Input → Microphone)
2. Ajoutez un nœud **Spectrogram** (AudioProcess → Spectrogram)
3. Ajoutez un nœud **Result Image** (Visual → Result Image)
4. Connectez : Microphone → Spectrogram → Result Image
5. Cliquez sur "Start" sur le nœud Microphone
6. Observez l'indicateur clignoter pendant que vous parlez
7. Voyez la visualisation en temps réel de votre entrée audio

### Exemple 2 : Pipeline d'Analyse Audio

1. Ajoutez un nœud **Microphone**
2. Ajoutez plusieurs nœuds **Spectrogram** avec différentes méthodes
3. Ajoutez un nœud **Image Concat** pour voir tous les spectrogrammes côte à côte
4. Connectez le Microphone à tous les nœuds Spectrogram
5. Connectez tous les Spectrogrammes à Image Concat
6. L'indicateur clignotera pour vous montrer quand l'audio est capturé

## Dépannage

### L'Indicateur Ne Clignote Pas

**Problème** : L'indicateur reste gris même quand vous parlez

**Solutions** :
- Vérifiez qu'un microphone est physiquement connecté
- Vérifiez les permissions du microphone dans les paramètres de votre système
- Augmentez le volume du microphone dans les paramètres système
- Rapprochez le microphone ou parlez plus fort
- Essayez un autre périphérique audio

### L'Indicateur Clignote Tout le Temps

**Problème** : L'indicateur clignote même en silence

**Solutions** :
- Il y a probablement du bruit ambiant
- Vérifiez qu'il n'y a pas de ventilateur ou autre source de bruit près du micro
- Réduisez le gain du microphone dans les paramètres système
- Utilisez un endroit plus calme pour l'enregistrement

### Aucun Microphone Détecté

**Problème** : Le menu déroulant affiche "No microphone detected"

**Solutions** :
- Vérifiez qu'un microphone est physiquement connecté
- Vérifiez les permissions du microphone dans les paramètres de votre système
- Redémarrez l'application
- Vérifiez que d'autres applications peuvent accéder au microphone

## Détails Techniques

### Calcul de l'Indicateur

- L'indicateur se base sur la valeur RMS (Root Mean Square) de l'audio
- RMS représente le niveau de volume moyen
- Le clignotement se produit quand RMS(actuel) > RMS(précédent)
- Seuil minimum : 0.01 pour ignorer le bruit très faible

### Couleurs de l'Indicateur

- **Gris (128, 128, 128)** : Aucune activité
- **Vert brillant (0, 255, 0)** : État "allumé" du clignotement
- **Vert foncé (0, 180, 0)** : État "éteint" du clignotement

### Performance

- Impact CPU négligeable
- Calcul RMS très rapide (< 1ms)
- Mise à jour à chaque chunk audio
- Compatible avec le système de queue horodatée

## Historique des Versions

- **0.0.2** (Version Actuelle)
  - Remplacement des jauges RMS et Peak par un indicateur clignotant
  - L'indicateur clignote en vert quand le niveau audio augmente
  - Retour visuel simplifié pour l'activité audio
  
- **0.0.1** (Version Initiale)
  - Fonctionnalité de capture de microphone de base
  - Taux d'échantillonnage et durée de chunk configurables
  - Support multi-périphérique
  - Repli gracieux quand sounddevice n'est pas disponible

## Voir Aussi

- [Nœud Spectrogram](../AudioProcessNode/SPECTROGRAM_METHODS.md) - Traiter l'audio en spectrogrammes visuels
- [README Principal de CV Studio](../../README.md) - Documentation complète de l'application
- [README Microphone (English)](README_Microphone.md) - Documentation en anglais
