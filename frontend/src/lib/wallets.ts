export type WalletSettings = {
  mpesa_phone?: string | null;
  mpesa_account_name?: string | null;
  emola_phone?: string | null;
  emola_account_name?: string | null;
};

export const walletProviderName = (provider: string) => provider === 'mpesa' ? 'M-Pesa' : provider === 'emola' ? 'e-Mola' : provider === 'demo' ? 'Pagamento de teste' : provider;

export function walletSettingsFromForm(form: FormData): WalletSettings {
  const result: WalletSettings = {};
  for (const provider of ['mpesa', 'emola'] as const) {
    const rawPhone = String(form.get(`${provider}_phone`) ?? '').trim();
    const accountName = String(form.get(`${provider}_account_name`) ?? '').trim();
    if (Boolean(rawPhone) !== Boolean(accountName)) throw new Error(`Indique o número e o nome do titular para ${walletProviderName(provider)}, ou deixe ambos vazios.`);
    const phone = rawPhone.replace(/[\s()-]/g, '').replace(/^\+?258/, '');
    if (rawPhone && !/^\d{9}$/.test(phone)) throw new Error(`Indique um número moçambicano de nove dígitos para ${walletProviderName(provider)}.`);
    if (accountName && (accountName.length < 2 || accountName.length > 160)) throw new Error(`O nome do titular de ${walletProviderName(provider)} deve ter entre 2 e 160 caracteres.`);
    result[`${provider}_phone`] = phone || null;
    result[`${provider}_account_name`] = accountName || null;
  }
  return result;
}
