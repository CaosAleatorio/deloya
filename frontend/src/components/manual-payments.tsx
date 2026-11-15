'use client';

import { useRef, useState } from 'react';
import { ArrowRight, CheckCircle2, Store as StoreIcon } from 'lucide-react';
import { toast } from 'sonner';
import { api, createIdempotencyKey, date, json, money, statusLabel } from '../lib/api';
import { manualPaymentState, paymentStatusLabel } from '../lib/payment-state';
import { useQuery } from '../lib/hooks';
import { walletProviderName } from '../lib/wallets';
import { Badge, Button, DemoNotice, Empty, ErrorPanel, Field, Loading, Modal, PageControls } from './ui';
import type { Order, Page, Payment, VendorOrder } from '../types';

export function PaymentHistory({ payments }: { payments?: Payment[] }) {
  if (!payments?.length) return null;
  return <div className="manual-payment-history">{payments.map((payment) => <div key={payment.id}><Badge tone={payment.status === 'success' ? 'green' : 'orange'}>{paymentStatusLabel(payment) ?? statusLabel(payment.status)}</Badge><p><strong>{walletProviderName(payment.provider)}</strong> · {money(payment.amount)}{payment.transfer_reference && <> · Referência enviada: <strong>{payment.transfer_reference}</strong></>}{payment.created_at && <> · {date(payment.created_at)}</>}</p>{payment.review_notes && <p>Nota do vendedor: {payment.review_notes}</p>}{payment.status === 'success' && <p>{payment.is_demo ? 'Confirmação de teste. Sem movimentação de dinheiro.' : 'O vendedor declarou ter recebido a transferência. Esta confirmação não é uma validação da operadora.'}</p>}</div>)}</div>;
}

function ManualVendorPayment({ order, vendor, onChange }: { order: Order; vendor: VendorOrder; onChange?: () => void }) {
  const destinations = vendor.payment_destinations ?? {};
  const options = (['mpesa', 'emola'] as const).filter((provider) => destinations[provider]);
  const [provider, setProvider] = useState<'mpesa' | 'emola'>(options[0] ?? 'mpesa');
  const [busy, setBusy] = useState(false);
  const attempt = useRef({ fingerprint: '', key: '' });
  const state = manualPaymentState(vendor);
  const isDemo = order.is_demo || vendor.is_demo === true;
  const destination = destinations[provider];
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setBusy(true);
    try {
      const values = new FormData(form);
      const reference = String(values.get('reference') ?? '').trim();
      const notes = String(values.get('notes') ?? '').trim() || null;
      const fingerprint = JSON.stringify({ provider, reference, notes });
      if (attempt.current.fingerprint !== fingerprint) attempt.current = { fingerprint, key: createIdempotencyKey() };
      await api(`/orders/${order.id}/vendor-orders/${vendor.id}/payments`, { method: 'POST', body: json({ provider, reference, notes, idempotency_key: attempt.current.key }) });
      await onChange?.();
      toast.success(isDemo ? 'Referência de teste enviada. Aguarda confirmação do vendedor.' : 'Referência enviada. Aguarda confirmação do vendedor.');
    } catch (error) { toast.error((error as Error).message); } finally { setBusy(false); }
  }
  return <article className="manual-payment"><div className="section-heading"><div><span className="eyebrow"><StoreIcon size={14} /> TRANSFERÊNCIA PARA ESTA LOJA</span><h3>{vendor.store.name}</h3></div><Badge tone={state === 'paid' ? 'green' : 'orange'}>{state === 'awaiting' ? 'Aguarda confirmação' : statusLabel(vendor.status)}</Badge></div><p>Valor desta loja, calculado pelo servidor: <strong>{money(vendor.total)}</strong></p>{isDemo && <div className="notice"><strong>Transferência de teste.</strong> Não envie dinheiro para nenhum dos números apresentados. Introduza apenas uma referência fictícia para testar a confirmação.</div>}<PaymentHistory payments={vendor.payments} />{state === 'paid' && <p className="manual-payment-summary"><CheckCircle2 size={16} /> {isDemo ? 'Pagamento de teste confirmado para esta loja.' : 'O vendedor confirmou o recebimento para esta loja.'}</p>}{state === 'awaiting' && <div className="notice">A referência está com o vendedor. Aguarde que confira a sua carteira; não repita a transferência. As restantes lojas têm pagamentos separados.</div>}{state === 'available' && order.status !== 'cancelada' && (options.length && destination ? <><Field label="Carteira desta loja"><select value={provider} onChange={(event) => setProvider(event.target.value as 'mpesa' | 'emola')}>{options.map((option) => <option key={option} value={option}>{walletProviderName(option)} · {option === 'mpesa' ? 'Vodacom' : 'Movitel'}</option>)}</select></Field><div className="wallet-recipient"><p>{walletProviderName(provider)} · Número: <strong>{destination.phone}</strong></p><p>Nome do titular: <strong>{destination.account_name}</strong></p><p>Dados declarados pelo vendedor e guardados nesta encomenda.</p></div>{!isDemo && <ol className="manual-payment-instructions"><li>Abra a sua carteira {walletProviderName(provider)} e escolha transferir para o número acima.</li><li>Antes de confirmar, confira o nome do destinatário apresentado pela operadora. Se não corresponder, pare e contacte a loja.</li><li>Transfira apenas <strong>{money(vendor.total)}</strong> para esta loja e guarde a referência.</li><li>Comunique a referência abaixo para o vendedor conferir o recebimento.</li></ol>}<form className="form-stack" onSubmit={submit}><Field label={isDemo ? 'Referência fictícia de teste' : 'Referência da transferência'} hint={isDemo ? 'Ex.: TESTE-12345. Não transfira dinheiro.' : 'Copie a referência fornecida pela sua carteira após a transferência.'}><input name="reference" minLength={3} maxLength={120} required autoComplete="off" /></Field><Field label="Nota para o vendedor (opcional)"><textarea name="notes" rows={2} maxLength={1000} /></Field><label className="checkbox-label"><input type="checkbox" required /><span>{isDemo ? 'Compreendo que este registo é de teste e não corresponde a dinheiro transferido.' : 'Já fiz a transferência para este destinatário e compreendo que o vendedor precisa de conferir o recebimento.'}</span></label><p className="form-help">Nunca introduza o PIN, código de acesso ou palavra-passe da carteira.</p><Button busy={busy}>Enviar referência{isDemo ? ' de teste' : ''}<ArrowRight size={16} /></Button></form></> : <div className="notice">Esta encomenda não tem uma carteira configurada para a loja. Contacte o vendedor antes de transferir. Uma alteração na loja não modifica os destinatários já guardados nesta encomenda.</div>)}</article>;
}

