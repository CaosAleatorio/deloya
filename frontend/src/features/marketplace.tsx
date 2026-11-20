'use client';

import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { ArrowRight, BadgeCheck, Building2, ChevronDown, Facebook, HeartHandshake, Instagram, Linkedin, MapPin, Menu, MessageCircle, Phone, Search, ShieldCheck, ShoppingBag, Store as StoreIcon, UserRound, X } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import { Toaster } from 'sonner';
import { api } from '../lib/api';
import { AuthProvider, useAuth, useQuery } from '../lib/hooks';
import { Catalog, HomePage, ListingDetail, StoresPage, StoreDetail } from './public';
import { AccountPage, AuthPage, CartPage, CheckoutPage, CustomerOrders, SupportPage } from './customer';
import { ManagementPage } from './management';
import type { Cart } from '../types';

function Brand() { return <Link href="/" className="brand" aria-label="Deloya, página inicial"><span className="brand-mark">d<span>·</span></span><span>deloya<span className="brand-caption">MARKETPLACE</span></span></Link>; }

function Header() {
  const router = useRouter();
  const path = usePathname();
  const search = useSearchParams();
  const { user } = useAuth();
  const cart = useQuery<Cart>(user ? '/cart' : null);
  const nav = [{ href: '/produtos', text: 'Produtos' }, { href: '/servicos', text: 'Serviços' }, { href: '/lojas', text: 'Lojas locais' }];
  function onSearch(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); router.push(`/produtos?q=${encodeURIComponent(String(form.get('q') ?? ''))}`); }
  return <header className="site-header"><div className="topbar"><div className="container topbar-content"><span><MapPin size={12} /> De Nampula, para mais perto de si.</span><span className="topbar-right">Comércio local <span className="tiny-dot" /> Português · MZN</span></div></div><div className="container header-main"><Brand /><form className="header-search" onSubmit={onSearch} role="search"><Search size={19} /><input aria-label="Pesquisar produtos" name="q" placeholder="O que procura hoje?" defaultValue={search.get('q') ?? ''} /><button aria-label="Pesquisar"><ArrowRight size={20} /></button></form><div className="header-actions"><Link href={user ? '/conta' : '/login'} className="account-link" aria-label={user ? 'Abrir a minha conta' : 'Iniciar sessão ou registar'}><UserRound size={21} /><span><small>{user ? 'Olá,' : 'Bem-vindo'}</small><strong>{user ? user.name.split(' ')[0] : 'Entrar / Registar'}</strong></span></Link><Link href="/carrinho" className="cart-link" aria-label="Abrir carrinho"><ShoppingBag size={22} /><span className="cart-count">{cart.data?.items.reduce((count, item) => count + item.quantity, 0) ?? 0}</span></Link><Dialog.Root><Dialog.Trigger className="icon-button mobile-menu" aria-label="Abrir menu"><Menu size={23} /></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="modal-overlay" /><Dialog.Content className="mobile-menu-content"><Dialog.Title>Explorar Deloya</Dialog.Title><Dialog.Description>Produtos, serviços e a sua conta.</Dialog.Description><Dialog.Close className="icon-button close-menu" aria-label="Fechar menu"><X /></Dialog.Close>{nav.map((item) => <Dialog.Close key={item.href} asChild><Link href={item.href}>{item.text}<ArrowRight size={17} /></Link></Dialog.Close>)}<Dialog.Close asChild><Link href="/vendedor/candidatura">Abrir uma loja<ArrowRight size={17} /></Link></Dialog.Close><Dialog.Close asChild><Link href={user ? '/conta' : '/login'}>A minha conta<ArrowRight size={17} /></Link></Dialog.Close></Dialog.Content></Dialog.Portal></Dialog.Root></div></div><nav className="container desktop-nav" aria-label="Navegação principal"><Link className="all-categories" href="/produtos"><Menu size={17} />Explorar categorias<ChevronDown size={14} /></Link><div>{nav.map((item) => <Link key={item.href} className={path.startsWith(item.href) ? 'nav-active' : ''} href={item.href}>{item.text}</Link>)}<Link href="/sobre">Sobre a Deloya</Link></div><Link className="sell-link" href={user?.role === 'vendor' ? '/vendedor/dashboard' : user?.role === 'admin' ? '/admin/dashboard' : '/vendedor/candidatura'}><StoreIcon size={16} />{user?.role === 'vendor' ? 'Gerir a minha loja' : user?.role === 'admin' ? 'Administração' : 'Venda na Deloya'}<ArrowRight size={14} /></Link></nav></header>;
}

