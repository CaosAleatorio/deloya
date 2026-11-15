export const MAX_ATTACHMENT_BYTES = 3 * 1024 * 1024;
export const MAX_TICKET_ATTACHMENTS = 10;
const extensions: Record<string, string[]> = {
  'application/pdf': ['pdf'],
  'image/jpeg': ['jpg', 'jpeg'],
  'image/png': ['png'],
  'image/webp': ['webp'],
};
export const ATTACHMENT_ACCEPT = Object.keys(extensions).join(',');

// These checks give immediate feedback; the API also validates the actual bytes.
export function attachmentFileError(file: Pick<File, 'name' | 'size' | 'type'>): string | null {
  if (!file.size) return 'O ficheiro está vazio.';
  if (file.size > MAX_ATTACHMENT_BYTES) return 'O ficheiro excede o limite de 3 MiB.';
  const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
  if (!extensions[file.type]?.includes(extension)) return 'Escolha um ficheiro PDF, JPEG, PNG ou WebP com a extensão correcta.';
  return null;
}

export function attachmentSize(bytes: number): string {
  const mib = bytes >= 1024 * 1024;
  return `${new Intl.NumberFormat('pt-MZ', { maximumFractionDigits: 1 }).format(bytes / (mib ? 1024 * 1024 : 1024))} ${mib ? 'MiB' : 'KiB'}`;
}
