import type { TpaFormValues } from "./tpa-form-modal";

export function tpaFormMissingFields(values: TpaFormValues): string[] {
  const missing: string[] = [];
  const cpf = values.cpf.replace(/\D/g, "");
  if (cpf.length !== 11) missing.push("CPF (11 dígitos)");
  if (!values.nome_completo.trim()) missing.push("Nome completo");
  const matricula = values.matricula_ogmo.trim();
  if (matricula.length < 1 || matricula.length > 10) {
    missing.push("Matrícula OGMO (1–10 caracteres)");
  }
  if (!values.telefone.trim()) missing.push("Telefone");
  if (values.funcao_ids.length < 1) missing.push("Ao menos uma função");
  if (values.funcao_ids.length > 0 && !values.funcao_base_id) {
    missing.push("Função principal");
  }
  if (
    values.funcao_base_id &&
    values.funcao_ids.length > 0 &&
    !values.funcao_ids.includes(values.funcao_base_id)
  ) {
    missing.push("Função principal deve estar entre as selecionadas");
  }
  return missing;
}

export function canSubmitTpaForm(values: TpaFormValues): boolean {
  return tpaFormMissingFields(values).length === 0;
}
