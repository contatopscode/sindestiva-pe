/**
 * SINDESTIVA-PE · /login layout (rota pública).
 *
 * Substitui o RootLayout (que tem gate de auth) pra esta página,
 * evitando loop de redirect. O RootLayout só é invocado para rotas
 * autenticadas; /login tem seu próprio layout.
 */
export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
