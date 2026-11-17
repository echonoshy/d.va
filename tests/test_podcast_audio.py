import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import gradio as gr
import numpy as np
from gradio.data_classes import FileData
from pydub import AudioSegment
from pydub.generators import Sine

from modules.webui.llm_podcast_tab import create_llm_podcast_tab, podcast_pipeline


class PodcastAudioTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.speech = (16000, np.full(16000, 500, dtype=np.int16))

    def make_track(self, name, duration, frequency=440):
        path = self.root / name
        track = Sine(frequency, sample_rate=16000).to_audio_segment(duration=duration)
        with path.open("wb") as output:
            track.export(output, format=path.suffix[1:])
        return str(path)

    def test_short_tracks_and_short_speech(self):
        for bgm_ms, speech_ms in ((250, 1000), (5000, 1000), (6000, 100)):
            with self.subTest(bgm_ms=bgm_ms, speech_ms=speech_ms):
                bgm = self.make_track("bgm.mp3", bgm_ms)
                output = self.root / "mixed.mp3"
                speech = (16000, self.speech[1][: 16 * speech_ms])
                self.assertTrue(podcast_pipeline.audio_postprocess(speech, bgm, str(output)))
                intro_ms = min(5000, bgm_ms)
                expected_ms = intro_ms + speech_ms - min(500, intro_ms, speech_ms)
                self.assertAlmostEqual(len(AudioSegment.from_mp3(output)), expected_ms, delta=5)

    def test_webui_preserves_each_result_with_uploaded_or_default_bgm(self):
        uploaded = self.make_track("uploaded.wav", 5500)
        default = self.make_track("default.mp3", 5500, frequency=220)
        with gr.Blocks(analytics_enabled=False) as demo:
            create_llm_podcast_tab()
        click = next(event for event in demo.fns.values() if event.name == "generate_podcast")
        upload_input = click.inputs[2]
        output = click.outputs[1]
        output.GRADIO_CACHE = str(self.root / "cache")
        with (
            patch.object(podcast_pipeline, "default_bgm_path", default),
            patch.object(podcast_pipeline, "generate_ssml", return_value="<speak/>"),
            patch.object(podcast_pipeline, "synthesize_speech", return_value=self.speech),
        ):
            track = upload_input.preprocess(FileData(path=uploaded))
            text, first = click.fn("First", "deepseek-chat", track)
            self.assertEqual(text, "<speak/>")
            first_path = Path(output.postprocess(first).path)
            original = first_path.read_bytes()
            text, second = click.fn("Second", "deepseek-chat", None)
            self.assertEqual(text, "<speak/>")
            second_path = Path(output.postprocess(second).path)

        self.assertNotEqual(first_path, second_path)
        self.assertEqual(first_path.read_bytes(), original)
        self.assertNotEqual(second_path.read_bytes(), original)
        for result in (first_path, second_path):
            self.assertEqual(result.suffix, ".mp3")
            self.assertAlmostEqual(len(AudioSegment.from_mp3(result)), 5500, delta=5)


if __name__ == "__main__":
    unittest.main()
