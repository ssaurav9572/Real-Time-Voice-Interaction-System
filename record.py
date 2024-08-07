import wave
import sounddevice as sd
from pathlib import Path

def record_audio(duration: int, output_dir: str, output_filename: str):
    output_path = Path(output_dir) / f"{output_filename}.wav"
    
    # Ensure the output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Record audio
    samplerate = 44100
    try:
        print("Recording...")
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=2, dtype='int16')
        sd.wait()  # Wait until recording is finished
        
        # Write audio data to WAV file
        with wave.open(str(output_path), 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(recording.tobytes())
        
        print("Recording saved to", output_path)
        
    except Exception as e:
        print(f"Error recording audio: {e}")
