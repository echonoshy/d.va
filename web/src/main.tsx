import { useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { createRoot } from 'react-dom/client';
import { PodcastIntro, StudioHeader } from './studio-shell';
import { ScriptEditor, EXAMPLE } from './script-editor';
import { Mixer, Result } from './audio';
import { isRecord, isSegment, isVoice } from './studio-types';
import type { Busy, DraftSegment, Output, Segment, Voice, VoiceSelection } from './studio-types';
import './studio.css';
import { Workbench } from './workbench';

const scriptCapacity = 8000;
let nextId = 1;
const createSegment = ({ role, text }: Segment): DraftSegment => ({ id: nextId++, role, text });
const cleanSegments = (items: DraftSegment[]): Segment[] =>
  items.map(({ role, text }) => ({ role, text: text.trim() }));

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : '请求失败，请稍后重试。';
}

async function request(url: string, options: RequestInit) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new Error('无法连接播客服务，请确认服务已启动后重试。');
  }
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw new Error(
      isRecord(payload) && typeof payload.error === 'string' ? payload.error : '请求失败，请稍后重试。',
    );
  }
  return response;
}

function App() {
  const [section, setSection] = useState('播客编辑台');
  const [opened, setOpened] = useState(false);
  function selectSection(value: string) {
    setSection(value);
    if (value !== '播客编辑台') setOpened(true);
  }

  const [segments, setSegments] = useState(() => EXAMPLE.map(createSegment));
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selected, setSelected] = useState<VoiceSelection>({ A: '', B: '' });
  const [music, setMusic] = useState<File | null>(null);
  const [canScript, setCanScript] = useState(false);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [voiceError, setVoiceError] = useState('');
  const [busy, setBusy] = useState<Busy>('');
  const [scriptError, setScriptError] = useState('');
  const [renderError, setRenderError] = useState('');
  const [output, setOutput] = useState<Output | null>(null);
  const active = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    request('/api/capabilities', { signal: controller.signal })
      .then((r) => r.json())
      .then((data) => {
        if (!controller.signal.aborted) setCanScript(data.scriptAvailable === true);
      })
      .catch(() => {});
    setLoading(true);
    setVoiceError('');
    (async () => {
      try {
        const config: unknown = await (await request('/api/voices', { signal: controller.signal })).json();
        if (!isRecord(config) || !Array.isArray(config.voices)) {
          throw new Error('语音服务返回了无效的音色列表，请重试。');
        }
        const list = config.voices.filter(isVoice);
        setCanScript(config.scriptAvailable === true);
        setVoices(list);
        if (!list.length) throw new Error('本机暂无可用音色，请安装语音引擎后重试。');
        const chinese = list.filter((v) => /^(zh|cmn|yue)([-_]|$)/i.test(v.language || ''));
        const first = chinese[0] || list[0];
        const second = chinese[1] || list.find((v) => v.id !== first.id) || first;
        setSelected({ A: first.id, B: second.id });
      } catch (error) {
        if (!controller.signal.aborted) setVoiceError(errorMessage(error));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => () => active.current?.abort(), []);
  useEffect(
    () => () => {
      if (output) URL.revokeObjectURL(output.url);
    },
    [output],
  );

  async function generate(topic: string) {
    if (active.current) return false;
    const controller = new AbortController();
    active.current = controller;
    setBusy('script');
    setScriptError('');
    try {
      const response = await request('/api/script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic }),
        signal: controller.signal,
      });
      const data: unknown = await response.json();
      if (
        !isRecord(data) ||
        !Array.isArray(data.segments) ||
        !data.segments.length ||
        data.segments.length > 40 ||
        !data.segments.every(isSegment)
      )
        throw new Error('未收到有效脚本，请换个话题重试。');
      setSegments(data.segments.map(createSegment));
      setRenderError('');
      return true;
    } catch (error) {
      if (!controller.signal.aborted) setScriptError(errorMessage(error));
      return false;
    } finally {
      if (active.current === controller) {
        active.current = null;
        setBusy('');
      }
    }
  }
  function updateDraft<T>(setter: Dispatch<SetStateAction<T>>, change: SetStateAction<T>) {
    setter(change);
    setRenderError('');
  }
  const script = cleanSegments(segments);
  const characters = script.reduce((sum, line) => sum + Array.from(line.text).length, 0);
  const signature = JSON.stringify([script, selected]);
  async function render() {
    if (active.current) return;
    if (!script.length || script.some((s) => !s.text)) {
      setRenderError('请填写每一段台词，或移除空白段落。');
      return;
    }
    if (script.some((s) => Array.from(s.text).length > 1200) || characters > scriptCapacity) {
      setRenderError('每段最多 1200 字，全部台词最多 8000 字。');
      return;
    }
    const controller = new AbortController();
    active.current = controller;
    setRenderError('');
    setBusy('render');
    try {
      const form = new FormData();
      form.set('script', JSON.stringify(script));
      form.set('voices', JSON.stringify(selected));
      if (music) form.set('music', music);
      const response = await request('/api/render', {
        method: 'POST',
        body: form,
        signal: controller.signal,
      });
      const audio = await response.blob();
      if (!audio.size || !/^audio\/(mpeg|mp3)\b/i.test(audio.type))
        throw new Error('服务未返回 MP3，请重试。');
      setOutput({ url: URL.createObjectURL(audio), signature, music });
    } catch (error) {
      if (!controller.signal.aborted) setRenderError(errorMessage(error));
    } finally {
      if (active.current === controller) {
        active.current = null;
        setBusy('');
      }
    }
  }
  return (
    <div className="app-frame">
      <StudioHeader
        select={selectSection}
        section={section}
        available={!loading && !voiceError}
        engine={
          loading
            ? '正在载入语音引擎'
            : voiceError
              ? '语音引擎不可用'
              : voices.some((v) => v.engine === 'api')
                ? '外部语音服务'
                : '本地语音引擎'
        }
      />
      <div className="workspace">
        <main className="podcast-page" hidden={section !== '播客编辑台'}>
          <PodcastIntro
            speakers={new Set(segments.map((s) => s.role)).size}
            characters={characters}
            segments={segments.length}
            capacity={scriptCapacity}
            select={selectSection}
          />
          <div className="studio">
            <ScriptEditor
              segments={segments}
              setSegments={(change) => updateDraft(setSegments, change)}
              createSegment={createSegment}
              scriptAvailable={canScript}
              busy={busy}
              generate={generate}
              scriptError={scriptError}
            />
            <div className="sound-column">
              <Mixer
                voices={voices}
                selected={selected}
                setSelected={(change) => updateDraft(setSelected, change)}
                file={music}
                setFile={(file) => updateDraft(setMusic, file)}
                busy={busy}
                loading={loading}
                voiceError={voiceError}
                retry={() => setAttempt((n) => n + 1)}
                render={render}
                error={renderError}
              />
              <Result
                output={output}
                changed={Boolean(output && (output.signature !== signature || output.music !== music))}
                busy={busy}
              />
            </div>
          </div>
        </main>
        {opened && (
          <div hidden={section === '播客编辑台'}>
            <Workbench section={section} onSection={selectSection} />
          </div>
        )}
      </div>
    </div>
  );
}
const root = document.getElementById('root');
if (!root) throw new Error('找不到播客编辑台的页面容器。');
createRoot(root).render(<App />);
