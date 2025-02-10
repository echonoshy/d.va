import base64
import copy
import dataclasses
import json
import uuid
import inspect
from typing import Any, Callable, Optional, Union

import numpy as np
import torch

from modules.core.spk.dcls import (
    DcSpk,
    DcSpkInferConfig,
    DcSpkMeta,
    DcSpkReference,
    DcSpkSample,
    DcSpkTrainInfo,
    DcSpkVoiceToken,
)
from modules.utils import audio_utils

dclses = [
    DcSpk,
    DcSpkInferConfig,
    DcSpkMeta,
    DcSpkVoiceToken,
    DcSpkTrainInfo,
    DcSpkSample,
    DcSpkReference,
]


def dcls_asdict(obj: Any) -> dict:
    ret = dict()
    for f in dataclasses.fields(obj):
        k = f.name
        v = getattr(obj, k)
        if dataclasses.is_dataclass(v):
            ret[k] = {
                "_type": v.__class__.__name__,
                "data": dcls_asdict(v),
            }
        else:
            ret[k] = v

    return ret


class DcSpkEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, torch.Tensor):
            # token 会触发这里
            arr_bytes = obj.cpu().float().detach().numpy().tobytes()
            return {
                "_type": "torch.Tensor",
                "data": base64.b64encode(arr_bytes).decode("utf-8"),
            }
        if isinstance(obj, bytes):
            # refrence wav 会触发这里
            return {
                "_type": "bytes",
                "data": base64.b64encode(obj).decode("utf-8"),
            }
        if dataclasses.is_dataclass(obj):
            return {
                "_type": obj.__class__.__name__,
                "data": dcls_asdict(obj),
            }
        return super().default(obj)


class DcSpkDecoder(json.JSONDecoder):

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if "_type" in obj:
            if obj["_type"] == "torch.Tensor":
                return torch.from_numpy(
                    np.frombuffer(
                        base64.b64decode(obj["data"]), dtype=np.float32
                    ).copy()
                )
            if obj["_type"] == "bytes":
                return base64.b64decode(obj["data"])
            for dlcs in dclses:
                if obj["_type"] == dlcs.__name__:
                    data = obj["data"]

                    params = inspect.signature(dlcs.__init__).parameters
                    filtered_data = {k: v for k, v in data.items() if k in params}
                    return dlcs(**filtered_data)
        return obj


