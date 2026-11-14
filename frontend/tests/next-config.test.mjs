import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../next.config.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
let version = 0;
async function loadConfig(hosts) {
  const previous = process.env.DEV_ALLOWED_HOSTS;
  if (hosts === undefined) delete process.env.DEV_ALLOWED_HOSTS;
  else process.env.DEV_ALLOWED_HOSTS = hosts;
  try {
    return (await import(`data:text/javascript;base64,${Buffer.from(`${compiled}\n// ${++version}`).toString('base64')}`)).default;
  } finally {
    if (previous === undefined) delete process.env.DEV_ALLOWED_HOSTS;
    else process.env.DEV_ALLOWED_HOSTS = previous;
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
