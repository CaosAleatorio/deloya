import { Suspense } from 'react';
import { Marketplace } from '../../src/features/marketplace';

export default function MarketplacePage() { return <Suspense fallback={<div className="state-panel">A carregar Deloya…</div>}><Marketplace /></Suspense>; }
