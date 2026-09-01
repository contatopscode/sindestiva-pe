// =============================================================================
// SINDESTIVA-PE · / — redirect para /centro-comando
// =============================================================================

import { redirect } from "next/navigation";

export default function HomePage() {
  redirect("/centro-comando");
}
