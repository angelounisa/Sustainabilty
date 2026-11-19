// Shared document style/helpers (same as build_paper.js) for the supplementary material
const fs = require("fs");
const path = require("path");
const sizeOf = (f) => { const b = fs.readFileSync(f); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; };
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  HeadingLevel, BorderStyle, ShadingType, Footer, PageNumber, LevelFormat, PageBreak, TabStopType,
} = require("docx");

const FONT = "Times New Roman";
let FIGDIR = path.join(__dirname, "figures");
const FIG = (n) => path.join(FIGDIR, n);
const TEXT_W = 9070;                 // A4 with 2.5 cm margins (DXA)
const IMG_W = 600;                   // px at 96 dpi ~ 15.9 cm

// ---- inline mini-markup: [b]..[/b], [i]..[/i], _{sub}, ^{sup}
function runs(text, base = {}) {
  const out = []; let bold = false, ital = false; let i = 0, buf = "";
  const flush = () => { if (buf) { out.push(new TextRun({ text: buf, bold: bold || undefined, italics: ital || undefined, font: FONT, ...base })); buf = ""; } };
  while (i < text.length) {
    if (text.startsWith("[b]", i)) { flush(); bold = true; i += 3; continue; }
    if (text.startsWith("[/b]", i)) { flush(); bold = false; i += 4; continue; }
    if (text.startsWith("[i]", i)) { flush(); ital = true; i += 3; continue; }
    if (text.startsWith("[/i]", i)) { flush(); ital = false; i += 4; continue; }
    if ((text[i] === "_" || text[i] === "^") && text[i + 1] === "{") {
      flush(); const j = text.indexOf("}", i);
      out.push(new TextRun({ text: text.slice(i + 2, j), bold: bold || undefined, italics: ital || undefined, font: FONT,
        subScript: text[i] === "_", superScript: text[i] === "^", ...base }));
      i = j + 1; continue;
    }
    buf += text[i]; i++;
  }
  flush(); return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t), alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 120, line: 300 }, indent: o.noIndent ? undefined : { firstLine: 0 }, ...o });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: runs(t) });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(t) });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: runs(t) });
const EQ = (t, n) => new Paragraph({ alignment: AlignmentType.LEFT, spacing: { before: 60, after: 120 },
  tabStops: [{ type: TabStopType.CENTER, position: Math.round(TEXT_W / 2) }, { type: TabStopType.RIGHT, position: TEXT_W }],
  children: [new TextRun({ text: "\t", font: FONT }), ...runs(t), new TextRun({ text: `\t(${n})`, font: FONT })] });
const BUL = (t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, children: runs(t),
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 300 } });
const NOTE = (t) => new Paragraph({ children: [new TextRun({ text: t, font: FONT, italics: true, highlight: "yellow" })],
  spacing: { after: 120 } });

let figN = 0, FIGPREFIX = "";
function figure(file, caption) {
  figN++;
  const { w, h } = sizeOf(FIG(file));
  const width = IMG_W, height = Math.round(IMG_W * h / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(FIG(file)), transformation: { width, height },
        altText: { title: `Figure ${FIGPREFIX}${figN}`, description: caption.replace(/\[\/?[bi]\]|[_^]\{|\}/g, ""), name: file } })] }),
    new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 240, line: 260 },
      children: [new TextRun({ text: `Figure ${FIGPREFIX}${figN}. `, bold: true, font: FONT, size: 22 }), ...runs(caption, { size: 22 })] }),
  ];
}

let tabN = 0, TABPREFIX = "";
const bd = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
function table(caption, header, rows, widths, opts = {}) {
  tabN++;
  const sum = widths.reduce((a, b) => a + b, 0);
  const W_ = widths.map((x) => Math.round(x * TEXT_W / sum));
  W_[W_.length - 1] += TEXT_W - W_.reduce((a, b) => a + b, 0);
  const cell = (t, i, isHead, last) => new TableCell({
    width: { size: W_[i], type: WidthType.DXA },
    borders: { top: isHead ? bd : none, bottom: (isHead || last) ? bd : none, left: none, right: none },
    shading: isHead ? { fill: "EDEDED", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 70, right: 70 },
    children: [new Paragraph({ alignment: i === 0 || (opts.leftCols || []).includes(i) ? AlignmentType.LEFT : AlignmentType.CENTER,
      children: runs(String(t), { size: opts.size || 20, bold: isHead || undefined }) })],
  });
  return [
    new Paragraph({ keepNext: true, spacing: { before: 200, after: 80 }, alignment: AlignmentType.JUSTIFIED,
      children: [new TextRun({ text: `Table ${TABPREFIX}${tabN}. `, bold: true, font: FONT, size: 22 }), ...runs(caption, { size: 22 })] }),
    new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: W_,
      rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true, false)) }),
        ...rows.map((r, k) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false, k === rows.length - 1)) }))] }),
    new Paragraph({ spacing: { after: 160 }, children: [] }),
  ];
}


module.exports = { runs, P, H1, H2, H3, EQ, BUL, NOTE, figure, table, FONT, TEXT_W,
  setFigDir: (d) => { FIGDIR = d; }, setPrefix: (f, t) => { FIGPREFIX = f; TABPREFIX = t; } };
