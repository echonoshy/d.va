import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from modules.studio.device import configure
from modules.repos_static.sys_paths import setup_repos_paths
from modules.studio.media import decode_media, read_mono


class StudioContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup_repos_paths()
        configure()
        from modules.webui.app import create_interface

        cls.form = create_interface()

    def test_baseline_operations_are_wired_in_their_own_panels(self):
        events = set()
        for event in self.form.events:
            node = self.form.nodes[event.source]
            button = node.props.get("value")
            if not isinstance(button, str):
                continue
            trail = []
            while node.parent is not None:
                node = self.form.nodes[node.parent]
                if node.kind in ("Tab", "TabItem"):
                    trail.insert(0, node.props["label"])
            events.add(("/".join(trail), button))
        for path, name in (
            ("TTS/ChatTTS", "🔊Generate Audio"),
            ("TTS/FishSpeech", "🔊Generate Audio"),
            ("SSML/Editor", "🔊Synthesize SSML"),
            ("SSML/Script", "📩Send to SSML"),
            ("SSML/长文本切分", "🔪Split Text"),
            ("SSML/多人播客", "📩Send to SSML"),
            ("SSML/字幕导入", "📩Send to Script"),
            ("音色管理/Builder", "Save .json file"),
            ("音色管理/Test Voice", "Test Voice"),
            ("音色管理/ChatTTS/Merger", "Save Speaker"),
            ("音色管理/ChatTTS/Creator", "Save .json file"),
            ("声音克隆", "转换音色"),
            ("训练", "Start Training"),
            ("训练", "Stop Training"),
            ("话题转 SSML 播客/LLM Podcast", "生成播客"),
            ("系统", "Unload All Models"),
            ("音频工具/Video Cut", "提取音频"),
        ):
            with self.subTest(path=path, name=name):
                self.assertIn((path, name), events)

    def test_original_model_api_routes(self):
        from modules.studio.legacy_api import routes

        expected = set(
            """
            /v1/ping /v1/versions /v1/audio_formats /v1/models/reload /v1/models/unload
            /v1/models/list /v1/styles/list /v1/speakers/list /v1/speakers/refresh
            /v1/speakers/update /v1/speaker/create /v1/speaker/update /v1/speaker/detail
            /v1/tts /v1/ssml /v1/prompt/refine /v1/text/normalize /v1/xtts_v2/speakers
            /v1/xtts_v2/tts_to_audio /v1/xtts_v2/tts_stream /v1/xtts_v2/set_tts_settings
            /v1/vc /v2/tts
        """.split()
        )
        self.assertEqual(set(routes().openapi()["paths"]), expected)

    def test_existing_card_and_subtitle_to_ssml(self):
        from modules.core.spk.TTSSpeaker import TTSSpeaker
        from modules.webui.ssml.subtitle_tab import read_subtitle_file
        from modules.core.ssml.SSMLParser import create_ssml_v01_parser

        card = TTSSpeaker.from_file("data/speakers/Bob.spkv1.json")
        self.assertEqual(card.get_token("chat-tts").tokens[0].numel(), 768)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "voice.srt"
            source.write_text("1\n00:00:00,300 --> 00:00:01,300\n你 & 我\n", encoding="utf-8")
            xml = read_subtitle_file(str(source), card.name)
        pause, voice = create_ssml_v01_parser().parse(xml)
        self.assertEqual(pause.attrs.duration, 300)
        self.assertEqual((voice.text, voice.attrs.spk), ("你 & 我", "Bob"))

    def test_media_decodes_to_pcm_and_keeps_sample_rate_consistent(self):
        with tempfile.TemporaryDirectory() as folder:
            source, decoded = (Path(folder) / n for n in ("input.wav", "result.wav"))
            sf.write(source, np.sin(np.arange(1600) / 16), 16000)
            decode_media(source, decoded)
            rate, mono = read_mono(decoded)
            self.assertEqual((rate, mono.ndim), (44100, 1))
            self.assertAlmostEqual(len(mono) / rate, 0.1, places=3)
            self.assertGreater(mono.std(), 1000)
