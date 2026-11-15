// Optional browser regression: UI APIs are mocked; backend tests cover ownership,
// immutable recipients, idempotency and transactional payment state.
import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const workspace = fileURLToPath(new URL('../../', import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH ??= resolve(workspace, '.local/browsers');
const { chromium } = await import('../../.local/browser-qa/node_modules/playwright/index.mjs');
const { default: AxeBuilder } = await import('../../.local/browser-qa/node_modules/@axe-core/playwright/dist/index.mjs');
const base = process.env.QA_BASE_URL ?? 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const csrf = 'manual-payment-regression';
const timestamp = '2026-11-15T10:00:00Z';

try {
  for (const width of [1440, 390]) {
    const order = { id: 'order-1', reference: 'DL-REGRESSION', status: 'pendente_pagamento', total: '300.00', is_demo: false, payment_mode: 'manual', can_cancel: true, created_at: timestamp, vendor_orders: [
      { id: 'vendor-order-1', order_id: 'order-1', store: { id: 'store-1', name: 'Loja Um', slug: 'loja-um' }, status: 'pendente_pagamento', total: '100.00', is_demo: false, payment_mode: 'manual', payments: [], payment_destinations: { mpesa: { phone: '841234567', account_name: 'Maria Um' } }, items: [] },
      { id: 'vendor-order-2', order_id: 'order-1', store: { id: 'store-2', name: 'Loja Dois', slug: 'loja-dois' }, status: 'pendente_pagamento', total: '200.00', is_demo: false, payment_mode: 'manual', payments: [], payment_destinations: { emola: { phone: '861234567', account_name: 'Ana Dois' } }, items: [] },
    ] };
    const errors = [];
    const claims = [];
    let reviews = 0;
    const contexts = [];
    async function open(role, storeId, storeStatus = 'approved') {
      const context = await browser.newContext({ viewport: { width, height: 1000 }, locale: 'pt-MZ' });
      contexts.push(context);
      await context.addCookies([{ url: base, name: 'csrf_token', value: csrf }]);
      const page = await context.newPage();
      page.on('pageerror', (error) => errors.push(error.message));
      await page.route('**/api/v1/**', async (route) => {
        const request = route.request();
        const url = new URL(request.url());
        const path = url.pathname;
        if (path.endsWith('/auth/session')) return route.fulfill({ json: { user: { id: `${role}-${storeId ?? ''}`, name: 'Regressão Carteira', role, email: 'regression@example.test', is_demo: false } } });
        if (path.endsWith('/cart')) return route.fulfill({ json: { items: [], total: '0.00' } });
        if (path.endsWith('/payment-settings')) return route.fulfill({ json: { mode: 'manual', demo_enabled: false } });
        if (path === '/api/v1/orders/order-1') return route.fulfill({ json: order });
        if (path === '/api/v1/orders') return route.fulfill({ json: { items: [order], total: 1, page: 1, page_size: 20 } });
        if (path === '/api/v1/service-requests') return route.fulfill({ json: { items: [], total: 0 } });
        if (path === '/api/v1/vendor/store') return route.fulfill({ json: { status: storeStatus } });
        if (path === '/api/v1/vendor/payments') {
          const status = url.searchParams.get('status');
          const items = order.vendor_orders.filter((vendor) => vendor.store.id === storeId).flatMap((vendor) => vendor.payments).filter((payment) => !status || payment.status === status);
          return route.fulfill({ json: { items, total: items.length, page: 1, page_size: 20 } });
        }
        const claim = path.match(/^\/api\/v1\/orders\/order-1\/vendor-orders\/(vendor-order-[12])\/payments$/);
        if (claim) {
          assert.equal(request.method(), 'POST');
          assert.equal(request.headers()['x-csrf-token'], csrf);
          const body = request.postDataJSON();
          assert.equal('amount' in body, false, 'The client must not supply payment amounts');
          assert.match(body.idempotency_key, /^[0-9a-f-]{36}$/);
          const vendor = order.vendor_orders.find((entry) => entry.id === claim[1]);
          const payment = { id: `payment-${claims.length + 1}`, reference: `DL-MAN-${claims.length + 1}`, order_id: order.id, order_reference: order.reference, vendor_order_id: vendor.id, store_id: vendor.store.id, provider: body.provider, status: 'pending', amount: vendor.total, is_demo: order.is_demo, payment_mode: 'manual', transfer_reference: body.reference.toUpperCase(), destination: vendor.payment_destinations[body.provider], created_at: timestamp };
          claims.push(body);
          vendor.payments.push(payment);
          order.can_cancel = false;
          return route.fulfill({ status: 201, json: payment });
        }
        const review = path.match(/^\/api\/v1\/vendor\/orders\/(vendor-order-[12])\/payments\/([^/]+)\/review$/);
        if (review) {
          assert.equal(request.headers()['x-csrf-token'], csrf);
          const vendor = order.vendor_orders.find((entry) => entry.id === review[1]);
          assert.equal(vendor.store.id, storeId);
          const payment = vendor.payments.find((entry) => entry.id === review[2]);
          const body = request.postDataJSON();
          reviews++;
          if (body.decision === 'confirm') {
            assert.equal(body.wallet_verified, true);
            payment.status = 'success';
            vendor.status = 'paga';
            order.status = 'parcialmente_paga';
          } else {
            assert.ok(body.notes.length >= 3);
            payment.status = 'failure';
            payment.review_notes = body.notes;
          }
          return route.fulfill({ json: payment });
        }
        return route.fulfill({ status: 404, json: { detail: `Unexpected mocked endpoint: ${path}` } });
      });
      await page.goto(`${base}${role === 'customer' ? '/checkout?order=order-1' : '/vendedor/pagamentos'}`);
      return page;
    }

    const buyer = await open('customer');
    const first = buyer.locator('.manual-payment').filter({ has: buyer.getByRole('heading', { name: 'Loja Um', exact: true }) });
    const second = buyer.locator('.manual-payment').filter({ has: buyer.getByRole('heading', { name: 'Loja Dois', exact: true }) });
    await first.getByText('Maria Um', { exact: true }).waitFor();
    await second.getByText('Ana Dois', { exact: true }).waitFor();
    assert.match(await first.textContent(), /100,00\s*MT/);
    assert.match(await second.textContent(), /200,00\s*MT/);
    assert.equal(await buyer.locator('input[type="password"]').count(), 0);
    await first.getByLabel('Referência da transferência').fill('MPESA-12345');
    await first.getByRole('checkbox').check();
    await first.getByRole('button', { name: 'Enviar referência', exact: true }).click();
    await first.getByText('A referência está com o vendedor.', { exact: false }).waitFor();
    assert.equal(await first.locator('input[name="reference"]').count(), 0);
    assert.equal(claims.length, 1);
    assert.equal(claims[0].provider, 'mpesa');
    const suspendedSeller = await open('vendor', 'store-1', 'suspended');
    const suspendedConfirm = suspendedSeller.getByRole('button', { name: 'Conferir e confirmar recebimento' });
    await suspendedConfirm.waitFor();
    assert.equal(await suspendedConfirm.isDisabled(), true);
    assert.equal(await suspendedSeller.getByRole('button', { name: 'Recusar referência', exact: true }).isEnabled(), true);
    const seller = await open('vendor', 'store-1');
    await seller.getByRole('button', { name: 'Conferir e confirmar recebimento' }).click();
    const confirm = seller.getByRole('dialog', { name: 'Confirmar recebimento desta loja' });
    await confirm.getByRole('button', { name: 'Confirmar este recebimento' }).click();
    assert.equal(reviews, 0, 'Review must require deliberate wallet verification');
    await confirm.getByRole('checkbox').check();
    await confirm.getByRole('button', { name: 'Confirmar este recebimento' }).click();
    await confirm.waitFor({ state: 'hidden' });
    await buyer.reload();
    await buyer.getByText('Pagamento parcial:', { exact: false }).waitFor();
    assert.equal(await first.locator('input[name="reference"]').count(), 0);
    await second.getByLabel('Referência da transferência').fill('EMOLA-67890');
    await second.getByRole('checkbox').check();
    await second.getByRole('button', { name: 'Enviar referência', exact: true }).click();
    await second.getByText('A referência está com o vendedor.', { exact: false }).waitFor();
    const sellerTwo = await open('vendor', 'store-2');
    await sellerTwo.getByRole('button', { name: 'Recusar referência', exact: true }).click();
    const reject = sellerTwo.getByRole('dialog', { name: 'Recusar referência', exact: true });
    await reject.getByLabel('Motivo da recusa').fill('Referência não encontrada na minha carteira.');
    await reject.getByRole('button', { name: 'Registar recusa' }).click();
    await reject.waitFor({ state: 'hidden' });
    await buyer.reload();
    await second.getByLabel('Referência da transferência').waitFor();
    assert.equal(order.status, 'parcialmente_paga');
    await buyer.goto(`${base}/conta/encomendas`);
    await buyer.getByRole('link', { name: 'Ver transferências' }).waitFor();
    assert.equal(await buyer.getByRole('button', { name: 'Cancelar encomenda' }).count(), 0);
    await buyer.goto(`${base}/checkout?order=order-1`);
    await second.getByLabel('Referência da transferência').waitFor();
    const axe = await new AxeBuilder({ page: buyer }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    assert.deepEqual(axe.violations.map(({ id, nodes }) => ({ id, targets: nodes.map(({ target }) => target) })), []);
    assert.equal(await buyer.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);

    order.is_demo = true;
    order.vendor_orders[1].is_demo = true;
    await buyer.reload();
    await second.getByLabel('Referência fictícia de teste').waitFor();
    assert.equal(await second.locator('.manual-payment-instructions').count(), 0);
    assert.match(await second.textContent(), /Não envie dinheiro/);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ width, separateRecipients: 'ok', serverAmounts: 'ok', pendingLock: 'ok', suspendedStore: 'confirmation-disabled', explicitReview: 'ok', partialPayment: 'ok', rejectRetry: 'ok', testWarning: 'ok', accessibilityViolations: 0 }));
    await Promise.all(contexts.map((context) => context.close()));
  }
} finally { await browser.close(); }
