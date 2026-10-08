// Mermaid-kaavio (stdin) -> SVG (stdout) beautiful-mermaidilla, joka piirtää
// ilman selainta. convert.py ajaa tämän jokaiselle uudelle ```mermaid-aidalle
// ja siistii tuloksen (mermaid_clean): värit ja kirjasin tulevat sivun
// CSS-muuttujista (diagrams.css), joten tässä ei valita värejä. Virheestä
// (syntaksi tms.) viesti stderriin ja paluuarvo 1. Vajaa kaavio (esim.
// "A <|-- " ilman toista luokkaa) ei kaada piirtäjää vaan antaa tyhjän kuvan,
// joka tulkitaan virheeksi, jottei se jää sivulle huomaamatta.
import { renderMermaidSVG } from "beautiful-mermaid";

let source = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) {
  source += chunk;
}
try {
  const svg = renderMermaidSVG(source, { transparent: true });
  if (/viewBox="0 0 0 0"/.test(svg)) {
    throw new Error("kaaviossa ei ole mitään piirrettävää (syntaksivirhe?)");
  }
  process.stdout.write(svg);
} catch (error) {
  process.stderr.write(`${error.message ?? error}\n`);
  process.exit(1);
}
