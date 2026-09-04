// =============================================================================
// SINDESTIVA-PE · Schema Zod do formulário de navios (issue #15)
// Espelha `app/schemas/navio.py` no backend: mesma normalização de IMO e
// mesmo catálogo de tipo de operação. Validar aqui é o que impede o
// submit de sair com payload que o backend recusaria com 422.
// =============================================================================

import { z } from "zod";

/** Catálogo de tipos de operação (igual ao `TIPOS_OPERACAO` do backend). */
export const TIPOS_OPERACAO = [
  "CONTAINER",
  "RO_RO",
  "GRANEL_SOLIDO",
  "GRANEL_LIQUIDO",
  "CARGA_GERAL",
  "PASSAGEIROS",
  "OUTRO",
] as const;

export type TipoOperacao = (typeof TIPOS_OPERACAO)[number];

export const ROTULO_TIPO_OPERACAO: Record<TipoOperacao, string> = {
  CONTAINER: "Contêiner",
  RO_RO: "Ro-Ro",
  GRANEL_SOLIDO: "Granel sólido",
  GRANEL_LIQUIDO: "Granel líquido",
  CARGA_GERAL: "Carga geral",
  PASSAGEIROS: "Passageiros",
  OUTRO: "Outro",
};

/** `""` / `"   "` → `undefined` (campo opcional não enviado). */
const opcional = (v: unknown) => (typeof v === "string" ? v.trim() : (v ?? undefined));

export const navioFormSchema = z.object({
  nome: z
    .string({ required_error: "Nome do navio é obrigatório." })
    .trim()
    .min(1, "Nome do navio é obrigatório.")
    .max(200, "Nome do navio deve ter no máximo 200 caracteres."),

  imo: z
    .string()
    .optional()
    // Normaliza antes de validar: "imo 9319466" e "9319466" são o mesmo navio.
    .transform((v) => (v ?? "").replace(/\s+/g, "").toUpperCase())
    .superRefine((v, ctx) => {
      if (v && !/^(?:IMO)?\d{7}$/.test(v)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "IMO deve ter 7 dígitos (ex.: IMO9319466 ou 9319466).",
        });
      }
    })
    .transform((v) => (v ? (v.startsWith("IMO") ? v : `IMO${v}`) : undefined)),

  bandeira: z
    .preprocess(
      opcional,
      z.string().max(60, "Bandeira deve ter no máximo 60 caracteres.").optional(),
    )
    .transform((v) => (v ? v : undefined)),

  tipo_operacao: z
    .preprocess(
      opcional,
      z
        .enum(TIPOS_OPERACAO, {
          errorMap: () => ({ message: "Selecione um tipo de operação válido." }),
        })
        .optional(),
    )
    .transform((v) => (v ? v : undefined)),
});

/** Valores brutos dos inputs (tudo string, como vem do DOM). */
export type NavioFormValues = {
  nome: string;
  imo: string;
  bandeira: string;
  tipo_operacao: string;
};

/** Payload já normalizado enviado ao `POST /api/v1/navios`. */
export type NavioInput = z.output<typeof navioFormSchema>;

export const NAVIO_FORM_VAZIO: NavioFormValues = {
  nome: "",
  imo: "",
  bandeira: "",
  tipo_operacao: "",
};

/**
 * Valida o formulário e devolve os erros por campo (formato pronto pra UI).
 * Retorna `data` apenas quando tudo passa — é isso que garante "zero
 * request disparada" com campo obrigatório vazio.
 */
export function validarNavioForm(
  values: Partial<NavioFormValues>,
):
  | { ok: true; data: NavioInput }
  | { ok: false; erros: Partial<Record<keyof NavioFormValues, string>> } {
  const r = navioFormSchema.safeParse(values);
  if (r.success) return { ok: true, data: r.data };

  const erros: Partial<Record<keyof NavioFormValues, string>> = {};
  for (const issue of r.error.issues) {
    const campo = issue.path[0] as keyof NavioFormValues | undefined;
    if (campo && !erros[campo]) erros[campo] = issue.message;
  }
  return { ok: false, erros };
}
