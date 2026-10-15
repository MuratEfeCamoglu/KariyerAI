import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Vitest `globals` kapalıyken Testing Library otomatik temizlik yapmaz; DOM testler arasında taşar.
afterEach(() => {
  cleanup();
});
