// Catalogue and cart regression. Every API request is intercepted; no real listings are changed.
import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const workspace = fileURLToPath(new URL('../../', import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH ??= resolve(workspace, '.local/browsers');
const { chromium } = await import('../../.local/browser-qa/node_modules/playwright/index.mjs');
const base = process.env.QA_BASE_URL ?? 'http://localhost:3011';
const browser = await chromium.launch({ headless: true });
const csrf = 'listing-regression';
const timestamp = '2026-11-20T10:00:00Z';

try {
  for (const width of [1440, 390]) {
    for (const kind of ['product', 'service']) {
      const path = kind === 'product' ? 'products' : 'services';
      const label = kind === 'product' ? 'produto' : 'serviço';
      const category = { id: 'category-1', slug: 'casa', name: 'Casa' };
      const store = { id: 'store-1', name: 'Loja de ensaio', slug: 'loja-ensaio', province: 'Nampula', district: 'Nampula', delivery_fee: null };
      const listings = [{ id: 'existing', slug: 'anuncio-existente', kind, name: 'Anúncio existente', description: 'Descrição fictícia do anúncio existente', price: '100.00', stock: kind === 'product' ? 5 : null, sku: kind === 'product' ? 'EXISTING' : null, service_location: kind === 'service' ? 'Na loja' : null, category_id: category.id, store_id: store.id, images: [], image_url: null, status: 'published', updated_at: timestamp, category, store, is_demo: true }];
      const mutations = [];
      const errors = [];
      const unexpected = [];
      let rejectSave = true;
      let rejectDelete = true;
      let cartItem = null;
      const context = await browser.newContext({ viewport: { width, height: 1000 }, locale: 'pt-MZ' });
      await context.addCookies([{ url: base, name: 'csrf_token', value: csrf }]);
      const page = await context.newPage();
      page.on('pageerror', (error) => errors.push(error.message));
      await page.route('**/api/v1/**', async (route) => {
        const request = route.request();
        const pathname = new URL(request.url()).pathname;
        const method = request.method();
        if (pathname === '/api/v1/auth/session') return route.fulfill({ json: { user: { id: 'vendor-1', name: 'Vendedor ensaio', email: 'vendor@example.test', role: 'vendor', is_demo: true } } });
        if (pathname === '/api/v1/categories') return route.fulfill({ json: { items: [category], total: 1, page: 1, page_size: 100 } });
        if (pathname === '/api/v1/cart') return route.fulfill({ json: { items: cartItem ? [cartItem] : [], total: cartItem?.subtotal ?? '0.00', is_demo: Boolean(cartItem) } });
        if (pathname === '/api/v1/cart/cart-1' && method === 'DELETE') {
          assert.equal(request.headers()['x-csrf-token'], csrf);
          cartItem = null;
          return route.fulfill({ json: { items: [], total: '0.00', is_demo: false } });
        }
        if (pathname === `/api/v1/vendor/${path}` && method === 'GET') {
          const items = listings.filter((listing) => listing.status !== 'archived');
          return route.fulfill({ json: { items, total: items.length, page: 1, page_size: 100 } });
        }
        if (pathname.startsWith(`/api/v1/vendor/${path}`) && ['POST', 'PATCH', 'DELETE'].includes(method)) {
          assert.equal(request.headers()['x-csrf-token'], csrf);
          const values = method === 'DELETE' ? null : request.postDataJSON();
          mutations.push({ method, values, pathname });
          if (method === 'DELETE') {
            if (rejectDelete) { rejectDelete = false; return route.fulfill({ status: 503, json: { detail: 'Não foi possível eliminar. Tente novamente.' } }); }
            const listing = listings.find((item) => item.id === pathname.split('/').at(-1));
            listing.status = 'archived';
            cartItem = { id: 'cart-1', quantity: 1, listing, unit_price: listing.price, subtotal: listing.price, available: false };
            return route.fulfill({ json: { message: 'Anúncio eliminado do catálogo. O histórico foi preservado.' } });
          }
          if (rejectSave) { rejectSave = false; return route.fulfill({ status: 409, json: { detail: 'O registo entra em conflito com dados existentes; verifique os campos únicos' } }); }
          const listing = { ...values, id: method === 'PATCH' ? pathname.split('/').at(-1) : 'created', slug: 'anuncio-criado', kind, category, store, store_id: store.id, updated_at: timestamp, is_demo: true, stock: kind === 'product' ? values.stock : null };
          const index = listings.findIndex((item) => item.id === listing.id);
          if (index >= 0) listings[index] = listing; else listings.push(listing);
          return route.fulfill({ status: method === 'POST' ? 201 : 200, json: listing });
        }
        unexpected.push(`${method} ${pathname}`);
        return route.fulfill({ status: 404, json: { detail: 'Unexpected mocked endpoint' } });
      });

      await page.goto(`${base}/vendedor/${kind === 'product' ? 'produtos' : 'servicos'}`);
      await page.getByRole('button', { name: 'Editar Anúncio existente', exact: true }).waitFor();
      assert.equal(await page.getByRole('navigation', { name: 'Gestão', exact: true }).getByRole('link', { name: 'A minha conta', exact: true }).getAttribute('href'), '/conta');
      await page.getByRole('button', { name: `Novo ${label}`, exact: true }).click();
      let dialog = page.getByRole('dialog', { name: `Novo ${label}`, exact: true });
      const field = (name) => dialog.locator(`[name="${name}"]`);
      assert.equal(await field('name').inputValue(), '');
      await field('name').fill('Anúncio criado');
      await field('description').fill('Descrição fictícia para o teste do catálogo');
      await field('category_id').selectOption(category.id);
      await field('status').selectOption('draft');
      if (kind === 'product') {
        await field('price').fill('42.50');
        await field('sku').fill('CREATE-TEST');
        await field('stock').fill('7');
      } else {
        await field('service_location').fill('Na loja');
        await field('estimated_duration').fill('2 horas');
      }
      await dialog.getByRole('button', { name: 'Guardar anúncio', exact: true }).click();
      await dialog.getByRole('alert').filter({ hasText: 'O registo entra em conflito' }).waitFor();
      assert.equal(await field('name').inputValue(), 'Anúncio criado');
      await dialog.getByRole('button', { name: 'Guardar anúncio', exact: true }).click();
      await dialog.waitFor({ state: 'hidden' });
      const created = mutations.at(-1);
      assert.equal(created.method, 'POST');
      assert.equal(created.values.status, 'draft');
      assert.equal(created.values.price, kind === 'product' ? '42.50' : null);
      assert.equal('expected_updated_at' in created.values, false);
      assert.equal('stock' in created.values, kind === 'product');

      await page.getByRole('button', { name: 'Editar Anúncio criado', exact: true }).click();
      dialog = page.getByRole('dialog', { name: `Editar ${label}`, exact: true });
      await field('category_id').locator(`option[value="${category.id}"]`).waitFor({ state: 'attached' });
      assert.equal(await field('category_id').inputValue(), category.id, 'The saved category must remain selected after options load');
      assert.equal(await field('name').inputValue(), 'Anúncio criado');
      await field('name').fill('Anúncio revisto');
      await field('status').selectOption('pending');
      if (kind === 'product') await field('stock').fill('9');
      else await field('service_location').fill('Ao domicílio');
      await dialog.getByRole('button', { name: 'Guardar anúncio', exact: true }).waitFor();
      assert.deepEqual(await dialog.locator('form').evaluate((form) => [...form.elements].filter((element) => element.willValidate && !element.checkValidity()).map((element) => ({ name: element.name, validation: element.validationMessage }))), [], 'Existing values must populate a valid edit form');
      await dialog.getByRole('button', { name: 'Guardar anúncio', exact: true }).click();
      await dialog.waitFor({ state: 'hidden' });
      assert.equal(mutations.at(-1).method, 'PATCH');
      assert.equal(mutations.at(-1).values.expected_updated_at, timestamp);
      assert.equal(mutations.at(-1).values.status, 'pending');
      assert.equal(mutations.at(-1).values[kind === 'product' ? 'stock' : 'service_location'], kind === 'product' ? 9 : 'Ao domicílio');

      const remove = page.getByRole('button', { name: 'Eliminar Anúncio revisto', exact: true });
      assert.match(await remove.textContent(), /Eliminar/);
      await remove.focus();
      await page.keyboard.press('Enter');
      dialog = page.getByRole('dialog', { name: `Eliminar ${label} do catálogo`, exact: true });
      await dialog.waitFor();
      assert.match(await dialog.textContent(), /histórico das encomendas e solicitações anteriores é preservado/);
      await page.keyboard.press('Escape');
      await dialog.waitFor({ state: 'hidden' });
      assert.equal(mutations.filter((entry) => entry.method === 'DELETE').length, 0);
      await page.waitForFunction(() => document.activeElement?.getAttribute('aria-label') === 'Eliminar Anúncio revisto');
      assert.equal(await remove.evaluate((button) => button === document.activeElement), true);
      await remove.click();
      await dialog.getByRole('button', { name: 'Eliminar do catálogo', exact: true }).click();
      await dialog.getByRole('alert').filter({ hasText: 'Não foi possível eliminar' }).waitFor();
      await dialog.getByRole('button', { name: 'Eliminar do catálogo', exact: true }).click();
      await dialog.waitFor({ state: 'hidden' });
      await remove.waitFor({ state: 'hidden' });
      await page.getByText('Anúncio eliminado do catálogo. O histórico foi preservado.', { exact: true }).waitFor();
      assert.equal(mutations.filter((entry) => entry.method === 'DELETE').length, 2);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);

      await page.goto(`${base}/carrinho`);
      await page.getByText('Indisponível', { exact: true }).waitFor();
      assert.equal(await page.getByRole('button', { name: 'Remova os artigos indisponíveis', exact: true }).isDisabled(), true);
      assert.equal(await page.getByRole('link', { name: 'Continuar para encomenda', exact: true }).count(), 0);
      assert.equal(await page.getByRole('link', { name: 'Anúncio revisto', exact: true }).count(), 0);
      const cartRow = page.locator('.cart-item').filter({ hasText: 'Anúncio revisto' });
      assert.equal(await cartRow.locator('.cart-quantity button').count(), 2);
      assert.equal(await cartRow.locator('.cart-quantity button:enabled').count(), 0);
      await page.getByRole('button', { name: 'Remover Anúncio revisto', exact: true }).click();
      await page.getByRole('heading', { name: 'O seu carrinho está à espera de uma descoberta', exact: true }).waitFor();
      assert.deepEqual(unexpected, []);
      assert.deepEqual(errors, []);
      console.log(JSON.stringify({ width, kind, create: 'ok', edit: 'ok', timestamp: 'ok', confirmationKeyboard: 'ok', errorRetry: 'ok', removeFromCatalogue: 'ok', unavailableCartRemoval: 'ok' }));
      await context.close();
    }
  }
} finally { await browser.close(); }
