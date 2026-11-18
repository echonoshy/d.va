import sys

from modules.studio import forms as ui

from modules.core.models import zoo
from modules.core.spk import spk_mgr
from modules.webui import webui_config
from modules.webui.webui_utils import get_speaker_names

from .ft_ui_utils import get_datasets_listfile
from .ProcessMonitor import ProcessMonitor


class SpeakerFt:
    def __init__(self):
        self.process_monitor = ProcessMonitor()
        self.status_str = "idle"

    def unload_main_thread_models(self):
        zoo.model_zoo.unload_all_models()

    def run(
        self,
        batch_size: int,
        epochs: int,
        lr: str,
        train_text: bool,
        data_path: str,
        select_speaker: str = "",
    ):
        if self.process_monitor.process and self.process_monitor.process.poll() is None:
            raise ValueError("训练任务正在运行")
        if data_path not in get_datasets_listfile():
            raise ValueError("请先在 datasets/data_*/ 中放置 .list 数据集并刷新")
        if not 0 < float(lr) <= 1:
            raise ValueError("学习率应介于 0 和 1 之间")
        self.unload_main_thread_models()
        spk_path = None
        if select_speaker != "" and select_speaker != "none":
            select_speaker = select_speaker.split(" : ")[-1].strip()
            spk = spk_mgr.get_speaker(select_speaker)
            if spk is None:
                raise ValueError("Speaker not found")
            spk_filename = spk_mgr.get_item_path(lambda x: x.id == spk.id)
            spk_path = f"./data/speakers/{spk_filename}"

        command = [sys.executable, "-u", "-m", "modules.finetune.train_speaker"]
        command += [
            f"--batch_size={batch_size}",
            f"--epochs={epochs}",
            f"--data_path={data_path}",
            f"--lr={float(lr)}",
            "--save_folder=./data/speakers",
        ]
        if train_text:
            command.append("--train_text")
        if spk_path:
            command.append(f"--init_speaker={spk_path}")

        self.status("Training process starting")

        self.process_monitor.start_process(command)

        self.status("Training started")

    def status(self, text: str):
        self.status_str = text

    def flush(self):
        stdout, stderr = self.process_monitor.get_output()
        process = self.process_monitor.process
        if process is not None and process.poll() is not None and self.status_str == "Training started":
            self.status("训练完成" if process.returncode == 0 else f"训练失败，退出码 {process.returncode}")
            if process.returncode == 0:
                spk_mgr.refresh()
        return f"{self.status_str}\n{stdout}\n{stderr}"

    def clear(self):
        self.process_monitor.clear()
        if self.process_monitor.process is None or self.process_monitor.process.poll() is not None:
            self.status("Logs cleared")

    def stop(self):
        self.process_monitor.stop_process()
        self.status("Training stopped")


def create_speaker_ft_tab(demo: ui.Blocks):
    spk_ft = SpeakerFt()
    speakers, speaker_names = get_speaker_names()
    speaker_names = ["none"] + speaker_names

    ui.Markdown("将录音和 UTF-8 的 `.list` 清单放进 `datasets/data_名称/`，点击「刷新数据集」。每行填写 `相对音频路径|说话人|语言|逐字稿`。训练完成后，音色卡会保存到 `data/speakers/`，可在 TTS 的音色选择框旁刷新。")
    with ui.Row():
        with ui.Column(scale=2):
            with ui.Group():
                ui.Markdown("🎛️hparams")
                dataset_input = ui.Dropdown(label="Dataset", choices=get_datasets_listfile())
                lr_input = ui.Textbox(label="Learning Rate", value="1e-2")
                epochs_input = ui.Slider(label="Epochs", value=10, minimum=1, maximum=100, step=1)
                batch_size_input = ui.Slider(label="Batch Size", value=4, minimum=1, maximum=64, step=1)
                train_text_checkbox = ui.Checkbox(label="Train text_loss", value=True)
                init_spk_dropdown = ui.Dropdown(
                    label="Initial Speaker",
                    choices=speaker_names,
                    value="none",
                )

            with ui.Group():
                start_train_btn = ui.Button("Start Training")
                stop_train_btn = ui.Button("Stop Training")
                clear_train_btn = ui.Button("Clear logs")
        with ui.Column(scale=5):
            with ui.Group():
                # log
                ui.Markdown("📜logs")
                log_output = ui.Textbox(show_label=False, label="Log", value="", lines=20, interactive=True)

    start_train_btn.click(
        spk_ft.run,
        inputs=[
            batch_size_input,
            epochs_input,
            lr_input,
            train_text_checkbox,
            dataset_input,
            init_spk_dropdown,
        ],
        outputs=[],
    )
    stop_train_btn.click(spk_ft.stop)
    clear_train_btn.click(spk_ft.clear)

    refresh = ui.Button("刷新数据集")
    refresh.click(lambda: ui.Dropdown(choices=get_datasets_listfile()), outputs=dataset_input)
    demo.load(spk_ft.flush, every=2, outputs=[log_output])
