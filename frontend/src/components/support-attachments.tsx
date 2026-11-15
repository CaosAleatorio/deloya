'use client';

import { useState } from 'react';
import { Download, Paperclip, Trash2, Upload } from 'lucide-react';
import { api, apiBlob, date } from '../lib/api';
import { ATTACHMENT_ACCEPT, attachmentFileError, attachmentSize, MAX_TICKET_ATTACHMENTS } from '../lib/attachments';
import { useQuery } from '../lib/hooks';
import { Button, Field, Modal } from './ui';

type Attachment = { id: string; ticket_id: string; filename: string; content_type: string; size_bytes: number; created_at: string; uploaded_by: string };

function AttachmentContents({ ticketId }: { ticketId: string }) {
  const query = useQuery<{ items: Attachment[] }>(`/support/${ticketId}/attachments`);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [removing, setRemoving] = useState<Attachment | null>(null);
  const items = query.data?.items ?? [];
  const canUpload = Boolean(query.data) && !query.loading && !query.error && items.length < MAX_TICKET_ATTACHMENTS;

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = new FormData(form).get('file');
    setError('');
    setNotice('');
    if (!(file instanceof File)) { setError('Escolha um ficheiro para anexar.'); return; }
    const invalid = attachmentFileError(file);
    if (invalid) { setError(invalid); return; }
    const body = new FormData();
    body.set('file', file);
    setBusy('upload');
    try {
      await api(`/support/${ticketId}/attachments`, { method: 'POST', body });
      form.reset();
      query.reload();
      setNotice('Anexo enviado.');
    } catch (reason) { setError((reason as Error).message); }
    finally { setBusy(''); }
  }

  async function download(item: Attachment) {
    setBusy(`download:${item.id}`);
    setError('');
    setNotice('');
    try {
      const bytes = await apiBlob(`/attachments/${item.id}`);
      const localUrl = URL.createObjectURL(bytes);
      const anchor = document.createElement('a');
      anchor.href = localUrl;
      anchor.download = item.filename;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(localUrl), 60_000);
      setNotice('Ficheiro pronto para descarregar.');
    } catch (reason) { setError((reason as Error).message); }
    finally { setBusy(''); }
  }

  async function remove() {
    if (!removing) return;
    setBusy(removing.id);
    setError('');
    setNotice('');
    try {
      await api(`/attachments/${removing.id}`, { method: 'DELETE' });
      setRemoving(null);
      query.reload();
      setNotice('Anexo eliminado.');
    } catch (reason) { setRemoving(null); setError((reason as Error).message); }
    finally { setBusy(''); }
  }

  return <div className="attachment-content" aria-busy={Boolean(busy)}>
    <p className="form-help">Disponíveis apenas para o autor deste pedido e para a administração da Deloya. Não envie palavras-passe nem PINs.</p>
    {query.loading ? <p role="status">A carregar anexos…</p> : query.error ? <div className="inline-error" role="alert"><p>{query.error}</p><Button type="button" variant="ghost" onClick={query.reload}>Tentar novamente</Button></div> : items.length ? <ul className="attachment-list">{items.map((item) => <li key={item.id}>
      <div><strong>{item.filename}</strong><small>{attachmentSize(item.size_bytes)} · {date(item.created_at)}</small></div>
      <div className="button-row"><Button type="button" variant="ghost" busy={busy === `download:${item.id}`} disabled={Boolean(busy)} onClick={() => download(item)} aria-label={`Descarregar anexo ${item.filename}`}><Download size={15} />Descarregar</Button><Button type="button" variant="ghost" disabled={Boolean(busy)} onClick={() => setRemoving(item)} aria-label={`Eliminar anexo ${item.filename}`}><Trash2 size={15} />Eliminar</Button></div>
    </li>)}</ul> : <p className="muted">Este pedido ainda não tem anexos.</p>}
    {error && <p className="inline-error" role="alert">{error}</p>}
    {notice && <p className="form-help" role="status">{notice}</p>}
    <form className="form-stack attachment-form" onSubmit={upload}>
      <Field label="Adicionar anexo privado" hint="PDF, JPEG, PNG ou WebP. Até 3 MiB por ficheiro e 10 anexos por pedido."><input name="file" type="file" accept={ATTACHMENT_ACCEPT} required disabled={!canUpload || Boolean(busy)} /></Field>
      <Button type="submit" variant="secondary" busy={busy === 'upload'} disabled={!canUpload || Boolean(busy)}><Upload size={15} />Enviar anexo</Button>
      {items.length >= MAX_TICKET_ATTACHMENTS && <p className="form-help">O pedido atingiu o limite de 10 anexos. Elimine um ficheiro antes de enviar outro.</p>}
    </form>
    <Modal open={Boolean(removing)} onOpenChange={(open) => { if (!busy && !open) setRemoving(null); }} title="Eliminar anexo" description="O ficheiro deixará de estar disponível neste pedido."><p className="attachment-filename">{removing?.filename}</p><div className="button-row"><Button type="button" variant="secondary" disabled={Boolean(busy)} onClick={() => setRemoving(null)}>Cancelar</Button><Button type="button" variant="danger" busy={Boolean(busy)} onClick={remove}>Eliminar anexo</Button></div></Modal>
  </div>;
}

export function SupportAttachments({ ticketId }: { ticketId: string }) {
  const [expanded, setExpanded] = useState(false);
  return <details className="support-attachments" onToggle={(event) => setExpanded(event.currentTarget.open)}><summary><Paperclip size={16} aria-hidden="true" />Anexos privados</summary>{expanded && <AttachmentContents ticketId={ticketId} />}</details>;
}
