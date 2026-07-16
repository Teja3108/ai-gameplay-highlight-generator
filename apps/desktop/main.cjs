const { app, BrowserWindow } = require('electron');
const { createServer } = require('node:http');
const { spawn } = require('node:child_process');
const { existsSync, mkdirSync, readFileSync } = require('node:fs');
const { extname, join, normalize, resolve } = require('node:path');

const API_PORT = 8000;
const WEB_PORT = 5173;
let mainWindow;
let apiProcess;
let webServer;
let isQuitting = false;
let apiRestartTimer;
let apiRestartAttempts = 0;
let shouldRestartApi = false;

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
};

function runtimePaths() {
  const root = app.isPackaged
    ? join(process.resourcesPath, 'runtime')
    : join(__dirname, '..', '..', '.release-staging', 'runtime');
  return {
    apiRoot: join(root, 'api'),
    apiPython: join(root, 'api-python', 'bin', 'python3.12'),
    engineRoot: join(root, 'engine'),
    enginePython: join(root, 'engine-python', 'bin', 'python3.12'),
    webRoot: app.isPackaged
      ? join(process.resourcesPath, 'web')
      : join(__dirname, '..', 'web', 'dist'),
  };
}

function splash(message) {
  return `data:text/html;charset=UTF-8,${encodeURIComponent(`<!doctype html><html><head><meta charset="utf-8"><title>AI Gameplay Shorts Generator</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b0c10;color:#f2f1f6;font:14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.card{text-align:center}.mark{display:grid;width:48px;height:48px;margin:0 auto 18px;place-items:center;background:linear-gradient(135deg,#a78bfa,#6354e9);border-radius:14px;font-size:22px;box-shadow:0 8px 30px #7258ff55}h1{margin:0;font-size:21px;letter-spacing:-.6px}p{margin:10px 0 0;color:#aaa8b3;font-size:12px}small{display:block;margin-top:28px;color:#747580;font-size:10px;letter-spacing:.07em}</style></head><body><main class="card"><div class="mark">✦</div><h1>AI Gameplay Shorts Generator</h1><p>${message}</p><small>DEVELOPED BY TEJA GOUD · BUILT FOR SENPAI PLAYS</small></main></body></html>`)}`;
}

function assertRuntime(paths) {
  const required = [
    paths.apiRoot,
    paths.apiPython,
    paths.engineRoot,
    paths.enginePython,
    join(paths.engineRoot, 'main.py'),
    paths.webRoot,
  ];
  const missing = required.filter((item) => !existsSync(item));
  if (missing.length)
    throw new Error('The installed runtime is incomplete. Reinstall the application.');
}

function startWebServer(webRoot) {
  webServer = createServer((request, response) => {
    const requestPath = new URL(request.url || '/', `http://127.0.0.1:${WEB_PORT}`).pathname;
    const relativePath =
      requestPath === '/' ? 'index.html' : decodeURIComponent(requestPath).replace(/^\/+/, '');
    const filePath = resolve(webRoot, relativePath);
    if (
      !filePath.startsWith(`${resolve(webRoot)}/`) &&
      filePath !== join(resolve(webRoot), 'index.html')
    ) {
      response.writeHead(403).end();
      return;
    }
    try {
      const body = readFileSync(filePath);
      response.writeHead(200, {
        'Content-Type': contentTypes[extname(filePath)] || 'application/octet-stream',
      });
      response.end(body);
    } catch {
      response.writeHead(404).end();
    }
  });
  return new Promise((resolveServer, reject) => {
    webServer.once('error', reject);
    webServer.listen(WEB_PORT, '127.0.0.1', resolveServer);
  });
}

function waitForApi() {
  return new Promise((resolveApi, reject) => {
    let attempts = 0;
    const poll = async () => {
      try {
        const response = await fetch(`http://127.0.0.1:${API_PORT}/api/health`);
        if (response.ok) return resolveApi();
      } catch {
        // The API is still starting.
      }
      attempts += 1;
      if (attempts >= 80) return reject(new Error('The local service did not start.'));
      setTimeout(poll, 250);
    };
    void poll();
  });
}

function startApi(paths) {
  const userData = join(app.getPath('userData'), 'data');
  mkdirSync(userData, { recursive: true });
  apiProcess = spawn(
    paths.apiPython,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(API_PORT)],
    {
      cwd: paths.apiRoot,
      env: {
        ...process.env,
        ALLOWED_HOSTS: 'localhost,127.0.0.1',
        CORS_ALLOW_ORIGINS: `http://127.0.0.1:${WEB_PORT}`,
        GAMEPLAY_DATA_DIR: userData,
        GAMEPLAY_ENGINE_ROOT: paths.engineRoot,
        GAMEPLAY_ENGINE_PYTHON: paths.enginePython,
        GAMEPLAY_ENGINE_OUTPUT_DIR: join(userData, 'engine-output'),
        STORAGE_ROOT: join(userData, 'storage'),
        DATABASE_URL: `sqlite:///${join(userData, 'gameplay.db')}`,
        TEMP_DIRECTORY: join(userData, 'tmp'),
        MODEL_CACHE_PATH: join(userData, 'models'),
        OUTPUT_DIRECTORY: join(userData, 'output'),
      },
      stdio: 'ignore',
    },
  );
  apiProcess.once('error', (error) => {
    console.error('Unable to start the bundled API:', error);
  });
  apiProcess.once('exit', () => {
    apiProcess = undefined;
    if (!isQuitting && shouldRestartApi) scheduleApiRestart(paths);
  });
}

function scheduleApiRestart(paths) {
  if (apiRestartTimer || apiRestartAttempts >= 3) return;
  const delay = 1_000 * 2 ** apiRestartAttempts;
  apiRestartAttempts += 1;
  apiRestartTimer = setTimeout(() => {
    apiRestartTimer = undefined;
    if (!isQuitting && !apiProcess) startApi(paths);
  }, delay);
}

function stopServices() {
  if (apiRestartTimer) {
    clearTimeout(apiRestartTimer);
    apiRestartTimer = undefined;
  }
  if (webServer) {
    webServer.close();
    webServer = undefined;
  }
  if (apiProcess && !apiProcess.killed) {
    apiProcess.kill('SIGTERM');
    apiProcess = undefined;
  }
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 960,
    minHeight: 680,
    show: true,
    backgroundColor: '#0b0c10',
    title: 'AI Gameplay Shorts Generator',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: join(__dirname, 'preload.cjs'),
    },
  });
  await mainWindow.loadURL(splash('Preparing your local creative workspace…'));
  try {
    const paths = runtimePaths();
    assertRuntime(paths);
    shouldRestartApi = true;
    startApi(paths);
    await waitForApi();
    apiRestartAttempts = 0;
    await startWebServer(paths.webRoot);
    await mainWindow.loadURL(`http://127.0.0.1:${WEB_PORT}`);
  } catch (error) {
    shouldRestartApi = false;
    stopServices();
    await mainWindow.loadURL(
      splash(error instanceof Error ? error.message : 'The application could not start.'),
    );
  }
}

const hasSingleInstanceLock = app.requestSingleInstanceLock();
if (!hasSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!mainWindow) return;
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  });
}

if (hasSingleInstanceLock) {
  app.whenReady().then(() => {
    void createWindow();
  });
}
app.on('before-quit', () => {
  if (isQuitting) return;
  isQuitting = true;
  shouldRestartApi = false;
  stopServices();
});
app.on('window-all-closed', () => app.quit());
