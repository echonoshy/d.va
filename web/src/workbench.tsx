import { useEffect, useRef, useState } from "react";
import { Microphone } from "./microphone";
import Markdown from "react-markdown";
import { SpeakerHub, jsonRequest } from "./studio-hub";
import "./workbench.css";

export const sections = [
  "TTS",
  "SSML",
  "音色管理",
  "声音克隆",
  "训练",
  "话题转 SSML 播客",
  "音频工具",
  "系统",
  "使用说明",
];
type Props = {
  value?: unknown;
  label?: string;
  id?: string;
  choices?: unknown[];
  headers?: string[];
  datatype?: string[];
  minimum?: number;
  maximum?: number;
  step?: number;
  lines?: number;
  placeholder?: string;
  selected?: string;
  visible?: boolean;
  interactive?: boolean;
  file_types?: string[];
  inputs?: number[];
  examples?: unknown[][];
  variant?: string;
};
type Item = { id: number; kind: string; parent: number | null; props: Props };
type Event = {
  id: number;
  source: number;
  trigger: string;
  inputs: number[];
  outputs: number[];
  parent: number | null;
  every?: number;
};
type Schema = {
  nodes: Item[];
  events: Event[];
  session: string;
  labels: Record<string, string | string[]>;
};
type FileValue = { file: string; name: string; url: string };
type Changes = Record<number, Props>;
const fileValue = (v: unknown): v is FileValue =>
  !!v && typeof v === "object" && "file" in v && "url" in v;

