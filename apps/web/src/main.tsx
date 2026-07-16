/* eslint-disable react-refresh/only-export-components, react-hooks/exhaustive-deps */
import {
  StrictMode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type CSSProperties,
  type ReactNode,
} from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import {
  Archive,
  ChevronRight,
  Clapperboard,
  Clock3,
  FileVideo,
  FolderKanban,
  Gauge,
  HelpCircle,
  Home,
  Layers3,
  MoreHorizontal,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  Sparkles,
  Upload,
  Video,
  WandSparkles,
  X,
} from 'lucide-react';
import './styles.css';

type Page = 'dashboard' | 'generate' | 'review' | 'history' | 'projects' | 'settings' | 'help';
type Highlight = {
  start_time: number;
  end_time: number;
  overall_score?: number;
  score?: number;
  hook_sentence?: string;
  reason_selected?: string;
  virality_reason?: string;
  gameplay_score?: number;
  emotion_score?: number;
  dialogue_score?: number;
  action_score?: number;
};
type Clip = Highlight & { clip_url?: string; title?: string };
type Job = {
  id: string;
  filename: string;
  status: string;
  stage: string;
  progress: number;
  logs: string[];
  error?: string;
  created_at: string;
  result?: { highlights?: Highlight[]; shorts?: Clip[] };
  options: { review_only?: boolean; game?: string; layout_mode?: string };
};

type ProjectDefaults = { game: string; layout: string };

const api = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';
const settingsKey = 'highlight-ai-project-defaults';
const defaultProjectDefaults: ProjectDefaults = { game: 'auto', layout: 'auto' };

function loadProjectDefaults(): ProjectDefaults {
  try {
    const saved = localStorage.getItem(settingsKey);
    if (!saved) return defaultProjectDefaults;
    const value = JSON.parse(saved) as Partial<ProjectDefaults>;
    return {
      game: ['auto', 'tlou', 'gta6', 'cyberpunk'].includes(value.game ?? '')
        ? value.game!
        : defaultProjectDefaults.game,
      layout: ['auto', 'single', 'dialogue', 'split'].includes(value.layout ?? '')
        ? value.layout!
        : defaultProjectDefaults.layout,
    };
  } catch {
    return defaultProjectDefaults;
  }
}

function clipFileUrl(path?: string) {
  return path ? `${api}/files?path=${encodeURIComponent(path)}` : undefined;
}
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 1_500, retry: 1, refetchOnWindowFocus: false } },
});
const stages = [
  'Preparing',
  'Transcribing',
  'Finding highlights',
  'Ranking',
  'Rendering',
  'Completed',
];
const nav: { id: Page; label: string; icon: typeof Home }[] = [
  { id: 'dashboard', label: 'Overview', icon: Home },
  { id: 'generate', label: 'Generate', icon: WandSparkles },
  { id: 'review', label: 'Review', icon: Layers3 },
  { id: 'history', label: 'History', icon: Clock3 },
  { id: 'projects', label: 'Projects', icon: FolderKanban },
];

function useJobs() {
  return useQuery<Job[]>({
    queryKey: ['jobs'],
    queryFn: async () => {
      const response = await fetch(`${api}/jobs`);
      if (!response.ok) throw new Error('The local service is unavailable.');
      return response.json();
    },
    refetchInterval: (query) =>
      query.state.data?.some((job) => ['queued', 'processing'].includes(job.status))
        ? 2_500
        : false,
  });
}

const formatSeconds = (value?: number) =>
  value == null
    ? '—'
    : `${Math.floor(value / 60)}:${String(Math.round(value % 60)).padStart(2, '0')}`;
const titleFromFile = (filename: string) => filename.replace(/\.[^/.]+$/, '');

