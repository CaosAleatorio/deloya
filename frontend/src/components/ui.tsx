'use client';

import * as Dialog from '@radix-ui/react-dialog';
import { AlertCircle, ArrowRight, LoaderCircle, PackageOpen, X } from 'lucide-react';
import Link from 'next/link';
import { Button as ButtonPrimitive } from './ui/button';

export { cn } from '../lib/utils';
export function Button({ className, children, busy, variant = 'primary', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { busy?: boolean; variant?: 'primary' | 'secondary' | 'ghost' | 'danger' }) {
  return <ButtonPrimitive variant={variant === 'primary' ? 'default' : variant === 'danger' ? 'destructive' : variant} className={className} {...props} disabled={busy || props.disabled}>{busy && <LoaderCircle size={17} className="spin" />}{children}</ButtonPrimitive>;
}
export function Field({ label, error, children, hint }: { label: string; error?: string; children: React.ReactNode; hint?: string }) {
  return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}{error && <small className="field-error" role="alert">{error}</small>}</label>;
}
export function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'green' | 'orange' }) { return <span className={`badge badge-${tone}`}>{children}</span>; }
export function Loading() { return <div className="state-panel" role="status"><LoaderCircle className="spin" size={26} /><p>A carregar…</p></div>; }
export function ErrorPanel({ message, retry }: { message: string; retry?: () => void }) { return <div className="state-panel error-panel" role="alert"><AlertCircle size={25} /><h3>Não foi possível carregar os dados</h3><p>{message}</p>{retry && <Button variant="secondary" onClick={retry}>Tentar novamente</Button>}</div>; }
export function Empty({ title = 'Ainda não há resultados', message = 'Experimente outros filtros ou volte mais tarde.', href, action }: { title?: string; message?: string; href?: string; action?: string }) { return <div className="state-panel"><PackageOpen size={32} /><h3>{title}</h3><p>{message}</p>{href && <Link className="button button-primary" href={href}>{action ?? 'Explorar catálogo'}<ArrowRight size={16} /></Link>}</div>; }
export function DemoNotice() { return <div className="demo-notice"><span className="status-dot" /><span><strong>PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO</strong><small>Os dados de teste não representam vendas nem dinheiro recebido.</small></span></div>; }
export function PageControls({ page, total, pageSize = 20, onPage }: { page: number; total: number; pageSize?: number; onPage: (page: number) => void }) {
  if (total <= pageSize) return null;
  return <nav className="pagination" aria-label="Paginação"><Button variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>Anterior</Button><span>Página {page} de {Math.ceil(total / pageSize)}</span><Button variant="secondary" disabled={page * pageSize >= total} onClick={() => onPage(page + 1)}>Seguinte</Button></nav>;
}
export function Modal({ open, onOpenChange, onCloseAutoFocus, title, description, children }: { open: boolean; onOpenChange: (value: boolean) => void; onCloseAutoFocus?: (event: Event) => void; title: string; description?: string; children: React.ReactNode }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="modal-overlay" /><Dialog.Content className="modal-content" onCloseAutoFocus={onCloseAutoFocus}><div className="section-heading"><div><Dialog.Title>{title}</Dialog.Title><Dialog.Description>{description ?? 'Preencha os campos abaixo.'}</Dialog.Description></div><Dialog.Close className="icon-button" aria-label="Fechar"><X size={20} /></Dialog.Close></div>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}
