export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

function csrfToken() {
  return document.cookie.split('; ').find((cookie) => cookie.startsWith('csrf_token='))?.split('=').slice(1).join('=') ?? '';
}

let refreshInFlight: Promise<boolean> | null = null;
async function renewSession() {
  if (!refreshInFlight) refreshInFlight = fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include', headers: { 'X-CSRF-Token': decodeURIComponent(csrfToken()) }, cache: 'no-store' }).then((response) => response.ok).catch(() => false).finally(() => { refreshInFlight = null; });
  return refreshInFlight;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase();
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    if (!csrfToken()) await fetch('/api/v1/auth/session', { credentials: 'include', cache: 'no-store' });
    headers.set('X-CSRF-Token', decodeURIComponent(csrfToken()));
  }
  let response = await fetch(`/api/v1${path}`, { ...options, headers, credentials: 'include', cache: 'no-store' });
  if (response.status === 401 && !path.startsWith('/auth/') && await renewSession()) {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers.set('X-CSRF-Token', decodeURIComponent(csrfToken()));
    response = await fetch(`/api/v1${path}`, { ...options, headers, credentials: 'include', cache: 'no-store' });
  }
  if (!response.ok) {
    let message = response.status === 401 ? 'Inicie sessão para continuar.' : response.status === 403 ? 'Não tem permissão para esta operação.' : 'Não foi possível comunicar com o serviço. Tente novamente.';
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((entry: { msg: string }) => entry.msg).join(' · ');
    } catch { /* Preserve a readable error for unavailable API servers. */ }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const json = (value: unknown) => JSON.stringify(value);
export const money = (value: string | number | null | undefined) => value == null ? 'Sob consulta' : `${new Intl.NumberFormat('pt-MZ', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value))} MT`;
export const date = (value: string) => new Intl.DateTimeFormat('pt-MZ', { timeZone: 'Africa/Maputo' }).format(new Date(value));
export const requestedDate = (value: FormDataEntryValue | null) => value ? `${value}T00:00:00+02:00` : null;
export const statusLabel = (value: string) => ({ pending: 'Pendente', approved: 'Aprovada', suspended: 'Suspensa', active: 'Activo', draft: 'Rascunho', published: 'Publicado', pending_payment: 'Aguarda pagamento', paid: 'Paga', preparing: 'Em preparação', ready: 'Pronta', delivered: 'Entregue', cancelled: 'Cancelada', failed: 'Falhou', expired: 'Expirado', success: 'Concluído', completed: 'Concluída', requested: 'Solicitado', confirmed: 'Confirmado', declined: 'Recusado', pending_approval: 'Aguarda aprovação', pendente_pagamento: 'Aguarda pagamento', paga: 'Paga', em_preparacao: 'Em preparação', pronta: 'Pronta', entregue: 'Entregue', cancelada: 'Cancelada' }[value] ?? value.replaceAll('_', ' '));
