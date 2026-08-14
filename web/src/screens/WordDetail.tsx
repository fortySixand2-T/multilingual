import { useEffect, useState } from "react";
import { api, WordForm, WordExample } from "../api";

// Study panel for ANY vocab card (personal or content-bank), addressed by its
// `cardKey`: the word's morphological forms (noun plural / verb conjugations /
// adjective m·f·pl) plus example sentences. Forms are generated once and cached per
// user; example sentences are generated FRESH on each "New example" press and kept as
// a small rolling history (newest first).
//
// Fetching is lazy — nothing loads until the panel opens. `defaultOpen` opens it
// immediately (used in the flashcard deck, where the panel appears only once the
// learner reveals the meaning, so the extra expander click is redundant); otherwise
// it starts collapsed behind a "Forms & examples ▸" toggle (used in the My-deck list,
// where every card is on screen at once and we don't want a fetch per row). On open it
// hydrates stored extras via /vocab/extra (free, no model call), then — only for an
// inflecting part of speech with no forms yet — generates the forms.
export default function WordDetail({
  cardKey,
  pos,
  defaultOpen = false,
}: {
  cardKey: string;
  pos?: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [forms, setForms] = useState<WordForm[] | null>(null);
  const [examples, setExamples] = useState<WordExample[]>([]);
  const [formsState, setFormsState] = useState<"idle" | "loading" | "over_budget" | "none">("idle");
  const [exState, setExState] = useState<"idle" | "loading" | "over_budget" | "error">("idle");

  // Load stored extras (and generate forms once for inflecting words). Guarded so a
  // second open — or the defaultOpen mount below — never re-fetches.
  const hydrate = async () => {
    if (formsState !== "idle" || examples.length) return; // already hydrated
    setFormsState(inflects(pos) ? "loading" : "none");
    try {
      const extra = await api.vocabExtra(cardKey);
      setExamples(extra.examples);
      if (!inflects(pos)) return;
      if (extra.forms !== null) {
        // already generated (possibly []) — show it, don't regenerate
        setForms(extra.forms);
        setFormsState(extra.forms.length ? "idle" : "none");
        return;
      }
      const r = await api.vocabForms(cardKey); // generate once
      if (r.over_budget) setFormsState("over_budget");
      else {
        setForms(r.forms);
        setFormsState(r.forms.length ? "idle" : "none");
      }
    } catch {
      setFormsState("none");
    }
  };

  const expand = () => {
    setOpen(true);
    void hydrate();
  };

  // defaultOpen: hydrate on mount without waiting for a click.
  useEffect(() => {
    if (defaultOpen) void hydrate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const newExample = async () => {
    setExState("loading");
    try {
      const r = await api.vocabExamples(cardKey);
      setExamples(r.examples);
      setExState(r.over_budget ? "over_budget" : "idle");
    } catch {
      setExState("error");
    }
  };

  if (!open) {
    return (
      <button className="btn secondary" style={LINK} onClick={expand}>
        Forms &amp; examples ▸
      </button>
    );
  }

  return (
    <div className="stack" style={{ gap: 10, marginTop: 8 }}>
      {inflects(pos) && (
        <div>
          <div className="muted" style={LABEL}>Forms</div>
          {formsState === "loading" && <div className="muted">Loading forms…</div>}
          {formsState === "over_budget" && (
            <div className="muted">Daily limit reached — try forms again tomorrow.</div>
          )}
          {formsState === "none" && <div className="muted">No forms for this word.</div>}
          {forms && forms.length > 0 && (
            <div className="stack" style={{ gap: 3 }}>
              {forms.map((f) => (
                <div key={f.label} style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                  <span className="muted" style={{ minWidth: 96, fontSize: 12 }}>{f.label}</span>
                  <span style={{ fontWeight: 700 }}>{f.fr}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div>
        <div className="btn-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div className="muted" style={LABEL}>Examples</div>
          <button className="btn secondary" style={{ padding: "4px 10px" }} onClick={newExample} disabled={exState === "loading"}>
            {exState === "loading" ? "…" : examples.length ? "🔄 New example" : "✨ Get examples"}
          </button>
        </div>
        {exState === "over_budget" && (
          <div className="muted">Daily limit reached — more examples tomorrow.</div>
        )}
        {exState === "error" && (
          <div className="muted">Couldn't generate an example right now.</div>
        )}
        {examples.length === 0 && exState === "idle" && (
          <div className="muted">Press for a sentence using this word.</div>
        )}
        {examples.length > 0 && (
          <ol className="stack" style={{ gap: 6, margin: "4px 0 0", paddingLeft: 18 }}>
            {examples.map((e, i) => (
              <li key={`${e.fr}-${i}`}>
                <div style={{ fontWeight: 600 }}>{e.fr}</div>
                {e.en && <div className="muted" style={{ fontSize: 13 }}>{e.en}</div>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

// Only nouns, verbs and adjectives have a useful form table (matches the backend skip).
const inflects = (pos?: string) => pos === "noun" || pos === "verb" || pos === "adjective";

const LINK = { padding: "4px 0", border: "none", boxShadow: "none", background: "none", color: "var(--green-dk)", fontSize: 13, textAlign: "left" as const };
const LABEL = { fontSize: 12, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: 0.4 };
