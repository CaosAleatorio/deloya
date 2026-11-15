'use client';

import { useState } from 'react';
import { Field } from './ui';
import { walletProviderName, type WalletSettings } from '../lib/wallets';

function WalletPair({ provider, initial }: { provider: 'mpesa' | 'emola'; initial?: WalletSettings }) {
  const [phone, setPhone] = useState(initial?.[`${provider}_phone`] ?? '');
  const [name, setName] = useState(initial?.[`${provider}_account_name`] ?? '');
  const label = walletProviderName(provider);
  return <div className="wallet-pair"><h3>{label} · {provider === 'mpesa' ? 'Vodacom' : 'Movitel'}</h3><div className="two-columns"><Field label={`Número ${label}`} hint="Nove dígitos. Pode incluir +258."><input name={`${provider}_phone`} type="tel" autoComplete="off" inputMode="tel" maxLength={24} value={phone} onChange={(event) => setPhone(event.target.value)} required={Boolean(name.trim())} placeholder="+258 8X XXX XXXX" /></Field><Field label={`Nome do titular ${label}`} hint="Escreva o nome exactamente como aparece na carteira."><input name={`${provider}_account_name`} autoComplete="off" minLength={2} maxLength={160} value={name} onChange={(event) => setName(event.target.value)} required={Boolean(phone.trim())} /></Field></div></div>;
}

export function WalletFields({ initial, isDemo = false }: { initial?: WalletSettings; isDemo?: boolean }) {
  return <fieldset className="wallet-fields"><legend>Receber por carteira móvel</legend><p>Configure M-Pesa, e-Mola ou ambas para receber directamente dos clientes. Pode actualizar estes dados na sua loja. Preencha sempre o número e o nome do titular juntos.</p>{isDemo && <div className="notice">Loja de teste: estes dados não devem ser usados para transferir dinheiro.</div>}<WalletPair provider="mpesa" initial={initial} /><WalletPair provider="emola" initial={initial} /><small>Os destinatários são declarados por si. A Deloya não verifica o titular junto da operadora. Nunca introduza um PIN ou palavra-passe.</small></fieldset>;
}
