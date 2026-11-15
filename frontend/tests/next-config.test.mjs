import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../next.config.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
let version = 0;
async function loadConfig(hosts, settings = {}) {
  const values = { DEV_ALLOWED_HOSTS: hosts, BACKEND_URL: undefined, VERCEL_ENV: undefined, VERCEL: undefined, ...settings };
  const previous = Object.fromEntries(Object.keys(values).map((key) => [key, process.env[key]]));
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  try {
    return (await import(`data:text/javascript;base64,${Buffer.from(`${compiled}\n// ${++version}`).toString('base64')}`)).default;
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

test('development origin allowlist includes the trusted loopback alias by default', async () => {
  assert.deepEqual((await loadConfig()).allowedDevOrigins, ['127.0.0.1']);
});

test('development hosts accept explicit LAN and DNS names without broadening access', async () => {
  assert.deepEqual((await loadConfig(' 192.168.50.20, Dev.Local,192.168.50.20,127.0.0.1, ')).allowedDevOrigins, ['127.0.0.1', '192.168.50.20', 'dev.local']);
});

test('development hosts reject wildcard, origin, port, path and ambiguous entries', async () => {
  for (const hosts of ['*', '*.example.com', 'https://dev.local', 'dev.local:3000', 'dev.local/path', 'dev.local?x=1', 'dev.local#test', 'user@dev.local', 'dev.local other.local']) {
    await assert.rejects(loadConfig(hosts), /DEV_ALLOWED_HOSTS/);
  }
});

test('local builds preserve the development API proxy without requiring cloud credentials', async () => {
  assert.deepEqual(await (await loadConfig()).rewrites(), [{ source: '/api/v1/:path*', destination: 'http://127.0.0.1:8000/api/v1/:path*' }]);
});

test('Vercel deployments require an explicit public HTTPS backend before the build', async () => {
  for (const VERCEL_ENV of ['production', 'preview']) {
    await assert.rejects(loadConfig(undefined, { VERCEL_ENV }), /BACKEND_URL/);
    for (const BACKEND_URL of ['http://api.example.com', 'https://localhost', 'https://127.0.0.1', 'https://[::1]']) {
      await assert.rejects(loadConfig(undefined, { VERCEL_ENV, BACKEND_URL }), /public HTTPS/);
    }
  }
  await assert.rejects(loadConfig(undefined, { VERCEL: '1' }), /BACKEND_URL/);
  const config = await loadConfig(undefined, { VERCEL_ENV: 'production', BACKEND_URL: 'https://deloya-api.vercel.app/' });
  assert.deepEqual(await config.rewrites(), [{ source: '/api/v1/:path*', destination: 'https://deloya-api.vercel.app/api/v1/:path*' }]);
});

test('backend proxy rejects credentials, paths, ambiguous URL syntax and query fragments', async () => {
  for (const BACKEND_URL of ['ftp://api.example.com', 'https://user:password@api.example.com', 'https://api.example.com/api/v1', 'https://api.example.com?x=1', 'https://api.example.com#fragment', ' https://api.example.com', 'https://api.example.com\\path', 'https://api.example.com?']) {
    await assert.rejects(loadConfig(undefined, { BACKEND_URL }), /BACKEND_URL/);
  }
});
