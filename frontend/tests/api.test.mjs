import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

// Run the actual browser API adapter without a DOM runner or a live server.
const source = await readFile(new URL('../src/lib/api.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { api, apiBlob, ApiError, createIdempotencyKey, money, date, requestedDate } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const originalFetch = globalThis.fetch;
const originalCrypto = Object.getOwnPropertyDescriptor(globalThis, 'crypto');

function setCrypto(value) { Object.defineProperty(globalThis, 'crypto', { configurable: true, value }); }
test.after(() => { globalThis.fetch = originalFetch; delete globalThis.document; });
test.afterEach(() => { if (originalCrypto) Object.defineProperty(globalThis, 'crypto', originalCrypto); else delete globalThis.crypto; });
test.beforeEach(() => { globalThis.document = { cookie: 'csrf_token=test-csrf-token' }; });

test('formats decimal API amounts and consultation prices in meticais', () => {
  assert.equal(money('1234.50').replaceAll(/\s/g, ''), '1234,50MT');
  assert.equal(money('0.00').replaceAll(/\s/g, ''), '0,00MT');
  assert.equal(money(null), 'Sob consulta');
});

test('presents UTC timestamps in Maputo and sends intended service dates with a timezone', () => {
  assert.equal(date('2026-08-03T22:30:00Z'), '04/08/2026');
  assert.equal(requestedDate('2026-08-04'), '2026-08-04T00:00:00+02:00');
  assert.equal(requestedDate(null), null);
});

test('creates idempotency keys with the native cryptographic UUID method when available', () => {
  const expected = 'e102788e-42d6-45c5-b9f0-990b29f060a7';
  const provider = {
    randomUUID() { assert.equal(this, provider); return expected; },
    getRandomValues() { assert.fail('Native UUID support must not use the fallback'); },
  };
  setCrypto(provider);
  assert.equal(createIdempotencyKey(), expected);
});

test('HTTP LAN fallback uses secure random bytes and preserves all 122 UUIDv4 random bits', () => {
  const keys = [];
  for (const fill of [0x00, 0xff, 0x73]) {
    const entropy = new Uint8Array(16).fill(fill);
    let secureCalls = 0;
    setCrypto({ getRandomValues(bytes) { assert.ok(bytes instanceof Uint8Array); assert.equal(bytes.length, 16); bytes.set(entropy); secureCalls++; return bytes; } });
    const key = createIdempotencyKey();
    assert.match(key, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    assert.equal(secureCalls, 1);
    const encoded = Buffer.from(key.replaceAll('-', ''), 'hex');
    for (let index = 0; index < 16; index++) {
      const randomMask = index === 6 ? 0x0f : index === 8 ? 0x3f : 0xff;
      assert.equal(encoded[index] & randomMask, entropy[index] & randomMask, `Random bits preserved in byte ${index}`);
    }
    keys.push(key);
  }
  assert.equal(new Set(keys).size, keys.length);
});

test('idempotency key generation fails clearly when no secure random source is available', () => {
  for (const provider of [undefined, {}]) {
    setCrypto(provider);
    assert.throws(() => createIdempotencyKey(), /recursos de segurança necessários/);
  }
});

test('sends authenticated reads without caching personal data', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/v1/orders');
    assert.equal(options.credentials, 'include');
    assert.equal(options.cache, 'no-store');
    return Response.json({ items: [] });
  };
  assert.deepEqual(await api('/orders'), { items: [] });
});

test('obtains a CSRF token before a first mutation and includes the token header', async () => {
  globalThis.document.cookie = '';
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push(url);
    if (url.endsWith('/session')) { globalThis.document.cookie = 'csrf_token=token%2Fvalue'; return Response.json({ user: null }); }
    assert.equal(options.headers.get('X-CSRF-Token'), 'token/value');
    assert.equal(options.headers.get('Content-Type'), 'application/json');
    return Response.json({ ok: true });
  };
  await api('/cart', { method: 'POST', body: JSON.stringify({ listing_id: 'example', quantity: 1 }) });
  assert.deepEqual(calls, ['/api/v1/auth/session', '/api/v1/cart']);
});

