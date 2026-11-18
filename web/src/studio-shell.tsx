import { useRef, useState } from 'react';
import { Icon, type IconName } from './graphics';

type Tool = { name: string; icon: IconName };
type ToolGroup = { title: string; tools: Tool[] };
const groups: ToolGroup[] = [
  {
    title: '创作空间',
    tools: [
      { name: '播客编辑台', icon: 'podcast' },
      { name: 'TTS', icon: 'text' },
      { name: 'SSML', icon: 'code' },
      { name: '话题转 SSML 播客', icon: 'chat' },
    ],
  },
  {
    title: '声音工具',
    tools: [
      { name: '音色管理', icon: 'voices' },
      { name: '声音克隆', icon: 'clone' },
      { name: '训练', icon: 'train' },
      { name: '音频工具', icon: 'tune' },
    ],
  },
  {
    title: '工作室',
    tools: [
      { name: '系统', icon: 'system' },
      { name: '使用说明', icon: 'help' },
    ],
  },
];

export function Sidebar({ section, select }: { section: string; select: (s: string) => void }) {
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  function close() {
    setOpen(false);
    if (open) toggle.current?.focus();
  }
  function go(name: string) {
    close();
    select(name);
    window.scrollTo({ top: 0, behavior: 'instant' });
  }
  return (
    <aside
      className="sidebar"
      onKeyDown={(e) => {
        if (e.key === 'Escape' && open) {
          close();
        }
      }}
    >
      <div className="brand-row">
        <button type="button" className="brand" onClick={() => go('播客编辑台')} aria-label="D.Va 工作室首页">
          <span className="brand-mark">
            <Icon name="headphones" size={29} />
            <i />
            <b />
          </span>
          <span className="brand-words">
            <strong>D.Va</strong>
            <span>语音工作室</span>
          </span>
        </button>
        <button
          ref={toggle}
          type="button"
          className="menu-toggle"
          aria-expanded={open}
          aria-controls="studio-nav"
          onClick={() => setOpen(!open)}
        >
          <Icon name={open ? 'close' : 'menu'} /> 工具菜单
        </button>
      </div>
      <nav id="studio-nav" className={'studio-navigation' + (open ? ' is-open' : '')} aria-label="工作台">
        {groups.map((group) => (
          <div className="nav-group" key={group.title}>
            <span className="nav-heading">{group.title}</span>
            {group.tools.map(({ name, icon }) => (
              <button key={name} type="button" aria-pressed={section === name} onClick={() => go(name)}>
                <Icon name={icon} size={19} />
                <span>{name}</span>
                {section === name && <i className="nav-dot" aria-hidden="true" />}
              </button>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}

export function WorkspaceBar({
  section,
  engine,
  available,
}: {
  section: string;
  engine: string;
  available: boolean;
}) {
  const group = groups.find((g) => g.tools.some((t) => t.name === section));
  return (
    <header className="workspace-bar">
      <div className="crumb">
        <span>{group?.title}</span>
        <b aria-hidden="true">/</b>
        <strong>{section}</strong>
      </div>
      <span className={'engine' + (available ? ' ready' : '')}>
        <i aria-hidden="true" />
        {engine}
      </span>
    </header>
  );
}

export function PodcastIntro({ speakers, characters }: { speakers: number; characters: number }) {
  return (
    <header className="podcast-hero studio-banner">
      <div className="hero-copy">
        <h1>播客编辑台</h1>
        <p>编辑对话、分配音色，生成可播放的 MP3。</p>
        <div className="hero-meta">
          <span>
            <Icon name="voices" size={16} />
            {speakers} 位角色
          </span>
          <span>
            <Icon name="script" size={15} />共 {characters} 字
          </span>
        </div>
      </div>
      <div className="studio-gear" aria-hidden="true" />
    </header>
  );
}

const instructions: Record<string, string> = {
  TTS: '选择合成模型和音色，输入台词后试听。',
  SSML: '用台词、角色和停顿编排多声部脚本。',
  音色管理: '创建、试音、合并或导入音色卡。',
  声音克隆: '提供原始语音和目标音色参考，生成转换后的录音。',
  训练: '选择数据集与训练参数，训练自己的 ChatTTS 音色。',
  '话题转 SSML 播客': '输入话题生成多人脚本，并配音、混入背景音乐。',
  音频工具: '调整音量、速度和音高，或从视频提取音轨。',
  系统: '查看本机资源使用情况，管理已加载的模型。',
};

export function ToolIntro({ section }: { section: string }) {
  const tool = groups.flatMap((g) => g.tools).find((t) => t.name === section);
  return (
    <header className="tool-intro studio-banner">
      <span className="tool-mark" aria-hidden="true">
        <Icon name={tool?.icon || 'tune'} size={28} />
      </span>
      <div>
        <h1>{section}</h1>
        {instructions[section] && <p>{instructions[section]}</p>}
      </div>
    </header>
  );
}
