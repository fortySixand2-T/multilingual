// Adds jest-dom matchers (toBeInTheDocument, etc.) to Vitest's expect, and unmounts
// rendered components between tests (auto-cleanup isn't registered without globals).
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(cleanup);
