type CategoryField = 'name' | 'slug';
export type CategoryFormErrors = Partial<Record<CategoryField, string>>;

export function normalizeCategorySlug(value: string) {
  return value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

export function categoryFormValues(form: FormData) {
  const name = String(form.get('name') ?? '').trim();
  const enteredSlug = String(form.get('slug') ?? '').trim();
  const slug = enteredSlug ? normalizeCategorySlug(enteredSlug) : undefined;
  const errors: CategoryFormErrors = {};
  if (name.length < 2 || name.length > 100) errors.name = 'Indique um nome entre 2 e 100 caracteres.';
  if (enteredSlug && (!slug || slug.length < 2 || slug.length > 120)) errors.slug = 'Use um identificador entre 2 e 120 letras ou números. Pode deixar este campo vazio para o gerar automaticamente.';
  return { values: { name, slug, parent_id: String(form.get('parent_id') ?? '').trim() || null }, errors };
}
