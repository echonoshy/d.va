import { useEffect, useRef, useState } from 'react';
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

type HeaderProps = {
  section: string;
  select: (name: string) => void;
  engine: string;
  available: boolean;
};

export function StudioHeader({ section, select, engine, available }: HeaderProps) {
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function dismiss(event: PointerEvent) {
      if (event.target instanceof Node && !menu.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener('pointerdown', dismiss);
    return () => document.removeEventListener('pointerdown', dismiss);
  }, [open]);

  function go(name: string) {
    setOpen(false);
    if (open) toggle.current?.focus();
    select(name);
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  return (
    <header className="studio-header">
      <button
        type="button"
        className="wordmark"
        aria-label="D.Va 工作室首页"
        onClick={() => go('播客编辑台')}
      >
        <strong>D.Va</strong>
        <span>语音工作室</span>
      </button>
      <span className={'engine' + (available ? ' ready' : '')}>
        <i aria-hidden="true" />
        {engine}
      </span>
      <div
        className="menu-wrap"
        ref={menu}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
        }}
        onKeyDown={(event) => {
          if (open && event.key === 'Escape') {
            setOpen(false);
            toggle.current?.focus();
          }
        }}
      >
        <button
          className="menu-toggle"
          type="button"
          ref={toggle}
          aria-expanded={open}
          aria-controls="studio-nav"
          onClick={() => setOpen(!open)}
        >
          <Icon name={open ? 'close' : 'menu'} size={15} />
          工具菜单
        </button>
        <nav className="tool-menu" aria-label="工作台" id="studio-nav" hidden={!open}>
          {groups.map((group) => (
            <div className="nav-group" key={group.title}>
              <p>{group.title}</p>
              {group.tools.map((tool) => (
                <button
                  key={tool.name}
                  type="button"
                  aria-pressed={section === tool.name}
                  onClick={() => go(tool.name)}
                >
                  <Icon name={tool.icon} size={17} />
                  {tool.name}
                </button>
              ))}
            </div>
          ))}
        </nav>
      </div>
    </header>
  );
}

type PodcastIntroProps = {
  select: (name: string) => void;
  speakers: number;
  characters: number;
  capacity: number;
  segments: number;
};

export function PodcastIntro({ select, speakers, characters, capacity, segments }: PodcastIntroProps) {
  const stations = [
    {
      english: 'SCRIPT',
      label: '编辑对话',
      target: 'script-title',
      art: 'running',
      detail: segments + ' 段',
    },
    { english: 'VOICES', label: '分配音色', target: 'mix-title', art: 'sitting', detail: speakers + ' 位' },
    { english: 'PLAYBACK', label: '成品试听', target: 'result-title', art: 'sleeping', detail: 'MP3' },
  ];
  return (
    <>
      <header className="sheet-heading">
        <div className="sheet-title">
          <h1>播客编辑台</h1>
          <p className="plate-label" lang="en">
            PODCAST STUDIO
          </p>
          <p className="sheet-description">编辑对话、分配音色，生成可试听的播客。</p>
        </div>
        <div className="tool-index">
          <p className="plate-label" lang="en">
            TOOL INDEX
          </p>
          <ul>
            <li>
              <button onClick={() => select('TTS')}>
                文本转语音 <small>TTS</small>
              </button>
            </li>
            <li>
              <button onClick={() => select('SSML')}>
                多声部脚本 <small>SSML</small>
              </button>
            </li>
            <li>
              <button onClick={() => select('音色管理')}>音色管理</button>
            </li>
          </ul>
        </div>
      </header>
      <div className="broadcast-scene">
        <div className="scene-image" role="img" aria-label="黑白猫跃过层层屋顶，向天台上的麦克风跳去" />
        <div className="scene-hud">
          <label className="script-gauge">
            <span>脚本字数</span>
            <meter
              min={0}
              max={capacity}
              value={Math.min(characters, capacity)}
              aria-label="脚本字数"
              aria-valuetext={characters + ' 字，上限 ' + capacity + ' 字'}
            />
            <small>
              {characters.toLocaleString()} / {capacity.toLocaleString()}
            </small>
          </label>
          <span className="scene-roles">
            <Icon name="voices" size={17} /> {speakers} 位角色
          </span>
        </div>
      </div>
      <nav className="studio-stations" aria-label="本期制作流程">
        {stations.map((station) => (
          <a key={station.target} href={'#' + station.target}>
            <span className="plate-label" lang="en">
              {station.english}
            </span>
            <span className={'cat-study ' + station.art} aria-hidden="true" />
            <span className="station-caption">
              {station.label}
              <small>{station.detail}</small>
            </span>
          </a>
        ))}
      </nav>
    </>
  );
}

const toolInfo: Record<string, [string, string]> = {
  TTS: ['SPEECH SYNTHESIS', '选择合成模型和音色，输入台词后试听。'],
  SSML: ['SCRIPT EDITOR', '用台词、角色和停顿编排多声部脚本。'],
  音色管理: ['VOICE LIBRARY', '创建、试音、合并或导入音色卡。'],
  声音克隆: ['VOICE CONVERSION', '提供原始语音和目标音色参考，生成转换后的录音。'],
  训练: ['VOICE TRAINING', '选择数据集与训练参数，训练自己的 ChatTTS 音色。'],
  '话题转 SSML 播客': ['PODCAST SCRIPT', '输入话题生成多人脚本，并配音、混入背景音乐。'],
  音频工具: ['AUDIO TOOLS', '调整音量、速度和音高，或从视频提取音轨。'],
  系统: ['SYSTEM', '查看本机资源使用情况，管理已加载的模型。'],
  使用说明: ['STUDIO MANUAL', ''],
};

export function ToolIntro({ section }: { section: string }) {
  const info = toolInfo[section];
  return (
    <header className="tool-heading sheet-heading">
      <div className="sheet-title">
        <h1>{section}</h1>
        {info && (
          <p className="plate-label" lang="en">
            {info[0]}
          </p>
        )}
        {info?.[1] && <p className="sheet-description">{info[1]}</p>}
      </div>
      <span className="cat-study sitting" aria-hidden="true" />
    </header>
  );
}
