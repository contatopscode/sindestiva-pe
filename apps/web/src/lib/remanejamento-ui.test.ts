import { describe, expect, it } from "vitest";
import {
  badgeLabelForRemanejamentoStatus,
  computeRemanejamentoKpis,
  mensagemMatriculaSemCadastro,
  MSG_MATRICULA_SEM_CADASTRO,
} from "./remanejamento-ui";

describe("badgeLabelForRemanejamentoStatus", () => {
  it("mapeia status do backend para PEND/SENT/ACK/NACK", () => {
    expect(badgeLabelForRemanejamentoStatus("PENDENTE")).toBe("PEND");
    expect(badgeLabelForRemanejamentoStatus("APROVADO")).toBe("SENT");
    expect(badgeLabelForRemanejamentoStatus("NOTIFICADO_OGMO")).toBe("SENT");
    expect(badgeLabelForRemanejamentoStatus("ACK")).toBe("ACK");
    expect(badgeLabelForRemanejamentoStatus("NACK")).toBe("NACK");
    expect(badgeLabelForRemanejamentoStatus("CANCELADO")).toBe("NACK");
  });
});

describe("computeRemanejamentoKpis", () => {
  const hoje = "2026-09-14";

  it("calcula KPIs apenas do dia de referência", () => {
    const kpis = computeRemanejamentoKpis(
      [
        {
          status: "ACK",
          data_referencia: hoje,
          created_at: `${hoje}T10:00:00Z`,
        },
        {
          status: "PENDENTE",
          data_referencia: hoje,
          created_at: `${hoje}T09:00:00Z`,
        },
        {
          status: "NACK",
          data_referencia: "2026-09-01",
          created_at: "2026-09-01T09:00:00Z",
        },
      ],
      hoje,
    );
    expect(kpis.totalHoje).toBe(2);
    expect(kpis.aceitosOgmo).toBe(1);
    expect(kpis.taxaAceitosPct).toBe(50);
    expect(kpis.pendentes).toBe(1);
    expect(kpis.recusados).toBe(0);
  });
});

describe("mensagemMatriculaSemCadastro", () => {
  it("alerta quando matrícula preenchida sem UUID resolvido", () => {
    expect(mensagemMatriculaSemCadastro("162", "")).toBe(
      MSG_MATRICULA_SEM_CADASTRO,
    );
    expect(mensagemMatriculaSemCadastro("162", "uuid-ok")).toBeNull();
    expect(mensagemMatriculaSemCadastro("", "")).toBeNull();
  });
});
