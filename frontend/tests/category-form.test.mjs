import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/lib/category-form.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { categoryFormValues, normalizeCategorySlug } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
function form(values) { const data = new FormData(); for (const [key, value] of Object.entries(values)) data.set(key, value); return data; }

test('the first category only needs a name and leaves slug generation to the server', () => {
  const result = categoryFormValues(form({ name: '  Saúde e Beleza  ', slug: '  ', parent_id: '' }));
  assert.deepEqual(result.errors, {});
  assert.deepEqual(JSON.parse(JSON.stringify(result.values)), { name: 'Saúde e Beleza', parent_id: null });
});

test('normalises a supplied Portuguese identifier and preserves a chosen parent', () => {
  const result = categoryFormValues(form({ name: 'Telemóveis', slug: '  Saúde & Beleza / Nampula  ', parent_id: 'parent-1' }));
  assert.deepEqual(result, { values: { name: 'Telemóveis', slug: 'saude-beleza-nampula', parent_id: 'parent-1' }, errors: {} });
  assert.equal(normalizeCategorySlug('já-normalizado-123'), 'ja-normalizado-123');
});

test('rejects missing names and supplied identifiers that cannot satisfy the API schema', () => {
  for (const name of ['', ' ', 'a', 'x'.repeat(101)]) assert.ok(categoryFormValues(form({ name })).errors.name);
  for (const slug of ['!!!', 'a', 'x'.repeat(121)]) assert.ok(categoryFormValues(form({ name: 'Categoria', slug })).errors.slug);
});
