// Optional UI regression using the repository's local Playwright installation.
// API responses are mocked here; backend tests verify storage and authorisation.
import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const workspace = fileURLToPath(new URL('../../', import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH ??= resolve(workspace, '.local/browsers');
const { chromium } = await import('../../.local/browser-qa/node_modules/playwright/index.mjs');
const { default: AxeBuilder } = await import('../../.local/browser-qa/node_modules/@axe-core/playwright/dist/index.mjs');
const base = process.env.QA_BASE_URL ?? 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const csrf = 'attachment-regression-csrf';
const ticketId = '86a3372c-09c7-4b4f-9c90-2108941070cc';
const attachmentId = 'eb97680e-9efe-4c48-b695-d952b3e52110';
const filename = 'recibo-privado.pdf';
const bytes = Buffer.from('%PDF-1.4\nAttachment browser regression\n%%EOF');
const metadata = { id: attachmentId, ticket_id: ticketId, filename, content_type: 'application/pdf', size_bytes: bytes.length, uploaded_by: 'owner', created_at: '2026-11-15T10:00:00Z' };

try {
  for (const role of ['customer', 'admin']) for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, locale: 'pt-MZ' });
    await context.addCookies([{ url: base, name: 'csrf_token', value: csrf }]);
    const page = await context.newPage();
    const pageErrors = [];
    const storageRequests = [];
    page.on('pageerror', (error) => pageErrors.push(error.message));
    context.on('request', (request) => { if (new URL(request.url()).hostname.endsWith('.blob.vercel-storage.com')) storageRequests.push(request.url()); });
    const user = { id: 'owner', role, name: 'Attachment regression', email: 'attachment-regression@example.test', phone: '', is_demo: false };
    const ticket = { id: ticketId, subject: 'Anexar um recibo', message: 'Mensagem de apoio para testar anexos privados.', status: 'open', created_at: metadata.created_at };
    let items = [];
    let uploads = 0;
    let downloadStatus = 200;
    let uploadStatus = 201;
    let attachmentReads = 0;
    await page.route('**/api/v1/**', async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (path === '/api/v1/auth/session') return route.fulfill({ json: { user, csrf_token: csrf } });
      if (path === '/api/v1/cart') return route.fulfill({ json: { items: [] } });
      if (path === `/api/v1/${role === 'admin' ? 'admin/' : ''}support`) return route.fulfill({ json: { items: [ticket], total: 1, page: 1, page_size: 20 } });
      if (path === `/api/v1/support/${ticketId}/attachments`) {
        if (request.method() === 'GET') { attachmentReads++; return route.fulfill({ json: { items } }); }
        uploads++;
        assert.equal(request.method(), 'POST');
        assert.equal(request.headers()['x-csrf-token'], csrf);
        assert.match(request.headers()['content-type'], /^multipart\/form-data; boundary=/);
        assert.ok(request.postDataBuffer().includes(bytes));
        if (uploadStatus !== 201) return route.fulfill({ status: uploadStatus, json: { detail: 'Armazenamento privado indisponível.' } });
        items = [metadata];
        return route.fulfill({ status: 201, json: metadata });
      }
      if (path === `/api/v1/attachments/${attachmentId}`) {
        if (request.method() === 'DELETE') {
          assert.equal(request.headers()['x-csrf-token'], csrf);
          items = [];
          return route.fulfill({ status: 204 });
        }
        if (downloadStatus !== 200) return route.fulfill({ status: downloadStatus, json: { detail: 'Não tem permissão para este anexo.' } });
        return route.fulfill({ contentType: 'application/pdf', headers: { 'Cache-Control': 'no-store' }, body: bytes });
      }
      return route.fulfill({ status: 404, json: { detail: `Unexpected mocked endpoint: ${path}` } });
    });

    await page.goto(`${base}${role === 'admin' ? '/admin/apoio' : '/ajuda'}`);
    const details = page.locator('.support-attachments');
    await details.waitFor();
    assert.equal(attachmentReads, 0, 'Closed attachment sections must not fetch private metadata');
    await details.locator('summary').click();
    await details.getByText('Este pedido ainda não tem anexos.').waitFor();
    const fileInput = details.locator('input[type="file"]');
    await fileInput.setInputFiles({ name: filename, mimeType: 'application/pdf', buffer: Buffer.alloc(3 * 1024 * 1024 + 1) });
    await details.getByRole('button', { name: 'Enviar anexo' }).click();
    await details.getByRole('alert').filter({ hasText: '3 MiB' }).waitFor();
    assert.equal(uploads, 0, 'Oversized files must fail before any upload');

    await fileInput.setInputFiles({ name: filename, mimeType: 'application/pdf', buffer: bytes });
    uploadStatus = 503;
    await details.getByRole('button', { name: 'Enviar anexo' }).click();
    await details.getByRole('alert').filter({ hasText: 'Armazenamento privado' }).waitFor();
    assert.equal(items.length, 0);
    uploadStatus = 201;
    await details.getByRole('button', { name: 'Enviar anexo' }).click();
    await details.locator('.attachment-list strong').filter({ hasText: filename }).waitFor();
    assert.equal(uploads, 2);
    assert.equal(await fileInput.inputValue(), '');

    downloadStatus = 403;
    await details.getByRole('button', { name: `Descarregar anexo ${filename}` }).click();
    await details.getByRole('alert').filter({ hasText: 'permissão' }).waitFor();
    downloadStatus = 200;
    const downloadReady = page.waitForEvent('download');
    await details.getByRole('button', { name: `Descarregar anexo ${filename}` }).click();
    const download = await downloadReady;
    assert.equal(download.suggestedFilename(), filename);
    const stream = await download.createReadStream();
    const chunks = [];
    for await (const chunk of stream) chunks.push(chunk);
    assert.deepEqual(Buffer.concat(chunks), bytes);

    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    assert.deepEqual(axe.violations.map(({ id, nodes }) => ({ id, targets: nodes.map(({ target }) => target) })), []);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await details.getByRole('button', { name: `Eliminar anexo ${filename}` }).click();
    const dialog = page.getByRole('dialog', { name: 'Eliminar anexo' });
    await dialog.getByRole('button', { name: 'Cancelar', exact: true }).click();
    assert.equal(items.length, 1);
    await details.getByRole('button', { name: `Eliminar anexo ${filename}` }).click();
    await dialog.getByRole('button', { name: 'Eliminar anexo', exact: true }).click();
    await details.getByText('Este pedido ainda não tem anexos.').waitFor();
    assert.equal(items.length, 0);
    assert.deepEqual(storageRequests, []);
    assert.deepEqual(pageErrors, []);
    console.log(JSON.stringify({ role, width, upload: 'ok', download: 'ok', delete: 'ok', oversized: 'rejected', unavailable: 'reported', permission: 'reported', accessibilityViolations: 0 }));
    await context.close();
  }
} finally { await browser.close(); }
