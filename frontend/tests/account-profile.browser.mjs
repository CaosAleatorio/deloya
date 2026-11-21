// Optional browser regression. Every account, address and session API is mocked.
import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const workspace = fileURLToPath(new URL('../../', import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH ??= resolve(workspace, '.local/browsers');
const { chromium } = await import('../../.local/browser-qa/node_modules/playwright/index.mjs');
const { default: AxeBuilder } = await import('../../.local/browser-qa/node_modules/@axe-core/playwright/dist/index.mjs');
const base = process.env.QA_BASE_URL ?? 'http://localhost:3011';
const browser = await chromium.launch({ headless: true });
const csrf = 'account-regression';
const currentPassword = 'actual-qa-password';
const nextPassword = 'updated-qa-password';

try {
  for (const width of [1440, 390]) for (const role of ['customer', 'vendor', 'admin']) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, locale: 'pt-MZ' });
    await context.addCookies([{ url: base, name: 'csrf_token', value: csrf }]);
    const page = await context.newPage();
    const pageErrors = [];
    const requests = [];
    const navigations = [];
    let user = { id: `account-${role}`, name: 'Conta Regressão', email: `${role}@example.test`, phone: '841234567', role, is_demo: false };
    let addresses = [];
    let rejected = null;
    let releaseMutation = null;
    let holdMutation = false;
    page.on('pageerror', (error) => pageErrors.push(error.message));
    page.on('framenavigated', (frame) => { if (frame === page.mainFrame()) navigations.push(frame.url()); });
    await page.route('**/api/v1/**', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname;
      const method = request.method();
      if (path === '/api/v1/auth/session') return route.fulfill({ json: { user } });
      if (path === '/api/v1/auth/refresh') return route.fulfill({ status: 401, json: { detail: 'Sessão terminada.' } });
      if (path === '/api/v1/me/addresses' && method === 'GET') return route.fulfill({ json: { items: addresses, total: addresses.length } });
      if (path === '/api/v1/cart') return route.fulfill({ json: { items: [], total: '0.00' } });
      if (path === '/api/v1/me' || path === '/api/v1/me/password' || path.startsWith('/api/v1/me/addresses')) {
        assert.equal(request.headers()['x-csrf-token'], csrf);
        const data = request.postData() ? request.postDataJSON() : null;
        requests.push({ method, path, data });
        assert.equal(url.search, '', 'Credentials must never appear in a request URL');
        if (holdMutation) await new Promise((resolve) => { releaseMutation = resolve; });
        if (rejected) { const failure = rejected; rejected = null; return route.fulfill({ status: failure.status, json: { detail: failure.message } }); }
        if (path === '/api/v1/me' && method === 'PATCH') { user = { ...user, name: data.name, email: data.email, phone: data.phone }; return route.fulfill({ json: user }); }
        if (path === '/api/v1/me/password') return route.fulfill({ json: { message: 'Palavra-passe alterada.' } });
        if (path === '/api/v1/me' && method === 'DELETE') { user = null; return route.fulfill({ json: { message: 'Conta eliminada.', retained_records: true } }); }
        if (method === 'DELETE') { addresses = addresses.filter((item) => item.id !== path.split('/').at(-1)); return route.fulfill({ status: 204 }); }
        const address = { ...data, id: method === 'PATCH' ? path.split('/').at(-1) : 'address-1' };
        if (method === 'PATCH') addresses = addresses.map((item) => item.id === address.id ? address : item); else addresses.push(address);
        return route.fulfill({ status: method === 'POST' ? 201 : 200, json: address });
      }
      return route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 20 } });
    });

    await page.goto(`${base}/conta`);
    const profile = page.getByRole('article', { name: 'Dados pessoais', exact: true });
    const password = page.getByRole('article', { name: 'Alterar palavra-passe', exact: true });
    await profile.getByRole('button', { name: 'Guardar alterações' }).waitFor();
    assert.equal(await profile.locator('form').getAttribute('method'), 'post');
    assert.equal(await password.locator('form').getAttribute('method'), 'post');
    await page.locator('.account-links').getByRole('link', { name: /As minhas encomendas/ }).waitFor();
    await page.locator('.account-links').getByRole('link', { name: /O meu carrinho/ }).waitFor();

    await profile.locator('input[name="name"]').fill('   ');
    await profile.getByRole('button', { name: 'Guardar alterações' }).click();
    await profile.getByRole('alert').filter({ hasText: 'Indique um nome entre 2 e 120 caracteres.' }).waitFor();
    assert.equal(requests.length, 0);
    await profile.locator('input[name="name"]').fill('  Actualizada Regressão  ');
    await profile.locator('input[name="phone"]').fill('861234567');
    holdMutation = true;
    await profile.getByRole('button', { name: 'Guardar alterações' }).click();
    await page.waitForFunction(() => document.querySelector('form[aria-busy="true"]') !== null);
    assert.equal(await password.locator('input[name="current_password"]').isDisabled(), true, 'Account mutations must not race each other');
    await page.waitForFunction(() => document.querySelector('form[aria-busy="true"] button[type="submit"]')?.disabled);
    while (!releaseMutation) await page.waitForTimeout(20);
    holdMutation = false;
    releaseMutation();
    await profile.getByRole('status').filter({ hasText: 'Perfil actualizado.' }).waitFor();
    assert.deepEqual(requests.at(-1).data, { name: 'Actualizada Regressão', phone: '861234567', email: `${role}@example.test` });
    await page.getByRole('heading', { name: 'Olá, Actualizada.' }).waitFor();
    assert.match(await page.locator('header .account-link').textContent(), /Actualizada/);

    await profile.locator('input[name="email"]').fill(`next-${role}@example.test`);
    await profile.getByRole('button', { name: 'Guardar alterações' }).click();
    await profile.getByRole('alert').filter({ hasText: 'Introduza a palavra-passe actual para alterar o email.' }).waitFor();
    assert.equal(requests.length, 1);
    await profile.locator('input[name="current_password"]').fill('wrong-qa-password');
    rejected = { status: 403, message: 'A palavra-passe actual está incorrecta.' };
    await profile.getByRole('button', { name: 'Guardar alterações' }).click();
    await profile.getByRole('alert').filter({ hasText: rejected?.message ?? 'A palavra-passe actual está incorrecta.' }).waitFor();
    await profile.locator('input[name="current_password"]').fill(currentPassword);
    rejected = { status: 409, message: 'Este email já está associado a outra conta.' };
    await profile.getByRole('button', { name: 'Guardar alterações' }).click();
    await profile.getByRole('alert').filter({ hasText: 'Este email já está associado a outra conta.' }).waitFor();
    assert.equal(await profile.locator('input[name="email"]').inputValue(), `next-${role}@example.test`);
    await profile.getByRole('button', { name: 'Guardar alterações' }).click();
    await profile.getByRole('status').filter({ hasText: 'Use o novo email para iniciar sessão.' }).waitFor();
    assert.equal(await profile.locator('input[type="password"]').count(), 0);
    assert.equal(requests.at(-1).data.current_password, currentPassword);

    await password.locator('input[name="current_password"]').fill(currentPassword);
    await password.locator('input[name="new_password"]').fill('short');
    await password.locator('input[name="confirm_password"]').fill('different');
    const beforePassword = requests.length;
    await password.getByRole('button', { name: 'Alterar palavra-passe', exact: true }).click();
    await password.getByRole('alert').filter({ hasText: 'Use entre 12 e 128 caracteres.' }).waitFor();
    await password.getByRole('alert').filter({ hasText: 'A confirmação deve ser igual à nova palavra-passe.' }).waitFor();
    assert.equal(requests.length, beforePassword);
    await password.locator('input[name="new_password"]').fill(nextPassword);
    await password.locator('input[name="confirm_password"]').fill(nextPassword);
    rejected = { status: 403, message: 'A palavra-passe actual está incorrecta.' };
    await password.getByRole('button', { name: 'Alterar palavra-passe', exact: true }).click();
    await password.getByRole('alert').filter({ hasText: 'A palavra-passe actual está incorrecta.' }).waitFor();
    await password.getByRole('button', { name: 'Alterar palavra-passe', exact: true }).click();
    await password.getByRole('status').filter({ hasText: 'Palavra-passe alterada.' }).waitFor();
    assert.deepEqual(requests.at(-1).data, { current_password: currentPassword, new_password: nextPassword });
    for (const input of await password.locator('input[type="password"]').all()) assert.equal(await input.inputValue(), '');

    await page.getByRole('button', { name: 'Adicionar morada', exact: true }).click();
    let dialog = page.getByRole('dialog', { name: 'Adicionar morada', exact: true });
    await dialog.locator('input[name="label"]').fill('Casa');
    await dialog.locator('textarea[name="address"]').fill('Rua de regressão, 1');
    await dialog.locator('input[name="phone"]').fill('841234567');
    await dialog.getByRole('button', { name: 'Guardar morada' }).click();
    await dialog.waitFor({ state: 'hidden' });
    await page.getByRole('button', { name: 'Editar morada Casa', exact: true }).click();
    dialog = page.getByRole('dialog', { name: 'Editar morada', exact: true });
    assert.equal(await dialog.locator('input[name="label"]').inputValue(), 'Casa');
    assert.equal(await dialog.locator('textarea[name="address"]').inputValue(), 'Rua de regressão, 1');
    await dialog.locator('input[name="label"]').fill('Trabalho');
    await dialog.locator('textarea[name="address"]').fill('Rua de regressão, 2');
    rejected = { status: 409, message: 'Não foi possível actualizar a morada.' };
    await dialog.getByRole('button', { name: 'Guardar morada' }).click();
    await dialog.getByRole('alert').filter({ hasText: 'Não foi possível actualizar a morada.' }).waitFor();
    assert.equal(await dialog.locator('input[name="label"]').inputValue(), 'Trabalho');
    await dialog.getByRole('button', { name: 'Guardar morada' }).click();
    await dialog.waitFor({ state: 'hidden' });
    assert.equal(requests.at(-1).method, 'PATCH');
    assert.equal(requests.at(-1).path, '/api/v1/me/addresses/address-1');
    assert.equal(requests.at(-1).data.address, 'Rua de regressão, 2');
    await page.getByRole('button', { name: 'Eliminar morada Trabalho', exact: true }).click();
    dialog = page.getByRole('dialog', { name: 'Eliminar morada', exact: true });
    const beforeCancel = requests.length;
    await dialog.getByRole('button', { name: 'Manter morada' }).click();
    assert.equal(requests.length, beforeCancel);
    await page.getByRole('button', { name: 'Eliminar morada Trabalho', exact: true }).click();
    rejected = { status: 409, message: 'Não foi possível eliminar a morada.' };
    await dialog.getByRole('button', { name: 'Eliminar morada', exact: true }).click();
    await dialog.getByRole('alert').filter({ hasText: 'Não foi possível eliminar a morada.' }).waitFor();
    await dialog.getByRole('button', { name: 'Eliminar morada', exact: true }).click();
    await dialog.waitFor({ state: 'hidden' });
    await page.getByText('Ainda não adicionou moradas.', { exact: true }).waitFor();

    const accessibility = await new AxeBuilder({ page }).include('.account-grid').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    assert.deepEqual(accessibility.violations.map((entry) => ({ id: entry.id, description: entry.description })), []);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.getByRole('button', { name: 'Eliminar a minha conta', exact: true }).click();
    dialog = page.getByRole('dialog', { name: 'Confirmar eliminação da conta' });
    assert.match(await dialog.textContent(), new RegExp(`next-${role}@example.test`));
    assert.match(await dialog.textContent(), /histórico.*conservado/);
    assert.equal(await dialog.locator('form').getAttribute('method'), 'post');
    const beforeDelete = requests.length;
    await dialog.getByRole('button', { name: 'Confirmar eliminação', exact: true }).click();
    await dialog.getByRole('alert').filter({ hasText: 'Escreva ELIMINAR, em maiúsculas, para confirmar.' }).waitFor();
    assert.equal(requests.length, beforeDelete);
    await dialog.locator('input[name="current_password"]').fill(nextPassword);
    await dialog.locator('input[name="confirmation"]').fill('ELIMINAR');
    rejected = { status: 403, message: 'A palavra-passe actual está incorrecta.' };
    await dialog.getByRole('button', { name: 'Confirmar eliminação', exact: true }).click();
    await dialog.getByRole('alert').filter({ hasText: 'A palavra-passe actual está incorrecta.' }).waitFor();
    const blocked = role === 'admin' ? 'Não pode eliminar a conta do último administrador activo.' : 'Resolva as encomendas ou pagamentos pendentes antes de eliminar a conta.';
    rejected = { status: 409, message: blocked };
    await dialog.getByRole('button', { name: 'Confirmar eliminação', exact: true }).click();
    await dialog.getByRole('alert').filter({ hasText: blocked }).waitFor();
    assert.equal(new URL(page.url()).pathname, '/conta');
    assert.equal(await page.getByRole('button', { name: 'Terminar sessão', exact: true }).isVisible(), false, 'The session control is hidden behind the open modal');
    await dialog.getByRole('button', { name: 'Manter a minha conta' }).click();
    await page.getByRole('button', { name: 'Eliminar a minha conta', exact: true }).click();
    assert.equal(await dialog.locator('input[name="current_password"]').inputValue(), '', 'Closing the modal must discard the password');
    await dialog.locator('input[name="current_password"]').fill(nextPassword);
    await dialog.locator('input[name="confirmation"]').fill('ELIMINAR');
    await dialog.getByRole('button', { name: 'Confirmar eliminação', exact: true }).click();
    await page.waitForURL(`${base}/`);
    await page.getByRole('link', { name: 'Iniciar sessão ou registar', exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Terminar sessão', exact: true }).count(), 0);
    assert.deepEqual(requests.at(-1).data, { current_password: nextPassword, confirmation: 'ELIMINAR' });
    assert.equal(navigations.some((url) => /password|ELIMINAR|current_password|new_password/.test(url)), false);
    assert.equal(await page.evaluate(() => `${JSON.stringify(localStorage)} ${JSON.stringify(sessionStorage)}`.includes('qa-password')), false);
    assert.deepEqual(pageErrors, []);
    console.log(JSON.stringify({ width, role, profile: 'ok', emailReauthentication: 'ok', password: 'ok', addressCrud: 'ok', deletionConflictAndSuccess: 'ok', accessibility: 'ok' }));
    await context.close();
  }
} finally { await browser.close(); }
