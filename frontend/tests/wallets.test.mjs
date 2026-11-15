import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/lib/wallets.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { walletSettingsFromForm } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const form = (values) => { const data = new FormData(); for (const [key, value] of Object.entries(values)) data.set(key, value); return data; };

test('normalises wallet numbers without dropping the declared account holder', () => {
  assert.deepEqual(walletSettingsFromForm(form({ mpesa_phone: '+258 84 123 4567', mpesa_account_name: '  Loja da Maria  ', emola_phone: '861234567', emola_account_name: 'Adelino João' })), { mpesa_phone: '841234567', mpesa_account_name: 'Loja da Maria', emola_phone: '861234567', emola_account_name: 'Adelino João' });
});

test('accepts nine local digits without inferring the wallet operator from a prefix', () => {
  const result = walletSettingsFromForm(form({ mpesa_phone: '258 123 456 789', mpesa_account_name: 'Loja Um' }));
  assert.equal(result.mpesa_phone, '123456789');
});

test('clearing wallet pairs sends nulls so a removed recipient is not retained', () => {
  assert.deepEqual(walletSettingsFromForm(form({ mpesa_phone: '  ', mpesa_account_name: '' })), { mpesa_phone: null, mpesa_account_name: null, emola_phone: null, emola_account_name: null });
});

test('never submits an incomplete recipient or a foreign / malformed wallet number', () => {
  for (const values of [{ mpesa_phone: '841234567' }, { emola_account_name: 'Maria' }, { mpesa_phone: '+27 841234567', mpesa_account_name: 'Maria' }, { emola_phone: '86123456', emola_account_name: 'Maria' }, { emola_phone: '861234567', emola_account_name: 'M' }]) assert.throws(() => walletSettingsFromForm(form(values)));
});
