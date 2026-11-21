'use client';

import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LockKeyhole, Trash2 } from 'lucide-react';
import { z } from 'zod';
import { toast } from 'sonner';
import { Button, Field, Modal } from '../components/ui';
import { api, ApiError, json } from '../lib/api';
import { useAuth, useHydrated } from '../lib/hooks';
import type { User } from '../types';

type Errors = Record<string, string>;
type Operation = 'profile' | 'password' | 'delete';
const value = (data: FormData, name: string) => String(data.get(name) ?? '');

function SecureFormNotice() {
  return <noscript><p className="inline-error" role="alert">Active o JavaScript para gerir a conta com segurança.</p></noscript>;
}

export function AccountProfileForms() {
  const { user, refresh } = useAuth();
  const hydrated = useHydrated();
  const router = useRouter();
  const inFlight = useRef(false);
  const [busy, setBusy] = useState<Operation | null>(null);
  const [email, setEmail] = useState(user?.email ?? '');
  const [profileErrors, setProfileErrors] = useState<Errors>({});
  const [passwordErrors, setPasswordErrors] = useState<Errors>({});
  const [deleteErrors, setDeleteErrors] = useState<Errors>({});
  const [profileSuccess, setProfileSuccess] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [deleteOpen, setDeleteOpen] = useState(false);
  if (!user) return null;

  const emailChanged = email.trim().toLowerCase() !== user.email.toLowerCase();
  const disabled = !hydrated || busy !== null;
  function start(operation: Operation) {
    if (!hydrated || inFlight.current) return false;
    inFlight.current = true;
    setBusy(operation);
    return true;
  }
  function finish() { inFlight.current = false; setBusy(null); }

  async function saveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user || !hydrated || inFlight.current) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const name = value(data, 'name').trim();
    const phone = value(data, 'phone').trim();
    const nextEmail = value(data, 'email').trim().toLowerCase();
    const currentPassword = value(data, 'current_password');
    const changingEmail = nextEmail !== user.email.toLowerCase();
    const errors: Errors = {};
    if (name.length < 2 || name.length > 120) errors.name = 'Indique um nome entre 2 e 120 caracteres.';
    if (phone.length > 30) errors.phone = 'Use no máximo 30 caracteres para o telemóvel.';
    if (!z.email().safeParse(nextEmail).success) errors.email = 'Introduza um email válido.';
    if (changingEmail && !currentPassword) errors.current_password = 'Introduza a palavra-passe actual para alterar o email.';
    setProfileErrors(errors);
    setProfileSuccess('');
    if (Object.keys(errors).length || !start('profile')) return;
    try {
      const updated = await api<User>('/me', { method: 'PATCH', body: json({ name, phone, email: nextEmail, ...(changingEmail ? { current_password: currentPassword } : {}) }) });
      const passwordInput = form.elements.namedItem('current_password');
      if (passwordInput instanceof HTMLInputElement) passwordInput.value = '';
      setEmail(updated.email);
      await refresh();
      setProfileSuccess(changingEmail ? 'Perfil actualizado. Use o novo email para iniciar sessão. As outras sessões foram terminadas.' : 'Perfil actualizado.');
    } catch (reason) {
      const error = reason as Error;
      setProfileErrors({ [reason instanceof ApiError && reason.status === 403 && changingEmail ? 'current_password' : reason instanceof ApiError && reason.status === 409 ? 'email' : 'form']: error.message });
    } finally { finish(); }
  }

  async function changePassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hydrated || inFlight.current) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const currentPassword = value(data, 'current_password');
    const newPassword = value(data, 'new_password');
    const errors: Errors = {};
    if (!currentPassword) errors.current_password = 'Introduza a palavra-passe actual.';
    if (newPassword.length < 12 || newPassword.length > 128) errors.new_password = 'Use entre 12 e 128 caracteres.';
    if (value(data, 'confirm_password') !== newPassword || !newPassword) errors.confirm_password = 'A confirmação deve ser igual à nova palavra-passe.';
    setPasswordErrors(errors);
    setPasswordSuccess('');
    if (Object.keys(errors).length || !start('password')) return;
    try {
      await api('/me/password', { method: 'POST', body: json({ current_password: currentPassword, new_password: newPassword }) });
      form.reset();
      await refresh();
      setPasswordSuccess('Palavra-passe alterada. As outras sessões foram terminadas.');
    } catch (reason) {
      setPasswordErrors({ [reason instanceof ApiError && reason.status === 403 ? 'current_password' : 'form']: (reason as Error).message });
    } finally { finish(); }
  }

  function toggleDelete(open: boolean) {
    if (inFlight.current) return;
    setDeleteErrors({});
    setDeleteOpen(open);
  }

  async function deleteAccount(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hydrated || inFlight.current) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const currentPassword = value(data, 'current_password');
    const confirmation = value(data, 'confirmation');
    const errors: Errors = {};
    if (!currentPassword) errors.current_password = 'Introduza a palavra-passe actual.';
    if (confirmation !== 'ELIMINAR') errors.confirmation = 'Escreva ELIMINAR, em maiúsculas, para confirmar.';
    setDeleteErrors(errors);
    if (Object.keys(errors).length || !start('delete')) return;
    try {
      await api('/me', { method: 'DELETE', body: json({ current_password: currentPassword, confirmation }) });
    } catch (reason) {
      setDeleteErrors({ [reason instanceof ApiError && reason.status === 403 ? 'current_password' : 'form']: (reason as Error).message });
      finish();
      return;
    }
    form.reset();
    await refresh();
    toast.success('Conta eliminada. A sua sessão foi terminada.');
    router.replace('/');
    router.refresh();
  }

  return <>
    <article className="panel" aria-labelledby="profile-title">
      <h2 id="profile-title">Dados pessoais</h2>
      <form className="form-stack" method="post" action="/conta" noValidate onSubmit={saveProfile} aria-busy={busy === 'profile'}>
        <SecureFormNotice />
        <fieldset className="form-stack" disabled={disabled}>
          <Field label="Nome completo" error={profileErrors.name}><input name="name" autoComplete="name" defaultValue={user.name} minLength={2} maxLength={120} required aria-invalid={Boolean(profileErrors.name)} /></Field>
          <Field label="Telemóvel" error={profileErrors.phone} hint="Pode deixar este campo vazio."><input name="phone" type="tel" autoComplete="tel" defaultValue={user.phone ?? ''} maxLength={30} aria-invalid={Boolean(profileErrors.phone)} /></Field>
          <Field label="Email" error={profileErrors.email} hint="Este email será utilizado para iniciar sessão."><input name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} maxLength={254} required aria-invalid={Boolean(profileErrors.email)} /></Field>
          {emailChanged && <>
            <p className="notice">Para alterar o email, confirme a palavra-passe actual. As outras sessões serão terminadas.</p>
            <Field label="Palavra-passe actual para alterar o email" error={profileErrors.current_password}><input name="current_password" type="password" autoComplete="current-password" maxLength={128} required aria-invalid={Boolean(profileErrors.current_password)} /></Field>
          </>}
          {profileErrors.form && <p className="inline-error" role="alert">{profileErrors.form}</p>}
          {profileSuccess && <p className="notice" role="status">{profileSuccess}</p>}
          <Button type="submit" busy={busy === 'profile'}>Guardar alterações</Button>
        </fieldset>
      </form>
    </article>
    <article className="panel" aria-labelledby="password-title">
      <h2 id="password-title">Alterar palavra-passe</h2>
      <form className="form-stack" method="post" action="/conta" noValidate onSubmit={changePassword} aria-busy={busy === 'password'}>
        <SecureFormNotice />
        <p className="muted">Use entre 12 e 128 caracteres. Ao guardar, as outras sessões serão terminadas.</p>
        <fieldset className="form-stack" disabled={disabled}>
          <Field label="Palavra-passe actual" error={passwordErrors.current_password}><input name="current_password" type="password" autoComplete="current-password" maxLength={128} required aria-invalid={Boolean(passwordErrors.current_password)} /></Field>
          <Field label="Nova palavra-passe" error={passwordErrors.new_password}><input name="new_password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required aria-invalid={Boolean(passwordErrors.new_password)} /></Field>
          <Field label="Confirmar nova palavra-passe" error={passwordErrors.confirm_password}><input name="confirm_password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required aria-invalid={Boolean(passwordErrors.confirm_password)} /></Field>
          {passwordErrors.form && <p className="inline-error" role="alert">{passwordErrors.form}</p>}
          {passwordSuccess && <p className="notice" role="status">{passwordSuccess}</p>}
          <Button type="submit" busy={busy === 'password'}><LockKeyhole size={16} />Alterar palavra-passe</Button>
        </fieldset>
      </form>
    </article>
    <article className="panel form-stack" aria-labelledby="delete-title">
      <h2 id="delete-title">Eliminar conta</h2>
      <p className="muted">Perderá o acesso à conta. Se tem uma loja, esta será suspensa e os seus produtos e serviços serão arquivados.</p>
      <p className="muted">O perfil será anonimizado. O histórico de encomendas, pagamentos, apoio e auditoria será conservado. Compromissos pendentes podem impedir a eliminação.</p>
      <Button type="button" variant="danger" disabled={disabled} onClick={() => toggleDelete(true)}><Trash2 size={16} />Eliminar a minha conta</Button>
    </article>
    <Modal open={deleteOpen} onOpenChange={toggleDelete} title="Confirmar eliminação da conta" description="Esta acção é definitiva e termina o seu acesso à plataforma.">
      <form className="form-stack" method="post" action="/conta" noValidate onSubmit={deleteAccount} aria-busy={busy === 'delete'}>
        <SecureFormNotice />
        <div className="notice" style={{ overflowWrap: 'anywhere' }}><strong>{user.name}</strong><br />{user.email}<p>O perfil será anonimizado e deixará de poder iniciar sessão. O histórico de encomendas, pagamentos, apoio e auditoria será conservado.</p></div>
        <fieldset className="form-stack" disabled={disabled}>
          <Field label="Palavra-passe actual" error={deleteErrors.current_password}><input name="current_password" type="password" autoComplete="current-password" maxLength={128} required aria-invalid={Boolean(deleteErrors.current_password)} /></Field>
          <Field label="Escreva ELIMINAR para confirmar" error={deleteErrors.confirmation}><input name="confirmation" autoComplete="off" autoCapitalize="characters" spellCheck={false} required aria-invalid={Boolean(deleteErrors.confirmation)} /></Field>
          {deleteErrors.form && <p className="inline-error" role="alert">{deleteErrors.form}</p>}
          <div className="button-row"><Button type="button" variant="secondary" disabled={busy !== null} onClick={() => toggleDelete(false)}>Manter a minha conta</Button><Button type="submit" variant="danger" busy={busy === 'delete'}>Confirmar eliminação</Button></div>
        </fieldset>
      </form>
    </Modal>
  </>;
}