function Button({
  children,
  variant = 'primary',
  className = '',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'quiet' | 'light';
}) {
  return (
    <button className={`button ${variant} ${className}`} {...props}>
      {children}
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${status}`}>{status === 'queued' ? 'Queued' : status}</span>;
}

function EmptyState({
  icon: Icon = Archive,
  title,
  description,
  action,
  onAction,
}: {
  icon?: typeof Archive;
  title: string;
  description: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon size={23} />
      </span>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {action && (
        <Button variant="secondary" onClick={onAction}>
          {action}
          <ChevronRight size={15} />
        </Button>
      )}
    </div>
  );
}

function ErrorNotice({
  title,
  detail,
  onRetry,
  onDismiss,
}: {
  title: string;
  detail: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}) {
  return (
    <section className="error-notice" role="alert">
      <div>
        <b>{title}</b>
        <p>{detail}</p>
      </div>
      <div>
        {onRetry && (
          <Button variant="secondary" onClick={onRetry}>
            <RefreshCw size={14} />
            Retry
          </Button>
        )}
        {onDismiss && (
          <Button variant="quiet" aria-label="Dismiss message" onClick={onDismiss}>
            <X size={16} />
          </Button>
        )}
      </div>
    </section>
  );
}

function LoadingRows() {
  return (
    <div className="loading-list" aria-label="Loading projects" aria-busy="true">
      {[0, 1, 2].map((item) => (
        <div className="skeleton-row" key={item}>
          <i />
          <span />
          <b />
        </div>
      ))}
    </div>
  );
}

function Sidebar({ page, setPage }: { page: Page; setPage: (page: Page) => void }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">
          <Sparkles size={17} />
        </span>
        <span className="brand-name">
          Highlight<span>AI</span>
        </span>
      </div>
      <div className="workspace">
        <span>WORKSPACE</span>
        <div>
          Senpai Plays <ChevronRight size={14} />
        </div>
      </div>
      <nav aria-label="Main navigation">
        {nav.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setPage(id)}
            className={page === id ? 'active' : ''}
            aria-current={page === id ? 'page' : undefined}
          >
            <Icon size={18} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <button
          type="button"
          onClick={() => setPage('settings')}
          className={page === 'settings' ? 'active' : ''}
        >
          <Settings size={18} />
          <span>Settings</span>
        </button>
        <button type="button" onClick={() => setPage('help')}>
          <HelpCircle size={18} />
          <span>Help & support</span>
        </button>
        <div className="account">
          <div>SG</div>
          <span>
            <b>Senpai Gaming</b>
            <small>Pro workspace</small>
          </span>
          <MoreHorizontal size={17} />
        </div>
      </div>
    </aside>
  );
}

function PageShell({
  eyebrow,
  title,
  action,
  children,
}: {
  eyebrow: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="main">
      <header className="topbar">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
        </div>
        <div className="top-actions">{action}</div>
      </header>
      {children}
    </main>
  );
}

function ProjectRow({ job, onOpen }: { job: Job; onOpen: () => void }) {
  return (
    <button
      className="project-row"
      type="button"
      onClick={onOpen}
      aria-label={`Open ${titleFromFile(job.filename)}`}
    >
      <span className="thumb">
        <Video size={19} />
        <b>{job.filename.slice(0, 1).toUpperCase()}</b>
      </span>
      <span className="project-info">
        <b>{titleFromFile(job.filename)}</b>
        <small>
          {new Date(job.created_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
          })}{' '}
          · AI gameplay analysis
        </small>
      </span>
      <span className="project-meta">
        <StatusBadge status={job.status} />
        <small>{job.result?.shorts?.length ?? 0} clips</small>
      </span>
      <ChevronRight size={18} />
    </button>
  );
}

function Dashboard({
  jobs,
  isLoading,
  setPage,
  onOpenJob,
}: {
  jobs: Job[];
  isLoading: boolean;
  setPage: (page: Page) => void;
  onOpenJob: (job: Job) => void;
}) {
  const completed = jobs.filter((job) => job.status === 'completed');
  const scores = completed.flatMap((job) =>
    (job.result?.highlights ?? []).map(
      (highlight) => highlight.overall_score ?? highlight.score ?? 0,
    ),
  );
  const statistics: [string, string, ComponentType<{ size?: number }>, string][] = [
    ['Videos processed', String(jobs.length), Video, 'All time'],
    [
      'Shorts generated',
      String(completed.reduce((total, job) => total + (job.result?.shorts?.length ?? 0), 0)),
      Sparkles,
      'All time',
    ],
    [
      'Avg. AI score',
      scores.length
        ? String(Math.round(scores.reduce((total, score) => total + score, 0) / scores.length))
        : '—',
      Gauge,
      'Completed projects',
    ],
  ];
  return (
    <PageShell
      eyebrow="Overview"
      title="Good evening, Teja."
      action={
        <Button onClick={() => setPage('generate')}>
          <Plus size={17} />
          New project
        </Button>
      }
    >
      <section className="hero-card">
        <div>
          <p className="eyebrow">CREATE YOUR NEXT VIRAL MOMENT</p>
          <h2>
            Turn raw gameplay into
            <br />
            <i>scroll-stopping</i> shorts.
          </h2>
          <p>Upload a session and let your AI editor find the moments worth sharing.</p>
          <Button variant="light" onClick={() => setPage('generate')}>
            Start creating <ChevronRight size={16} />
          </Button>
        </div>
        <div className="hero-orb" aria-hidden="true">
          <Clapperboard size={54} />
          <span>AI</span>
        </div>
      </section>
      <section className="stats" aria-label="Workspace statistics">
        {statistics.map(([label, value, Icon, caption]) => (
          <article className="stat" key={label}>
            <span className="icon-box">
              <Icon size={18} />
            </span>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{caption}</small>
          </article>
        ))}
      </section>
      <div className="section-heading">
        <div>
          <h2>Recent projects</h2>
          <p>Pick up where you left off.</p>
        </div>
        <Button variant="quiet" onClick={() => setPage('projects')}>
          View all <ChevronRight size={16} />
        </Button>
      </div>
      <section className="project-list">
        {isLoading ? (
          <LoadingRows />
        ) : jobs.length ? (
          jobs
            .slice(0, 4)
            .map((job) => <ProjectRow key={job.id} job={job} onOpen={() => onOpenJob(job)} />)
        ) : (
          <EmptyState
            title="Your creative workspace is ready"
            description="Upload a gameplay session and your first project will appear here."
            action="Create a project"
            onAction={() => setPage('generate')}
          />
        )}
      </section>
    </PageShell>
  );
}

function Generate({ defaults, onJob }: { defaults: ProjectDefaults; onJob: (job: Job) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File>();
  const [dragging, setDragging] = useState(false);
  const [clips, setClips] = useState(5);
  const [game, setGame] = useState(defaults.game);
  const [layout, setLayout] = useState(defaults.layout);
  const [review, setReview] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const chooseFile = (selected?: File) => {
    if (!selected) return;
    if (!selected.type.startsWith('video/')) {
      setError('Choose a supported video file (MP4, MOV, or MKV) and try again.');
      return;
    }
    setFile(selected);
    setError('');
  };
  const submit = async () => {
    if (!file) {
      setError('Add a gameplay recording before starting the AI editor.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const upload = await fetch(`${api}/uploads`, {
        method: 'POST',
        headers: { 'Content-Type': file.type, 'X-Filename': file.name },
        body: file,
      });
      if (!upload.ok)
        throw new Error('The upload could not be saved. Check available disk space, then retry.');
      const { path, filename } = await upload.json();
      const response = await fetch(`${api}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: path,
          filename,
          clips,
          game,
          layout_mode: layout,
          review_only: review,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail ?? 'The AI editor could not start. Please retry.');
      }
      const job = await response.json();
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      onJob(job);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'We could not start processing this video. Please try again.',
      );
    } finally {
      setSubmitting(false);
    }
  };
  const removeFile = () => {
    setFile(undefined);
    if (inputRef.current) inputRef.current.value = '';
  };
  return (
    <PageShell eyebrow="New project" title="Generate clips">
      <p className="page-description">
        Give your session to your AI editor. It will find, rank, and render your strongest moments.
      </p>
      <div className="generate-grid">
        <section className="form-card">
          <h2>Source video</h2>
          <button
            type="button"
            className={`dropzone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              chooseFile(event.dataTransfer.files[0]);
            }}
            onClick={() => inputRef.current?.click()}
          >
            {file ? (
              <>
                <FileVideo size={34} />
                <b>{file.name}</b>
                <span>{(file.size / 1024 / 1024).toFixed(1)} MB · Ready to analyze</span>
                <span className="change-file">Choose a different file</span>
              </>
            ) : (
              <>
                <span className="upload-icon">
                  <Upload size={23} />
                </span>
                <b>Drop your gameplay recording here</b>
                <span>MP4, MOV, or MKV · Up to 10 GB</span>
                <span className="button secondary">Browse files</span>
              </>
            )}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="video/*"
            hidden
            onChange={(event) => chooseFile(event.target.files?.[0])}
          />
          {file && (
            <div className="file-info">
              <span>
                <Video size={16} />
                Video selected
              </span>
              <span>Metadata is checked before processing</span>
              <button type="button" aria-label="Remove selected video" onClick={removeFile}>
                <X size={14} />
              </button>
            </div>
          )}
          <div className="form-section">
            <h3>Creative direction</h3>
            <label>
              Game profile
              <select value={game} onChange={(event) => setGame(event.target.value)}>
                <option value="auto">Auto-detect</option>
                <option value="tlou">The Last of Us</option>
                <option value="gta6">GTA VI</option>
                <option value="cyberpunk">Cyberpunk</option>
              </select>
            </label>
            <div className="field-row">
              <label>
                Layout
                <select value={layout} onChange={(event) => setLayout(event.target.value)}>
                  <option value="auto">Adaptive</option>
                  <option value="single">Single focus</option>
                  <option value="dialogue">Dialogue</option>
                  <option value="split">Split screen</option>
                </select>
              </label>
            </div>
          </div>
        </section>
        <aside className="settings-card">
          <h2>Clip settings</h2>
          <label>Number of clips</label>
          <div className="segmented" role="group" aria-label="Number of clips">
            {[3, 5, 10, 15].map((count) => (
              <button
                key={count}
                type="button"
                className={clips === count ? 'selected' : ''}
                aria-pressed={clips === count}
                onClick={() => setClips(count)}
              >
                {count}
              </button>
            ))}
          </div>
          <div className="switch-row">
            <div>
              <b>Review before rendering</b>
              <span>Choose the highlights you want to export.</span>
            </div>
            <button
              type="button"
              className={`switch ${review ? 'on' : ''}`}
              role="switch"
              aria-checked={review}
              aria-label="Review before rendering"
              onClick={() => setReview((value) => !value)}
            >
              <i />
            </button>
          </div>
          <div className="estimate">
            <Clock3 size={17} />
            <span>
              Estimated processing time<strong>4–8 minutes</strong>
            </span>
          </div>
          <Button className="generate-button" disabled={submitting} onClick={submit}>
            {submitting ? (
              <>
                <span className="spinner" />
                Uploading video…
              </>
            ) : (
              <>
                {review ? 'Find highlights' : 'Generate clips'} <Sparkles size={17} />
              </>
            )}
          </Button>
          {error && (
            <ErrorNotice
              title="We couldn’t start this project"
              detail={error}
              onRetry={submit}
              onDismiss={() => setError('')}
            />
          )}
        </aside>
      </div>
    </PageShell>
  );
}

function Processing({
  job,
  onComplete,
  onRetry,
}: {
  job: Job;
  onComplete: () => void;
  onRetry: () => Promise<void>;
}) {
  const current = Math.max(0, stages.indexOf(job.stage));
  const [retryError, setRetryError] = useState('');
  useEffect(() => {
    if (job.status === 'completed') onComplete();
  }, [job.status, onComplete]);
  const cancel = async () => {
    await fetch(`${api}/jobs/${job.id}/cancel`, { method: 'POST' });
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
  };
  const retry = async () => {
    setRetryError('');
    try {
      await onRetry();
    } catch (reason) {
      setRetryError(reason instanceof Error ? reason.message : 'The project could not be resumed.');
    }
  };
  return (
    <PageShell
      eyebrow="Processing"
      title={job.status === 'failed' ? 'This project needs attention.' : 'Your editor is at work.'}
    >
      <div className="process-layout">
        <section className="process-card">
          <div className="progress-visual">
            <div
              className="progress-ring"
              aria-label={`${job.progress}% complete`}
              style={{ '--progress': `${job.progress * 3.6}deg` } as CSSProperties}
            >
              <b>{job.progress}%</b>
            </div>
            <span>{job.status === 'failed' ? 'Processing paused' : job.stage}</span>
          </div>
          <div className="stages">
            {stages.map((stage, index) => (
              <div
                className={
                  index < current || job.status === 'completed'
                    ? 'done'
                    : index === current
                      ? 'current'
                      : ''
                }
                key={stage}
              >
                <i>{index < current || job.status === 'completed' ? '✓' : index + 1}</i>
                <span>{stage}</span>
              </div>
            ))}
          </div>
          {job.status === 'failed' && (
            <ErrorNotice
              title="The AI editor stopped before finishing"
              detail={
                job.error ||
                'Your source video may be unsupported or a local dependency needs attention.'
              }
              onRetry={() => void retry()}
            />
          )}
          {retryError && <ErrorNotice title="Couldn’t resume this project" detail={retryError} />}
        </section>
        <aside className="log-card">
          <div>
            <h3>Live activity</h3>
            <span className={job.status === 'processing' ? 'live-dot' : 'muted'}>
              {job.status === 'processing' ? 'Live' : job.status}
            </span>
          </div>
          <div className="logs" aria-live="polite">
            {job.logs.length ? (
              job.logs.slice(-10).map((line, index) => (
                <p key={`${index}-${line}`}>
                  <span>›</span>
                  {line}
                </p>
              ))
            ) : (
              <p>Preparing your project. Activity will appear here.</p>
            )}
          </div>
          <Button variant="secondary" disabled={job.status !== 'processing'} onClick={cancel}>
            Cancel processing
          </Button>
        </aside>
      </div>
    </PageShell>
  );
}

function Review({
  jobs,
  jobId,
  setPage,
  onRender,
}: {
  jobs: Job[];
  jobId?: string;
  setPage: (page: Page) => void;
  onRender: (job: Job, selectedIndices: number[]) => Promise<void>;
}) {
  const job = jobId
    ? jobs.find((item) => item.id === jobId)
    : jobs.find((item) => item.status === 'completed' && item.result?.highlights?.length);
  const highlights = job?.result?.highlights ?? [];
  const shorts = job?.result?.shorts ?? [];
  const canRenderSelection = Boolean(job?.options.review_only && !shorts.length);
  const [selected, setSelected] = useState<number[]>([]);
  useEffect(() => {
    setSelected(highlights.map((_, index) => index));
  }, [job?.id, highlights.length]);
  if (!job || !highlights.length)
    return (
      <PageShell eyebrow="Review" title="Choose your best moments">
        <p className="page-description">AI-ranked candidates, ready for your creative direction.</p>
        <EmptyState
          icon={Layers3}
          title="No highlights ready for review"
          description="Run a project in review mode to choose exactly which moments to render."
          action="Generate a project"
          onAction={() => setPage('generate')}
        />
      </PageShell>
    );
  return (
    <PageShell
      eyebrow="Review"
      title="Choose your best moments"
      action={
        canRenderSelection ? (
          <Button disabled={!selected.length} onClick={() => void onRender(job!, selected)}>
            Render {selected.length} selected <Sparkles size={16} />
          </Button>
        ) : undefined
      }
    >
      <p className="page-description">
        AI-ranked candidates from <b>{titleFromFile(job.filename)}</b>. You stay in control of the
        final cut.
      </p>
      <div className="review-summary">
        <span className="thumb large">
          <Play size={23} />
        </span>
        <div>
          <b>{job.filename}</b>
          <span>{highlights.length} highlights detected · Ranked by gameplay intelligence</span>
        </div>
        <div className="summary-score">
          <b>
            {Math.round(
              highlights.reduce((sum, item) => sum + (item.overall_score ?? item.score ?? 0), 0) /
                highlights.length,
            )}
          </b>
          <span>Avg. score</span>
        </div>
      </div>
      <div className="highlight-grid">
        {highlights.map((highlight, index) => {
          const score = highlight.overall_score ?? highlight.score ?? 0;
          const checked = selected.includes(index);
          return (
            <article
              className={`highlight-card ${checked ? 'checked' : ''}`}
              key={`${highlight.start_time}-${index}`}
            >
              <button
                type="button"
                className="check"
                aria-label={`${checked ? 'Remove' : 'Add'} highlight ${index + 1}`}
                aria-pressed={checked}
                onClick={() =>
                  setSelected((current) =>
                    checked ? current.filter((item) => item !== index) : [...current, index],
                  )
                }
              >
                {checked ? '✓' : ''}
              </button>
              <div className="highlight-preview">
                <Play size={21} />
                <span>
                  {formatSeconds(highlight.start_time)} – {formatSeconds(highlight.end_time)}
                </span>
              </div>
              <div className="highlight-content">
                <div>
                  <span className="rank">#{index + 1} highlight</span>
                  <b className="score">
                    {score}
                    <small>/100</small>
                  </b>
                </div>
                <h3>{highlight.hook_sentence || 'A moment worth replaying'}</h3>
                <p>
                  {highlight.reason_selected ||
                    highlight.virality_reason ||
                    'Strong gameplay moment identified by the AI.'}
                </p>
                <div className="score-bars">
                  {[
                    ['Gameplay', highlight.gameplay_score],
                    ['Emotion', highlight.emotion_score],
                    ['Action', highlight.action_score],
                  ].map(([label, value]) => (
                    <span key={String(label)}>
                      {label}
                      <i>
                        <b style={{ width: `${Number(value ?? score)}%` }} />
                      </i>
                    </span>
                  ))}
                </div>
              </div>
            </article>
          );
        })}
      </div>
      {shorts.length > 0 && (
        <section className="rendered-clips" aria-label="Rendered clips">
          <div className="section-heading">
            <div>
              <h2>Rendered clips</h2>
              <p>Ready to preview or save from your browser.</p>
            </div>
          </div>
          <div className="highlight-grid">
            {shorts.map((clip, index) => {
              const url = clipFileUrl(clip.clip_url);
              return (
                <article className="highlight-card" key={`${clip.clip_url}-${index}`}>
                  {url ? (
                    <video className="clip-video" controls preload="metadata" src={url} />
                  ) : (
                    <div className="highlight-preview">This clip could not be rendered.</div>
                  )}
                  <div className="highlight-content">
                    <h3>{clip.title || `Clip ${index + 1}`}</h3>
                    <p>
                      {formatSeconds(clip.start_time)} – {formatSeconds(clip.end_time)}
                    </p>
                    {url && (
                      <a className="button secondary" href={url} download>
                        Save clip
                      </a>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}
    </PageShell>
  );
}

function ProjectsTable({
  type,
  jobs,
  isLoading,
  setPage,
  onOpenJob,
}: {
  type: 'history' | 'projects';
  jobs: Job[];
  isLoading: boolean;
  setPage: (page: Page) => void;
  onOpenJob: (job: Job) => void;
}) {
  const [search, setSearch] = useState('');
  const [latest, setLatest] = useState(true);
  const filtered = useMemo(
    () =>
      jobs
        .filter((job) => titleFromFile(job.filename).toLowerCase().includes(search.toLowerCase()))
        .sort((a, b) =>
          latest
            ? b.created_at.localeCompare(a.created_at)
            : a.created_at.localeCompare(b.created_at),
        ),
    [jobs, search, latest],
  );
  const isHistory = type === 'history';
  return (
    <PageShell
      eyebrow={isHistory ? 'Archive' : 'Workspace'}
      title={isHistory ? 'Processing history' : 'Projects'}
      action={
        !isHistory ? (
          <Button onClick={() => setPage('generate')}>
            <Plus size={17} />
            New project
          </Button>
        ) : undefined
      }
    >
      <p className="page-description">
        {isHistory
          ? 'A complete record of your local AI processing activity.'
          : 'Every upload is saved as a project, ready to revisit.'}
      </p>
      <div className="toolbar">
        <label className="search">
          <Search size={17} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search projects"
            aria-label="Search projects"
          />
        </label>
        <Button variant="secondary" onClick={() => setLatest((value) => !value)}>
          {latest ? 'Latest first' : 'Oldest first'}
        </Button>
      </div>
      <section className="table-card">
        <div className="table-head">
          <span>PROJECT</span>
          <span>STATUS</span>
          <span>CLIPS</span>
          <span>CREATED</span>
          <span />
        </div>
        {isLoading ? (
          <LoadingRows />
        ) : filtered.length ? (
          filtered.map((job) => <ProjectRow key={job.id} job={job} onOpen={() => onOpenJob(job)} />)
        ) : (
          <EmptyState
            icon={isHistory ? Clock3 : FolderKanban}
            title={
              search
                ? 'No matching projects'
                : isHistory
                  ? 'No processing history yet'
                  : 'No projects yet'
            }
            description={
              search
                ? 'Try another project name or clear your search.'
                : isHistory
                  ? 'Your uploads and processing runs will be recorded here.'
                  : 'Create a project to save a gameplay session and its clips.'
            }
            action={search ? 'Clear search' : 'Create a project'}
            onAction={() => (search ? setSearch('') : setPage('generate'))}
          />
        )}
      </section>
    </PageShell>
  );
}

function SettingsPage({
  defaults,
  onSave,
}: {
  defaults: ProjectDefaults;
  onSave: (value: ProjectDefaults) => void;
}) {
  return (
    <PageShell eyebrow="Workspace" title="Settings">
      <div className="settings-layout">
        <section className="settings-panel">
          <h2>General preferences</h2>
          <p>
            Set defaults for new projects. They are saved in this browser and can be changed before
            processing.
          </p>
          <label>
            Default game profile
            <select
              value={defaults.game}
              onChange={(event) => onSave({ ...defaults, game: event.target.value })}
            >
              <option value="auto">Auto-detect</option>
              <option value="tlou">The Last of Us</option>
              <option value="gta6">GTA VI</option>
              <option value="cyberpunk">Cyberpunk</option>
            </select>
          </label>
          <label>
            Default layout
            <select
              value={defaults.layout}
              onChange={(event) => onSave({ ...defaults, layout: event.target.value })}
            >
              <option value="auto">Adaptive</option>
              <option value="single">Single focus</option>
              <option value="dialogue">Dialogue</option>
              <option value="split">Split screen</option>
            </select>
          </label>
        </section>
      </div>
    </PageShell>
  );
}

function Help() {
  return (
    <PageShell eyebrow="Support" title="How can we help?">
      <p className="page-description">
        Clear, local-first guidance for every stage of your workflow.
      </p>
      <section className="settings-panel">
        <h2>Workflow</h2>
        <p>
          Upload a supported gameplay video, choose the number of clips, then start processing. Use
          review mode to select candidates before rendering; otherwise completed clips appear in
          Review for preview and saving.
        </p>
        <h2>Troubleshooting</h2>
        <p>
          Start the API before opening the web app. If processing fails, check that the engine paths
          in <code>.env</code> point to an installed engine and Python environment, then resume the
          project from its processing screen.
        </p>
      </section>
    </PageShell>
  );
}

function App() {
  const [page, setPage] = useState<Page>('dashboard');
  const [activeJob, setActiveJob] = useState<Job>();
  const [reviewJobId, setReviewJobId] = useState<string>();
  const [defaults, setDefaults] = useState<ProjectDefaults>(loadProjectDefaults);
  const { data: jobs = [], isError, isLoading, refetch } = useJobs();
  const liveJob = activeJob
    ? (jobs.find((job) => job.id === activeJob.id) ?? activeJob)
    : undefined;
  const showReview = useCallback(() => {
    setReviewJobId(activeJob?.id);
    setPage('review');
  }, [activeJob?.id]);
  const openProject = useCallback((job: Job) => {
    if (job.status === 'completed') {
      setReviewJobId(job.id);
      setActiveJob(undefined);
      setPage('review');
      return;
    }
    setActiveJob(job);
    setPage('history');
  }, []);
  const saveDefaults = useCallback((value: ProjectDefaults) => {
    localStorage.setItem(settingsKey, JSON.stringify(value));
    setDefaults(value);
  }, []);
  const resumeProject = useCallback(async (job: Job) => {
    const response = await fetch(`${api}/jobs/${job.id}/resume`, { method: 'POST' });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail ?? 'The project could not be resumed.');
    }
    setActiveJob(await response.json());
    await queryClient.invalidateQueries({ queryKey: ['jobs'] });
  }, []);
  const renderSelection = useCallback(async (job: Job, selectedIndices: number[]) => {
    const response = await fetch(`${api}/jobs/${job.id}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_indices: selectedIndices }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail ?? 'Selected clips could not be rendered.');
    }
    setActiveJob(await response.json());
    await queryClient.invalidateQueries({ queryKey: ['jobs'] });
  }, []);
  const content =
    liveJob && ['queued', 'processing', 'failed'].includes(liveJob.status) ? (
      <Processing job={liveJob} onComplete={showReview} onRetry={() => resumeProject(liveJob)} />
    ) : (
      (() => {
        switch (page) {
          case 'dashboard':
            return (
              <Dashboard
                jobs={jobs}
                isLoading={isLoading}
                setPage={setPage}
                onOpenJob={openProject}
              />
            );
          case 'generate':
            return <Generate defaults={defaults} onJob={(job) => setActiveJob(job)} />;
          case 'review':
            return (
              <Review
                jobs={jobs}
                jobId={reviewJobId}
                setPage={setPage}
                onRender={renderSelection}
              />
            );
          case 'history':
            return (
              <ProjectsTable
                type="history"
                jobs={jobs}
                isLoading={isLoading}
                setPage={setPage}
                onOpenJob={openProject}
              />
            );
          case 'projects':
            return (
              <ProjectsTable
                type="projects"
                jobs={jobs}
                isLoading={isLoading}
                setPage={setPage}
                onOpenJob={openProject}
              />
            );
          case 'settings':
            return <SettingsPage defaults={defaults} onSave={saveDefaults} />;
          default:
            return <Help />;
        }
      })()
    );
  return (
    <div className="app">
      <Sidebar page={page} setPage={setPage} />
      <div className="content">
        {isError && (
          <div className="api-warning" role="alert">
            <b>Local service is offline.</b>
            <span>Start the API, then reconnect.</span>
            <Button variant="secondary" onClick={() => refetch()}>
              <RefreshCw size={14} />
              Reconnect
            </Button>
          </div>
        )}
        {content}
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
