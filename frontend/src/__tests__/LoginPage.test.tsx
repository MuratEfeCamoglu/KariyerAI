import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";

import { routes } from "../router.tsx";

describe("router", () => {
  it("bilinmeyen yolu giriş sayfasına yönlendirir", async () => {
    const router = createMemoryRouter(routes, { initialEntries: ["/"] });

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "KariyerAI" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });
});
