import type { UserFormValues } from "./user-form-modal";

export function userFormMissingFields(
  values: UserFormValues,
  mode: "create" | "edit",
): string[] {
  const missing: string[] = [];
  if (!values.email.trim()) missing.push("E-mail");
  if (values.telefone.trim().length < 8) missing.push("Telefone (mín. 8 caracteres)");
  if (mode === "create" && values.password.length < 8) {
    missing.push("Senha inicial (mín. 8 caracteres)");
  }
  const cpf = values.cpf.replace(/\D/g, "");
  if (cpf.length !== 11) missing.push("CPF (11 dígitos)");
  if (values.nome_completo.trim().length < 2) missing.push("Nome completo");
  if (values.matricula_sindicato.trim().length < 2) {
    missing.push("Matrícula sindicato");
  }
  if (values.role === "FISCAL") {
    if (!values.porto_codigo) missing.push("Porto");
    if (!values.turno_codigo) missing.push("Turno");
  } else if (!values.cargo.trim()) {
    missing.push("Cargo");
  }
  return missing;
}

export function canSubmitUserForm(
  values: UserFormValues,
  mode: "create" | "edit",
): boolean {
  return userFormMissingFields(values, mode).length === 0;
}
