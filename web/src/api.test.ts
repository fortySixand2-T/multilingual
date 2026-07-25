import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, setToken, getToken } from "./api";

// A Map-backed localStorage so setToken/getToken behave deterministically in the test
// env (matches the stub style in level.test.tsx).
const store = new Map<string, string>();
vi.stubGlobal("localStorage", {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
});

function mockFetch(status: number) {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    statusText: "",
    json: async () => ({ detail: "invalid or expired token" }),
  });
}

describe("api 401 interceptor (qa-466)", () => {
  beforeEach(() => {
    store.clear();
    vi.restoreAllMocks();
  });

  it("clears the token and fires tef:unauthorized when an authenticated request 401s", async () => {
    setToken("stale.jwt.token");
    vi.stubGlobal("fetch", mockFetch(401));
    const fired = vi.fn();
    window.addEventListener("tef:unauthorized", fired);

    await expect(api.me()).rejects.toMatchObject({ status: 401 });

    expect(getToken()).toBeNull(); // dead session cleared
    expect(fired).toHaveBeenCalledTimes(1); // app told to drop to login
    window.removeEventListener("tef:unauthorized", fired);
  });

  it("does NOT fire on a 401 with no token (e.g. a rejected login attempt)", async () => {
    vi.stubGlobal("fetch", mockFetch(401));
    const fired = vi.fn();
    window.addEventListener("tef:unauthorized", fired);

    await expect(api.login({ email: "x@y.z", password: "nope" })).rejects.toMatchObject({
      status: 401,
    });

    expect(fired).not.toHaveBeenCalled();
    window.removeEventListener("tef:unauthorized", fired);
  });
});
