import sounddevice as sd
import numpy as np

# Génère un son simple : un sinus de 440 Hz pendant 2 secondes
samplerate = 44100  # échantillons par seconde
duration = 2  # secondes
frequency = 440  # Hz (La4)

t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
my_audio_array = 0.5 * np.sin(2 * np.pi * frequency * t)

# Lecture du son
sd.play(my_audio_array, samplerate=samplerate)
sd.wait()  # attend la fin de la lecture