function Footer() {
  const socialExamples = [
    { name: 'Instagram', Icon: Instagram },
    { name: 'Facebook', Icon: Facebook },
    { name: 'LinkedIn', Icon: Linkedin },
  ];

  return <footer className="site-footer">
    <div className="container footer-top">
      <div><Brand /><p>O comércio local, com novas possibilidades.<br />Um ponto de encontro para produtos e serviços.</p><span className="footer-location"><MapPin size={14} aria-hidden="true" />Nampula, Moçambique</span></div>
      <div><h4>Descobrir</h4><Link href="/produtos">Produtos</Link><Link href="/servicos">Serviços</Link><Link href="/lojas">Lojas locais</Link></div>
      <div><h4>Fazer parte</h4><Link href="/registo">Criar conta</Link><Link href="/vendedor/candidatura">Abrir uma loja</Link><Link href="/conta/encomendas">As minhas encomendas</Link></div>
      <div><h4>Deloya Serviços e Comércios</h4><Link href="/sobre">Sobre o projecto</Link><Link href="/ajuda">Ajuda e reclamações</Link><Link href="/privacidade">Privacidade</Link><Link href="/termos">Termos de utilização</Link></div>
    </div>
    <div className="container footer-connect">
      <section className="footer-contact" aria-labelledby="footer-contact-title">
        <h4 id="footer-contact-title">Fale connosco</h4>
        <p>Uma conversa aproxima-nos.</p>
        <div className="footer-contact-links">
          <a href="tel:+258871707406" className="footer-phone" aria-label="Ligar para +258 87 170 7406"><Phone size={17} aria-hidden="true" /><span><small>Telefone</small><strong>+258 87 170 7406</strong></span></a>
          <a href="https://wa.me/258871707406" target="_blank" rel="noopener noreferrer" className="footer-whatsapp" aria-label="Conversar no WhatsApp pelo número +258 87 170 7406 (abre numa nova janela)"><MessageCircle size={17} aria-hidden="true" />WhatsApp<ArrowRight size={14} aria-hidden="true" /></a>
        </div>
      </section>
      <section className="footer-social" aria-labelledby="footer-social-title">
        <div className="footer-social-heading"><h4 id="footer-social-title">Redes sociais</h4><span>Exemplos de perfil</span></div>
        <p>Adelino Fonseca João · perfis ilustrativos</p>
        <ul className="footer-social-examples">
          {socialExamples.map(({ name, Icon }) => <li key={name}><Icon size={18} aria-hidden="true" /><span><strong>{name}</strong><small>@adelino.fonseca.joao</small></span></li>)}
        </ul>
      </section>
    </div>
    <div className="container footer-bottom"><span>© 2026 Deloya Marketplace</span><span>Desenvolvido por Adelino Fonseca João</span></div>
  </footer>;
}

