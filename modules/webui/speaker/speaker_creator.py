import tempfile

from modules.studio import forms as ui
import torch

from modules.core.models.tts.ChatTtsModel import ChatTTSModel
from modules.utils.hf import spaces
from modules.utils.rng import np_rng
from modules.webui import webui_config
from modules.webui.webui_utils import tts_generate

names_list = [
    "Alice",
    "Bob",
    "Carol",
    "Carlos",
    "Charlie",
    "Chuck",
    "Chad",
    "Craig",
    "Dan",
    "Dave",
    "David",
    "Erin",
    "Eve",
    "Yves",
    "Faythe",
    "Frank",
    "Grace",
    "Heidi",
    "Ivan",
    "Judy",
    "Mallory",
    "Mallet",
    "Darth",
    "Michael",
    "Mike",
    "Niaj",
    "Olivia",
    "Oscar",
    "Peggy",
    "Pat",
    "Rupert",
    "Sybil",
    "Trent",
    "Ted",
    "Trudy",
    "Victor",
    "Vanna",
    "Walter",
    "Wendy",
]


@torch.inference_mode()
@spaces.GPU(duration=120)
def create_spk_from_seed(seed: int, name: str, gender: str, desc: str, author: str, version: str):
    spk = ChatTTSModel.create_speaker_from_seed(seed)
    spk.set_name(name=name)
    spk.set_desc(desc=desc)
    spk.set_gender(gender=gender)
    spk.set_author(author=author)
    spk.set_version(version=version)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".spkv1.json") as tmp_file:
        json_str = spk.to_json_str()
        tmp_file.write(json_str.encode("utf-8"))
        tmp_file_path = tmp_file.name

    return tmp_file_path


@torch.inference_mode()
@spaces.GPU(duration=120)
def test_spk_voice(
    seed: int,
    text: str,
    progress=None,
):
    spk = ChatTTSModel.create_speaker_from_seed(seed)
    return tts_generate(spk=spk, text=text, progress=progress)


def random_speaker():
    seed = np_rng()
    name = names_list[seed % len(names_list)]
    return seed, name


def speaker_creator_ui():
    def on_generate(seed, name, gender, desc, author, version):
        file_path = create_spk_from_seed(seed, name, gender, desc, author, version)
        return file_path

    def create_test_voice_card(seed_input):
        with ui.Group():
            ui.Markdown("🎤Test voice")
            with ui.Row():
                test_voice_btn = ui.Button("Test Voice", variant="secondary")

                with ui.Column(scale=4):
                    test_text = ui.Textbox(
                        label="Test Text",
                        placeholder="Please input test text",
                        value=webui_config.localization.DEFAULT_SPEAKER_TEST_TEXT,
                    )
                    with ui.Row():
                        current_seed = ui.Label(label="Current Seed", value=-1)
                        with ui.Column(scale=4):
                            output_audio = ui.Audio(label="Output Audio", format="mp3")

        test_voice_btn.click(
            fn=test_spk_voice,
            inputs=[seed_input, test_text],
            outputs=[output_audio],
        )
        test_voice_btn.click(
            fn=lambda x: x,
            inputs=[seed_input],
            outputs=[current_seed],
        )

    ui.Markdown("SPEAKER_CREATOR_GUIDE")

    with ui.Row():
        with ui.Column(scale=2):
            with ui.Group():
                ui.Markdown("ℹ️Speaker info")
                seed_input = ui.Number(label="Seed", value=2)
                name_input = ui.Textbox(label="Name", placeholder="Enter speaker name", value="Bob")
                gender_input = ui.Textbox(label="Gender", placeholder="Enter gender", value="*")
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
                )
                random_button = ui.Button("Random Speaker")
            with ui.Group():
                ui.Markdown("🔊Generate speaker.json")
                generate_button = ui.Button("Save .json file")
                output_file = ui.File(label="Save to File")
        with ui.Column(scale=5):
            create_test_voice_card(seed_input=seed_input)
            create_test_voice_card(seed_input=seed_input)
            create_test_voice_card(seed_input=seed_input)
            create_test_voice_card(seed_input=seed_input)

    random_button.click(
        random_speaker,
        outputs=[seed_input, name_input],
    )

    generate_button.click(
        fn=on_generate,
        inputs=[
            seed_input,
            name_input,
            gender_input,
            desc_input,
            author_input,
            version_input,
        ],
        outputs=[output_file],
    )
