import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';

const root = resolve(new URL('..', import.meta.url).pathname);
const stage = join(root, '.release-staging');
const runtime = join(stage, 'runtime');

function run(command, args, options = {}) {
  execFileSync(command, args, { cwd: root, stdio: 'inherit', ...options });
}

function configuredEngineRoot() {
  if (process.env.RELEASE_ENGINE_ROOT || process.env.GAMEPLAY_ENGINE_ROOT) {
    return resolve(process.env.RELEASE_ENGINE_ROOT || process.env.GAMEPLAY_ENGINE_ROOT);
  }
  const envPath = join(root, '.env');
  if (existsSync(envPath)) {
    const line = readFileSync(envPath, 'utf8')
      .split(/\r?\n/)
      .find((item) => item.startsWith('GAMEPLAY_ENGINE_ROOT='));
    if (line) return resolve(line.slice('GAMEPLAY_ENGINE_ROOT='.length).trim());
  }
  throw new Error(
    'Set RELEASE_ENGINE_ROOT to the existing local AI engine before building a release.',
  );
}

function copy(source, destination, filter) {
  cpSync(source, destination, { dereference: true, recursive: true, filter });
}

function ignoredEnginePath(source) {
  return [
    '.DS_Store',
    '.env',
    '.git',
    'output',
    '__pycache__',
    '.venv',
    '.pytest_cache',
    '.ruff_cache',
    'tests',
  ].includes(basename(source));
}

rmSync(stage, { recursive: true, force: true });
mkdirSync(runtime, { recursive: true });
const engineRoot = configuredEngineRoot();
const engineVenv = join(engineRoot, '.venv');
if (!existsSync(join(engineRoot, 'main.py')) || !existsSync(join(engineVenv, 'lib'))) {
  throw new Error(`AI engine is incomplete: ${engineRoot}`);
}

run('uv', ['python', 'install', '3.12', '--preview', '--no-progress']);
const managedPython = execFileSync('uv', ['python', 'find', '--managed-python', '3.12'], {
  cwd: root,
  encoding: 'utf8',
}).trim();
const pythonRoot = dirname(dirname(managedPython));
const apiPythonRoot = join(runtime, 'api-python');
const enginePythonRoot = join(runtime, 'engine-python');
copy(pythonRoot, apiPythonRoot);
copy(pythonRoot, enginePythonRoot);
const bundledApiPython = join(apiPythonRoot, 'bin', basename(managedPython));

copy(engineRoot, join(runtime, 'engine'), (source) => !ignoredEnginePath(source));
copy(
  join(engineVenv, 'lib', 'python3.12', 'site-packages'),
  join(enginePythonRoot, 'lib', 'python3.12', 'site-packages'),
  (source) => basename(source) !== '__pycache__',
);

copy(
  join(root, 'apps', 'api'),
  join(runtime, 'api'),
  (source) =>
    !['.venv', 'data', '__pycache__', '.pytest_cache', '.ruff_cache', 'tests'].includes(
      basename(source),
    ),
);
run(
  'uv',
  [
    'sync',
    '--project',
    join(runtime, 'api'),
    '--no-dev',
    '--python',
    bundledApiPython,
    '--link-mode',
    'copy',
  ],
  {
    env: process.env,
  },
);
copy(
  join(runtime, 'api', '.venv', 'lib', 'python3.12', 'site-packages'),
  join(apiPythonRoot, 'lib', 'python3.12', 'site-packages'),
  (source) => basename(source) !== '__pycache__',
);
rmSync(join(runtime, 'api', '.venv'), { recursive: true, force: true });
console.log(`Prepared bundled runtime from ${engineRoot}`);
