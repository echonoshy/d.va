import atexit
import subprocess
from collections import deque
from threading import Lock, Thread


class ProcessMonitor:
    def __init__(self):
        self.process = None
        self.lines = deque(maxlen=300)
        self.lock = Lock()
        atexit.register(self.stop_process)

    def start_process(self, command):
        with self.lock:
            if self.process and self.process.poll() is None:
                raise ValueError("A training job is already running")
            self.lines.clear()
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
            started = self.process
            pipe = started.stdout

        def collect():
            with pipe:
                for line in pipe:
                    with self.lock:
                        if self.process is started:
                            self.lines.append(line[-2000:])

        Thread(target=collect, daemon=True).start()

    def get_output(self):
        with self.lock:
            return "".join(self.lines), ""

    def clear(self):
        with self.lock:
            self.lines.clear()

    def stop_process(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