export function ManualPayments({ order, onChange }: { order: Order; onChange?: () => void }) {
  return <div className="panel payment-panel"><div className="section-heading"><div><span className="eyebrow">ENCOMENDA {order.reference}</span><h2>Transferência directa ao vendedor</h2></div><Badge>{statusLabel(order.status)}</Badge></div><p>Total da encomenda: <strong>{money(order.total)}</strong></p>{order.is_demo && <DemoNotice />}<p className="manual-payment-summary">Cada loja recebe o seu próprio valor. {order.vendor_orders.length > 1 ? 'Faça uma transferência por loja; pagar uma loja não paga as restantes.' : 'O pagamento fica a aguardar a confirmação do vendedor.'} A Deloya regista a referência e a decisão do vendedor, sem consultar a operadora.</p>{order.status === 'parcialmente_paga' && <div className="notice">Pagamento parcial: consulte cada loja abaixo para saber qual já confirmou e qual ainda aguarda pagamento ou conferência.</div>}<div className="manual-payments">{order.vendor_orders.map((vendor) => <ManualVendorPayment key={vendor.id} order={order} vendor={vendor} onChange={onChange} />)}</div></div>;
}

export function VendorPaymentQueue() {
  const [status, setStatus] = useState('pending');
  const [page, setPage] = useState(1);
  const query = useQuery<Page<Payment>>(`/vendor/payments?status=${status}&page=${page}&page_size=20`);
  const store = useQuery<{ status: string }>('/vendor/store');
  const canConfirm = store.data?.status === 'approved';
  const [review, setReview] = useState<{ payment: Payment; decision: 'confirm' | 'reject' } | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!review) return;
    const form = new FormData(event.currentTarget);
    setBusy(true);
    try {
      await api(`/vendor/orders/${review.payment.vendor_order_id}/payments/${review.payment.id}/review`, { method: 'POST', body: json({ decision: review.decision, wallet_verified: form.get('wallet_verified') === 'on', notes: String(form.get('notes') ?? '').trim() || null }) });
      setReview(null);
      query.reload();
      toast.success(review.decision === 'confirm' ? 'Recebimento confirmado para a sua loja.' : 'Referência recusada. O cliente poderá enviar uma nova referência.');
    } catch (error) { toast.error((error as Error).message); } finally { setBusy(false); }
  }
  return <><div className="notice">Confira a referência, o montante e o destinatário no histórico da sua própria carteira antes de confirmar. A Deloya não consulta a operadora. Não basta receber uma mensagem ou uma referência do comprador.</div>{store.error && <p className="inline-error" role="alert">Não foi possível confirmar o estado da loja. A confirmação de recebimentos fica indisponível até actualizar esta página.</p>}{store.data && !canConfirm && <div className="notice">A loja precisa de estar aprovada para confirmar recebimentos. Pode consultar e recusar uma referência pendente, indicando o motivo ao cliente.</div>}<div className="toolbar"><Field label="Estado da conferência"><select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="pending">Aguardam confirmação</option><option value="success">Confirmados pelo vendedor</option><option value="failure">Referências recusadas</option><option value="">Todos</option></select></Field></div>{query.loading ? <Loading /> : query.error ? <ErrorPanel message={query.error} retry={query.reload} /> : query.data?.items.length ? <div className="orders-list">{query.data.items.map((payment) => <article className="panel" key={payment.id}><div className="section-heading"><div><span className="eyebrow">{payment.order_reference ?? payment.reference}</span><h2>{money(payment.amount)} · {walletProviderName(payment.provider)}</h2></div><Badge tone={payment.status === 'success' ? 'green' : 'orange'}>{paymentStatusLabel(payment) ?? statusLabel(payment.status)}</Badge></div>{payment.is_demo && <DemoNotice />}<p>Referência comunicada pelo cliente: <strong>{payment.transfer_reference}</strong></p>{payment.destination && <div className="wallet-recipient"><p>Carteira guardada nesta encomenda: <strong>{payment.destination.phone}</strong></p><p>Titular declarado: <strong>{payment.destination.account_name}</strong></p></div>}{payment.notes && <p>Nota do cliente: {payment.notes}</p>}{payment.created_at && <p className="form-help">Comunicada em {date(payment.created_at)}</p>}{payment.review_notes && <p>Nota da conferência: {payment.review_notes}</p>}{payment.status === 'pending' && <div className="button-row row-spacing"><Button disabled={!canConfirm} onClick={() => setReview({ payment, decision: 'confirm' })}>{payment.is_demo ? 'Confirmar teste' : 'Conferir e confirmar recebimento'}</Button><Button variant="secondary" onClick={() => setReview({ payment, decision: 'reject' })}>Recusar referência</Button></div>}</article>)}</div> : <Empty title="Sem referências neste estado" message="As referências enviadas pelos clientes da sua loja aparecem aqui." />}{query.data && <PageControls page={page} total={query.data.total} onPage={setPage} />}<Modal open={Boolean(review)} onOpenChange={(open) => { if (!open && !busy) setReview(null); }} title={review?.decision === 'confirm' ? 'Confirmar recebimento desta loja' : 'Recusar referência'} description={review?.payment.is_demo ? 'Registo de teste. Não confirme nem solicite uma transferência real.' : 'A sua decisão fica registada e é apresentada ao cliente.'}>{review && <form className="form-stack" onSubmit={submit}><p>{walletProviderName(review.payment.provider)} · <strong>{money(review.payment.amount)}</strong></p><p>Referência: <strong>{review.payment.transfer_reference}</strong></p>{review.decision === 'confirm' ? <label className="checkbox-label"><input type="checkbox" name="wallet_verified" required /><span>{review.payment.is_demo ? 'Confirmo apenas este registo de teste. Não houve movimentação de dinheiro.' : 'Consultei a minha carteira e confirmei o recebimento deste montante, com esta referência e neste destinatário.'}</span></label> : <p>A recusa mantém a encomenda por pagar e permite ao cliente corrigir a referência. Não cancela uma transferência nem devolve dinheiro.</p>}<Field label={review.decision === 'reject' ? 'Motivo da recusa' : 'Nota da conferência (opcional)'}><textarea name="notes" rows={3} maxLength={1000} minLength={review.decision === 'reject' ? 3 : undefined} required={review.decision === 'reject'} /></Field><Button type="submit" busy={busy} variant={review.decision === 'reject' ? 'danger' : 'primary'}>{review.decision === 'confirm' ? 'Confirmar este recebimento' : 'Registar recusa'}</Button></form>}</Modal></>;
}
