"""Adaptery silników ASR. Wspólny interfejs: Engine(spec).transcribe(list[np.ndarray 16 kHz]) -> list[str].

Dekodowanie Whisper: greedy (num_beams=1), language="pl", task="transcribe", bez promptu —
identyczne dla wszystkich modeli z rodziny Whisper.
"""
import torch


def device():
    return "mps" if torch.backends.mps.is_available() else "cpu"


class HFWhisper:
    batch = 8

    def __init__(self, spec):
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
        dev = device()
        self.dev, self.dtype = dev, torch.float16 if dev == "mps" else torch.float32
        self.proc = WhisperProcessor.from_pretrained(spec["model"])
        model = WhisperForConditionalGeneration.from_pretrained(spec["model"], torch_dtype=torch.float32)
        if spec.get("lora"):
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, spec["lora"]).merge_and_unload()
        self.model = model.to(dev, self.dtype).eval()

    @torch.inference_mode()
    def transcribe(self, audios):
        inp = self.proc(audios, sampling_rate=16000, return_tensors="pt", return_attention_mask=True)
        ids = self.model.generate(inp.input_features.to(self.dev, self.dtype), attention_mask=inp.attention_mask.to(self.dev),
                                  language="pl", task="transcribe", num_beams=1, do_sample=False, max_new_tokens=220)
        return [t.strip() for t in self.proc.batch_decode(ids, skip_special_tokens=True)]


class HFCTC:
    batch = 8

    def __init__(self, spec, target_lang=None):
        from transformers import AutoProcessor, AutoModelForCTC, Wav2Vec2Processor
        self.batch = spec.get("batch", self.batch)
        self.dev = device()
        # repo wav2vec2-xlsr-53-polish zawiera też KenLM; AutoProcessor wybrałby wtedy dekoder z LM.
        # Testujemy wariant bez LM, więc wymuszamy zwykły procesor CTC.
        cls = Wav2Vec2Processor if spec.get("processor") == "wav2vec2" else AutoProcessor
        self.proc = cls.from_pretrained(spec["model"])
        kw = dict(target_lang=target_lang, ignore_mismatched_sizes=True) if target_lang else {}
        self.model = AutoModelForCTC.from_pretrained(spec["model"], **kw)
        if target_lang:
            self.proc.tokenizer.set_target_lang(target_lang)
            self.model.load_adapter(target_lang)
        self.model = self.model.to(self.dev).eval()
        self.decoder = self._lm_decoder(spec["lm"]) if spec.get("lm") else None

    def _lm_decoder(self, repo):
        """Beam search CTC + KenLM (pyctcdecode). LM i jego wagi alpha/beta z repo `repo/language_model/`."""
        import json
        from huggingface_hub import hf_hub_download
        from pyctcdecode import build_ctcdecoder
        get = lambda f: hf_hub_download(repo, f"language_model/{f}")
        attrs = json.load(open(get("attrs.json")))
        unigrams = [w for w in open(get("unigrams.txt"), encoding="utf-8").read().split("\n") if w]
        tok = self.proc.tokenizer
        n = self.model.lm_head.out_features
        labels = [""] * n
        for t, i in tok.get_vocab().items():
            if i < n:
                labels[i] = t
        labels = ["" if t == tok.pad_token else " " if t == tok.word_delimiter_token else t for t in labels]
        return build_ctcdecoder(labels, kenlm_model_path=get("lm.binary"), unigrams=unigrams,
                                alpha=attrs.get("alpha", 0.5), beta=attrs.get("beta", 1.5))

    @torch.inference_mode()
    def transcribe(self, audios):
        inp = self.proc(audios, sampling_rate=16000, return_tensors="pt", padding=True)
        logits = self.model(**{k: v.to(self.dev) for k, v in inp.items()}).logits
        if self.decoder is None:
            ids = logits.argmax(-1).cpu()
            return [t.strip() for t in self.proc.batch_decode(ids)]
        lens = self.model._get_feat_extract_output_lengths(torch.tensor([len(a) for a in audios])).tolist()
        lp = torch.log_softmax(logits.float(), -1).cpu().numpy()
        return [self.decoder.decode(lp[k, :lens[k]]).strip() for k in range(len(audios))]


def make(spec):
    if spec["engine"] == "hf_whisper":
        return HFWhisper(spec)
    if spec["engine"] == "hf_ctc":
        return HFCTC(spec)
    if spec["engine"] == "hf_mms":
        return HFCTC(spec, target_lang="pol")
    raise NotImplementedError(spec["engine"])
