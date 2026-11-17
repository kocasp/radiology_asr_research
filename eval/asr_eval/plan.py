"""Plan badania: lista modeli w kolejności uruchamiania.

Zakres: tylko gotowe, dostępne rozwiązania. Modele dotrenowane na ADMEDVOICE (whisper-medium-medical-pl,
VoxMedic) są wykluczone — znają frazy testowe (przeciek danych, README sekcja 4.2).

status ustala runner: pending / running / done / blocked / failed.
`blocked_reason` = czego brakuje (np. klucz API, akceptacja warunków na HF).
`leak_risk` = model mógł widzieć nasze frazy/mówców w treningu.
"""
import os

LORA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "kaggle_lora", "medical-transcribe-pl")

def lora(variant):
    return os.path.abspath(os.path.join(LORA_DIR, variant))

PLAN = [
    # --- 1. model bazowy z publikacji -------------------------------------------------------------
    dict(id="whisper-medium", group="Model bazowy z publikacji ADMEDVOICE", name="Whisper medium",
         engine="hf_whisper", model="openai/whisper-medium", mode="offline", params="769M",
         note="Model bazowy z artykułu (deklarowany WER 24,0 na teście natural)."),
    # --- 3. modele otwarte (offline) --------------------------------------------------------------------
    dict(id="whisper-large-v3-turbo", group="Open source (offline)", name="Whisper large-v3-turbo",
         engine="hf_whisper", model="openai/whisper-large-v3-turbo", mode="offline", params="809M"),
    dict(id="whisper-large-v3", group="Open source (offline)", name="Whisper large-v3",
         engine="hf_whisper", model="openai/whisper-large-v3", mode="offline", params="1,55B"),
    dict(id="nemo-fastconformer-pl", group="Open source (offline)", name="NVIDIA FastConformer PL (hybrid, P&C)",
         engine="nemo", model="nvidia/stt_pl_fastconformer_hybrid_large_pc", mode="offline", params="115M",
         note="Wymaga osobnego środowiska z NVIDIA NeMo."),
    # --- SOTA 2025–2026 z obsługą polskiego (sprawdzone w kartach modeli na HF, 2026-11-17) ---------
    dict(id="nvidia-canary-1b-v2", group="Open source SOTA 2025–2026 (offline)", name="NVIDIA Canary-1B-v2",
         engine="nemo", model="nvidia/canary-1b-v2", mode="offline", params="978M", source_lang="pl",
         note="25 języków europejskich (w tym pl), CC-BY-4.0, sierpień 2025."),
    dict(id="nvidia-parakeet-tdt-v3", group="Open source SOTA 2025–2026 (offline)", name="NVIDIA Parakeet-TDT-0.6B-v3",
         engine="nemo", model="nvidia/parakeet-tdt-0.6b-v3", mode="offline", params="600M",
         note="25 języków europejskich (w tym pl), automatyczne wykrywanie języka, CC-BY-4.0, sierpień 2025."),
    dict(id="qwen3-asr-1.7b", group="Open source SOTA 2025–2026 (offline)", name="Qwen3-ASR-1.7B",
         engine="qwen_asr", model="Qwen/Qwen3-ASR-1.7B", mode="offline", params="1,7B",
         note="30 języków (w tym pl), Apache-2.0, styczeń 2026."),
    dict(id="cohere-transcribe", group="Open source SOTA 2025–2026 (offline)", name="Cohere Transcribe 03-2026",
         engine="cohere", model="CohereLabs/cohere-transcribe-03-2026", mode="offline", params="?",
         gated="Wymaga akceptacji warunków na HF (CohereLabs).", note="Apache-2.0, marzec 2026, tag pl."),
    dict(id="nemotron-3.5-transcribe", group="Open source SOTA 2025–2026 (offline)", name="NVIDIA Nemotron 3.5 Transcribe 30B-A4B",
         engine="gpu_remote", model="nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B", mode="offline", params="30B (4,3B aktywnych, MoE)",
         gated="Za duży na Maca 16 GB (BF16 ~60 GB, FP8 ~30 GB). Wymaga wynajętego GPU (np. HF Jobs A100).",
         note="40 języków (w tym pl), licencja OpenMDW-1.1, październik 2025/2026 — najnowszy model NVIDIA."),
    dict(id="omniasr-ctc-1b", group="Open source SOTA 2025–2026 (offline)", name="Meta Omnilingual ASR (CTC 1B)",
         engine="omniasr", model="facebook/omniASR-CTC-1B", mode="offline", params="1B",
         note="1600+ języków (w tym pl), Apache-2.0, listopad 2025. Wariant LLM-7B za duży na 16 GB RAM."),
    dict(id="wav2vec2-xlsr53-pl", group="Open source (offline)", name="wav2vec2 XLSR-53 Polish (bez LM)",
         engine="hf_ctc", model="jonatasgrosman/wav2vec2-large-xlsr-53-polish", mode="offline", params="315M", processor="wav2vec2", batch=4),
    dict(id="mms-1b-all-pol", group="Open source (offline)", name="Meta MMS-1b-all (adapter pol, bez LM)",
         engine="hf_mms", model="facebook/mms-1b-all", mode="offline", params="1B", batch=1, note="Licencja CC-BY-NC 4.0."),
    dict(id="wav2vec2-xlsr53-pl-lm", group="Open source (offline)", name="wav2vec2 XLSR-53 Polish + KenLM",
         engine="hf_ctc", model="jonatasgrosman/wav2vec2-large-xlsr-53-polish", mode="offline", params="315M + 5-gram LM",
         processor="wav2vec2", batch=4, lm="jonatasgrosman/wav2vec2-large-xlsr-53-polish",
         note="Ogólny polski KenLM z repozytorium modelu (2021, sprzed ADMEDVOICE); beam search pyctcdecode."),
    dict(id="mms-1b-all-pol-lm", group="Open source (offline)", name="Meta MMS-1b-all (pol) + KenLM",
         engine="hf_mms", model="facebook/mms-1b-all", mode="offline", params="1B + 5-gram LM", batch=1,
         lm="jonatasgrosman/wav2vec2-large-xlsr-53-polish",
         note="Ten sam ogólny polski KenLM co dla wav2vec2. Licencja CC-BY-NC 4.0."),
    dict(id="google-medasr", group="Open source (offline)", name="Google MedASR",
         engine="hf_ctc", model="google/medasr", mode="offline", params="105M",
         gated="Wymaga akceptacji warunków HAI-DEF na HF i tokenu HF.",
         note="KONTROLA NEGATYWNA: model tylko angielski (karta modelu). Oczekiwany wynik bliski 100% WER — sprawdza, czy metryka działa; nie jest kandydatem do polskiej radiologii."),
    # --- 4. usługi chmurowe (online) ---------------------------------------------------------------------
    dict(id="elevenlabs-scribe", key="ELEVENLABS_API_KEY", group="Chmura (online)", name="ElevenLabs Scribe v2", engine="cloud",
         model="scribe_v2", mode="online", gated="Brak klucza ELEVENLABS_API_KEY."),
    dict(id="openai-whisper-1", key="OPENAI_API_KEY", group="Chmura (online)", name="OpenAI whisper-1", engine="cloud",
         model="whisper-1", mode="online", gated="Brak klucza OPENAI_API_KEY."),
    dict(id="openai-gpt-4o-transcribe", key="OPENAI_API_KEY", group="Chmura (online)", name="OpenAI gpt-4o-transcribe", engine="cloud",
         model="gpt-4o-transcribe", mode="online", gated="Brak klucza OPENAI_API_KEY."),
    dict(id="deepgram-nova-3", key="DEEPGRAM_API_KEY", group="Chmura (online)", name="Deepgram Nova-3", engine="cloud",
         model="nova-3", mode="online", gated="Brak klucza DEEPGRAM_API_KEY."),
    dict(id="speechmatics", key="SPEECHMATICS_API_KEY", group="Chmura (online)", name="Speechmatics (pl) / Oak (medyczny)",
         engine="cloud", model="enhanced", mode="online", gated="Brak klucza SPEECHMATICS_API_KEY.",
         note="Deklaruje polski i model medyczny Oak (październik 2026) — deklaracja producenta."),
    dict(id="soniox", key="SONIOX_API_KEY", group="Chmura (online)", name="Soniox", engine="cloud", model="stt-async",
         mode="online", gated="Brak klucza SONIOX_API_KEY."),
    dict(id="assemblyai", key="ASSEMBLYAI_API_KEY", group="Chmura (online)", name="AssemblyAI Universal", engine="cloud",
         model="universal", mode="online", gated="Brak klucza ASSEMBLYAI_API_KEY.",
         note="W benchmarku BIGOS V2 (2024) jeden z dwóch najlepszych systemów dla polskiego."),
    dict(id="gemini-transcribe", key="GEMINI_API_KEY", group="Chmura (online)", name="Google Gemini (transkrypcja przez LLM)",
         engine="cloud", model="gemini-2.5/3.x", mode="online", gated="Brak klucza GEMINI_API_KEY.",
         note="Multimodalny LLM; prompt wyłącznie „przepisz dosłownie”."),
    dict(id="google-chirp", key="GOOGLE_APPLICATION_CREDENTIALS", group="Chmura (online)", name="Google Cloud STT Chirp", engine="cloud",
         model="chirp_2/chirp_3", mode="online", gated="Brak projektu i poświadczeń Google Cloud."),
    dict(id="azure-speech", key="AZURE_SPEECH_KEY", group="Chmura (online)", name="Microsoft Azure AI Speech", engine="cloud",
         model="pl-PL", mode="online", gated="Brak klucza AZURE_SPEECH_KEY i regionu."),
]
