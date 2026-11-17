import React, { useRef, useState } from 'react';
import { Icon, Meter, Wave } from './graphics';
import { ROLES, Select } from './script-editor';

function Upload({ file, setFile, disabled }) {
  const input = useRef(null);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  function choose(value) {
    if (disabled || !value) return;
    if (value.size > 20 * 1024 * 1024 || value.size === 0) {
      setError(value.size === 0 ? '所选文件为空，请更换音频文件。' : '背景音乐超过 20 MB，请更换文件。');
      return;
    }
    setError('');
    setFile(value);
  }
  return (
    <div className="music-group">
      <h3>背景音乐</h3>
      <input
        ref={input}
        className="sr-only"
        type="file"
        tabIndex="-1"
        aria-label="背景音乐文件"
        accept="audio/*,.mp3,.wav,.m4a,.ogg,.flac"
        disabled={disabled}
        onChange={(e) => {
          choose(e.target.files[0]);
          e.target.value = '';
        }}
      />
      <button
        type="button"
        className={'upload' + (dragging ? ' drag-active' : '')}
        disabled={disabled}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          choose(e.dataTransfer.files[0]);
        }}
      >
        <Icon name="upload" size={29} />
        <strong>{file ? file.name : '上传音频（可选）'}</strong>
        <small>{file ? '点击更换背景音乐' : 'MP3、WAV 等格式，最多 20 MB'}</small>
      </button>
      {file && (
        <button
          type="button"
          className="text-button remove-file"
          disabled={disabled}
          onClick={() => {
            setFile(null);
            setError('');
          }}
        >
          移除背景音乐
        </button>
      )}
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function Mixer({
  voices,
  selected,
  setSelected,
  file,
  setFile,
  busy,
  loading,
  voiceError,
  retry,
  render,
  error,
}) {
  const disabled = Boolean(busy);
  const available = voices.length > 0;
  return (
    <aside className="paper mixer" aria-labelledby="mix-title">
      <div className="section-head">
        <h2 id="mix-title">
          <Icon name="tune" size={23} />
          声音设置
        </h2>
      </div>
      <div className="voice-group">
        {Object.entries(ROLES).map(([role, name]) => (
          <div className="voice" key={role}>
            <label htmlFor={'voice-' + role}>{name}</label>
            <div className="voice-control">
              <span aria-hidden="true" className={'role-key role-' + role}>
                {role}
              </span>
              <Select
                id={'voice-' + role}
                value={selected[role]}
                disabled={disabled || loading || !available}
                onChange={(e) => setSelected((prev) => ({ ...prev, [role]: e.target.value }))}
              >
                {!available && <option value="">{loading ? '正在载入音色…' : '暂无可用音色'}</option>}
                {voices.map((voice) => (
                  <option key={voice.id} value={voice.id}>
                    {voice.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        ))}
        {voiceError && (
          <div className="notice error" role="alert">
            {voiceError}{' '}
            <button type="button" className="text-button" disabled={loading} onClick={retry}>
              重试
            </button>
          </div>
        )}
      </div>
      <Upload file={file} setFile={setFile} disabled={disabled} />
      <div className="render-action">
        {error && (
          <p className="notice error" role="alert">
            {error}
          </p>
        )}
        <button
          type="button"
          className="render-button"
          disabled={disabled || loading || !available}
          onClick={render}
        >
          <Meter small />
          {busy === 'render' ? '正在合成音频…' : '生成 MP3'}
        </button>
      </div>
    </aside>
  );
}

export function Result({ output, changed, busy }) {
  return (
    <section
      className={'result' + (output ? ' has-output' : '')}
      aria-labelledby="result-title"
      aria-live="polite"
    >
      <div className="result-head">
        <h2 id="result-title">
          <Icon name="headphones" size={21} />
          成品试听
        </h2>
        <Wave />
        <span>
          {busy === 'render'
            ? '正在合成，请稍候…'
            : output
              ? changed
                ? '内容已更改，当前为上次生成的音频。'
                : '音频已生成'
              : '生成后可在这里试听和下载。'}
        </span>
      </div>
      {output && (
        <div className="player">
          <audio key={output.url} src={output.url} preload="metadata" controls aria-label="播客成品播放器" />
          <a className="download" href={output.url} download="D.Va-播客.mp3">
            <Icon name="download" size={16} />
            下载 MP3
          </a>
        </div>
      )}
    </section>
  );
}
