// Optional browser regression. API routes are mocked, including a completely empty catalogue.
import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const workspace = fileURLToPath(new URL('../../', import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH ??= resolve(workspace, '.local/browsers');
const { chromium } = await import('../../.local/browser-qa/node_modules/playwright/index.mjs');
const browser = await chromium.launch({ headless: true });
const base = process.env.QA_BASE_URL ?? 'http://localhost:3011';

try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, locale: 'pt-MZ' });
    await context.addCookies([{ url: base, name: 'csrf_token', value: 'category-regression' }]);
    const page = await context.newPage();
    const pageErrors = [];
    const patternErrors = [];
    const mutations = [];
    const categories = [];
    let rejectNext = false;
    page.on('pageerror', (error) => pageErrors.push(error.message));
    page.on('console', (entry) => { if (/Pattern attribute|Invalid regular expression/.test(entry.text())) patternErrors.push(entry.text()); });
    await page.route('**/api/v1/**', async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (path.endsWith('/auth/session')) return route.fulfill({ json: { user: { id: 'admin', name: 'Admin', email: 'admin@example.test', role: 'admin', is_demo: false } } });
      if (path.endsWith('/cart')) return route.fulfill({ json: { items: [], total: '0.00' } });
      if (path === '/api/v1/admin/categories' && request.method() === 'GET') return route.fulfill({ json: { items: categories, total: categories.length, page: 1, page_size: 100 } });
      if (/^\/api\/v1\/admin\/categories(?:\/[^/]+)?$/.test(path) && ['POST', 'PATCH'].includes(request.method())) {
        assert.equal(request.headers()['x-csrf-token'], 'category-regression');
        const values = request.postDataJSON();
        mutations.push({ path, method: request.method(), values });
        if (rejectNext) { rejectNext = false; return route.fulfill({ status: 409, json: { detail: 'Já existe uma categoria com este identificador.' } }); }
        const item = { ...values, slug: values.slug ?? 'saude-e-beleza', id: request.method() === 'PATCH' ? path.split('/').at(-1) : `category-${categories.length + 1}` };
        const index = categories.findIndex((category) => category.id === item.id);
        if (index >= 0) categories[index] = item; else categories.push(item);
        return route.fulfill({ status: request.method() === 'POST' ? 201 : 200, json: item });
      }
      return route.fulfill({ json: { items: [], total: 0 } });
    });

    async function create() { await page.getByRole('button', { name: 'Nova categoria', exact: true }).click(); return page.getByRole('dialog', { name: 'Nova categoria', exact: true }); }
    const save = (dialog) => dialog.getByRole('button', { name: 'Guardar categoria', exact: true }).click();
    const input = (dialog, name) => dialog.locator(`input[name="${name}"]`);
    await page.goto(`${base}/admin/categorias`);
    await page.getByRole('heading', { name: 'Ainda não há categorias' }).waitFor();
    let dialog = await create();
    assert.match(await dialog.textContent(), /Só o nome é obrigatório/);
    assert.equal(await dialog.locator('select').getAttribute('required'), null);
    assert.deepEqual(await dialog.locator('select option').allTextContents(), ['Sem categoria principal']);
    await input(dialog, 'name').fill(' ');
    await save(dialog);
    await dialog.getByText('Indique um nome entre 2 e 100 caracteres.', { exact: true }).waitFor();
    assert.equal(mutations.length, 0);
    await input(dialog, 'name').fill('  Saúde e Beleza  ');
    await save(dialog);
    await dialog.waitFor({ state: 'hidden' });
    assert.deepEqual(mutations[0].values, { name: 'Saúde e Beleza', parent_id: null });
    await page.getByRole('button', { name: 'Editar Saúde e Beleza', exact: true }).waitFor();

    dialog = await create();
    await input(dialog, 'name').fill('Telemóveis');
    await dialog.locator('select').selectOption('category-1');
    await input(dialog, 'slug').fill('!!!');
    await input(dialog, 'slug').press('Enter');
    await dialog.getByText('Use um identificador entre 2 e 120 letras ou números. Pode deixar este campo vazio para o gerar automaticamente.', { exact: true }).waitFor();
    assert.equal(mutations.length, 1);
    await input(dialog, 'slug').fill('telemoveis-e-acessorios');
    assert.equal(await input(dialog, 'slug').evaluate((element) => element.checkValidity()), true, 'Hyphens must work with the modern HTML pattern v flag');
    await input(dialog, 'slug').fill('Telemóveis & Acessórios');
    assert.equal(await input(dialog, 'slug').evaluate((element) => element.validity.patternMismatch), true, 'The native pattern must be valid and enforce its character set');
    await input(dialog, 'slug').press('Enter');
    await dialog.waitFor({ state: 'hidden' });
    assert.deepEqual(mutations[1].values, { name: 'Telemóveis', slug: 'telemoveis-acessorios', parent_id: 'category-1' });
    await page.getByRole('button', { name: 'Editar Telemóveis', exact: true }).waitFor();

    await page.getByRole('button', { name: 'Editar Saúde e Beleza', exact: true }).click();
    dialog = page.getByRole('dialog', { name: 'Editar categoria', exact: true });
    assert.equal(await dialog.locator('select').inputValue(), '');
    assert.equal(await dialog.locator('select option[value="category-1"]').count(), 0);
    await input(dialog, 'name').fill('Saúde e Cuidados');
    await save(dialog);
    await dialog.waitFor({ state: 'hidden' });
    assert.equal(mutations[2].method, 'PATCH');
    assert.equal(mutations[2].values.parent_id, null);
    await page.getByRole('button', { name: 'Editar Saúde e Cuidados', exact: true }).waitFor();

    dialog = await create();
    assert.equal(await input(dialog, 'name').inputValue(), '', 'A new form must not retain edited values');
    await input(dialog, 'name').fill('Informática');
    await input(dialog, 'slug').fill('informatica');
    rejectNext = true;
    await save(dialog);
    await dialog.getByRole('alert').filter({ hasText: 'Já existe uma categoria com este identificador.' }).waitFor();
    assert.equal(await input(dialog, 'name').inputValue(), 'Informática');
    assert.equal(await input(dialog, 'slug').inputValue(), 'informatica');
    await input(dialog, 'slug').fill('informática e acessórios');
    await input(dialog, 'slug').blur();
    assert.equal(await input(dialog, 'slug').inputValue(), 'informatica-e-acessorios');
    await save(dialog);
    await dialog.waitFor({ state: 'hidden' });
    assert.equal(mutations.at(-1).values.parent_id, null);
    assert.equal(mutations.at(-1).values.slug, 'informatica-e-acessorios');
    assert.deepEqual(patternErrors, []);
    assert.deepEqual(pageErrors, []);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    console.log(JSON.stringify({ width, firstTopLevel: 'ok', parentOptional: 'ok', subcategory: 'ok', rootEdit: 'ok', slugNormalization: 'ok', modernPattern: 'ok', inlineErrorsAndRetry: 'ok' }));
    await context.close();
  }
} finally { await browser.close(); }
