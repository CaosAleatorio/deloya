import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/lib/attachments.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { attachmentFileError, attachmentSize, MAX_ATTACHMENT_BYTES } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);

test('attachment preflight accepts supported files up to the exact 3 MiB boundary', () => {
  for (const [name, type] of [['recibo.PDF', 'application/pdf'], ['foto.jpg', 'image/jpeg'], ['foto.JPEG', 'image/jpeg'], ['foto.png', 'image/png'], ['foto.webp', 'image/webp']]) {
    assert.equal(attachmentFileError({ name, type, size: MAX_ATTACHMENT_BYTES }), null);
  }
});

test('attachment preflight rejects empty, oversized, unsupported and mismatched files', () => {
  assert.match(attachmentFileError({ name: 'recibo.pdf', type: 'application/pdf', size: 0 }), /vazio/);
  assert.match(attachmentFileError({ name: 'recibo.pdf', type: 'application/pdf', size: MAX_ATTACHMENT_BYTES + 1 }), /3 MiB/);
  for (const [name, type] of [['script.html', 'text/html'], ['foto.pdf', 'image/jpeg'], ['recibo', 'application/pdf'], ['recibo.pdf.exe', 'application/pdf'], ['foto.png', '']]) {
    assert.match(attachmentFileError({ name, type, size: 1024 }), /extensão correcta/);
  }
});

test('attachment sizes show binary units matching the upload limit', () => {
  assert.equal(attachmentSize(1024), '1 KiB');
  assert.equal(attachmentSize(MAX_ATTACHMENT_BYTES), '3 MiB');
});
