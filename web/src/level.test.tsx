import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LevelProvider, LevelSwitcher, useLevel } from "./level";
import { api } from "./api";

vi.mock("./api", () => ({
  api: { levels: vi.fn(), me: vi.fn() },
}));

// jsdom's default opaque origin makes localStorage throw; give it a real in-memory one.
const store = new Map<string, string>();
vi.stubGlobal("localStorage", {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
});

function Probe() {
  const { level } = useLevel();
  return <div data-testid="level">{level}</div>;
}

const renderWithLevels = (levels: string[], meLevel: string) => {
  vi.mocked(api.levels).mockResolvedValue({ levels } as never);
  vi.mocked(api.me).mockResolvedValue({ level: meLevel } as never);
  return render(
    <LevelProvider>
      <LevelSwitcher />
      <Probe />
    </LevelProvider>,
  );
};

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe("level switcher", () => {
  it("seeds the level from the learner's progress when none is stored", async () => {
    renderWithLevels(["a1", "a2"], "a2");
    await waitFor(() => expect(screen.getByTestId("level").textContent).toBe("a2"));
  });

  it("switching updates the level and persists the choice", async () => {
    renderWithLevels(["a1", "a2"], "a1");
    await waitFor(() => expect(screen.getByRole("combobox")).toBeTruthy());
    await userEvent.selectOptions(screen.getByRole("combobox"), "a2");
    expect(screen.getByTestId("level").textContent).toBe("a2");
    expect(localStorage.getItem("tef.level")).toBe("a2");
  });

  it("a stored choice wins over the learner's progress level", async () => {
    localStorage.setItem("tef.level", "a2");
    renderWithLevels(["a1", "a2"], "a1");
    await waitFor(() => expect(screen.getByTestId("level").textContent).toBe("a2"));
  });

  it("hides the switcher until more than one level has content", async () => {
    renderWithLevels(["a1"], "a1");
    await waitFor(() => expect(api.levels).toHaveBeenCalled());
    expect(screen.queryByRole("combobox")).toBeNull();
  });
});
