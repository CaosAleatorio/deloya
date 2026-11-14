import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const workspace = fileURLToPath(new URL('../', import.meta.url));
process.env.PLAYWRIGHT_BROWSERS_PATH ??= resolve(workspace, '.local/browsers');
const { chromium } = await import('../.local/browser-qa/node_modules/playwright/index.mjs');
const { default: AxeBuilder } = await import('../.local/browser-qa/node_modules/@axe-core/playwright/dist/index.mjs');
const base = process.env.QA_BASE_URL ?? 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const results = [];
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, locale: 'pt-MZ' });
    const page = await context.newPage();
    for (const path of ['/', '/produtos', '/login', '/registo']) {
      await page.goto(`${base}${path}`);
      if (path === '/' || path === '/produtos') await page.locator('.product-card').first().waitFor();
      else await page.locator('form.form-stack').waitFor();
      const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
      const violations = result.violations.map((entry) => ({ id: entry.id, impact: entry.impact, description: entry.description,
        nodes: entry.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })) }));
      results.push({ width, path, violations });
      console.log(JSON.stringify({ width, path, violations: violations.map((entry) => ({ id: entry.id, count: entry.nodes.length, samples: entry.nodes.slice(0, 3) })) }));
    }
    await context.close();
  }
  await mkdir(resolve(workspace, '.local/browser-results'), { recursive: true });
  await writeFile(resolve(workspace, '.local/browser-results/accessibility.json'), JSON.stringify(results, null, 2));
  if (results.some((result) => result.violations.length)) process.exitCode = 1;
} finally { await browser.close(); }
