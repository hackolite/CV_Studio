"""Simple audio playback utility module.

This module generates and plays a simple sine wave tone using sounddevice.
It serves as a basic example of audio generation and playback.
"""
import sounddevice as sd
import numpy as np

# Generate a simple sound: a 440 Hz sine wave for 2 seconds
samplerate = 44100  # samples per second
duration = 2  # seconds
frequency = 440  # Hz (A4 note)

t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
my_audio_array = 0.5 * np.sin(2 * np.pi * frequency * t)

# Play the sound
sd.play(my_audio_array, samplerate=samplerate)
sd.wait()  # wait until playback is finished
