import { useState, useEffect } from "react";

type Card = {
  id: string;
  name: string;
  url: string;
  filename?: string;
  gender?: string;
  author?: string;
  desc?: string;
  tags?: string[];
  created_date?: number;
  version?: string;
};
export async function jsonRequest<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok)
    throw new Error(String(data.error || data.detail || res.statusText));
  return data as T;
}
function publicLink(value: string, base?: string) {
  const url = new URL(value, base);
  if (
    url.protocol !== "https:" &&
    !(
      url.protocol === "http:" &&
      ["127.0.0.1", "localhost"].includes(url.hostname)
    )
  )
    throw new Error("请输入 HTTPS 音色目录地址");
  return url.href;
}
export function SpeakerHub({
  session,
  initial,
}: {
  session: string;
  initial: string;
}) {
  const [url, setUrl] = useState(initial),
    [base, setBase] = useState(""),
    [query, setQuery] = useState("");
  const [files, setFiles] = useState<Card[]>([]),
    [tag, setTag] = useState<string[]>([]),
    [sort, setSort] = useState("newest");
  const [installed, setInstalled] = useState<Record<string, string>>({});
  useEffect(() => {
    const abort = new AbortController();
    jsonRequest<Record<string, string>>("/api/studio/speakers/" + session, {
      signal: abort.signal,
    })
      .then(setInstalled)
      .catch((e) => {
        if (!abort.signal.aborted) setMessage(String(e));
      });
    return () => abort.abort();
  }, [session]);
  const [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  async function job(fn: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try {
      await fn();
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function install(card: unknown) {
    const result = await jsonRequest<{
      name: string;
      id: string;
      version: string;
    }>("/api/studio/speakers/" + session, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(card),
    });
    setInstalled((old) => ({ ...old, [result.id]: result.version }));
    setMessage("已安装 " + result.name + "。请在音色选择处刷新。");
  }
  const visible = files
    .filter(
      (f) =>
        f.name.toLowerCase().includes(query.toLowerCase()) &&
        ![...(f.tags || []), f.gender || ""].some((t) => tag.includes(t)),
    )
    .sort((a, b) =>
      sort === "az"
        ? a.name.localeCompare(b.name)
        : sort === "za"
          ? b.name.localeCompare(a.name)
          : (sort === "newest" ? -1 : 1) *
            ((a.created_date || 0) - (b.created_date || 0)),
    );
  return (
    <section className="wf-group">
      <h3>音色目录</h3>
      <label>
        目录索引 URL
        <input value={url} onChange={(e) => setUrl(e.target.value)} />
      </label>
      <button
        disabled={busy || !url}
        onClick={() =>
          void job(async () => {
            const address = publicLink(url);
            const index = await jsonRequest<{ files: Card[] }>(address);
            if (!Array.isArray(index.files)) throw new Error("无效的音色目录");
            setFiles(
              index.files
                .filter(
                  (f) =>
                    typeof f?.name === "string" &&
                    (typeof f.url === "string" ||
                      typeof f.filename === "string"),
                )
                .map((f) => ({
                  ...f,
                  url: publicLink(f.url || f.filename!, address),
                  tags: Array.isArray(f.tags)
                    ? f.tags.filter((t) => typeof t === "string")
                    : [],
                })),
            );
            setBase(address);
            setMessage("目录已加载");
          })
        }
      >
        加载目录
      </button>
      <label>
        导入本地音色卡
        <input
          type="file"
          accept=".json"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void job(async () => install(JSON.parse(await f.text())));
          }}
        />
      </label>
      <label>
        搜索音色
        <input value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      <label>
        排序
        <select value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="newest">最新</option>
          <option value="oldest">最早</option>
          <option value="az">A–Z</option>
          <option value="za">Z–A</option>
        </select>
      </label>
      {Array.from(
        new Set(
          files
            .flatMap((f) => [...(f.tags || []), f.gender || ""])
            .filter(Boolean),
        ),
      ).map((t) => (
        <label key={t}>
          <input
            type="checkbox"
            checked={tag.includes(t)}
            onChange={(e) =>
              setTag(
                e.target.checked ? [...tag, t] : tag.filter((x) => x !== t),
              )
            }
          />{" "}
          隐藏 {t}
        </label>
      ))}
      {visible.length > 0 && (
        <div className="wf-sheet">
          <table>
            <thead>
              <tr>
                {[
                  "ID",
                  "音色",
                  "描述",
                  "性别",
                  "作者",
                  "版本",
                  "标签",
                  "创建日期",
                  "卡片文件",
                  "操作",
                ].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((f) => (
                <tr key={f.id || f.url}>
                  <td>{f.id?.slice(0, 5)}</td>
                  <td>{f.name}</td>
                  <td>{f.desc}</td>
                  <td>{f.gender}</td>
                  <td>{f.author}</td>
                  <td>{f.version}</td>
                  <td>{f.tags?.join("、")}</td>
                  <td>
                    {f.created_date
                      ? new Date(f.created_date).toLocaleDateString()
                      : ""}
                  </td>
                  <td>
                    <a href={f.url} target="_blank" rel="noreferrer">
                      {f.filename || "查看卡片"}
                    </a>
                  </td>
                  <td>
                    <button
                      disabled={busy}
                      onClick={() =>
                        void job(async () =>
                          install(await jsonRequest(publicLink(f.url, base))),
                        )
                      }
                    >
                      {!(f.id in installed)
                        ? "安装"
                        : installed[f.id] === (f.version || "")
                          ? "重新安装"
                          : "更新版本"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p role="status">{message}</p>
    </section>
  );
}