function About({ kind }: { kind: string }) {
  if (kind === 'privacidade' || kind === 'termos') return <section className="container prose-page">
    <span className="eyebrow">INFORMAÇÃO DELOYA</span>
    <h1>{kind === 'privacidade' ? 'Privacidade e protecção de dados' : 'Termos de utilização'}</h1>
    <p className="lead">{kind === 'privacidade' ? 'Saiba como a Deloya utiliza os dados necessários à sua conta e às suas encomendas.' : 'Condições de utilização da Deloya Marketplace para clientes e vendedores.'}</p>
    {kind === 'privacidade' ? <>
      <h2>Dados necessários</h2><p>O sistema guarda o nome, email, contacto e moradas que fornecer, as suas encomendas e registos técnicos de segurança. As palavras-passe são guardadas através de hashing. Nunca pedimos o PIN da sua carteira móvel.</p>
      <h2>Dados para transferências</h2><p>O vendedor pode indicar o número e o nome do titular da sua carteira M-Pesa ou e-Mola. Estes dados são apresentados ao comprador na sua encomenda, para transferência directa. A referência comunicada pelo comprador e a decisão do vendedor ficam registadas para acompanhamento e apoio.</p>
      <h2>Finalidade e acesso</h2><p>Os dados permitem gerir contas, lojas e encomendas. Cada vendedor acede apenas às encomendas da sua loja. A administração acede aos dados necessários à moderação e ao apoio.</p>
      <h2>Segurança da conta</h2><p>Utilize uma palavra-passe exclusiva e mantenha os seus dados de acesso privados. O acesso aos dados pessoais depende das permissões de cada conta.</p>
      <h2>Pedidos sobre os seus dados</h2><p>Utilize a área de ajuda autenticada para solicitar informação, correcção ou eliminação dos seus dados, de acordo com os requisitos de conservação aplicáveis.</p>
    </> : <>
      <h2>Âmbito</h2><p>A Deloya Marketplace, da Deloya Serviços e Comércios, liga clientes e vendedores em Nampula, Moçambique. Lojas, artigos e contas de teste estão identificados na plataforma.</p>
      <h2>Pagamentos e entregas</h2><p>Quando disponível na encomenda, o comprador transfere directamente para a carteira M-Pesa ou e-Mola indicada pelo vendedor. Cada loja recebe o seu próprio valor. Antes de confirmar a transferência, verifique o nome do destinatário na sua carteira móvel. Depois, comunique a referência na Deloya e aguarde que o vendedor confira o recebimento. A plataforma não valida a transferência junto da operadora nem guarda o seu PIN. Os pagamentos de teste não movimentam dinheiro. O levantamento é feito na loja; entregas e serviços dependem das condições apresentadas em cada encomenda.</p>
      <h2>Responsabilidades</h2><p>O vendedor é responsável pela informação do anúncio e pela disponibilidade. O comprador deve verificar o conteúdo da encomenda. Reclamações podem ser registadas na área de ajuda.</p>
      <h2>Utilização responsável</h2><p>Não forneça dados financeiros sensíveis nem publique conteúdos ilegais ou dados de terceiros sem autorização. O acesso administrativo e de vendedor está sujeito a aprovação e auditoria.</p>
    </>}
  </section>;
  return <section className="container prose-page">
    <span className="eyebrow">COMÉRCIO LOCAL, NOVAS POSSIBILIDADES</span><h1>Feito para aproximar.</h1>
    <p className="lead">A Deloya Marketplace liga quem procura a quem tem para oferecer: produtos, serviços e lojas, a partir de Nampula.</p>
    <div className="about-values">
      <article><Building2 /><h3>Um projecto com raízes locais</h3><p>Uma plataforma da Deloya Serviços e Comércios para aproximar lojas, prestadores de serviços e clientes em Nampula, Moçambique.</p></article>
      <article><HeartHandshake /><h3>Mais espaço para o comércio</h3><p>Cada vendedor gere a sua loja e cada cliente encontra produtos e serviços num catálogo comum.</p></article>
      <article><ShieldCheck /><h3>Informação transparente</h3><p>Artigos e contas de teste são identificados. Os pagamentos de teste são apresentados separadamente dos valores reais e não movimentam dinheiro.</p></article>
    </div>
    <h2>Sobre o projecto</h2><p>Deloya Marketplace é um projecto profissional de Adelino Fonseca João, desenvolvido em 2026 para a Deloya Serviços e Comércios.</p>
    <p>Clientes podem consultar o catálogo, organizar as suas compras e acompanhar os pedidos. Vendedores dispõem de uma área própria para gerir os seus anúncios e encomendas.</p>
    <Link href="/vendedor/candidatura" className="button button-primary">Faça parte do projecto<ArrowRight size={16} /></Link>
  </section>;
}

function Content() {
  const path = usePathname().split('/').filter(Boolean);
  if (!path.length) return <HomePage />;
  if (path[0] === 'produtos' || path[0] === 'servicos') return path[1] ? <ListingDetail key={path.join("/")} slug={path[1]} kind={path[0] === 'produtos' ? 'product' : 'service'} /> : <Catalog kind={path[0] === 'produtos' ? 'product' : 'service'} />;
  if (path[0] === 'lojas') return path[1] ? <StoreDetail slug={path[1]} /> : <StoresPage />;
  if (path[0] === 'login' || path[0] === 'registo') return <AuthPage register={path[0] === 'registo'} key={path[0]} />;
  if (path[0] === 'carrinho') return <CartPage />;
  if (path[0] === 'checkout') return <CheckoutPage />;
  if (path[0] === 'conta') return path[1] === 'encomendas' ? <CustomerOrders /> : <AccountPage />;
  if (path[0] === 'vendedor' || path[0] === 'admin') return <ManagementPage area={path[0]} section={path[1] ?? 'dashboard'} key={path.join('/')} />;
  if (path[0] === 'ajuda') return <SupportPage />;
  if (['sobre', 'privacidade', 'termos'].includes(path[0])) return <About kind={path[0]} />;
  return <section className="container prose-page"><h1>Página não encontrada</h1><p>O endereço indicado não existe.</p><Link className="button button-primary" href="/">Voltar à página inicial</Link></section>;
}

function SessionBar() {
  const { user, refresh } = useAuth();
  const router = useRouter();
  if (!user) return null;
  return <div className="session-bar container"><span><BadgeCheck size={14} />{user.is_demo ? 'Conta de teste' : 'Sessão iniciada'} · {user.name}</span><button onClick={async () => { await api('/auth/logout', { method: 'POST' }); await refresh(); router.push('/'); }}>Terminar sessão</button></div>;
}

export function Marketplace() { return <AuthProvider><a href="#conteudo" className="skip-link">Saltar para o conteúdo</a><Header /><SessionBar /><main id="conteudo"><Content /></main><Footer /><Toaster position="top-right" richColors closeButton /></AuthProvider>; }
