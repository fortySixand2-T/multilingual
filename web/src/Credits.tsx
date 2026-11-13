const BY_SA = "https://creativecommons.org/licenses/by-sa/4.0/";

// Wiktionary and Lexique are CC BY-SA 4.0: credit, licence link and a note that the
// data was changed (QA 1192). The full notice is app/content/data/NOTICE.md.
export default function Credits() {
  return (
    <footer className="credits muted">
      Word meanings adapted and shortened from{" "}
      <a href="https://en.wiktionary.org" target="_blank" rel="noreferrer">Wiktionary</a>; word gender and
      frequency from{" "}
      <a href="http://www.lexique.org" target="_blank" rel="noreferrer">Lexique 3</a>. Both are licensed{" "}
      <a href={BY_SA} target="_blank" rel="noreferrer">CC BY-SA 4.0</a>.
    </footer>
  );
}
