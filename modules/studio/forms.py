"""Typed widget descriptions and callback bindings consumed by the React studio."""

from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile

building = ContextVar("studio_form", default=None)
Error = ValueError


def components(items):
    return items if isinstance(items, (tuple, list)) else [] if items is None else [items]


@dataclass
class Binding:
    source: int
    trigger: str
    fn: object
    inputs: list
    outputs: list
    parent: int | None = None
    every: int | None = None

    def then(self, fn, inputs=None, outputs=None, **kwargs):
        form = building.get()
        return form.bind(self.source, "then", fn, inputs, outputs, form.events.index(self))


class Form:
    def __init__(self):
        self.nodes = []
        self.events = []
        self.stack = []

    def __enter__(self):
        self.token = building.set(self)
        return self

    def __exit__(self, *args):
        building.reset(self.token)

    def bind(self, source, trigger, fn, inputs, outputs, parent=None, every=None):
        event = Binding(source, trigger, fn, components(inputs), components(outputs), parent, every)
        self.events.append(event)
        return event

    def schema(self):
        return {
            "nodes": [{"id": n.id, "kind": n.kind, "parent": n.parent, "props": n.props} for n in self.nodes],
            "events": [
                {"id": i, "source": e.source, "trigger": e.trigger, "inputs": [n.id for n in e.inputs], "outputs": [n.id for n in e.outputs], "parent": e.parent, "every": e.every}
                for i, e in enumerate(self.events)
            ],
        }


class Widget:
    def __init__(self, *args, **props):
        self.kind = type(self).__name__
        names = {"Tab": ["label"], "TabItem": ["label"], "Slider": ["minimum", "maximum"], "Dropdown": ["choices"], "Radio": ["choices"], "CheckboxGroup": ["choices"]}.get(self.kind, ["value"])
        for name, value in zip(names, args):
            props.setdefault(name, value)
        if self.kind == "Examples":
            props["inputs"] = [n.id for n in components(props["inputs"])]
        if building.get() is not None:
            defaults = {"Textbox": "", "Text": "", "Checkbox": False, "DataFrame": [], "State": None, "Number": 0}
            if self.kind in defaults:
                props.setdefault("value", defaults[self.kind])
        self.props = props
        self.form = building.get()
        if self.form is not None:
            self.id = len(self.form.nodes)
            self.parent = self.form.stack[-1] if self.form.stack else None
            self.form.nodes.append(self)

    def __enter__(self):
        self.form.stack.append(self.id)
        return self

    def __exit__(self, *args):
        self.form.stack.pop()

    def click(self, fn, inputs=None, outputs=None, **kwargs):
        return self.form.bind(self.id, "click", fn, inputs, outputs)

    def submit(self, fn, inputs=None, outputs=None, **kwargs):
        return self.form.bind(self.id, "submit", fn, inputs, outputs)

    def change(self, fn, inputs=None, outputs=None, **kwargs):
        return self.form.bind(self.id, "change", fn, inputs, outputs)

    def load(self, fn, inputs=None, outputs=None, every=None, **kwargs):
        return self.form.bind(self.id, "load", fn, inputs, outputs, every=every)

    def move_resource_to_block_cache(self, filename):
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as f:
            with open(filename, "rb") as source:
                shutil.copyfileobj(source, f)
            return f.name


# Each declaration has a distinct wire type so React can select the native control.
for _kind in (
    "Blocks Row Column Group Tabs Tab TabItem Markdown Examples Text Textbox Number Slider Dropdown Radio Checkbox CheckboxGroup Button Audio Video File Label State DataFrame HTML Hub"
).split():
    globals()[_kind] = type(_kind, (Widget,), {})


def update(**props):
    return Widget(**props)
