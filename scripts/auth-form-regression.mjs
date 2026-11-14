// Optional browser QA using .local/browser-qa. Only mocked authentication is used.
import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const workspace = fileURLToPath(new URL('../', import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH ??= resolve(workspace, '.local/browsers');
const { chromium } = await import('../.local/browser-qa/node_modules/playwright/index.mjs');
const base = process.env.QA_BASE_URL ?? 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const sensitiveKeys = ['name', 'email', 'password', 'phone', 'consent'];
const sample = { name: 'Form regression', email: 'form-regression@example.test', password: 'Only-a-test-value-123' };
const csrf = 'form-regression-csrf';

function observeCredentialQueries(context) {
  const leaks = [];
  context.on('request', (request) => {
    if (request.method() === 'GET' && sensitiveKeys.some((key) => new URL(request.url()).searchParams.has(key))) leaks.push(new URL(request.url()).pathname);
  });
  return leaks;
}

try {
  for (const path of ['/login', '/registo']) {
    const context = await browser.newContext({ javaScriptEnabled: false });
    const leaks = observeCredentialQueries(context);
    const page = await context.newPage();
    await page.goto(`${base}${path}`);
    const form = page.locator('.auth-form-card form');
    await form.waitFor();
    assert.equal(await form.getAttribute('method'), 'post');
    assert.equal(await form.getAttribute('action'), path);
    assert.equal(await form.locator('input[type="password"]').isDisabled(), true);
    assert.equal(await form.locator('button[type="submit"]').isDisabled(), true);
    assert.equal(await form.locator('noscript').isVisible(), true);
    await page.keyboard.press('Enter');
    assert.equal(new URL(page.url()).pathname, path);
    assert.equal(new URL(page.url()).search, '');

    // Even if browser autofill or a future change bypasses the hydration gate,
    // native submission must use a POST body and a clean URL.
    await page.route(`**${path}`, (route) => route.request().method() === 'POST' ? route.fulfill({ status: 200, contentType: 'text/plain', body: 'Native POST captured by regression test.' }) : route.continue());
    await form.evaluate((element) => {
      element.querySelector('fieldset').disabled = false;
      element.querySelector('button[type="submit"]').disabled = false;
    });
    if (path === '/registo') await form.locator('input[name="name"]').fill(sample.name);
    await form.locator('input[name="email"]').fill(sample.email);
    await form.locator('input[name="password"]').fill(sample.password);
    if (path === '/registo') await form.locator('input[name="consent"]').check();
    const nativeSubmission = page.waitForRequest((request) => request.isNavigationRequest() && request.method() === 'POST');
    await form.locator('button[type="submit"]').click();
    const request = await nativeSubmission;
    assert.equal(new URL(request.url()).search, '');
    assert.equal(new URLSearchParams(request.postData()).get('password'), sample.password);
    assert.deepEqual(leaks, []);
    console.log(`PASS ${path}: JavaScript disabled blocks input; fallback uses POST without credentials in URL`);
    await context.close();
  }

  for (const path of ['/login', '/registo']) {
    const context = await browser.newContext();
    const leaks = observeCredentialQueries(context);
    const page = await context.newPage();
    let authenticated = false;
    let submissions = 0;
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await context.route('**/api/v1/**', async (route) => {
      const request = route.request();
      const endpoint = new URL(request.url()).pathname;
      const user = { id: 'form-regression-user', name: sample.name, email: sample.email, phone: '', role: 'customer', is_demo: true };
      if (endpoint === '/api/v1/auth/session') return route.fulfill({ json: { user: authenticated ? user : null }, headers: { 'set-cookie': `csrf_token=${csrf}; Path=/; SameSite=Lax` } });
      if (endpoint === '/api/v1/auth/refresh') return route.fulfill({ status: 401, json: { detail: 'No test session.' } });
      if (endpoint === `/api/v1/auth/${path === '/registo' ? 'register' : 'login'}`) {
        submissions++;
        assert.equal(request.method(), 'POST');
        assert.equal(request.headers()['content-type'], 'application/json');
        assert.equal(request.headers()['x-csrf-token'], csrf);
        assert.equal(new URL(request.url()).search, '');
        const payload = request.postDataJSON();
        assert.equal(payload.email, sample.email);
        assert.equal(payload.password, path === '/registo' ? sample.password : 'short');
        authenticated = true;
        return route.fulfill({ json: { user } });
      }
      if (endpoint === '/api/v1/cart') return route.fulfill({ json: { items: [] } });
      if (endpoint === '/api/v1/me/addresses') return route.fulfill({ json: [] });
      return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked endpoint.' } });
    });
    await page.goto(`${base}${path}`);
    const form = page.locator('.auth-form-card form');
    await page.waitForFunction(() => !document.querySelector('.auth-form-card fieldset')?.disabled);
    if (path === '/registo') await form.locator('input[name="name"]').fill(sample.name);
    await form.locator('input[name="email"]').fill(sample.email);
    if (path === '/registo') {
      await form.locator('input[name="password"]').fill('too-short');
      await form.locator('input[name="consent"]').check();
      await form.locator('button[type="submit"]').click();
      assert.equal(await form.locator('input[name="password"]').evaluate((element) => element.validity.tooShort), true);
      assert.equal(submissions, 0);
    }
    await form.locator('input[name="password"]').fill(path === '/registo' ? sample.password : 'short');
    await form.locator('button[type="submit"]').click();
    await page.waitForURL('**/conta');
    await page.locator('.session-bar').waitFor();
    assert.equal(submissions, 1);
    assert.deepEqual(leaks, []);
    assert.deepEqual(errors, []);
    console.log(`PASS ${path}: hydrated form sends JSON POST with CSRF and opens account`);
    await context.close();
  }
} finally {
  await browser.close();
}
