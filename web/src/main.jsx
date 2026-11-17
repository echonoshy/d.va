import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Meter } from './graphics';
import { ScriptEditor, EXAMPLE } from './script-editor';
import { Mixer, Result } from './audio';
import './studio.css';

let nextId = 1;
const createSegment = ({ role, text }) => ({ id: nextId++, role, text });
const cleanSegments = (items) => items.map(({ role, text }) => ({ role, text: text.trim() }));

async function request(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('无法连接播客服务，请确认服务已启动后重试。');
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(typeof payload.error === 'string' ? payload.error : '请求失败，请稍后重试。');
  }
  return response;
}

function App() {
  const [segments, setSegments] = useState(() => EXAMPLE.map(createSegment));
  const [voices, setVoices] = useState([]);
  const [selected, setSelected] = useState({ A: '', B: '' });
  const [music, setMusic] = useState(null);
  const [canScript, setCanScript] = useState(false);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [voiceError, setVoiceError] = useState('');
  const [busy, setBusy] = useState('');
  const [scriptError, setScriptError] = useState('');
  const [renderError, setRenderError] = useState('');
  const [output, setOutput] = useState(null);
  const active = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setVoiceError('');
    (async () => {
      try {
        const config = await (await request('/api/voices', { signal: controller.signal })).json();
        const list = Array.isArray(config.voices)
          ? config.voices.filter((v) => v && typeof v.id === 'string' && typeof v.name === 'string')
          : [];
        setCanScript(config.scriptAvailable === true);
        setVoices(list);
        if (!list.length) throw new Error('本机暂无可用音色，请安装语音引擎后重试。');
        const chinese = list.filter((v) => /^(zh|cmn|yue)([-_]|$)/i.test(v.language || ''));
        const first = chinese[0] || list[0];
        const second = chinese[1] || list.find((v) => v.id !== first.id) || first;
        setSelected({ A: first.id, B: second.id });
      } catch (error) {
        if (!controller.signal.aborted) setVoiceError(error.message);
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

  async function generate(topic) {
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
      const data = await response.json();
      if (
        !Array.isArray(data.segments) ||
        !data.segments.length ||
        data.segments.length > 40 ||
        !data.segments.every(
          (s) => s && ['A', 'B'].includes(s.role) && typeof s.text === 'string' && s.text.trim(),
        )
      )
        throw new Error('未收到有效脚本，请换个话题重试。');
      setSegments(data.segments.map(createSegment));
      setRenderError('');
      return true;
    } catch (error) {
      if (!controller.signal.aborted) setScriptError(error.message);
      return false;
    } finally {
      if (active.current === controller) {
        active.current = null;
        setBusy('');
      }
    }
  }
  function updateDraft(setter, change) {
    setter(change);
    setRenderError('');
  }
  const script = cleanSegments(segments);
  const signature = JSON.stringify([script, selected]);
  async function render() {
    if (active.current) return;
    if (!script.length || script.some((s) => !s.text)) {
      setRenderError('请填写每一段台词，或移除空白段落。');
      return;
    }
    if (
      script.some((s) => Array.from(s.text).length > 1200) ||
      script.reduce((sum, s) => sum + Array.from(s.text).length, 0) > 8000
    ) {
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
      if (!controller.signal.aborted) setRenderError(error.message);
    } finally {
      if (active.current === controller) {
        active.current = null;
        setBusy('');
      }
    }
  }
  return (
    <>
      <header className="mast">
        <div className="mast-inner">
          <div className="brand">
            <Meter />
            <b>D.Va</b>
            <span>播客工作室</span>
          </div>
          <div className="engine">
            <Meter small />
            本地语音引擎
          </div>
        </div>
      </header>
      <main>
        <div className="intro">
          <h1>播客编辑台</h1>
          <p>编辑对话、分配音色，生成可播放的 MP3。</p>
        </div>
        <div className="studio">
          <div className="left">
            <ScriptEditor
              segments={segments}
              setSegments={(change) => updateDraft(setSegments, change)}
              createSegment={createSegment}
              scriptAvailable={canScript}
              busy={busy}
              generate={generate}
              scriptError={scriptError}
            />
            <Result
              output={output}
              changed={Boolean(output && (output.signature !== signature || output.music !== music))}
              busy={busy}
            />
          </div>
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
        </div>
      </main>
    </>
  );
}
createRoot(document.getElementById('root')).render(<App />);
