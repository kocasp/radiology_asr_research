"""Adapter NVIDIA NeMo (FastConformer hybrid TDT/CTC). Uruchamiany w eval/.venv-nemo.
Dekodowanie: domyślny dekoder RNNT/TDT modelu (greedy), bez modelu językowego.
"""
import os
import tempfile
import soundfile as sf


class NeMo:
    batch = 8

    def __init__(self, spec):
        import nemo.collections.asr as nemo_asr
        self.model = nemo_asr.models.ASRModel.from_pretrained(spec["model"].split("/")[-1]
                                                              if not spec["model"].startswith("nvidia/") else spec["model"])
        self.model.eval()
        self.kw = dict(source_lang=spec["source_lang"], target_lang=spec["source_lang"]) if spec.get("source_lang") else {}
        self.tmp = tempfile.mkdtemp(prefix="nemo_eval_")

    def transcribe(self, audios):
        paths = []
        for k, a in enumerate(audios):
            p = os.path.join(self.tmp, f"{k}.wav"); sf.write(p, a, 16000); paths.append(p)
        out = self.model.transcribe(paths, batch_size=len(paths), verbose=False, **self.kw)
        if isinstance(out, tuple):          # (best, all) w części wersji NeMo
            out = out[0]
        return [(o.text if hasattr(o, "text") else str(o)).strip() for o in out]
