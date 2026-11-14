import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: 'Deloya — O que procura está mais perto', template: '%s · Deloya Marketplace' },
  description: "Produtos, serviços e lojas locais num só lugar. Deloya Marketplace, da Deloya Serviços e Comércios, Nampula, Moçambique.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-MZ">
      <body>{children}</body>
    </html>
  );
}
