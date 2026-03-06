import os
from pathlib import Path
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

text = Path(__file__).with_name("three_topics_tts.txt").read_text(encoding="utf-8").strip()

key = os.getenv("AZURE_AI_SERVICES_KEY", "").strip().strip('"')
region = os.getenv("AZURE_AI_SERVICES_REGION", "").strip().strip('"')
if not key or not region:
    raise SystemExit("Missing AZURE_AI_SERVICES_KEY or AZURE_AI_SERVICES_REGION")

out_dir = Path("dist")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "three_topics_tts.mp3"

speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
)
audio_config = speechsdk.audio.AudioOutputConfig(filename=str(out_file))
synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
result = synthesizer.speak_text_async(text).get()

if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
    print(f"OK:{out_file}")
else:
    details = speechsdk.CancellationDetails(result)
    raise RuntimeError(f"Synthesis failed: {details.reason}; {details.error_details}")
