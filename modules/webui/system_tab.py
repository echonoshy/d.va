from modules.studio import forms as ui

from modules.webui import webui_config
from modules.core.models.zoo import model_zoo
from modules.devices import devices
import os

is_huggingface_space = os.environ.get("IS_HF_SPACE", None) is not None


def get_system_status():
    cpu_mem = devices.get_cpu_memory()
    gpu_mem = devices.get_gpu_memory() if devices.torch.cuda.is_available() else None

    status = (
        f"**CPU Memory**:\n"
        f"- Total: {cpu_mem.total_mb:.2f} MB\n"
        f"- Used: {cpu_mem.used_mb:.2f} MB\n"
        f"- Free: {cpu_mem.free_mb:.2f} MB\n\n"
    )
    if gpu_mem:
        status += f"GPU memory: {gpu_mem.used_mb:.0f} / {gpu_mem.total_mb:.0f} MB"
    else:
        status += f"Inference device: {devices.device}"
    return status


# NOTE: 这样写会抢占输出队列...
# def update_markdown():
#     while True:
#         yield get_system_status()
#         time.sleep(5)


def create_system_tab(demo: ui.Blocks):
    with ui.Row():
        with ui.Column(scale=1):
            ui.Markdown("info")

            with ui.Group():
                ui.Markdown("🏗 System Monitor")
                status_box = ui.Markdown(value="")

                # 每秒更新一次状态
                demo.load(fn=get_system_status, inputs=[], outputs=status_box)

        with ui.Column(scale=5):
            with ui.Group():
                ui.Markdown("🚩 Features")
                ui.Checkbox(
                    label="Enable Experimental Features",
                    value=webui_config.experimental,
                    interactive=False,
                )

            with ui.Group():
                ui.Markdown("🦁Model zoo")
                with ui.Row():
                    with ui.Column():
                        unload_models_btn = ui.Button(
                            "Unload All Models",
                            interactive=is_huggingface_space is False,
                        )
                    with ui.Column():
                        reload_models_btn = ui.Button(
                            "Reload All Models",
                            interactive=is_huggingface_space is False,
                        )

                def reload_models():
                    model_zoo.reload_all_models()

                def unload_models():
                    model_zoo.unload_all_models()

                unload_models_btn.click(fn=unload_models, inputs=None, outputs=None)
                reload_models_btn.click(fn=reload_models, inputs=None, outputs=None)
