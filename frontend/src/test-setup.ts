import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// vitest runs without globals here, so @testing-library/react's
// automatic cleanup never hooks in — unmount after every test so
// renders from one test cannot leak into the next.
afterEach(() => {
  cleanup();
});
