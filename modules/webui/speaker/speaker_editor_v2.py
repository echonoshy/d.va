import tempfile

from modules.studio import forms as ui
import numpy as np
import torch

from modules.core.models.tts.ChatTtsModel import ChatTTSModel
from modules.core.spk.dcls import DcSpkInferConfig, DcSpkReference, DcSpkSample
from modules.core.spk.TTSSpeaker import TTSSpeaker
from modules.utils.hf import spaces
from modules.webui import webui_config
from modules.webui.speaker.wav_misc import encode_to_wav
from modules.webui.webui_utils import tts_generate

# TODO: 增加 png 编辑


@torch.inference_mode()
@spaces.GPU(duration=120)
def test_spk_voice(
    spk_file,
    text: str,
    progress=None,
):
    if spk_file == "" or spk_file is None:
        return None
    spk = TTSSpeaker.from_file(spk_file)
    return tts_generate(spk=spk, text=text, progress=progress)


@torch.inference_mode()
@spaces.GPU(duration=120)
# v2 可以编辑更多内容，比如上传参考音频
def speaker_editor_ui_v2():
    def on_generate(
        # meta
        name: str,
        desc: str,
        gender: str,
        version: str,
        author: str,
        # from seed
        chat_tts_seed: int,
        # sample audio
        sample_audio: tuple[int, np.ndarray],
        sample_audio_text: str,
        # ref audio
        ref_audio: tuple[int, np.ndarray],
        ref_audio_text: str,
        # recommend
        rec_temperature: float,
        rec_top_p: float,
        rec_top_k: int,
        rec_max_tokens: int,
        rec_repetition_penalty: float,
        rec_emotion: str,
        # avatar
        # avatar_file: str,
        # train
    ):
        if name.strip() == "":
            raise ui.Error(
                "Please enter speaker name.",
            )

        spk: TTSSpeaker = ChatTTSModel.create_speaker_from_seed(chat_tts_seed) if chat_tts_seed >= 0 else TTSSpeaker.empty()
        spk._data.meta.author = author
        spk._data.meta.name = name
        spk._data.meta.desc = desc
        spk._data.meta.version = version
        spk._data.meta.gender = gender

        spk._data.recommend_config = DcSpkInferConfig(
            tempature=rec_temperature,
            top_p=rec_top_p,
            top_k=rec_top_k,
            max_tokens=rec_max_tokens,
            repetition_penalty=rec_repetition_penalty,
            emotion=rec_emotion,
        )

        if sample_audio and sample_audio_text:
            sr, wav = encode_to_wav(sample_audio)
            spk.add_sample(sample=DcSpkSample(wav=wav, wav_sr=sr, text=sample_audio_text))
        elif sample_audio_text:
            raise ui.Error(
                "Please upload sample audio file or enter sample text.",
            )
        elif sample_audio:
            raise ui.Error(
                "Please enter sample text.",
            )

        if ref_audio and ref_audio_text:
            sr, wav = encode_to_wav(ref_audio)
            spk.add_ref(ref=DcSpkReference(wav=wav, wav_sr=sr, text=ref_audio_text))
        elif ref_audio_text:
            raise ui.Error(
                "Please upload refrence audio file or enter refrence text.",
            )
        elif ref_audio:
            raise ui.Error(
                "Please enter refrence text.",
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".spkv1.json") as tmp_file:
            json_str = spk.to_json_str()
            tmp_file.write(json_str.encode("utf-8"))
            tmp_file_path = tmp_file.name

        return tmp_file_path

    with ui.Row():
        with ui.Column(scale=2):
            with ui.Group():
                ui.Markdown("ℹ️Speaker info")
                name_input = ui.Textbox(
                    label="Name",
                    placeholder="Enter speaker name",
                    value="",
                )
                gender_input = ui.Textbox(
                    label="Gender",
                    placeholder="Enter gender",
                    value="",
                )
                author_input = ui.Textbox(
                    label="Author",
                    placeholder="Enter author",
                    value="",
                )
                version_input = ui.Textbox(
                    label="Version",
                    placeholder="Enter version",
                    value="",
                )
                desc_input = ui.Textbox(
                    label="Description",
                    placeholder="Enter description",
                    value="",
                )

            with ui.Group():
                # 设置推荐参数
                ui.Markdown("🔊Recommend Config")
                rec_temperature = ui.Slider(0.01, 2.0, value=0.1, step=0.01, label="Temperature")
                rec_top_p = ui.Slider(0.1, 1.0, value=0.7, step=0.1, label="Top P")
                rec_top_k = ui.Slider(1, 50, value=20, step=1, label="Top K")
                rec_max_tokens = ui.Slider(100, 2048, value=2048, step=1, label="Max Tokens")
                rec_repetition_penalty = ui.Slider(0.0, 2.0, value=1.1, step=0.1, label="Repetition Penalty")
                rec_emotion = ui.Textbox(label="Emotion", placeholder="Enter emotion", value="*")

            with ui.Group():
                ui.Markdown("🔊Generate speaker.json")
                generate_button = ui.Button("Save .json file", variant="primary")
                output_file = ui.File(label="Save to File")

            # TODO
            with ui.Group(visible=False):
                ui.Markdown("🔊Embed to .png")
                ui.File(label="avatar file", file_types=["image"])

                ui.Button(
                    "Save .png file",
                )
                ui.File(label="Save to File")

        with ui.Column(scale=5):
            # NOTE: 这里暂时不显示了，需要创建的话可以从 ChatTTS/creator 里面创建
            with ui.Group(visible=False):
                # 从种子创建 spk -1 为默认值，即不使用种子
                ui.Markdown("From Seed")
                chat_tts_seed = ui.Number(label="ChatTTS Seed", value=-1, minimum=-1, maximum=2**23)

            with ui.Group():
                # 上传参考音频 模型将参考此文件输出
                ui.Markdown("🔊Refrence Audio")
                ref_audio = ui.Audio(label="Refrence Audio")
                ref_audio_text = ui.Textbox(label="Refrence Text", placeholder="Enter refrence text")

            with ui.Group():
                # 上传示例音频 仅用于演示api (xtts)
                ui.Markdown("🔊Sample Audio")
                sample_audio = ui.Audio(label="Sample Audio")
                sample_audio_text = ui.Textbox(label="Sample Text", placeholder="Enter sample text")

            with ui.Group(visible=False):
                # 设置训练数据
                ui.Markdown("🔊Traing Info")
                # TODO
                ui.Number()

    generate_button.click(
        fn=on_generate,
        inputs=[
            name_input,
            desc_input,
            gender_input,
            version_input,
            author_input,
            chat_tts_seed,
            sample_audio,
            sample_audio_text,
            ref_audio,
            ref_audio_text,
            rec_temperature,
            rec_top_p,
            rec_top_k,
            rec_max_tokens,
            rec_repetition_penalty,
            rec_emotion,
            # avatar_file,
        ],
        outputs=[output_file],
    )
