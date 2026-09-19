import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { OGMO_RECIFE_DEFAULT_URL } from "@sindestiva/shared";
import { OgmoRecifeEmbed } from "@sindestiva/ui";

describe("OgmoRecifeEmbed (render estático)", () => {
  it("monta iframe e fallback com o mesmo href/src da URL canônica", () => {
    const html = renderToStaticMarkup(
      <OgmoRecifeEmbed variant="web" portalUrl={OGMO_RECIFE_DEFAULT_URL} />,
    );
    expect(html).toContain(`src="${OGMO_RECIFE_DEFAULT_URL}"`);
    expect(html).toContain(`href="${OGMO_RECIFE_DEFAULT_URL}"`);
    expect(html).toContain('data-testid="ogmo-recife-iframe"');
    expect(html).toContain('data-testid="ogmo-recife-fallback"');
  });
});
