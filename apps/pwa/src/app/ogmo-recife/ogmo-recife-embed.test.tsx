import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { OGMO_RECIFE_DEFAULT_URL } from "@sindestiva/shared";
import { OgmoRecifeEmbed } from "@sindestiva/ui";

describe("PWA · OgmoRecifeEmbed", () => {
  it("iframe src e fallback href usam a URL canônica", () => {
    const html = renderToStaticMarkup(
      <OgmoRecifeEmbed variant="pwa" portalUrl={OGMO_RECIFE_DEFAULT_URL} />,
    );
    expect(html).toContain(`src="${OGMO_RECIFE_DEFAULT_URL}"`);
    expect(html).toContain(`href="${OGMO_RECIFE_DEFAULT_URL}"`);
  });
});
