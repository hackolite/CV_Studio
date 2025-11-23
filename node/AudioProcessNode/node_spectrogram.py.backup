import numpy as np
from matplotlib import pyplot as plt
from numpy.lib import stride_tricks
import scipy.io.wavfile as wav
from PIL import Image

# ============================================
# CONSTANTES
# ============================================

# Reference amplitude for dB conversion (matching ESC-50 training code)
# IMPORTANT: The user's training code uses 10e-6, which mathematically equals 1e-5
# We preserve 10e-6 notation to exactly match the training code for traceability
# Formula: 20.*np.log10(np.abs(sshow)/10e-6) from the ESC-50 training implementation
REFERENCE_AMPLITUDE = 10e-6  # Do not change to 1e-5, must match training code exactly

# ============================================
# FONCTIONS DE BASE (identiques au training)
# ============================================

def fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning):
    """Transformée de Fourier avec fenêtrage"""
    win = window(frameSize)
    hopSize = int(frameSize - np.floor(overlapFac * frameSize))

    # Zeros au début pour centrer la première fenêtre sur l'échantillon 0
    samples = np.append(np.zeros(int(np.floor(frameSize/2.0))), sig)
    # Colonnes pour le fenêtrage
    cols = np.ceil((len(samples) - frameSize) / float(hopSize)) + 1
    # Zeros à la fin pour couvrir complètement les échantillons
    samples = np.append(samples, np.zeros(frameSize))

    frames = stride_tricks.as_strided(
        samples, 
        shape=(int(cols), frameSize), 
        strides=(samples.strides[0]*hopSize, samples.strides[0])
    ).copy()
    frames *= win

    return np.fft.rfft(frames)


def make_logscale(spec, sr=44100, factor=20.):
    """Convertit le spectrogramme en échelle logarithmique"""
    timebins, freqbins = np.shape(spec)

    scale = np.linspace(0, 1, freqbins) ** factor
    scale *= (freqbins-1)/max(scale)
    scale = np.unique(np.round(scale))

    # Créer le spectrogramme avec les nouvelles bins de fréquence
    newspec = np.complex128(np.zeros([timebins, len(scale)]))
    for i in range(0, len(scale)):
        if i == len(scale)-1:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):], axis=1)
        else:
            newspec[:,i] = np.sum(spec[:,int(scale[i]):int(scale[i+1])], axis=1)

    # Lister les fréquences centrales des bins
    allfreqs = np.abs(np.fft.fftfreq(freqbins*2, 1./sr)[:freqbins+1])
    freqs = []
    for i in range(0, len(scale)):
        if i == len(scale)-1:
            freqs += [np.mean(allfreqs[int(scale[i]):])]
        else:
            freqs += [np.mean(allfreqs[int(scale[i]):int(scale[i+1])])]

    return newspec, freqs


# ============================================
# FONCTION CORRIGÉE POUR L'INFÉRENCE
# ============================================

def plot_spectrogram_for_inference(location, plotpath, binsize=2**10, colormap="jet", target_size=(224, 224)):
    """
    Crée un spectrogramme EXACTEMENT comme pendant l'entraînement.
    
    DIFFÉRENCES CLÉS avec l'ancienne version:
    1. factor=1.0 dans make_logscale (pas 20.0)
    2. Redimensionnement à 224x224 APRÈS sauvegarde
    3. Mêmes paramètres de figure et d'axes
    
    Args:
        location: Chemin du fichier audio (.wav)
        plotpath: Chemin de sauvegarde obligatoire
        binsize: Taille FFT (défaut: 1024 = 2**10)
        colormap: Colormap matplotlib (défaut: "jet")
        target_size: Taille finale (défaut: (224, 224))
    
    Returns:
        ims: Matrice du spectrogramme en décibels
    """
    # 1. Lire le fichier audio
    samplerate, samples = wav.read(location)
    
    # 2. Transformée de Fourier
    s = fourier_transformation(samples, binsize)
    
    # 3. Échelle logarithmique avec factor=1.0 (IMPORTANT!)
    sshow, freq = make_logscale(s, factor=1.0, sr=samplerate)
    
    # 4. Conversion en décibels
    ims = 20. * np.log10(np.abs(sshow) / REFERENCE_AMPLITUDE)

    timebins, freqbins = np.shape(ims)

    # 5. Créer la figure avec les MÊMES paramètres que le training
    plt.figure(figsize=(15, 7.5))
    plt.imshow(
        np.transpose(ims), 
        origin="lower", 
        aspect="auto", 
        cmap=colormap, 
        interpolation="none"
    )
    
    # 6. Axes X (temps) - identique au training
    xlocs = np.float32(np.linspace(0, timebins-1, 5))
    plt.xticks(
        xlocs, 
        ["%.02f" % l for l in ((xlocs*len(samples)/timebins)+(0.5*binsize))/samplerate]
    )
    
    # 7. Axes Y (fréquence) - identique au training
    ylocs = np.int16(np.round(np.linspace(0, freqbins-1, 10)))
    plt.yticks(ylocs, ["%.02f" % freq[i] for i in ylocs])

    # 8. Sauvegarder avec bbox_inches="tight" (comme le training)
    plt.savefig(plotpath, bbox_inches="tight")
    plt.clf()
    
    # 9. Redimensionner APRÈS sauvegarde (comme dans le code d'inférence)
    img = Image.open(plotpath)
    img = img.resize(target_size, Image.LANCZOS)
    img.save(plotpath)

    return ims


# ============================================
# FONCTION POUR TRAITER UN DOSSIER
# ============================================

def process_chunks_to_spectrograms_corrected(chunks_folder, spectro_output_folder):
    """
    Génère des spectrogrammes pour l'inférence avec les MÊMES paramètres que le training
    
    Args:
        chunks_folder: Dossier contenant les fichiers .wav
        spectro_output_folder: Dossier de sortie pour les spectrogrammes
    """
    import os
    os.makedirs(spectro_output_folder, exist_ok=True)

    for filename in sorted(os.listdir(chunks_folder)):
        if filename.endswith(".wav"):
            audio_path = os.path.join(chunks_folder, filename)
            base_name = os.path.splitext(filename)[0]
            save_path = os.path.join(spectro_output_folder, f"{base_name}.png")

            print(f"Création du spectrogramme pour {filename}...")
            try:
                plot_spectrogram_for_inference(
                    location=audio_path,
                    plotpath=save_path,
                    binsize=2**10,  # 1024
                    colormap="jet",
                    target_size=(224, 224)
                )
                print(f"✅ Sauvegardé: {save_path}")
            except Exception as e:
                print(f"❌ Erreur avec {filename}: {e}")


# ============================================
# EXEMPLE D'UTILISATION
# ============================================

if __name__ == "__main__":
    # Exemple 1: Traiter un seul fichier
    plot_spectrogram_for_inference(
        location="chunk_1.wav",
        plotpath="chunk_1_inference.png"
    )
    
    # Exemple 2: Traiter un dossier complet
    process_chunks_to_spectrograms_corrected(
        chunks_folder="/content/chunks_audiotrain_audio",
        spectro_output_folder="/content/chunks_audiotrain_spectrograms_corrected"
    )
