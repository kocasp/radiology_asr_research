"""Adaptery usług chmurowych (REST, tylko biblioteka standardowa). Każde nagranie wysyłane osobno jako WAV
16 kHz mono PCM16, język polski, bez promptów i bez słowników (etap 1 badania: modele bez pomocy).
Wyjątek: Google Gemini wymaga polecenia tekstowego, więc dostaje wyłącznie neutralne „przepisz dosłownie” (GEMINI_PROMPT),
bez słownictwa i bez kontekstu medycznego. Pliki i zadania są usuwane z serwerów usług po odczytaniu wyniku.

Płatne wywołania startują tylko z flagą `run.py --cloud` (zabezpieczenie przed przypadkowym kosztem).
Klucze z eval/.env. Dane testowe są publiczne (ADMEDVOICE, CC BY 4.0), więc mogą być wysyłane do chmury.
"""
import base64, io, json, os, time, uuid, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import soundfile as sf
import google.auth


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


def post(url, data, headers, retries=5, method="POST"):
    for k in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and k < retries - 1:
                ra = e.headers.get("Retry-After")
                time.sleep(float(ra) if ra and ra.replace(".", "", 1).isdigit() else 2 ** k * 2)
                continue
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


def get(url, headers):
    return post(url, None, headers, method="GET")


def poll(fetch, done, failed, every=1.0, timeout=600):
    """Wywołuje fetch() aż done(r) albo failed(r); zwraca ostatnią odpowiedź."""
    t0 = time.time()
    while True:
        r = fetch()
        if done(r):
            return r
        if failed(r):
            raise RuntimeError(f"zadanie odrzucone: {str(r)[:300]}")
        if time.time() - t0 > timeout:
            raise RuntimeError("przekroczony czas oczekiwania na transkrypcję")
        time.sleep(every)


GEMINI_PROMPT = ("Przepisz dosłownie wypowiedź z nagrania w języku polskim. "
                 "Zwróć wyłącznie transkrypcję, bez komentarzy.")


_vertex = {"token": None, "expiry": 0.0, "project": None}


def vertex_auth():
    """Token OAuth i project_id z klucza konta usługi GCP (Vertex AI). Token jest buforowany."""
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        return None, None
    if _vertex["token"] and time.time() < _vertex["expiry"]:
        return _vertex["token"], _vertex["project"]
    from google.auth.transport.requests import Request as GARequest
    creds, project = google.auth.load_credentials_from_file(
        creds_path, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not creds.valid or creds.expired:
        creds.refresh(GARequest())
    _vertex["token"] = creds.token
    _vertex["expiry"] = time.time() + (creds.expiry.timestamp() - time.time()) / 2 if creds.expiry else 3600
    _vertex["project"] = project or json.load(open(creds_path, encoding="utf-8")).get("project_id")
    return _vertex["token"], _vertex["project"]


class Cloud:
    # Nagrania z jednej paczki są wysyłane równolegle (osobne żądania, każde z jednym nagraniem).

    def __init__(self, spec):
        self.spec = spec
        self.kind = spec["id"]
        self.fn = {"openai-whisper-1": self.openai, "openai-gpt-4o-transcribe": self.openai,
                   "elevenlabs-scribe": self.elevenlabs, "deepgram-nova-3": self.deepgram,
                   "azure-speech": self.azure, "speechmatics": self.speechmatics, "soniox": self.soniox,
                   "assemblyai": self.assemblyai, "gemini-transcribe": self.gemini}.get(self.kind)
        if not self.fn:
            raise NotImplementedError(f"Adapter {self.kind} jeszcze nie gotowy")
        self.batch = 8
        self._last = 0.0
        self._interval = 0.0

    def transcribe(self, audios):
        with ThreadPoolExecutor(len(audios)) as ex:
            return [t.strip() for t in ex.map(lambda a: self.fn(wav_bytes(a)), audios)]

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

    # --- usługi asynchroniczne (wysłanie zadania, odpytywanie o wynik) ----------------------------------
    def speechmatics(self, wav):
        base = "https://eu1.asr.api.speechmatics.com/v2/jobs"
        h = {"Authorization": f"Bearer {need('SPEECHMATICS_API_KEY')}"}
        cfg = json.dumps({"type": "transcription",
                          "transcription_config": {"language": "pl", "operating_point": self.spec["model"]}})
        body, ct = multipart({"config": cfg}, "data_file", wav)
        jid = json.loads(post(base, body, dict(h, **{"Content-Type": ct})))["id"]
        poll(lambda: json.loads(get(f"{base}/{jid}", h))["job"]["status"],
             lambda st: st == "done", lambda st: st in ("rejected", "deleted", "expired"))
        txt = get(f"{base}/{jid}/transcript?format=txt", h)
        post(f"{base}/{jid}", None, h, method="DELETE")
        return txt

    def soniox(self, wav):
        base = "https://api.soniox.com/v1"
        h = {"Authorization": f"Bearer {need('SONIOX_API_KEY')}"}
        body, ct = multipart({}, "file", wav)
        fid = json.loads(post(f"{base}/files", body, dict(h, **{"Content-Type": ct})))["id"]
        req = json.dumps({"model": self.spec["model"], "file_id": fid, "language_hints": ["pl"]}).encode()
        tid = json.loads(post(f"{base}/transcriptions", req, dict(h, **{"Content-Type": "application/json"})))["id"]
        poll(lambda: json.loads(get(f"{base}/transcriptions/{tid}", h)),
             lambda r: r["status"] == "completed", lambda r: r["status"] == "error")
        txt = json.loads(get(f"{base}/transcriptions/{tid}/transcript", h))["text"]
        post(f"{base}/transcriptions/{tid}", None, h, method="DELETE")
        post(f"{base}/files/{fid}", None, h, method="DELETE")
        return txt

    def assemblyai(self, wav):
        base = "https://api.eu.assemblyai.com/v2"
        h = {"authorization": need("ASSEMBLYAI_API_KEY")}
        url = json.loads(post(f"{base}/upload", wav, dict(h, **{"Content-Type": "application/octet-stream"})))["upload_url"]
        req = json.dumps({"audio_url": url, "speech_models": [self.spec["model"]], "language_code": "pl"}).encode()
        tid = json.loads(post(f"{base}/transcript", req, dict(h, **{"Content-Type": "application/json"})))["id"]
        r = poll(lambda: json.loads(get(f"{base}/transcript/{tid}", h)),
                 lambda r: r["status"] == "completed", lambda r: r["status"] == "error")
        post(f"{base}/transcript/{tid}", None, h, method="DELETE")
        return r.get("text") or ""

    def gemini(self, wav):
        if self._interval:
            wait = self._interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
        self._last = time.time()
        model = self.spec["model"]
        req = {"contents": [{"parts": [{"text": GEMINI_PROMPT},
                                       {"inline_data": {"mime_type": "audio/wav",
                                                        "data": base64.b64encode(wav).decode()}}]}],
               "generationConfig": {"temperature": 0}}
        token, project = vertex_auth()
        if token:
            location = os.environ.get("VERTEX_LOCATION", "us-central1")
            url = (f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}"
                   f"/publishers/google/models/{model}:generateContent")
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            headers = {"x-goog-api-key": need("GEMINI_API_KEY"), "Content-Type": "application/json"}
        r = json.loads(post(url, json.dumps(req).encode(), headers))
        parts = r["candidates"][0].get("content", {}).get("parts", [])
        return " ".join(p.get("audioTranscription", {}).get("text") or p.get("text", "")
                         for p in parts if not p.get("thought"))
