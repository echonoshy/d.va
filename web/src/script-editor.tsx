import { useId, useRef, useState } from 'react';
import type { ComponentPropsWithoutRef, Dispatch, FormEvent, RefCallback, SetStateAction } from 'react';
import { Icon } from './graphics';
import { isRole } from './studio-types';
import type { Busy, DraftSegment, Role, Segment as SegmentValue } from './studio-types';

export const ROLES: Record<Role, string> = { A: '主持人', B: '嘉宾' };
export const EXAMPLE: SegmentValue[] = [
  {
    role: 'A',
    text: '欢迎收听《城市的声音》。今天想问你一个问题：你觉得，一座城市醒来的第一声是什么？是远处进站的公交车，还是楼下那一声“早”？',
  },
  {
    role: 'B',
    text: '我想到的是楼下早餐铺拉开卷帘门的声音。紧接着是蒸笼冒气、瓷勺碰碗，还有老板对熟客说的那句“早啊”。你还没看表，就知道这条街开始了一天。',
  },
  {
    role: 'A',
    text: '那我们明早试一试，出门时先摘下耳机，听一听自己那条街的开场白。有些细节，光用眼睛看很容易错过。',
  },
];

export function Select({ className = '', children, ...props }: ComponentPropsWithoutRef<'select'>) {
  return (
    <span className={'select-wrap ' + className}>
      <select {...props}>{children}</select>
      <Icon name="chevron" size={15} />
    </span>
  );
}

type SegmentProps = {
  segment: DraftSegment;
  index: number;
  locked: boolean;
  update: (patch: Partial<SegmentValue>) => void;
  remove: () => void;
  setNode: RefCallback<HTMLTextAreaElement>;
};

function Segment({ segment, index, locked, update, remove, setNode }: SegmentProps) {
  const number = String(index + 1).padStart(2, '0');
  return (
    <li className={'segment segment-' + segment.role}>
      <div className="segment-toolbar">
        <span className="sequence" aria-hidden="true">
          {number}
        </span>
        <Select
          className={'role role-' + segment.role}
          value={segment.role}
          aria-label={'第 ' + (index + 1) + ' 段角色'}
          disabled={locked}
          onChange={(e) => {
            const role = e.currentTarget.value;
            if (isRole(role)) update({ role });
          }}
        >
          {Object.entries(ROLES).map(([role, name]) => (
            <option key={role} value={role}>
              {role}　{name}
            </option>
          ))}
        </Select>
        <button
          className="icon-button delete"
          type="button"
          title="删除段落"
          aria-label={'删除第 ' + (index + 1) + ' 段'}
          disabled={locked}
          onClick={remove}
        >
          <Icon name="trash" size={17} />
        </button>
      </div>
      <textarea
        ref={setNode}
        aria-label={'第 ' + (index + 1) + ' 段台词'}
        placeholder="输入这一段的台词…"
        rows={2}
        disabled={locked}
        value={segment.text}
        onChange={(e) => update({ text: e.target.value })}
      />
    </li>
  );
}

type ScriptEditorProps = {
  segments: DraftSegment[];
  setSegments: Dispatch<SetStateAction<DraftSegment[]>>;
  createSegment: (segment: SegmentValue) => DraftSegment;
  scriptAvailable: boolean;
  busy: Busy;
  generate: (topic: string) => Promise<boolean>;
  scriptError: string;
};

export function ScriptEditor({
  segments,
  setSegments,
  createSegment,
  scriptAvailable,
  busy,
  generate,
  scriptError,
}: ScriptEditorProps) {
  const [topicOpen, setTopicOpen] = useState(false);
  const [topic, setTopic] = useState('');
  const panelId = useId();
  const nextFocus = useRef<number | null>(null);
  const locked = Boolean(busy);
  function add() {
    const role = segments.at(-1)?.role === 'A' ? 'B' : 'A';
    const segment = createSegment({ role, text: '' });
    nextFocus.current = segment.id;
    setSegments((items) => [...items, segment]);
  }
  function update(id: number, patch: Partial<SegmentValue>) {
    setSegments((items) => items.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }
  async function submitTopic(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (topic.trim() && (await generate(topic.trim()))) setTopicOpen(false);
  }

  return (
    <section className="paper script" aria-labelledby="script-title">
      <div className="section-head editor-head">
        <h2 id="script-title">
          <span className="heading-icon script-icon">
            <Icon name="script" size={22} />
          </span>
          对话脚本<span className="count">{segments.length} 段</span>
        </h2>
        <div className="editor-actions">
          <button
            type="button"
            className="outline topic-toggle"
            aria-expanded={topicOpen}
            aria-controls={panelId}
            disabled={locked}
            onClick={() => setTopicOpen(!topicOpen)}
          >
            <Icon name="spark" size={16} />
            话题生成
          </button>
        </div>
      </div>
      {topicOpen && (
        <form className="topic-form" id={panelId} onSubmit={submitTopic}>
          <label htmlFor="topic">播客话题</label>
          <input
            id="topic"
            maxLength={500}
            value={topic}
            placeholder="想和嘉宾聊点什么？"
            onChange={(e) => setTopic(e.target.value)}
            disabled={locked || !scriptAvailable}
          />
          <div className="topic-form-end">
            <small>
              {scriptAvailable
                ? '生成后会替换当前脚本。'
                : '请先在服务端配置话题生成服务，也可直接编辑台词。'}
            </small>
            <button className="outline" disabled={!scriptAvailable || locked || !topic.trim()}>
              {busy === 'script' ? '正在生成…' : '生成脚本'}
            </button>
          </div>
          {scriptError && (
            <p className="notice error" role="alert">
              {scriptError}
            </p>
          )}
        </form>
      )}
      <ol className="segments">
        {segments.map((segment, index) => (
          <Segment
            key={segment.id}
            segment={segment}
            index={index}
            locked={locked}
            update={(patch) => update(segment.id, patch)}
            remove={() => setSegments((items) => items.filter((item) => item.id !== segment.id))}
            setNode={(node) => {
              if (node && nextFocus.current === segment.id) {
                nextFocus.current = null;
                node.focus();
              }
            }}
          />
        ))}
      </ol>
      {segments.length === 0 && <p className="empty-script">添加第一段台词，开始制作播客。</p>}
      <button
        type="button"
        className="outline add"
        disabled={locked || segments.length >= 40}
        title={segments.length >= 40 ? '最多添加 40 段' : undefined}
        onClick={add}
      >
        <Icon name="add" size={16} />
        添加段落
      </button>
    </section>
  );
}