test('renews an expired access token once before retrying an authorised request', async () => {
  const calls = [];
  let reads = 0;
  globalThis.fetch = async (url) => {
    calls.push(url);
    if (url.endsWith('/refresh')) return Response.json({ user: {} });
    return ++reads === 1 ? Response.json({ detail: 'expired' }, { status: 401 }) : Response.json({ id: 'customer' });
  };
  assert.deepEqual(await api('/me'), { id: 'customer' });
  assert.deepEqual(calls, ['/api/v1/me', '/api/v1/auth/refresh', '/api/v1/me']);
});

test('coalesces concurrent refresh requests to avoid rotating the same token twice', async () => {
  const reads = new Map();
  let renewals = 0;
  globalThis.fetch = async (url) => {
    if (url.endsWith('/refresh')) { renewals++; await Promise.resolve(); return Response.json({}); }
    reads.set(url, (reads.get(url) ?? 0) + 1);
    return reads.get(url) === 1 ? Response.json({}, { status: 401 }) : Response.json({ ok: true });
  };
  await Promise.all([api('/orders'), api('/cart')]);
  assert.equal(renewals, 1);
});

test('does not retry a wrong login password through refresh', async () => {
  let calls = 0;
  globalThis.fetch = async () => { calls++; return Response.json({ detail: 'Credenciais inválidas' }, { status: 401 }); };
  await assert.rejects(() => api('/auth/login', { method: 'POST', body: '{}' }), (error) => error instanceof ApiError && error.status === 401);
  assert.equal(calls, 1);
});

test('exposes validation errors without replacing them with fabricated success', async () => {
  globalThis.fetch = async () => Response.json({ detail: [{ msg: 'Stock insuficiente' }] }, { status: 422 });
  await assert.rejects(() => api('/orders'), /Stock insuficiente/);
});

test('handles non-JSON service errors and empty successful responses', async () => {
  globalThis.fetch = async () => new Response('<html>unavailable</html>', { status: 502 });
  await assert.rejects(() => api('/products'), (error) => error instanceof ApiError && error.status === 502);
  globalThis.fetch = async () => new Response(null, { status: 204 });
  assert.equal(await api('/cart/item', { method: 'DELETE' }), undefined);
});

test('uploads attachments as multipart without overriding the browser boundary and sends CSRF', async () => {
  const body = new FormData();
  body.set('file', new Blob(['%PDF-test'], { type: 'application/pdf' }), 'recibo.pdf');
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/v1/support/ticket-id/attachments');
    assert.equal(options.body, body);
    assert.equal(options.headers.has('Content-Type'), false);
    assert.equal(options.headers.get('X-CSRF-Token'), 'test-csrf-token');
    assert.equal(options.credentials, 'include');
    assert.equal(options.cache, 'no-store');
    return Response.json({ id: 'attachment-id' }, { status: 201 });
  };
  assert.deepEqual(await api('/support/ticket-id/attachments', { method: 'POST', body }), { id: 'attachment-id' });
});

test('downloads private bytes through the authenticated proxy after refreshing an expired session', async () => {
  const calls = [];
  let reads = 0;
  globalThis.fetch = async (url, options) => {
    calls.push(url);
    assert.equal(options.credentials, 'include');
    assert.equal(options.cache, 'no-store');
    if (url.endsWith('/refresh')) return Response.json({});
    return ++reads === 1 ? Response.json({ detail: 'expired' }, { status: 401 }) : new Response('%PDF-private', { headers: { 'Content-Type': 'application/pdf' } });
  };
  const blob = await apiBlob('/attachments/attachment-id');
  assert.equal(await blob.text(), '%PDF-private');
  assert.equal(blob.type, 'application/pdf');
  assert.deepEqual(calls, ['/api/v1/attachments/attachment-id', '/api/v1/auth/refresh', '/api/v1/attachments/attachment-id']);
});

test('private download errors preserve permission and unavailable-storage messages', async () => {
  for (const [status, detail] of [[403, 'Acesso restrito.'], [503, 'Armazenamento privado indisponível.']]) {
    globalThis.fetch = async () => Response.json({ detail }, { status });
    await assert.rejects(() => apiBlob('/attachments/attachment-id'), (error) => error instanceof ApiError && error.status === status && error.message === detail);
  }
});
