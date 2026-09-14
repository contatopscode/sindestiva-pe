/** Rótulo do campo TPA a remover na lista de pendências (UX2). */
export function labelPendenciaTpaOut(
  tpaOutMatricula: string,
  tpaOutIdResolved: string,
): string {
  const mat = tpaOutMatricula.trim();
  if (mat && !tpaOutIdResolved) {
    return "matrícula sem cadastro";
  }
  return "TPA a remover";
}
