import { useState, useRef } from 'react';

// ── Constants ─────────────────────────────────────────────────────────────────

const LANGUAGES = [
  { id: 'java',       label: 'Java',       color: '#E76F00', icon: '☕' },
  { id: 'typescript', label: 'TypeScript', color: '#3178C6', icon: '𝑇𝑆' },
  { id: 'python',     label: 'Python',     color: '#4B8BBE', icon: '🐍' },
  { id: 'csharp',     label: 'C#',         color: '#9B4F96', icon: '#' },
  { id: 'javascript', label: 'JavaScript', color: '#F7DF1E', icon: '𝐽𝑆' },
  { id: 'ruby',       label: 'Ruby',       color: '#CC342D', icon: '💎' },
];

const FRAMEWORKS = {
  java:       [{ id: 'playwright', label: 'Playwright' }, { id: 'selenium', label: 'Selenium' }],
  typescript: [{ id: 'playwright', label: 'Playwright' }, { id: 'cypress', label: 'Cypress' }, { id: 'webdriverio', label: 'WebdriverIO' }],
  javascript: [{ id: 'playwright', label: 'Playwright' }, { id: 'cypress', label: 'Cypress' }, { id: 'puppeteer', label: 'Puppeteer' }],
  python:     [{ id: 'playwright', label: 'Playwright' }, { id: 'selenium', label: 'Selenium' }],
  csharp:     [{ id: 'playwright', label: 'Playwright' }, { id: 'selenium', label: 'Selenium' }],
  ruby:       [{ id: 'selenium', label: 'Selenium' }, { id: 'capybara', label: 'Capybara' }],
};

const BUILD_TOOLS = {
  java: ['Maven', 'Gradle'],
  typescript: ['npm', 'yarn', 'pnpm'],
  javascript: ['npm', 'yarn'],
  python: ['pip', 'poetry'],
  csharp: ['dotnet'],
  ruby: ['bundler'],
};

const RUNNERS = {
  java:       ['TestNG', 'JUnit 5'],
  typescript: ['Jest', 'Mocha'],
  javascript: ['Jest', 'Mocha'],
  python:     ['pytest'],
  csharp:     ['NUnit', 'MSTest', 'xUnit'],
  ruby:       ['RSpec'],
};

const FILE_ICONS = {
  java: '☕', xml: '📋', json: '{}', ts: '𝑇𝑆', tsx: '𝑇𝑆',
  py: '🐍', cs: '🔵', yml: '⚙', yaml: '⚙', md: '📄',
  properties: '⚙', txt: '📄', toml: '📋', gradle: '🐘',
  dockerfile: '🐳', 'docker-compose': '🐳',
};

const LANG_COLORS = {
  java: '#E76F00', xml: '#e66', json: '#4EC9B0', ts: '#3178C6',
  py: '#4B8BBE', cs: '#9B4F96', yml: '#CE9178', md: '#78C2FF',
  properties: '#9CDCFE', sh: '#89D185', dockerfile: '#2496ED',
};

const QUICK_PROMPTS = [
  { label: 'Java + Playwright + Maven',   lang: 'java',       fw: 'playwright', build: 'Maven',  runner: 'TestNG' },
  { label: 'TypeScript + Playwright',     lang: 'typescript', fw: 'playwright', build: 'npm',    runner: 'Jest' },
  { label: 'TypeScript + Cypress',        lang: 'typescript', fw: 'cypress',    build: 'npm',    runner: 'Mocha' },
  { label: 'Python + Playwright',         lang: 'python',     fw: 'playwright', build: 'pip',    runner: 'pytest' },
  { label: 'C# + Playwright + NUnit',     lang: 'csharp',     fw: 'playwright', build: 'dotnet', runner: 'NUnit' },
];

// ── API ───────────────────────────────────────────────────────────────────────

