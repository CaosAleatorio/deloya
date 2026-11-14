// Optional browser QA: install Playwright in .local/browser-qa (see docs/TESTING.md).
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { randomBytes } from 'node:crypto';

const workspace = fileURLToPath(new URL('../', import.meta.url));
try { process.loadEnvFile(resolve(workspace, '.env')); } catch { /* Guest checks can run without seed credentials. */ }
process.env.PLAYWRIGHT_BROWSERS_PATH ??= resolve(workspace, '.local/browsers');
const { chromium } = await import('../.local/browser-qa/node_modules/playwright/index.mjs');
const base = process.env.QA_BASE_URL ?? 'http://localhost:3000';
const output = resolve(workspace, '.local/browser-results');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const errors = [];
const checks = [];
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'pt-MZ' });
const page = await context.newPage();
page.on('pageerror', (error) => errors.push(error.message));
page.on('response', (response) => { if (response.url().includes('/api/v1/') && response.status() >= 500) errors.push(`API HTTP ${response.status()}: ${new URL(response.url()).pathname}`); });
function passed(name) { checks.push(name); console.log(`PASS ${name}`); }
async function open(path) { const response = await page.goto(`${base}${path}`); assert.equal(response.status(), 200, path); }
async function noOverflow(target) { assert.equal(await target.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true, 'Horizontal overflow'); }
async function logout() { await page.getByRole('button', { name: 'Terminar sessão' }).click(); await page.locator('.session-bar').waitFor({ state: 'hidden' }); }
async function login(email, password) {
  await open('/login');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Palavra-passe', { exact: false }).fill(password);
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.waitForURL('**/conta');
  await page.locator('.session-bar').waitFor();
}
try {
  await open('/');
  await page.locator('.product-card').first().waitFor();
  assert.ok((await page.locator('.product-card').count()) > 0);
  await noOverflow(page);
  await page.screenshot({ path: resolve(output, 'home-desktop.png'), fullPage: true });
  passed('Home loads catalogue from PostgreSQL through the API proxy');

  if (!process.argv.includes('--panels-only')) {
  const products = await (await context.request.get(`${base}/api/v1/products?page_size=100`)).json();
  const first = products.items.find((item) => item.is_demo && item.stock > 2);
  const second = products.items.find((item) => item.is_demo && item.stock > 2 && item.store_id !== first?.store_id);
  assert.ok(first && second, 'Seed must provide in-stock demo products from two stores');
  await open(`/produtos?q=${encodeURIComponent(first.name)}`);
  await page.getByRole('heading', { name: first.name, exact: true }).waitFor();
  assert.equal(await page.locator('.product-card').count(), 1);
  passed('Product search returns the requested live listing');

  const password = `QA-${randomBytes(16).toString('hex')}!`;
  const email = `qa-${Date.now()}@demo.deloya.example.com`;
  await open('/registo');
  await page.getByLabel('Nome completo', { exact: true }).fill('Utilizador QA de teste');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Palavra-passe', { exact: false }).fill(password);
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Criar a minha conta', exact: true }).click();
  await page.waitForURL('**/conta');
  await page.locator('.session-bar').waitFor();
  passed('Registration creates an authenticated account using the visible form');

  for (const listing of [first, second]) {
    await open(`/produtos/${listing.slug}`);
    await page.getByRole('heading', { name: listing.name, exact: true }).waitFor();
    await page.getByRole('button', { name: 'Adicionar ao carrinho', exact: true }).click();
    await page.waitForURL('**/carrinho');
    await page.getByRole('heading', { name: listing.name, exact: true }).waitFor();
  }
  assert.equal(await page.locator('.cart-item').count(), 2);
  await page.getByRole('link', { name: 'Continuar para encomenda' }).click();
  await page.getByRole('heading', { name: 'Como pretende receber?', exact: true }).waitFor();
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Confirmar encomenda', exact: true }).click();
  await page.getByRole('button', { name: 'Iniciar pagamento de teste' }).waitFor();
  assert.ok((await page.getByText('PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO', { exact: true }).count()) > 0);
  await page.getByRole('button', { name: 'Iniciar pagamento de teste' }).click();
  await page.getByRole('button', { name: 'Testar sucesso', exact: true }).click();
  await page.getByText('Paga', { exact: true }).waitFor();
  passed('Two-store cart completes a visibly simulated checkout');

  await open('/conta/encomendas');
  await page.locator('.order-card').first().waitFor();
  assert.equal(await page.locator('.order-card').first().locator('.vendor-order').count(), 2);
  const orders = await (await context.request.get(`${base}/api/v1/orders`)).json();
  const receipt = await context.request.get(`${base}/api/v1/orders/${orders.items[0].id}/receipt.pdf`);
  assert.equal(receipt.status(), 200);
  assert.match(receipt.headers()['content-type'], /application\/pdf/);
  assert.equal((await receipt.body()).subarray(0, 4).toString(), '%PDF');
  assert.match(receipt.headers()['cache-control'], /no-store/);
  await page.screenshot({ path: resolve(output, 'orders-desktop.png'), fullPage: true });
  passed('Customer history shows both vendor suborders and downloads its private PDF');
  await logout();
  await login(email, password);
  passed('Logout and login work with the created account');
  await logout();

  }
  if (process.env.DEMO_PASSWORD) {
    await login('admin@demo.deloya.example.com', process.env.DEMO_PASSWORD);
    for (const route of ['dashboard', 'vendedores', 'catalogo', 'categorias', 'encomendas', 'pagamentos', 'relatorios', 'apoio', 'auditoria']) {
      await open(`/admin/${route}`);
      await page.locator('.management-main').waitFor();
      await page.locator('.management-main .page-heading').waitFor();
      await page.waitForFunction(() => !document.querySelector('.management-main .state-panel[role="status"]'));
      assert.equal(await page.locator('.management-main [role="alert"]').count(), 0, route);
      await noOverflow(page);
    }
    passed('All administrator pages render with real API data');
    await logout();
    await login('vendedor1@demo.deloya.example.com', process.env.DEMO_PASSWORD);
    for (const route of ['dashboard', 'loja', 'produtos', 'servicos', 'encomendas', 'solicitacoes', 'relatorios']) {
      await open(`/vendedor/${route}`);
      await page.locator('.management-main .page-heading').waitFor();
      await page.waitForFunction(() => !document.querySelector('.management-main .state-panel[role="status"]'));
      assert.equal(await page.locator('.management-main [role="alert"]').count(), 0, route);
      await noOverflow(page);
    }
    passed('All vendor pages render with real API data');
    await logout();
  }

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'pt-MZ' });
  const mobilePage = await mobile.newPage();
  mobilePage.on('pageerror', (error) => errors.push(error.message));
  await mobilePage.goto(base);
  await mobilePage.locator('.product-card').first().waitFor();
  await noOverflow(mobilePage);
  await mobilePage.screenshot({ path: resolve(output, 'home-mobile.png'), fullPage: true });
  await mobilePage.getByRole('button', { name: 'Abrir menu' }).click();
  await mobilePage.getByRole('dialog').getByRole('link', { name: 'Serviços' }).click();
  await mobilePage.getByRole('heading', { name: 'Serviços para o dia a dia' }).waitFor();
  await noOverflow(mobilePage);
  await mobilePage.goto(`${base}/registo`);
  await mobilePage.getByRole('button', { name: 'Criar a minha conta' }).waitFor();
  await noOverflow(mobilePage);
  passed('Mobile home, navigation and registration form fit the viewport');
  await mobile.close();
  assert.deepEqual(errors, [], 'Unexpected browser/API errors');
  await writeFile(resolve(output, 'result.json'), JSON.stringify({ checks, errors }, null, 2));
  console.log(`Browser QA complete: ${checks.length} checks.`);
} catch (error) {
  await page.screenshot({ path: resolve(output, 'failure.png'), fullPage: true }).catch(() => {});
  await writeFile(resolve(output, 'result.json'), JSON.stringify({ checks, errors, failure: error.message }, null, 2));
  throw error;
} finally {
  await context.close();
  await browser.close();
}
