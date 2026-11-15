import type { Order, Payment, VendorOrder } from '../types';

export function manualPaymentState(vendor: Pick<VendorOrder, 'status' | 'payments'>): 'paid' | 'awaiting' | 'available' | 'closed' {
  if (vendor.payments?.some((payment) => payment.status === 'success') || ['paga', 'em_preparacao', 'pronta', 'entregue'].includes(vendor.status)) return 'paid';
  if (vendor.status === 'cancelada') return 'closed';
  if (vendor.payments?.some((payment) => payment.status === 'pending')) return 'awaiting';
  return vendor.status === 'pendente_pagamento' ? 'available' : 'closed';
}

export function canCancelOrder(order: Pick<Order, 'can_cancel' | 'status' | 'vendor_orders'>): boolean {
  if (order.can_cancel !== undefined) return order.can_cancel;
  return order.status === 'pendente_pagamento' && order.vendor_orders.every((vendor) => manualPaymentState(vendor) === 'available');
}

export const paymentStatusLabel = (payment: Pick<Payment, 'payment_mode' | 'status'>) => payment.payment_mode === 'manual' ? ({ pending: 'Aguarda confirmação do vendedor', success: 'Recebimento confirmado pelo vendedor', failure: 'Referência recusada pelo vendedor', expired: 'Expirada' }[payment.status] ?? payment.status) : null;