async function generateFramework(payload) {
  const res = await fetch('/api/generate-framework', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Generation failed: ${res.status} — ${err}`);
  }
  return res.json();
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getExt(filename) {
  const lower = filename.toLowerCase();
  if (lower === 'dockerfile') return 'dockerfile';
  if (lower.includes('docker-compose')) return 'docker-compose';
  return lower.split('.').pop() || 'txt';
}

function getFileIcon(filename) {
  const ext = getExt(filename);
  return FILE_ICONS[ext] || '📄';
}

function getLangColor(filename) {
  const ext = getExt(filename);
  return LANG_COLORS[ext] || '#8B949E';
}

function buildFileTree(files) {
  const tree = {};
  files.forEach((f) => {
    const parts = f.filename.split('/');
    let node = tree;
    parts.forEach((part, i) => {
      if (i === parts.length - 1) {
        node[part] = f;
      } else {
        node[part] = node[part] || {};
        node = node[part];
      }
    });
  });
  return tree;
}

function highlight(code, ext) {
  if (!code) return '';
  const escape = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  let s = escape(code);
  // strings
  s = s.replace(/(["'`])((?:\\.|(?!\1)[^\\])*)\1/g, '<span class="tok-str">$1$2$1</span>');
  // comments
  s = s.replace(/(\/\/[^\n]*|\/\*[\s\S]*?\*\/#?|#[^\n]*)/g, '<span class="tok-cmt">$1</span>');
  // keywords by language
  const kws = {
    java: 'public|private|protected|static|final|class|interface|extends|implements|new|return|void|import|package|if|else|for|while|try|catch|throw|throws|abstract|enum|super|this|null|true|false|boolean|int|long|double|String|List|Map|void',
    ts:   'const|let|var|function|class|interface|type|extends|implements|new|return|import|export|from|default|async|await|if|else|for|while|try|catch|throw|null|undefined|true|false|boolean|number|string|void|any|Promise',
    py:   'def|class|import|from|return|if|elif|else|for|while|try|except|raise|with|as|in|not|and|or|True|False|None|self|async|await|yield|pass|break|continue|lambda|global|nonlocal',
    cs:   'public|private|protected|static|readonly|class|interface|namespace|using|new|return|void|async|await|var|if|else|for|foreach|while|try|catch|throw|null|true|false|bool|int|string|Task|override|base|this|abstract|sealed|partial',
  };
  const kwMap = { java: kws.java, ts: kws.ts, tsx: kws.ts, py: kws.py, cs: kws.cs };
  const kwPattern = kwMap[ext];
  if (kwPattern) {
    s = s.replace(new RegExp(`\\b(${kwPattern})\\b`, 'g'), '<span class="tok-kw">$1</span>');
  }
  // numbers
  s = s.replace(/\b(\d+\.?\d*)\b/g, '<span class="tok-num">$1</span>');
  // xml/html tags
  if (['xml', 'html'].includes(ext)) {
    s = s.replace(/(&lt;\/?[\w:-]+)/g, '<span class="tok-tag">$1</span>');
  }
  return s;
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const [lang,       setLang]       = useState('java');
  const [framework,  setFramework]  = useState('playwright');
  const [buildTool,  setBuildTool]  = useState('Maven');
  const [runner,     setRunner]     = useState('TestNG');
  const [projName,   setProjName]   = useState('');
  const [appUrl,     setAppUrl]     = useState('');
  const [pages,      setPages]      = useState('');
  const [author,     setAuthor]     = useState('');
  const [status,     setStatus]     = useState('idle'); // idle | loading | done | error
  const [progress,   setProgress]   = useState('');
  const [files,      setFiles]      = useState([]);
  const [selected,   setSelected]   = useState(null);
  const [copied,     setCopied]     = useState(false);
  const [openDirs,   setOpenDirs]   = useState({});
  const [error,      setError]      = useState('');
  const codeRef = useRef(null);

  const currentLang = LANGUAGES.find(l => l.id === lang);
  const availableFrameworks = FRAMEWORKS[lang] || [];
  const availableBuildTools = BUILD_TOOLS[lang] || [];
  const availableRunners    = RUNNERS[lang]     || [];

  const applyQuickPrompt = (q) => {
    setLang(q.lang);
    setFramework(q.fw);
    setBuildTool(q.build);
    setRunner(q.runner);
  };

  const handleLangChange = (id) => {
    setLang(id);
    setFramework(FRAMEWORKS[id]?.[0]?.id || '');
    setBuildTool(BUILD_TOOLS[id]?.[0] || '');
    setRunner(RUNNERS[id]?.[0] || '');
  };

  const handleGenerate = async () => {
    if (!projName.trim()) { setError('Project name is required.'); return; }
    setError('');
    setStatus('loading');
    setFiles([]);
    setSelected(null);
    setProgress('Initialising agents…');

    const slug = projName.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-');
    const groupBase = slug.replace(/-/g, '');
    const payload = {
      project_name:   projName,
      group_id:       `com.${groupBase}.automation`,
      artifact_id:    `${slug}-automation`,
      language:       lang,
      framework,
      build_tool:     buildTool,
      test_runner:    runner,
      app_url:        appUrl || `https://${slug}.example.com`,
      pages:          pages.split(',').map(p => p.trim()).filter(Boolean),
      test_scenarios: pages || 'verify page loads, verify positive flow, verify error handling',
      browser:        'chromium',
      author:         author || 'Developer',
    };

    const steps = [
      `Generating ${lang} project structure…`,
      `Creating Page Objects…`,
      `Building utility classes…`,
      `Writing CI/CD pipeline…`,
      'Packaging files…',
    ];
    let stepIdx = 0;
    const stepTimer = setInterval(() => {
      stepIdx = (stepIdx + 1) % steps.length;
      setProgress(steps[stepIdx]);
    }, 1800);

    try {
      const result = await generateFramework(payload);
      clearInterval(stepTimer);
      setFiles(result.files || []);
      setStatus('done');
      setProgress('');
      if (result.files?.length) {
        setSelected(result.files[0]);
        const initOpen = {};
        result.files.forEach(f => {
          const parts = f.filename.split('/');
          if (parts.length > 1) initOpen[parts[0]] = true;
          if (parts.length > 2) initOpen[`${parts[0]}/${parts[1]}`] = true;
        });
        setOpenDirs(initOpen);
      }
    } catch (err) {
      clearInterval(stepTimer);
      setError(err.message);
      setStatus('error');
    }
  };

  const copyFile = () => {
    if (!selected) return;
    navigator.clipboard.writeText(selected.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const downloadAll = () => {
    files.forEach(f => {
      const blob = new Blob([f.content], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = f.filename.split('/').pop();
      a.click();
    });
  };

  const selectedExt = selected ? getExt(selected.filename) : '';

  return (
    <div className="app">
      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">⚡</div>
          <div>
            <div className="brand-name">AutoGen</div>
            <div className="brand-sub">Test Framework Generator</div>
          </div>
        </div>

        <div className="sidebar-scroll">
          {/* Quick prompts */}
          <div className="section">
            <div className="section-label">Quick Start</div>
            <div className="quick-list">
              {QUICK_PROMPTS.map(q => (
                <button key={q.label} className="quick-btn" onClick={() => applyQuickPrompt(q)}>
                  {q.label}
                </button>
              ))}
            </div>
          </div>

          {/* Language */}
          <div className="section">
            <div className="section-label">Language</div>
            <div className="lang-grid">
              {LANGUAGES.map(l => (
                <button
                  key={l.id}
                  className={`lang-btn${lang === l.id ? ' lang-btn--active' : ''}`}
                  style={lang === l.id ? { borderColor: l.color, color: l.color } : {}}
                  onClick={() => handleLangChange(l.id)}
                >
                  <span className="lang-icon">{l.icon}</span>
                  <span>{l.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Framework */}
          <div className="section">
            <div className="section-label">Framework</div>
            <div className="chip-row">
              {availableFrameworks.map(f => (
                <button
                  key={f.id}
                  className={`chip${framework === f.id ? ' chip--active' : ''}`}
                  onClick={() => setFramework(f.id)}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Build tool + Test runner */}
          <div className="section row-2">
            <div>
              <div className="section-label">Build Tool</div>
              <div className="chip-row">
                {availableBuildTools.map(b => (
                  <button
                    key={b}
                    className={`chip${buildTool === b ? ' chip--active' : ''}`}
                    onClick={() => setBuildTool(b)}
                  >{b}</button>
                ))}
              </div>
            </div>
            <div>
              <div className="section-label">Test Runner</div>
              <div className="chip-row">
                {availableRunners.map(r => (
                  <button
                    key={r}
                    className={`chip${runner === r ? ' chip--active' : ''}`}
                    onClick={() => setRunner(r)}
                  >{r}</button>
                ))}
              </div>
            </div>
          </div>

          {/* Project details */}
          <div className="section">
            <div className="section-label">Project</div>
            <input
              className="field"
              placeholder="Project name *"
              value={projName}
              onChange={e => setProjName(e.target.value)}
            />
            <input
              className="field"
              placeholder="App URL (https://…)"
              value={appUrl}
              onChange={e => setAppUrl(e.target.value)}
            />
            <input
              className="field"
              placeholder="Pages (comma-separated: Login, Home, Cart)"
              value={pages}
              onChange={e => setPages(e.target.value)}
            />
            <input
              className="field"
              placeholder="Your name (for README)"
              value={author}
              onChange={e => setAuthor(e.target.value)}
            />
          </div>

          {error && <div className="err-msg">{error}</div>}

          <button
            className={`gen-btn${status === 'loading' ? ' gen-btn--loading' : ''}`}
            onClick={handleGenerate}
            disabled={status === 'loading'}
          >
            {status === 'loading' ? (
              <><span className="spin" /> Generating…</>
            ) : (
              <><span>⚡</span> Generate Framework</>
            )}
          </button>

          {status === 'loading' && (
            <div className="progress-row">
              <div className="progress-bar">
                <div className="progress-fill" />
              </div>
              <div className="progress-text">{progress}</div>
            </div>
          )}

          {status === 'done' && files.length > 0 && (
            <div className="stats-row">
              <div className="stat"><span className="stat-n">{files.length}</span><span>files</span></div>
              <div className="stat"><span className="stat-n">{(files.reduce((a, f) => a + f.content.length, 0) / 1024).toFixed(0)}KB</span><span>code</span></div>
              <div className="stat"><span className="stat-n">{currentLang?.icon}</span><span>{lang}</span></div>
            </div>
          )}
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────────────── */}
      <main className="main">
        {status === 'idle' && (
          <Welcome lang={lang} framework={framework} langColor={currentLang?.color} />
        )}

        {status === 'loading' && (
          <div className="loading-screen">
            <div className="loading-ring" style={{ borderTopColor: currentLang?.color }}>
              <div className="loading-inner" style={{ color: currentLang?.color }}>{currentLang?.icon}</div>
            </div>
            <div className="loading-title">Generating your framework</div>
            <div className="loading-sub">{progress}</div>
            <div className="loading-stack">
              <span className="stack-badge" style={{ color: currentLang?.color }}>{lang}</span>
              <span className="stack-sep">·</span>
              <span className="stack-badge">{framework}</span>
              <span className="stack-sep">·</span>
              <span className="stack-badge">{buildTool}</span>
              <span className="stack-sep">·</span>
              <span className="stack-badge">{runner}</span>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="error-screen">
            <div className="error-icon">⚠</div>
            <div className="error-title">Generation failed</div>
            <div className="error-msg">{error}</div>
            <button className="retry-btn" onClick={() => setStatus('idle')}>Try again</button>
          </div>
        )}

        {status === 'done' && files.length > 0 && (
          <div className="output">
            {/* File tree */}
            <div className="file-tree">
              <div className="tree-header">
                <span className="tree-title">📁 {projName.toLowerCase().replace(/[^a-z0-9]/g, '-')}-automation</span>
                <button className="dl-btn" onClick={downloadAll} title="Download all files">↓ Download all</button>
              </div>
              <div className="tree-body">
                <FileTree
                  tree={buildFileTree(files)}
                  selected={selected}
                  onSelect={setSelected}
                  openDirs={openDirs}
                  setOpenDirs={setOpenDirs}
                  path=""
                />
              </div>
            </div>

            {/* Code viewer */}
            <div className="code-panel">
              {selected ? (
                <>
                  <div className="code-topbar">
                    <div className="code-filename">
                      <span style={{ color: getLangColor(selected.filename) }}>{getFileIcon(selected.filename)}</span>
                      <span>{selected.filename}</span>
                    </div>
                    <button className={`copy-btn${copied ? ' copy-btn--done' : ''}`} onClick={copyFile}>
                      {copied ? '✓ Copied' : 'Copy'}
                    </button>
                  </div>
                  <div className="code-scroll" ref={codeRef}>
                    <pre className="code-pre">
                      <code
                        dangerouslySetInnerHTML={{
                          __html: highlight(selected.content, selectedExt),
                        }}
                      />
                    </pre>
                  </div>
                  <div className="code-footer">
                    <span>{selected.content.split('\n').length} lines</span>
                    <span>·</span>
                    <span>{(selected.content.length / 1024).toFixed(1)} KB</span>
                    <span>·</span>
                    <span style={{ color: getLangColor(selected.filename) }}>{selectedExt.toUpperCase()}</span>
                  </div>
                </>
              ) : (
                <div className="code-empty">Select a file to view its content</div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ── FileTree ──────────────────────────────────────────────────────────────────

function FileTree({ tree, selected, onSelect, openDirs, setOpenDirs, path }) {
  const entries = Object.entries(tree).sort(([, a], [, b]) => {
    const aIsFile = a && typeof a.filename === 'string';
    const bIsFile = b && typeof b.filename === 'string';
    if (aIsFile !== bIsFile) return aIsFile ? 1 : -1;
    return 0;
  });

  return (
    <ul className="tree-list">
      {entries.map(([name, node]) => {
        const fullPath = path ? `${path}/${name}` : name;
        const isFile = node && typeof node.filename === 'string';

        if (isFile) {
          const isActive = selected?.filename === node.filename;
          return (
            <li key={name}>
              <button
                className={`tree-file${isActive ? ' tree-file--active' : ''}`}
                onClick={() => onSelect(node)}
                style={isActive ? { color: getLangColor(node.filename) } : {}}
              >
                <span className="tree-file-icon" style={{ color: getLangColor(node.filename) }}>
                  {getFileIcon(node.filename)}
                </span>
                <span className="tree-file-name">{name}</span>
              </button>
            </li>
          );
        }

        const isOpen = openDirs[fullPath] !== false;
        return (
          <li key={name}>
            <button
              className="tree-dir"
              onClick={() => setOpenDirs(prev => ({ ...prev, [fullPath]: !isOpen }))}
            >
              <span className="tree-dir-arrow">{isOpen ? '▾' : '▸'}</span>
              <span className="tree-dir-icon">📂</span>
              <span>{name}</span>
            </button>
            {isOpen && (
              <div className="tree-children">
                <FileTree
                  tree={node}
                  selected={selected}
                  onSelect={onSelect}
                  openDirs={openDirs}
                  setOpenDirs={setOpenDirs}
                  path={fullPath}
                />
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

// ── Welcome ───────────────────────────────────────────────────────────────────

function Welcome({ lang, framework, langColor }) {
  return (
    <div className="welcome">
      <div className="welcome-glow" style={{ background: `radial-gradient(ellipse at 50% 30%, ${langColor}18 0%, transparent 70%)` }} />
      <div className="welcome-icon" style={{ color: langColor }}>⚡</div>
      <h1 className="welcome-title">Test Automation Framework Generator</h1>
      <p className="welcome-sub">
        Configure your stack on the left, hit <strong>Generate</strong>, and get a complete
        production-ready automation framework — Page Objects, utilities, CI/CD, Docker, and README — in seconds.
      </p>
      <div className="feature-grid">
        {[
          ['☕', 'Java',        'Playwright · Selenium · Maven · Gradle · TestNG · JUnit'],
          ['𝑇𝑆', 'TypeScript', 'Playwright · Cypress · WebdriverIO · npm · Jest · Allure'],
          ['🐍', 'Python',     'Playwright · Selenium · pytest · Allure · poetry'],
          ['#',  'C#',         'Playwright · Selenium · NUnit · MSTest · dotnet'],
          ['𝐽𝑆', 'JavaScript', 'Cypress · Playwright · Puppeteer · Mocha · Jest'],
          ['💎', 'Ruby',       'Selenium · Capybara · RSpec · Bundler'],
        ].map(([icon, name, desc]) => (
          <div key={name} className="feature-card">
            <div className="feature-icon">{icon}</div>
            <div className="feature-name">{name}</div>
            <div className="feature-desc">{desc}</div>
          </div>
        ))}
      </div>
      <div className="welcome-footer">
        Selected stack: <strong style={{ color: langColor }}>{lang}</strong> · <strong>{framework}</strong>
      </div>
    </div>
  );
}
