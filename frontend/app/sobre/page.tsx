import { Suspense } from 'react';
import { Marketplace } from '../../src/features/marketplace';

export default function Sobre() { return <Suspense fallback={<p>A carregar…</p>}><Marketplace /></Suspense>; }
