"""Adaptery usług chmurowych (REST, tylko biblioteka standardowa). Każde nagranie wysyłane osobno jako WAV
16 kHz mono PCM16, język polski, bez promptów i bez słowników (wariant „surowy”, porównywalny z modelami offline).

Płatne wywołania startują tylko z flagą `run.py --cloud` (zabezpieczenie przed przypadkowym kosztem).
Klucze z eval/.env. Dane testowe są publiczne (ADMEDVOICE, CC BY 4.0), więc mogą być wysyłane do chmury.
"""
import io, json, os, time, uuid, urllib.request, urllib.error
import numpy as np
import soundfile as sf


def wav_bytes(a):
    buf = io.BytesIO(); sf.write(buf, a, 16000, subtype="PCM_16", format="WAV"); return buf.getvalue()


def multipart(fields, file_field, file_bytes, filename="audio.wav", ctype="audio/wav"):
    b = uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    out.write(f'--{b}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
              f"Content-Type: {ctype}\r\n\r\n".encode())
    out.write(file_bytes); out.write(f"\r\n--{b}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={b}"


def post(url, data, headers, retries=5):
    for k in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and k < retries - 1:
                time.sleep(2 ** k * 2); continue
            raise RuntimeError(f"HTTP {e.code}: {body}") from None
        except urllib.error.URLError:
            if k < retries - 1:
                time.sleep(2 ** k * 2); continue
            raise


def need(var):
    v = os.environ.get(var)
    if not v:
        raise RuntimeError(f"Brak {var} w eval/.env")
    return v


class Cloud:
    batch = 1

    def __init__(self, spec):
        self.spec = spec
        self.kind = spec["id"]
        self.fn = {"openai-whisper-1": self.openai, "openai-gpt-4o-transcribe": self.openai,
                   "elevenlabs-scribe": self.elevenlabs, "deepgram-nova-3": self.deepgram,
                   "azure-speech": self.azure}.get(self.kind)
        if not self.fn:
            raise NotImplementedError(f"Adapter {self.kind} jeszcze nie gotowy")

    def transcribe(self, audios):
        return [self.fn(wav_bytes(a)).strip() for a in audios]

    def openai(self, wav):
        body, ct = multipart(dict(model=self.spec["model"], language="pl", response_format="json"), "file", wav)
        r = post("https://api.openai.com/v1/audio/transcriptions", body,
                 {"Authorization": f"Bearer {need('OPENAI_API_KEY')}", "Content-Type": ct})
        return json.loads(r)["text"]

    def elevenlabs(self, wav):
        body, ct = multipart(dict(model_id=self.spec["model"], language_code="pol", tag_audio_events="false",
                                  diarize="false"), "file", wav)
        r = post("https://api.elevenlabs.io/v1/speech-to-text", body,
                 {"xi-api-key": need("ELEVENLABS_API_KEY"), "Content-Type": ct})
        return json.loads(r)["text"]

    def deepgram(self, wav):
        url = f"https://api.deepgram.com/v1/listen?model={self.spec['model']}&language=pl&punctuate=true&smart_format=true"
        r = post(url, wav, {"Authorization": f"Token {need('DEEPGRAM_API_KEY')}", "Content-Type": "audio/wav"})
        return json.loads(r)["results"]["channels"][0]["alternatives"][0]["transcript"]

    def azure(self, wav):
        region = need("AZURE_SPEECH_REGION")
        url = (f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
               f"?language=pl-PL&format=simple")
        r = json.loads(post(url, wav, {"Ocp-Apim-Subscription-Key": need("AZURE_SPEECH_KEY"),
                                       "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000"}))
        return r.get("DisplayText", "") if r.get("RecognitionStatus") == "Success" else ""
