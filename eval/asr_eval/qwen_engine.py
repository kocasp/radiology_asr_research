"""Adapter Qwen3-ASR (pakiet `qwen-asr`, backend transformers). Uruchamiany w eval/.venv-qwen.
Język wymuszony: Polish. Dekodowanie domyślne pakietu (bez promptu kontekstowego)."""
import torch


class QwenASR:
    batch = 4

    def __init__(self, spec):
        from qwen_asr import Qwen3ASRModel
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        self.m = Qwen3ASRModel.from_pretrained(spec["model"], dtype=torch.float16 if dev == "mps" else torch.float32,
                                               device_map=dev, max_inference_batch_size=self.batch, max_new_tokens=256)

    def transcribe(self, audios):
        res = self.m.transcribe(audio=[(a, 16000) for a in audios], language="Polish")
        return [r.text.strip() for r in res]