export function Workbench({
  section,
  onSection,
}: {
  section: string;
  onSection: (s: string) => void;
}) {
  const [schema, setSchema] = useState<Schema>(),
    [attempt, retry] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const [fields, setFields] = useState<Changes>({});
  const live = useRef<Changes>({}),
    chain = useRef(Promise.resolve()),
    pending = useRef(0);
  function patch(changes: Changes) {
    const next = { ...live.current };
    for (const [key, props] of Object.entries(changes))
      next[+key] = { ...next[+key], ...props };
    live.current = next;
    setFields(next);
  }
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    jsonRequest<Schema>("/api/studio/schema", { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        live.current = Object.fromEntries(
          data.nodes.map((n) => [n.id, n.props]),
        );
        setFields(live.current);
        setSchema(data);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(String(e));
      });
    return () => controller.abort();
  }, [attempt]);
  function label(text: unknown) {
    const key = String(text ?? "");
    const found = schema?.labels[key];
    return Array.isArray(found) ? found.join("\n") : found || key;
  }
  const children = (id: number | null) =>
    schema?.nodes.filter((n) => n.parent === id) || [];
  const rootTabs = schema?.nodes.find((n) => n.kind === "Tabs");
  const tabs = rootTabs ? children(rootTabs.id) : [];
  const active = tabs.find((n) => n.props.label === section);
  const onSectionRef = useRef(onSection);
  onSectionRef.current = onSection;
  async function action(e: Event, config: Schema) {
    const values = e.inputs.map((id) => live.current[id]?.value ?? null);
    const out = await jsonRequest<Changes>(
      "/api/studio/run/" + config.session + "/" + e.id,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ values }),
      },
    );
    patch(out);
    if (rootTabs && out[rootTabs.id]?.selected) {
      const target = tabs.find((t) => t.props.id === out[rootTabs.id].selected);
      if (target?.props.label) onSectionRef.current(target.props.label);
    }
    for (const follow of config.events.filter((f) => f.parent === e.id))
      await action(follow, config);
  }
  function queue(fn: () => Promise<void>) {
    pending.current++;
    setBusy(true);
    setError("");
    chain.current = chain.current
      .then(fn)
      .catch((e) => setError(String(e)))
      .finally(() => {
        pending.current--;
        if (!pending.current) setBusy(false);
      });
  }
  function trigger(id: number, type: string) {
    if (!schema) return;
    const events = schema.events.filter(
      (e) => e.source === id && e.trigger === type,
    );
    if (events.length)
      queue(async () => {
        for (const e of events) await action(e, schema);
      });
  }
  function change(id: number, value: unknown) {
    patch({ [id]: { value } });
    trigger(id, "change");
  }
  useEffect(() => {
    if (!schema || !["训练", "系统"].includes(section)) return;
    const events = schema.events.filter(
      (e) =>
        e.trigger === "load" && (section === "训练" ? !!e.every : !e.every),
    );
    let alive = true,
      running = false;
    async function refresh() {
      if (!schema || running || pending.current) return;
      running = true;
      try {
        for (const e of events) {
          const out = await jsonRequest<Changes>(
            "/api/studio/run/" + schema.session + "/" + e.id,
            {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: '{"values":[]}',
            },
          );
          if (alive) patch(out);
        }
      } catch (e) {
        if (alive) setError(String(e));
      } finally {
        running = false;
      }
    }
    void refresh();
    const timer = section === "训练" ? setInterval(refresh, 2000) : undefined;
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [schema, section]);
  function tree(n: Item): React.ReactNode {
    const p = fields[n.id] || n.props;
    if (p.visible === false) return null;
    const key = n.id,
      k = n.kind,
      value = p.value,
      title = label(p.label),
      disabled = busy || p.interactive === false;
    const kids = children(key),
      nested = () => kids.map(tree);
    if (k === "Tabs") {
      const items = kids.filter((c) => c.props.visible !== false);
      const target =
        items.find((c) => (c.props.id || String(c.id)) === p.selected) ||
        items[0];
      return (
        <div className="wf-tabs" key={key}>
          <nav aria-label="工具分类">
            {items.map((c) => (
              <button
                key={c.id}
                aria-pressed={c.id === target?.id}
                onClick={() =>
                  patch({ [key]: { selected: c.props.id || String(c.id) } })
                }
              >
                {label(c.props.label)}
              </button>
            ))}
          </nav>
          {target && tree(target)}
        </div>
      );
    }
    if (
      k === "Tab" ||
      k === "TabItem" ||
      k === "Blocks" ||
      k === "Column" ||
      k === "Row" ||
      k === "Group"
    )
      return (
        <div key={key} className={"wf-" + k.toLowerCase()}>
          {nested()}
        </div>
      );
    if (k === "Markdown")
      return (
        <div key={key} className="wf-text">
          <Markdown skipHtml>{label(value)}</Markdown>
        </div>
      );
    if (k === "Label") return <output key={key}>{label(value)}</output>;
    if (k === "State") return null;
    if (k === "Hub")
      return (
        <SpeakerHub
          key={key}
          session={schema!.session}
          initial={String(value || "")}
        />
      );
    if (k === "Button")
      return (
        <button
          key={key}
          className={p.variant === "primary" ? "wf-primary" : ""}
          disabled={disabled}
          onClick={() => trigger(key, "click")}
        >
          {label(value)}
        </button>
      );
    if (k === "Examples")
      return (
        <div key={key}>
          {p.examples?.map((row, i) => (
            <button
              key={i}
              onClick={() =>
                p.inputs?.forEach((id, j) =>
                  change(id, Array.isArray(row) ? row[j] : row),
                )
              }
            >
              示例 {i + 1}
            </button>
          ))}
        </div>
      );
    if (k === "DataFrame") {
      const rows = (Array.isArray(value) ? value : []) as unknown[][];
      return (
        <div className="wf-sheet" key={key}>
          <table>
            <thead>
              <tr>
                {p.headers?.map((h) => (
                  <th key={h}>{label(h)}</th>
                ))}
                {!disabled && <th>操作</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {p.headers?.map((h, j) => (
                    <td key={j}>
                      <input
                        aria-label={h + " " + (i + 1)}
                        disabled={disabled}
                        value={String(row[j] ?? "")}
                        onChange={(e) =>
                          change(
                            key,
                            rows.map((r, idx) =>
                              idx === i
                                ? r.map((x, col) =>
                                    col === j ? e.target.value : x,
                                  )
                                : r,
                            ),
                          )
                        }
                      />
                    </td>
                  ))}
                  {!disabled && (
                    <td>
                      <button
                        aria-label={"删除第" + (i + 1) + "行"}
                        onClick={() =>
                          change(
                            key,
                            rows.filter((_, j) => j !== i),
                          )
                        }
                      >
                        删除
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {!disabled && (
            <button
              onClick={() =>
                change(key, [
                  ...rows,
                  (p.headers || []).map((_, i) =>
                    i === 0 ? rows.length + 1 : "",
                  ),
                ])
              }
            >
              插入空行
            </button>
          )}
        </div>
      );
    }
    let control: React.ReactNode;
    if (["File", "Audio", "Video"].includes(k)) {
      const input = schema!.events.some((e) => e.inputs.includes(key));
      function upload(file: File) {
        queue(async () => {
          const ref = await jsonRequest<FileValue>(
            "/api/studio/upload/" +
              schema!.session +
              "?name=" +
              encodeURIComponent(file.name),
            { method: "POST", body: file },
          );
          change(key, ref);
        });
      }
      return (
        <div key={key} className="wf-media">
          <span>{title}</span>
          {input && (
            <input
              aria-label={title}
              type="file"
              disabled={disabled}
              accept={
                k === "Audio"
                  ? "audio/*,.webm"
                  : k === "Video"
                    ? "video/*"
                    : p.file_types?.filter(Boolean).join(",")
              }
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) upload(file);
                e.target.value = "";
              }}
            />
          )}
          {input && k === "Audio" && (
            <Microphone disabled={disabled} onFile={upload} />
          )}
          {fileValue(value) && (
            <>
              {k === "Audio" && <audio controls src={value.url} />}{" "}
              {k === "Video" && (
                <video controls preload="metadata" src={value.url} />
              )}
              <a download={value.name} href={value.url}>
                {value.name}
              </a>
              {input && <button onClick={() => change(key, null)}>移除</button>}
              {k === "File" && !input && value.name.endsWith(".json") && (
                <button
                  disabled={busy}
                  onClick={() =>
                    queue(async () => {
                      const card = await jsonRequest(value.url);
                      const saved = await jsonRequest<{ name: string }>(
                        "/api/studio/speakers/" + schema!.session,
                        {
                          method: "POST",
                          headers: { "content-type": "application/json" },
                          body: JSON.stringify(card),
                        },
                      );
                      setNotice("已保存到音色库：" + saved.name);
                    })
                  }
                >
                  保存到音色库
                </button>
              )}
            </>
          )}
        </div>
      );
    }
    if (k === "Dropdown" || k === "Radio") {
      control = (
        <select
          disabled={disabled}
          value={String(value ?? "")}
          onChange={(e) => change(key, e.target.value)}
        >
          <option value="">选择…</option>
          {p.choices?.map((c, i) => {
            const [name, v] = Array.isArray(c) ? c : [c, c];
            return (
              <option key={i} value={String(v)}>
                {label(name)}
              </option>
            );
          })}
        </select>
      );
    } else if (k === "Checkbox")
      control = (
        <input
          type="checkbox"
          checked={Boolean(value)}
          disabled={disabled}
          onChange={(e) => change(key, e.target.checked)}
        />
      );
    else if (k === "Slider" || k === "Number")
      control = (
        <input
          type="number"
          step={p.step || "any"}
          min={p.minimum}
          max={p.maximum}
          disabled={disabled}
          value={typeof value === "number" ? value : ""}
          onChange={(e) =>
            change(key, e.target.value === "" ? null : Number(e.target.value))
          }
        />
      );
    else if ((p.lines || 1) > 1)
      control = (
        <textarea
          rows={Math.min(p.lines || 3, 15)}
          disabled={disabled}
          value={String(value ?? "")}
          placeholder={label(p.placeholder)}
          onChange={(e) => change(key, e.target.value)}
        />
      );
    else
      control = (
        <input
          disabled={disabled}
          value={String(value ?? "")}
          placeholder={label(p.placeholder)}
          onChange={(e) => change(key, e.target.value)}
        />
      );
    return (
      <label
        key={key}
        onKeyDown={(e) => {
          if (
            e.key === "Enter" &&
            !e.nativeEvent.isComposing &&
            !e.shiftKey &&
            schema?.events.some(
              (ev) => ev.trigger === "submit" && ev.source === key,
            )
          ) {
            e.preventDefault();
            trigger(key, "submit");
          }
        }}
        className={"wf-field wf-" + k.toLowerCase()}
      >
        {title}
        {control}
      </label>
    );
  }
  const [notice, setNotice] = useState("");
  return (
    <main className="workbench">
      <div className="intro">
        <h1>{section}</h1>
      </div>
      {error && (
        <div role="alert" className="notice error">
          {error}{" "}
          {!schema && <button onClick={() => retry((n) => n + 1)}>重试</button>}
        </div>
      )}
      {!schema && !error && <p role="status">正在启动本机语音工作台…</p>}
      {busy && <p role="status">正在处理…</p>}
      {notice && <p role="status">{notice}</p>}
      {active && tree(active)}
    </main>
  );
}
