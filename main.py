import os
from time import time
import requests
from dotenv import load_dotenv
import openai
import pygame
from pygame import mixer
from record import record_audio

# Load API keys
load_dotenv()
OPENAI_API_KEY = os.getenv("api_key")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("elevenlabs_api_key")
ASSISTANT_ID = os.getenv("assistant_id")

# Initialize clients
openai.api_key = OPENAI_API_KEY
mixer.init()

# Define paths
RECORDING_PATH = "audio/recording.wav"

def transcribe_audio(file_path: str) -> str:
    url = "https://api.deepgram.com/v1/listen"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/wav"
    }
    try:
        with open(file_path, "rb") as audio_file:
            response = requests.post(url, headers=headers, data=audio_file)
            response.raise_for_status()  # Raise an exception for HTTP errors
            transcription = response.json()
            return transcription['results']['channels'][0]['alternatives'][0]['transcript']
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return ""

def log(log: str):
    print(log)
    with open("status.txt", "w") as f:
        f.write(log)

def convert_text_to_audio(text_content: str, voice_id="pNInz6obpgDQGcFmaJgB") -> str:
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text_content,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    timestamp = int(time())
    output_file_path = f"audio/response_{timestamp}.mp3"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    response = requests.post(url, json=data, headers=headers, stream=True)
    with open(output_file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    return output_file_path

def get_openai_response(prompt: str) -> str:
    url = f"https://api.openai.com/v1/assistants/{ASSISTANT_ID}"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2",
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return ""

    assistant_data = response.json()
    instruction = assistant_data.get('instructions', '')

    # Create a new thread
    response = openai.beta.threads.create()
    thread_id = response.id

    # Send a message to the assistant
    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    # Run the assistant
    run = openai.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
        instructions=instruction
    )

    if run.status == 'completed':
        messages = openai.beta.threads.messages.list(
            thread_id=thread_id
        )
        for message in messages.data:
            if message.role == 'assistant':
                return "".join(block.text.value for block in message.content)
    return "No response from assistant."

if __name__ == "__main__":
    while True:
        # Record audio
        log("Listening...")
        record_audio(duration=20, output_dir="audio", output_filename="recording")
        log("Done listening")

        # Transcribe audio
        transcription = transcribe_audio(RECORDING_PATH)
        with open("conv.txt", "a") as f:
            f.write(f"{transcription}\n")
        log(f"Finished transcribing.")
        if "stop" in transcription.lower():
            log("Stop command detected. Ending conversation.")
            break

        # Get response from OpenAI
        response = get_openai_response(transcription)
        with open("conv.txt", "a") as f:
            f.write(f"{response}\n")

        # Convert response to audio
        response_audio_path = convert_text_to_audio(response)
        log("Finished generating audio.")

        # Play response
        log("Speaking...")
        try:
            sound = mixer.Sound(response_audio_path)
            sound.play()
            pygame.time.wait(int(sound.get_length() * 1000))
            print(f"\n --- USER: {transcription}\n --- ASSISTANT: {response}\n")
        except Exception as e:
            print(f"Error playing audio: {e}")
