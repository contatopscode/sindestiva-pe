// =============================================================================
// SINDESTIVA-PE · /tpa/perfil — PWA TPA · Perfil
// =============================================================================

import type { ReactNode } from "react";

export const metadata = { title: "PWA · Perfil · SINDESTIVA-PE" };

const PERFIL_MOCK = {
  nome: "Manoel Florêncio da Costa",
  matricula_ogmo: "247",
  cpf: "***.***.***-**",
  data_nascimento: "1978-04-12",
  funcao_principal: "Emp. GP",
  categoria: "TECNICA",
  data_cadastro: "2010-03-15",
  contato: {
    telefone: "(81) 9 9876-5432",
    email: "manoel.florencio@example.com",
    emergencia: "Esposa — (81) 9 1234-5678",
  },
};

export default function TpaPerfilPage(): ReactNode {
  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Perfil</h1>
          <p className="section-subtitle">Dados cadastrais e contato de emergência</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Dados pessoais">
          <Row label="Nome completo" value={PERFIL_MOCK.nome} />
          <Row label="Matrícula OGMO" value={PERFIL_MOCK.matricula_ogmo} mono />
          <Row label="CPF" value={PERFIL_MOCK.cpf} mono />
          <Row label="Data de nascimento" value={PERFIL_MOCK.data_nascimento} mono />
        </Card>

        <Card title="Dados profissionais">
          <Row label="Função principal" value={PERFIL_MOCK.funcao_principal} />
          <Row label="Categoria" value={PERFIL_MOCK.categoria} />
          <Row label="Cadastrado em" value={PERFIL_MOCK.data_cadastro} mono />
        </Card>

        <Card title="Contato" className="md:col-span-2">
          <Row label="Telefone" value={PERFIL_MOCK.contato.telefone} mono />
          <Row label="E-mail" value={PERFIL_MOCK.contato.email} />
          <Row label="Contato de emergência" value={PERFIL_MOCK.contato.emergencia} />
        </Card>
      </div>

      <div className="mt-6 rounded-md border border-[#e8a33d]/40 bg-[#e8a33d]/10 p-3 text-[11px] text-[#e8a33d]">
        🔒 Em conformidade com a LGPD, edição de dados pessoais passa por
        solicitação ao Fiscal. (Termo de consentimento — Sprint 0 / T1-10)
      </div>
    </div>
  );
}

function Card({ title, children, className = "" }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-[#1e3a52] bg-[#0f2438] p-4 ${className}`}>
      <h2 className="mb-3 text-[12px] font-bold uppercase tracking-wider text-[#94a8bd]">
        {title}
      </h2>
      <dl className="space-y-2">{children}</dl>
    </section>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-[11px] text-[#94a8bd]">{label}</dt>
      <dd className={`text-[13px] text-[#e8eef4] ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}