class TTSSpeaker:

    @staticmethod
    def empty() -> "TTSSpeaker":
        """
        return a empty TTSSpeaker
        """
        return TTSSpeaker(
            DcSpk(
                id=uuid.uuid4().hex,
            )
        )

    @staticmethod
    def from_json(data: dict) -> "TTSSpeaker":
        return TTSSpeaker(
            json.loads(
                json.dumps(data, cls=DcSpkEncoder, ensure_ascii=False),
                cls=DcSpkDecoder,
            )
        )

    @staticmethod
    def from_file(path: str) -> "TTSSpeaker":
        if path.endswith(".spkv1.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TTSSpeaker.from_json(data)
        elif path.endswith(".spkv1.png"):
            raise NotImplementedError("load speaker from png not implemented")
        else:
            raise ValueError(f"unsupported file type: {path}")

    @staticmethod
    def from_token(model_id: str, tokens: list) -> "TTSSpeaker":
        spk = TTSSpeaker.empty()
        spk.set_token(tokens=tokens, model_id=model_id)
        return spk

    @staticmethod
    def from_ref_wav(ref_wav: tuple[int, np.ndarray], text="") -> "TTSSpeaker":
        sr, data = ref_wav
        assert data.dtype == np.int16, f"ref wav must be int16, but got {data.dtype}"

        spk = TTSSpeaker.empty()
        spk.add_ref(ref=DcSpkReference(text=text, wav=data.tobytes(), wav_sr=sr))
        return spk

    @staticmethod
    def from_ref_wav_bytes(ref_wav: tuple[int, bytes], text="") -> "TTSSpeaker":
        sr, data = ref_wav
        spk = TTSSpeaker.empty()
        spk.add_ref(ref=DcSpkReference(text=text, wav=data, wav_sr=sr))
        return spk

    def __init__(self, data: DcSpk) -> None:
        assert isinstance(data, DcSpk), "data must be a DcSpk instance"

        self._data = data

    @property
    def has_refs(self):
        """
        用于判断是否可以作为 ref spk 用于 vicoe clone pipeline
        """
        return len(self._data.refs) != 0

    def to_json_str(self, just_info=False) -> str:
        data = self._data
        if just_info:
            data = copy.copy(data)
            data.recommend_config = None
            data.refs = None
            data.samples = None
            data.token = None
        return json.dumps(data, cls=DcSpkEncoder, ensure_ascii=False)

    def to_json(self, just_info=False) -> dict:
        json_str = self.to_json_str(just_info)
        data = json.loads(json_str)
        return data

    def get_token(self, model_id: str) -> Optional[DcSpkVoiceToken]:
        for token in self._data.token:
            if token.model_id == model_id:
                return token
        # 当前 speaker 不支持此模型
        # NOTE: 如果 spk 提供了 refrence wav 可以根据 refrence wav 计算出来
        #       对应的逻辑应该写在 pre processor 里
        # raise ValueError(f"speaker {self._data.meta.name} not support model {model_id}")
        return None

    def get_ref(
        self, get_func: Optional[Callable[[DcSpkReference], bool]] = None
    ) -> Optional[DcSpkReference]:
        if self._data.refs is None:
            return None
        if len(self._data.refs) == 0:
            return None
        ref0 = self._data.refs[0]
        if len(self._data.refs) == 1 or get_func is None:
            return ref0

        found_ref = None
        for ref in self._data.refs:
            if get_func(ref):
                found_ref = ref
                break
        if found_ref is not None:
            return found_ref
        return ref0

    def get_ref_wav(
        self, get_func: Optional[Callable[[DcSpkReference], bool]] = None
    ) -> Union[tuple[int, np.ndarray, str], tuple[None, None, None]]:
        ref0 = self.get_ref(get_func)
        if ref0 is None:
            return None, None, None
        sr = ref0.wav_sr
        wav_bytes = ref0.wav
        wav = audio_utils.bytes_to_librosa_array(audio_bytes=wav_bytes, sample_rate=sr)
        text = ref0.text
        return sr, wav, text

    def get_recommend_config(self) -> Optional[DcSpkInferConfig]:
        if self._data.recommend_config:
            return self._data.recommend_config
        return None

    def set_name(self, name: str) -> None:
        self._data.meta.name = name

    def set_gender(self, gender: str) -> None:
        self._data.meta.gender = gender

    def set_author(self, author: str) -> None:
        self._data.meta.author = author

    def set_desc(self, desc: str) -> None:
        self._data.meta.desc = desc

    def set_version(self, version: str) -> None:
        self._data.meta.version = version

    def set_token(self, tokens: list, model_id: str, model_hash: str = "") -> None:
        token = DcSpkVoiceToken(
            model_id=model_id,
            model_hash=model_hash,
            tokens=tokens,
        )
        self.set_token_obj(token=token)

    def set_token_obj(self, *, token: DcSpkVoiceToken):
        for i, t in enumerate(self._data.token):
            if t.model_id == token.model_id:
                self._data.token[i] = token
                return
        self._data.token.append(token)

    def add_ref(self, *, ref: DcSpkReference) -> None:
        if self._data.refs is None:
            self._data.refs = []
        self._data.refs.append(ref)

    def add_sample(self, *, sample: DcSpkSample) -> None:
        if self._data.samples is None:
            self._data.samples = []
        self._data.samples.append(sample)

    @property
    def id(self) -> str:
        return self._data.id

    @property
    def name(self) -> str:
        return self._data.meta.name

    @property
    def desc(self) -> str:
        return self._data.meta.desc

    @property
    def gender(self) -> str:
        return self._data.meta.gender

    @property
    def author(self) -> str:
        return self._data.meta.author

    @property
    def version(self) -> str:
        return self._data.meta.version

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, TTSSpeaker):
            return False
        return str(self.id) == str(other.id)
