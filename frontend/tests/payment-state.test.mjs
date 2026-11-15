import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/lib/payment-state.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { canCancelOrder, manualPaymentState, paymentStatusLabel } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const vendor = (status = 'pendente_pagamento', payments = []) => ({ status, payments });

test('a pending transfer awaits seller review and cannot be resubmitted as unpaid', () => {
  assert.equal(manualPaymentState(vendor('pendente_pagamento', [{ status: 'pending' }])), 'awaiting');
  assert.equal(canCancelOrder({ status: 'pendente_pagamento', vendor_orders: [vendor('pendente_pagamento', [{ status: 'pending' }])] }), false);
});

test('one confirmed store leaves another store payable and blocks whole-order cancellation', () => {
  const paid = vendor('paga', [{ status: 'success' }]);
  const unpaid = vendor();
  assert.equal(manualPaymentState(paid), 'paid');
  assert.equal(manualPaymentState(unpaid), 'available');
  assert.equal(canCancelOrder({ status: 'parcialmente_paga', vendor_orders: [paid, unpaid] }), false);
});

test('rejected references allow retry; the server cancellation decision is authoritative', () => {
  const unpaid = vendor('pendente_pagamento', [{ status: 'failure' }]);
  assert.equal(manualPaymentState(unpaid), 'available');
  assert.equal(canCancelOrder({ can_cancel: false, status: 'pendente_pagamento', vendor_orders: [unpaid] }), false);
  assert.equal(manualPaymentState(vendor('cancelada')), 'closed');
});

test('manual success is explicitly attributed to the seller rather than the wallet operator', () => {
  assert.equal(paymentStatusLabel({ payment_mode: 'manual', status: 'success' }), 'Recebimento confirmado pelo vendedor');
  assert.equal(paymentStatusLabel({ payment_mode: 'manual', status: 'pending' }), 'Aguarda confirmação do vendedor');
  assert.equal(paymentStatusLabel({ payment_mode: 'demo', status: 'success' }), null);
});
