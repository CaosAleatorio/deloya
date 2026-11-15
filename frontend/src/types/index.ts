import type { WalletSettings } from '../lib/wallets';

export type User = { id: string; name: string; email: string; phone?: string; role: 'customer' | 'vendor' | 'admin'; is_demo: boolean };
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };
export type Category = { id: string; name: string; slug: string; description?: string; parent_id?: string | null };
export type Store = WalletSettings & { id: string; name: string; slug: string; description: string; province: string; district: string; phone?: string; email?: string; address?: string; contact?: string; logo_url?: string; status: string; is_demo: boolean; owner_id?: string; nuit?: string; delivery_fee: string | null };
export type Listing = { id: string; slug: string; kind: 'product' | 'service'; name: string; description: string; price: string | null; stock: number | null; sku?: string; category_id: string; store_id: string; image_url?: string | null; images: string[]; updated_at: string; status: string; is_demo: boolean; service_location?: string; estimated_duration?: string; store: Pick<Store, 'id' | 'name' | 'slug' | 'province' | 'district' | 'delivery_fee'>; category: Category };
export type Cart = { items: { id: string; quantity: number; listing: Listing; unit_price: string; subtotal: string }[]; total: string; is_demo: boolean };
export type PaymentMode = 'manual' | 'demo' | 'disabled';
export type PaymentSettings = { mode: PaymentMode; demo_enabled: boolean };
export type WalletDestination = { phone: string; account_name: string };
export type VendorOrder = { id: string; order_id?: string; reference?: string; is_demo?: boolean; payment_mode?: PaymentMode; payment_destinations?: Partial<Record<'mpesa' | 'emola', WalletDestination>>; payments?: Payment[]; service_status?: string | null; store: Pick<Store, 'id' | 'name' | 'slug'>; status: string; total: string; items: { id: string; name: string; kind: string; quantity: number; unit_price: string; total: string }[]; delivery_method?: string; address?: string; notes?: string };
export type Order = { id: string; reference: string; status: string; total: string; is_demo: boolean; payment_mode?: PaymentMode; can_cancel?: boolean; created_at: string; vendor_orders: VendorOrder[]; delivery_method?: string; address?: string; notes?: string };
export type Payment = { id: string; reference: string; provider: string; status: string; amount: string; is_demo: boolean; order_id: string; order_reference?: string; store_id?: string; vendor_order_id?: string; payment_mode?: PaymentMode; transfer_reference?: string | null; notes?: string | null; review_notes?: string | null; reviewed_at?: string | null; reviewed_by?: string | null; destination?: WalletDestination | null; created_at?: string };
