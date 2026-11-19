// Builds paper/Manuscript_landslide_discrimination.docx  (node paper/build_paper.js, from repo root)
const fs = require("fs");
const path = require("path");
const sizeOf = (f) => { const b = fs.readFileSync(f); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; };
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  HeadingLevel, BorderStyle, ShadingType, Footer, PageNumber, LevelFormat, PageBreak, TabStopType,
} = require("docx");

const FONT = "Times New Roman";
const FIG = (n) => path.join(__dirname, "figures", n);
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

let figN = 0;
function figure(file, caption) {
  figN++;
  const { w, h } = sizeOf(FIG(file));
  const width = IMG_W, height = Math.round(IMG_W * h / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(FIG(file)), transformation: { width, height },
        altText: { title: `Figure ${figN}`, description: caption.replace(/\[\/?[bi]\]|[_^]\{|\}/g, ""), name: file } })] }),
    new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 240, line: 260 },
      children: [new TextRun({ text: `Figure ${figN}. `, bold: true, font: FONT, size: 22 }), ...runs(caption, { size: 22 })] }),
  ];
}

let tabN = 0;
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
      children: [new TextRun({ text: `Table ${tabN}. `, bold: true, font: FONT, size: 22 }), ...runs(caption, { size: 22 })] }),
    new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: W_,
      rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true, false)) }),
        ...rows.map((r, k) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false, k === rows.length - 1)) }))] }),
    new Paragraph({ spacing: { after: 160 }, children: [] }),
  ];
}

// =====================================================================================
const C = [];
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
  children: [new TextRun({ text: "Quantitative discrimination of landslide-triggering events: a multi-variable analysis of rainfall intensity and soil hydrological state", font: FONT, size: 32, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
  children: [new TextRun({ text: "[Authors and affiliations]", font: FONT, italics: true })] }));

C.push(H1("Abstract"));
C.push(P(`Rainfall thresholds remain the operational core of territorial landslide early warning systems, but they ignore the hydrological state of the slope that controls how a given storm is transformed into pore-water pressure. This study quantifies how much information in situ measurements of volumetric water content (VWC) and matric suction add to rainfall descriptors in discriminating landslide-triggering from non-triggering rainfall events. Twenty-one months of data (January 2025 – September 2026) were analysed for a pyroclastic slope near Salerno (Lattari Mountains, southern Italy): 10-min rainfall from five regional rain gauges and 5-min VWC and suction at 15, 30–35 and 60 cm in two instrumented verticals under forest cover (V) and in an open area (NV). Rainfall events were identified with an inter-event time definition of 24 h (E ≥ 10 mm; 44–46 events per gauge), and each event was described by rainfall indices (duration D, cumulative rainfall E, maximum hourly intensity I_{max}, antecedent rainfall) and by event-scale hydrological indices (antecedent VWC_{0} and suction s_{0}, VWC peak, ΔVWC, suction drop). Four landslides occurred between October 2025 and February 2026, all within the wet season. Event rainfall was the strongest single discriminant (AUC* = 0.88–1.00), followed by the deep ΔVWC in the vegetated profile (0.90–0.95) and by the shallow antecedent state of the open-area profile (s_{0} at 15 cm: 0.78–0.90; VWC_{0} at 15 cm: 0.74–0.89); antecedent VWC at 60 cm was a weaker discriminant (0.61–0.80). Vegetation reduced event ΔVWC in 97% of events at 15 cm and slowed the propagation of the wetting front below 30 cm (median 1.8 vs 9.5 cm h^{-1}, p = 0.003). A transparent percentile-based indicator evaluated by leave-one-event-out cross-validation showed that adding the shallow antecedent VWC to event rainfall halves false alarms (POFD from 0.16 to 0.09) and raises the true skill statistic from 0.62 to 0.74 (0.82 with short-duration and 7-day antecedent rainfall). The results support the integration of shallow soil-state monitoring into rainfall-based warning criteria, with the caveat that four landslides constrain the robustness of any selected combination.`));
C.push(P(`[b]Keywords:[/b] rainfall-induced landslides; soil moisture; matric suction; early warning; pyroclastic soils; vegetation; infiltration`, { noIndent: true }));

// ------------------------------------------------------------------ 1 INTRODUCTION
C.push(H1("1. Introduction"));
C.push(P(`Rainfall-induced shallow landslides and flow-like movements in loose pyroclastic covers are a recurrent hazard along the Campania coastal mountain belt, where steep carbonate slopes mantled by unsaturated volcanic soils have repeatedly experienced catastrophic failures (Fiorillo and Wilson, 2004; Forte et al., 2019; Fiorillo et al., 2019). Territorial landslide early warning systems (LEWS) in this setting, as in most regions worldwide, rely on rainfall thresholds: accumulations over predefined windows are compared with critical values and translated into alert levels (Calvello and Piciullo, 2016; Piciullo et al., 2017, 2018). The approach is operationally robust because rain gauges are widely available and rainfall can be forecast, but it implicitly assumes that the same storm has the same effect on the slope regardless of its antecedent hydrological state.`));
C.push(P(`That assumption is the main limitation of purely rainfall-based thresholds. Slope stability in unsaturated pyroclastic soils is governed by the suction-dependent contribution to shear strength and by the amount of water already stored in the cover: a storm falling on a dry profile at the end of summer is largely absorbed, whereas the same storm on a profile close to saturation can generate positive pore-water pressures and failure. Recent studies have shown that soil moisture and pore-water pressure measurements can reduce false and missed alarms when combined with rainfall (Wicki et al., 2020; Marino et al., 2020; Pecoraro and Calvello, 2021; Oorthuis et al., 2023), and the integration of hydrological information is regarded as a key element of the next generation of LEWS (Mirus et al., 2025). In Campania, threshold-based regional warning has been complemented by physically based and data-driven approaches (Rianna et al., 2023; Pota et al., 2022; Zhang et al., 2025).`));
C.push(P(`Event-based analyses of landslide-triggering rainfall usually face two practical issues: landslides are rare, so that the triggering class contains few samples, and many candidate predictors (accumulation windows, antecedent indices, sensor depths) are correlated with each other. Patton et al. (2023) showed, in a data-sparse setting, that short-duration rainfall totals were the best predictors and that adding antecedent conditions did not necessarily improve skill. Whether direct measurements of the soil state change that conclusion is an open question, and the answer is likely to depend on depth, on vegetation cover and on the season.`));
C.push(P(`This study addresses that question at a monitored pyroclastic slope near Salerno. The objectives are: (i) to characterise rainfall events and the event-scale response of VWC and suction at three depths under vegetated and non-vegetated conditions; (ii) to quantify infiltration dynamics and the buffering effect of vegetation; (iii) to quantify, for each rain gauge, the discriminant power of rainfall and hydrological variables between landslide-triggering and non-triggering events with effect sizes and non-parametric tests; and (iv) to evaluate, with cross-validation, whether simple combinations of rainfall and soil-state variables improve the detection of triggering events with respect to rainfall alone.`));

// ------------------------------------------------------------------ 2 STUDY AREA
C.push(H1("2. Study area and monitoring setup"));
C.push(H2("2.1 Geomorphological setting and geotechnical characterization"));
C.push(P(`The study area is located within a limestone quarry in the municipality of Salerno, on the eastern flank of the Lattari Mountains, in the Campania region of southern Italy (Urciuoli et al., 2025; Pirone et al., 2025). From a geological and geomorphological viewpoint, the site belongs to the carbonate–pyroclastic setting that characterizes large sectors of the Lattari Mountains and, more generally, the Campania coastal mountain belt, where shallow rainfall-induced failures recurrently affect steep slopes mantled by loose pyroclastic deposits (Forte et al., 2019; Fiorillo and Wilson, 2004). At the site scale, the slope is mantled by a shallow pyroclastic cover resting on dolomitic bedrock, a stratigraphic setting that is typical of many Campanian slopes affected by flow-like landslides in unsaturated volcanic soils (Urciuoli et al., 2025; Bilotta et al., 2005). The local slope inclination generally ranges between 25° and 30°, with steeper sectors exceeding 35° near morphological discontinuities, which is consistent with the critical slope conditions frequently reported for shallow flow-like landslide initiation in the Lattari Mountains (Urciuoli et al., 2025; Forte et al., 2019).`));
C.push(P(`The study area has a documented history of slope instability, including the Molina landslide of 1954, and it lies within the broader Salerno–Amalfi sector, historically affected by catastrophic rainfall-induced landslides and debris flows, such as those triggered by the October 1954 storm in the Vietri sul Mare–Maiori area (Urciuoli et al., 2025; Fiorillo et al., 2019). According to recent site investigations, the local stratigraphic sequence includes a biogeochemically active topsoil horizon (A1), an underlying brown silty-sand ash layer rich in pumice fragments related to the 79 AD eruption (A2), and a deeper yellowish silty-sand ash horizon predating the 79 AD eruption (C1) (Urciuoli et al., 2025). From a geotechnical viewpoint, these soils can be classified as volcanic silty sands, and their behaviour is consistent with that commonly reported for Campanian pyroclastic covers, whose mechanical and hydraulic response is strongly influenced by layering, porosity, unsaturated conditions and slope morphology (Urciuoli et al., 2025; Bilotta et al., 2005; Forte et al., 2019).`));
C.push(P(`Two instrumented verticals were installed under contrasting vegetation conditions, namely beneath forest cover and in a nearby open area, in order to investigate the influence of vegetation on the hydrological response of the shallow pyroclastic mantle to rainfall forcing (Urciuoli et al., 2025). This experimental choice is consistent with recent research on Campanian pyroclastic slopes, which highlights the role of vegetation in modulating rainfall interception, soil moisture evolution, suction dynamics and, consequently, slope hydrological response (Urciuoli et al., 2025; Comegna et al., 2016).`));
C.push(...figure("Fig01_study_area.png", `Location of the study area in the Campania region (left; dashed cyan line: warning zone Camp-3) and detail of the Salerno–Amalfi coastal sector (right) with the five rain gauges of the regional network used in this study.`));
C.push(NOTE("[To be completed: add the two instrumented verticals and the locations of landslides L1–L4 to Figure 1.]"));

C.push(H2("2.2 Monitoring network and instrumentation"));
C.push(H3("2.2.1 Rain gauge network"));
C.push(P(`Rainfall data were obtained from the rain-gauge network operated by the Centro Funzionale Multirischi di Protezione Civile della Regione Campania, which performs real-time meteo-hydro-pluviometric monitoring in support of the regional warning system for hydrogeological and hydraulic risk. Within this framework, the Campania warning system combines a forecasting phase with a real-time monitoring phase over eight alert zones. For the study area (alert zone 3), five gauges located in the Salerno–Amalfi coastal sector were selected: Albori, Cetara, Cetara–Serbatoio comunale (Cetara S.C.), Dragonea and Salerno Genio Civile (Salerno G.C.) (Figure 1).`));
C.push(P(`Their use is consistent with the operational logic of the regional warning model, in which rainfall observations from the nearest gauges are used as point pluviometric precursors for municipalities affected by local hydrogeological instability, whereas areal rainfall precursors are adopted for larger drainage basins. In the original operational scheme, point rainfall thresholds are evaluated over 1, 3, 6, 24, 48 and 72 h accumulation windows, while areal precursors are assessed over 3, 6, 12, 24 and 48 h windows. These thresholds are linked to increasing operational alert states (attention, pre-alarm and alarm), corresponding to return periods of 2, 5 and 10 years, respectively (Regione Campania, 2005). In the current regional configuration, warning messages are communicated through colour-coded alert levels, while the threshold-based approach remains the core of the operational decision chain. This setting is consistent with the broader framework of territorial LEWS, in which rain gauges are the primary monitoring instrumentation and rainfall thresholds are the key operational criterion (Calvello and Piciullo, 2016; Piciullo et al., 2017, 2018). Recent studies in Campania have confirmed the relevance of this threshold-based regional setting while highlighting possible improvements through physically based and machine-learning approaches (Rianna et al., 2017; Reder and Rianna, 2021; Pota et al., 2022; Rianna et al., 2023), and more recent developments have extended this line of research toward probabilistic multidimensional rainfall thresholds tested in the Camp-3 warning zone and independently validated deep-learning forecasting systems (Zhang et al., 2025; Guzzetti et al., 2024; Dal Seno et al., 2024).`));
C.push(H3("2.2.2 Soil moisture and matric suction sensors"));
C.push(P(`Integrating soil water content sensors and, more broadly, in situ hydrological sensors into LEWS can improve warning reliability because these measurements provide direct information on antecedent wetness and subsurface response that rainfall alone cannot capture (Wicki et al., 2020; Marino et al., 2020). Combining rainfall with monitored volumetric water content or pore-water pressure has been shown to improve predictive skill relative to rainfall-only criteria, for example by reducing false negatives and false positives (Oorthuis et al., 2023; Pecoraro and Calvello, 2021), and the next generation of LEWS is expected to follow a measure-and-model strategy that explicitly accounts for subsurface storage dynamics (Mirus et al., 2025).`));
C.push(P(`The hydrological state of an unsaturated soil can be described through two complementary variables: volumetric water content, which quantifies the amount of water stored in the pores, and matric potential, which expresses the energy state of that water; in geotechnical applications the latter is commonly discussed in terms of matric suction, i.e. the absolute value of the negative matric potential. The relationship between the two is governed by the soil water retention curve (METER Group, 2026c; Aldaz-Lusarreta et al., 2023).`));
C.push(P(`Soil moisture was monitored with TEROS 10 sensors and matric suction with TEROS 21 sensors (METER Group). The TEROS 10 is a dielectric sensor that estimates VWC from the apparent dielectric permittivity of the surrounding medium at 70 MHz, a frequency chosen to limit the influence of salinity and texture (METER Group, 2026a, 2026c). The TEROS 21 is a maintenance-free matric-potential sensor based on engineered porous ceramic discs that equilibrate hydraulically with the surrounding soil; the sensor measures the dielectric response of the ceramic and converts it into matric potential through the known retention behaviour of the ceramic material (METER Group, 2026b, 2026d; Peranić et al., 2022). The combined use of the two sensors allows simultaneous tracking of water storage and suction, which is useful under transient infiltration because similar water contents may correspond to different suction states depending on wetting or drying paths. TEROS-based configurations are increasingly used in laboratory slope models, field landslide monitoring and IoT-based slope forecasting (Peranić et al., 2022; Oguz et al., 2022; Piciullo et al., 2025); dielectric sensors may benefit from soil-specific calibration when high accuracy is required (Cominelli et al., 2024; Fragkos et al., 2025), and ceramic capacitive suction sensors offer practical advantages in terms of installation and maintenance (Aldaz-Lusarreta et al., 2023).`));
C.push(P(`Vertical z6-28525 (V) is located beneath forest cover and vertical z6-28531 (NV) in an adjacent open area (Tagarelli and Cotecchia, 2022). V includes TEROS 10 and TEROS 21 sensors at 15, 35 and 60 cm below ground level, NV at 15, 30 and 60 cm. In both cases a trench was excavated and the sensors were installed in the trench wall with the TEROS Borehole Installation Tool, which allows controlled insertion and reduces errors due to poor soil–sensor contact, air gaps and preferential flow (METER Group, 2018, 2026). Particular care was devoted to the suction sensors, which require intimate hydraulic contact between the ceramic and the soil; the soil around them was carefully restored after placement (METER Group, 2018; Sattler et al., 2021). Cable terminals were protected with corrugated sheaths, and backfilling was carried out so as to minimise artificial preferential pathways (Bovolenta et al., 2020).`));
C.push(H3("2.2.3 Data acquisition and monitoring period"));
C.push(P(`The dataset covers the period from 1 January 2025 to 30 September 2026. Rainfall was recorded at 10-min resolution at the five gauges, and VWC and suction at 5-min resolution from 31 January 2025 onwards (Table 1). All timestamps were referred to UTC+1; the soil logger switched to daylight-saving time on 29 March 2026 and was corrected accordingly. Soil data are complete except for a gap of the VWC sensor at 15 cm in the vegetated vertical between 31 January and 4 March 2026. No gap filling was applied: an event index was not computed when any sample in its window was missing.`));
C.push(...table(`Monitoring dataset (1 January 2025 – 30 September 2026). Rainfall totals per gauge; soil sensors with completeness and median values over the record.`,
  ["Series", "Resolution", "Start", "Total / median", "Completeness"],
  [["Albori (rain)", "10 min", "01/01/2025", "2014 mm", "–"],
   ["Cetara (rain)", "10 min", "01/01/2025", "1837 mm", "–"],
   ["Cetara S.C. (rain)", "10 min", "01/01/2025", "2140 mm", "–"],
   ["Dragonea (rain)", "10 min", "01/01/2025", "2247 mm", "–"],
   ["Salerno G.C. (rain)", "10 min", "01/01/2025", "1694 mm", "–"],
   ["NV: VWC 15 / 30 / 60 cm", "5 min", "31/01/2025", "0.061 / 0.146 / 0.213 m^{3} m^{-3}", "100%"],
   ["NV: suction 15 / 30 / 60 cm", "5 min", "31/01/2025", "33.5 / 56.2 / 57.0 kPa", "100%"],
   ["V: VWC 15 / 35 / 60 cm", "5 min", "31/01/2025", "0.038 / 0.116 / 0.083 m^{3} m^{-3}", "94.8% / 100% / 100%"],
   ["V: suction 15 / 35 / 60 cm", "5 min", "31/01/2025", "75.1 / 107.6 / 96.9 kPa", "100%"]],
  [2.6, 1.1, 1.3, 2.6, 1.7]));
C.push(P(`Figure 2 shows the joint time series. Rainfall totals over the 21 months ranged from 1694 mm at Salerno G.C. to 2247 mm at Dragonea, with 987–1332 mm in 2025. The signals are physically consistent and display a marked seasonal cycle. During summer 2025 both profiles dried to suctions above 10^{3} kPa and VWC below 0.05 m^{3} m^{-3} at 15 cm. Re-wetting started in September 2025 at the open-area site, where every storm produced a sharp VWC rise and suction drop at all three depths. In the vegetated profile, by contrast, the deeper sensors remained dry (VWC at 60 cm ≈ 0.026 m^{3} m^{-3}, suction ≈ 1500 kPa) until the storm of 25–26 October 2025, about five to six weeks later. From November 2025 to February 2026 both profiles were close to saturation, with suction frequently below 10 kPa and down to the sensor floor (0.1 kPa), and all four documented landslides occurred within this wet period. The open-area profile was systematically wetter than the vegetated one (median VWC at 60 cm 0.213 vs 0.083 m^{3} m^{-3}) and responded to many more events. A second drying phase began in March–April 2026.`));
C.push(...figure("Fig02_timeseries.png", `Monitoring time series, January 2025 – September 2026. (a) Daily rainfall at Salerno G.C. (bars, left axis) and cumulative rainfall at the five gauges (lines, right axis). (b) VWC and (c) matric suction at 15, 30 and 60 cm in the non-vegetated vertical (NV). (d) VWC and (e) matric suction at 15, 35 and 60 cm in the vegetated vertical (V). Dashed red lines: landslides L1–L4. Suction is shown on a logarithmic axis; 0.1 kPa is the lower limit of the sensor output.`));

// ------------------------------------------------------------------ 3 EVENTS & INFILTRATION
C.push(H1("3. Event characterization and infiltration dynamics"));
C.push(H2("3.1 Identification of hydrometeorological events"));
C.push(H3("3.1.1 Rainfall events and pluviometric indices"));
C.push(P(`Independent rainfall events were identified with the Inter-Event Time Definition (IETD) approach (Restrepo-Posada and Eagleson, 1982; Adams and Papa, 2000; Dunkerley, 2008). The method assumes that rainfall can be partitioned into independent events if successive precipitation pulses are separated by a sufficiently long dry interval T_{s}, which represents the minimum time required for the system to recover from antecedent conditions. A threshold T_{s} = 24 h was adopted, consistent with practice in Mediterranean environments and event-based hydrological modelling. Let P(t_{i}) > 0 denote the rainfall recorded in the 10-min interval ending at t_{i}; a new event starts whenever the dry interval between two consecutive wet intervals exceeds T_{s}. For each event j, the start time t_{start}^{(j)} is the beginning of its first wet interval and the end time t_{end}^{(j)} the end of its last wet interval. The cumulative rainfall is`));
C.push(EQ(`E^{(j)} = Σ_{i ∈ j} P(t_{i})`, 1));
C.push(P(`and the duration is D^{(j)} = t_{end}^{(j)} − t_{start}^{(j)}. The maximum intensity I_{max} was computed as the largest 60-min moving sum within the event (mm h^{-1}). Following Patton et al. (2023), the largest moving totals over 1, 3, 6, 12 and 24 h within the event (P_{1h}–P_{24h}) and the antecedent rainfall over 3, 7, 14 and 30 days before t_{start} (A_{3d}–A_{30d}) were also computed. Events with E < 10 mm were discarded, as such low-magnitude occurrences are unlikely to alter soil moisture significantly, especially in the context of landslide triggering. The analysis was carried out separately for each rain gauge.`));
C.push(P(`The IETD procedure yielded 93–123 rain spells per gauge, of which 44–46 exceeded 10 mm (Table 2). Median events lasted 30–35 h and delivered 24–32 mm, with maxima of 148–246 mm and peak hourly intensities of 38–48 mm h^{-1}. Figure 3a illustrates the identification for the autumn of 2025 at Salerno G.C.`));
C.push(...table(`Rainfall events identified at each gauge (IETD = 24 h, E ≥ 10 mm). Medians and maxima over all events; landslide events are those associated with at least one documented landslide (Section 4.1).`,
  ["Gauge", "Rain spells", "Events E ≥ 10 mm", "Median D (h)", "Median E (mm)", "Max E (mm)", "Max I_{max} (mm h^{-1})", "Events with soil data", "Landslide events"],
  [["Albori", "100", "46", "34.3", "31.5", "174.3", "38.5", "42", "4"],
   ["Cetara", "93", "44", "29.8", "28.2", "148.2", "42.6", "40", "4"],
   ["Cetara S.C.", "123", "46", "35.4", "30.2", "226.7", "48.1", "41", "4"],
   ["Dragonea", "113", "46", "33.2", "30.7", "246.1", "46.0", "42", "3"],
   ["Salerno G.C.", "96", "44", "31.4", "24.2", "190.6", "38.2", "39", "3"]],
  [1.6, 1, 1.1, 1, 1, 1, 1.2, 1.1, 1.1], { size: 19 }));
C.push(H3("3.1.2 Hydrological indices"));
C.push(P(`To quantify rainfall–soil interactions, a set of event-scale indices was derived from the VWC and suction series (Table 3). The antecedent state was computed as the mean over the 60 min preceding t_{start}, which reduces the effect of sensor noise. The response was searched in the window [t_{start}, t_{end} + 24 h]: since by construction of the IETD no rain falls in the 24 h after t_{end}, the extension captures the delayed peaks of the deeper sensors without mixing different events. The TEROS 21 output is expressed as matric suction s = −ψ (kPa, positive), so that wetting corresponds to a suction decrease.`));
C.push(...table(`Event-based hydrological indices derived from VWC and matric suction series for each depth and vertical.`,
  ["Index", "Definition", "Description"],
  [["VWC_{0}^{(j)}", "mean VWC in [t_{start} − 60 min, t_{start}]", "Antecedent volumetric water content: moisture state at the onset of the event."],
   ["VWC_{peak}^{(j)}", "max VWC in [t_{start}, t_{end} + 24 h]", "Maximum water content reached in response to the event."],
   ["ΔVWC^{(j)}", "VWC_{peak} − VWC_{0}", "Net increase of stored water; proxy of the effective infiltration response."],
   ["s_{0}^{(j)}", "mean suction in [t_{start} − 60 min, t_{start}]", "Antecedent matric suction: initial hydraulic state and capacity of the soil to absorb rainfall."],
   ["s_{min}^{(j)}", "min suction in [t_{start}, t_{end} + 24 h]", "Lowest suction reached, i.e. maximum reduction of capillary stresses."],
   ["Δs^{(j)}", "s_{min} − s_{0}", "Suction change induced by infiltration (negative values = suction drop)."]],
  [1.3, 2.6, 4.6], { leftCols: [1, 2] }));
C.push(P(`Figure 3b–d illustrates the extraction for the storm of 25–28 October 2025 (landslide L1). At the open-area site the 15-cm sensor peaked about 1 h after the main burst (ΔVWC = 0.089), the 30-cm sensor shortly after (0.064) and the 60-cm sensor about 6 h later (0.034); suction at 15 and 30 cm collapsed from 5–12 kPa to the sensor floor within the first hours, whereas at 60 cm it decreased from 33 to 9 kPa.`));
C.push(...figure("Fig03_events_and_indices.png", `(a) Identification of rainfall events at Salerno G.C., 18 October – 5 December 2025: hourly rainfall, retained events (shaded; labels give E and D) and landslides (dashed). (b–d) Extraction of the hydrological indices for the event of 25–28 October 2025 (landslide L1) at the non-vegetated vertical: (b) hourly rainfall; (c) VWC with antecedent value (circle), peak (triangle) and ΔVWC (arrows); (d) matric suction with antecedent value and minimum (inverted triangle). Yellow: rainfall event; grey: 24-h response window.`));

C.push(H2("3.2 Clustering and infiltration velocity analysis"));
C.push(H3("3.2.1 Event classification"));
C.push(P(`For each vertical and depth, events were first filtered according to the relative magnitude of their response; an event was considered relevant when`));
C.push(EQ(`ΔVWC^{(j)} ≥ 0.05 · VWC_{0}^{(j)}`, 2));
C.push(P(`The ΔVWC values of the relevant events were then standardised as Z^{(j)} = (ΔVWC^{(j)} − μ)/σ, where μ and σ are the mean and standard deviation of ΔVWC over the relevant events of the same gauge, vertical and depth, which allows comparison across depths and sites with different baselines. Events were classified as irrelevant (Eq. 2 not satisfied), relevant (Eq. 2 satisfied and Z < 1) or extreme (Eq. 2 satisfied and Z ≥ 1).`));
C.push(H3("3.2.2 Infiltration velocity"));
C.push(P(`Assuming predominantly vertical flow, the propagation velocity of the wetting front was approximated as`));
C.push(EQ(`v = Δz / Δt`, 3));
C.push(P(`where Δz is the vertical distance between two sensors and Δt the lag between their VWC peaks; only events classified as relevant or extreme at both depths were used. Four layers were considered: 0–15 cm (Δt between the centre of the hour of maximum rainfall intensity and the VWC peak at 15 cm), 15–30/35 cm, 30/35–60 cm and 15–60 cm. As a secondary metric, the arrival of the wetting front was defined as the first time at which VWC exceeded VWC_{0} + 0.1·ΔVWC. Velocities at the two verticals were compared with the two-sided Mann–Whitney U test (Mann and Whitney, 1947); ΔVWC and the other indices were compared event by event with the Wilcoxon signed-rank test. In this section the events of the gauge closest to the verticals (Salerno G.C.) are used.`));
C.push(H3("3.2.3 Results"));
C.push(P(`The magnitude of the response decreased with depth (Table 4, Figure 4). At 15 cm in the open area every event was at least relevant, whereas at 60 cm 72% (NV) and 77% (V) of the events with data were irrelevant. Extreme events had median E of 48–82 mm and median I_{max} of 13–35 mm h^{-1}, against 13–19 mm and about 6 mm h^{-1} for irrelevant events. In the E–D space (Figure 4) the deep response is confined to the upper-right region, where all landslide events also fall. In the vegetated profile the only extreme event at 60 cm was the storm of L1, which re-wetted a profile that had been dry since summer (VWC_{0} = 0.026, s_{0} ≈ 1500 kPa).`));
C.push(...table(`Classification of events at Salerno G.C. by vertical and depth: number of events and medians of E and ΔVWC per class (events without soil data excluded).`,
  ["Vertical, depth", "Irrelevant n", "Relevant n", "Extreme n", "Median E irrel. / rel. / extr. (mm)", "Median ΔVWC rel. / extr."],
  [["NV, 15 cm", "0", "32", "7", "– / 20.3 / 67.8", "0.069 / 0.151"],
   ["NV, 30 cm", "14", "20", "5", "13.3 / 30.2 / 67.8", "0.031 / 0.157"],
   ["NV, 60 cm", "28", "8", "3", "17.5 / 67.9 / 55.2", "0.048 / 0.092"],
   ["V, 15 cm", "10", "22", "3", "12.9 / 30.2 / 68.0", "0.012 / 0.094"],
   ["V, 35 cm", "25", "12", "2", "16.8 / 66.4 / 47.6", "0.024 / 0.074"],
   ["V, 60 cm", "30", "8", "1", "18.5 / 67.9 / 81.8", "0.019 / 0.095"]],
  [1.4, 1, 1, 1, 2.4, 1.9]));
C.push(...figure("Fig04_ED_classes.png", `Rainfall events at Salerno G.C. in the duration–cumulative rainfall (D–E) space, coloured by the class of the soil-moisture response at 60 cm in (a) the non-vegetated and (b) the vegetated vertical. Stars: landslide events (L3 and L4 fall in the same event at this gauge). Logarithmic axes.`));
C.push(P(`Vegetation strongly attenuated the response (Figure 5, Table 5). Event by event, ΔVWC in the vegetated profile was smaller than in the open area in 97% of the events at 15 cm (median 0.009 vs 0.080 m^{3} m^{-3}), 90% at 30/35 cm (0.002 vs 0.020) and 69% at 60 cm (Wilcoxon p ≤ 0.001 at all depths). The suction drop was also smaller under forest cover at 15 cm (median −9.2 vs −23.6 kPa, p = 0.010) and at 30/35 cm (p = 0.004). Antecedent VWC was lower in the vegetated profile at all depths (at 60 cm in all events: 0.126 vs 0.243 m^{3} m^{-3}) and antecedent suction at 60 cm higher (31.7 vs 23.0 kPa), indicating a drier deep profile, consistent with root-water uptake and interception.`));
C.push(P(`The wetting front propagated more slowly under vegetation. From the surface to 15 cm, the median peak-lag velocity was 0.9 cm h^{-1} at V and 4.9 cm h^{-1} at NV (median lag 14.8 vs 1.7 h; p = 0.031). In the lower layer (30/35–60 cm) the difference was the largest, 1.8 vs 9.5 cm h^{-1} (rank-biserial r = −0.80, p = 0.003), and over 15–60 cm 2.4 vs 10.6 cm h^{-1} (p = 0.014); in the intermediate layer the difference was not significant (3.0 vs 4.2 cm h^{-1}, p = 0.53). The onset-based velocities showed the same direction with smaller, non-significant differences. At the vegetated vertical, the 35-cm sensor often responded earlier and more than the 15-cm sensor, which may indicate preferential flow along roots or a local contact effect and should be verified in the field.`));
C.push(...table(`Infiltration velocity (peak-lag, Eq. 3) at the vegetated (V) and non-vegetated (NV) verticals, Salerno G.C. events. n: events with a positive lag; p: two-sided Mann–Whitney test; RB: rank-biserial correlation (negative = slower under vegetation).`,
  ["Layer", "n V", "n NV", "Median v V (cm h^{-1})", "Median v NV (cm h^{-1})", "RB", "p"],
  [["0–15 cm", "21", "35", "0.9", "4.9", "−0.35", "0.031"],
   ["15–35 (V) / 15–30 (NV) cm", "11", "23", "3.0", "4.2", "−0.14", "0.531"],
   ["35–60 (V) / 30–60 (NV) cm", "8", "11", "1.8", "9.5", "−0.80", "0.003"],
   ["15–60 cm", "7", "10", "2.4", "10.6", "−0.71", "0.014"]],
  [2.6, .7, .7, 1.4, 1.4, .8, .8]));
C.push(...figure("Fig05_infiltration.png", `Infiltration dynamics at the vegetated (V) and non-vegetated (NV) verticals (Salerno G.C. events). (a) Peak-lag velocity of the wetting front by layer (boxes: interquartile range and median; points: events); p-values of the Mann–Whitney test, in bold when < 0.05. (b) Event ΔVWC at V versus NV for the three depth pairs; points below the 1:1 line indicate a smaller response under vegetation.`));

C.push(H2("3.3 Statistical analysis of landslide predictors"));
C.push(H3("3.3.1 Univariate discriminant metrics"));
C.push(P(`The discriminant capacity of each variable was evaluated separately for each rain gauge, in order to preserve spatial heterogeneity. Let X denote a feature and Y ∈ {0, 1} the response, with Y = 1 for events associated with a landslide. The primary metric is the area under the ROC curve, AUC = P(X_{1} > X_{0}), equivalent to the normalised Mann–Whitney U statistic, with X_{1} ~ P(X | Y = 1) and X_{0} ~ P(X | Y = 0). Since some predictors have inverse relationships with instability (e.g. suction), a direction-invariant form was adopted:`));
C.push(EQ(`AUC* = max(AUC, 1 − AUC)`, 4));
C.push(P(`The significance of the separation was tested with the two-sided Mann–Whitney U test (Mann and Whitney, 1947) and, because many features were tested, p-values were also adjusted with the Holm (1979) procedure within each gauge. The effect size was expressed by the rank-biserial correlation RB = 2·AUC − 1 (Kerby, 2014), which is signed: positive values indicate larger values in triggering events. To locate triggering conditions within the overall distribution, the empirical percentile π_{i} = 100·F̂_{X}(x_{i}^{(1)}) of each landslide event was computed and summarised by the median π̃; for variables in which lower values indicate a more critical state, 100 − π̃ was used. An operational threshold τ* was obtained by maximising the Youden (1950) index`));
C.push(EQ(`J(τ) = TPR(τ) − FPR(τ),   τ* = arg max_{τ} J(τ)`, 5));
C.push(P(`where TPR(τ) = P(X ≥ τ | Y = 1) and FPR(τ) = P(X ≥ τ | Y = 0) (with the inequality reversed for inverse variables), and the recall TP/(TP + FN) at τ* was reported. Because these thresholds are estimated on the same events, they are descriptive; out-of-sample performance is assessed in Section 3.3.3.`));
C.push(H3("3.3.2 Bivariate, vertical-profile and multivariate analyses"));
C.push(P(`The interaction between antecedent soil conditions and rainfall forcing was examined in bivariate phase spaces (E versus antecedent VWC), where the joint density of non-triggering events was estimated by Gaussian kernel density estimation with Scott's (1992) bandwidth. The antecedent vertical profile X_{pre} = [VWC_{0,15}, VWC_{0,30/35}, VWC_{0,60}] of each landslide event was compared with the median and interquartile range of the non-triggering events. Finally, a multivariate anomaly index was computed as the Mahalanobis (1936) distance from the distribution of non-triggering events,`));
C.push(EQ(`D_{M}(x) = [(x − μ)^{T} Σ^{−1} (x − μ)]^{1/2}`, 6));
C.push(P(`with μ and Σ estimated from non-triggering events and x = [E, I_{max}, VWC_{0} NV 60 cm]. Under multivariate normality D_{M}^{2} ~ χ^{2}_{k}, and events with D_{M} > (χ^{2}_{k,0.95})^{1/2} = 2.80 (k = 3) were classified as anomalous.`));
C.push(H3("3.3.3 Multi-variable landslide indicator and cross-validation"));
C.push(P(`To test whether combining rainfall and soil-state variables improves the detection of triggering events, a transparent indicator was defined for each gauge and each combination of k variables. Each variable is converted into its empirical percentile within the non-triggering events, oriented so that higher values are more critical (more rainfall, wetter soil, larger ΔVWC; suction with reversed sign), and the indicator is the mean of the k percentiles:`));
C.push(EQ(`I = (1/k) Σ_{m=1}^{k} 100 · F̂_{m,0}(x_{m})`, 7));
C.push(P(`where F̂_{m,0} is the empirical distribution function of variable m in non-triggering events. An alarm is issued when I ≥ τ, with τ chosen by maximising the Youden index (ties resolved toward the lower threshold, i.e. favouring detection). Percentiles make variables with different units commensurable without estimating weights. Performance was evaluated by leave-one-event-out cross-validation: for every event, the reference distributions and the threshold were recomputed without that event, which was then classified. The contingency table was summarised by the probability of detection POD = TP/(TP + FN), the probability of false detection POFD = FP/(FP + TN), the false alarm ratio FAR = FP/(TP + FP) and the true skill statistic TSS = POD − POFD (Hanssen and Kuipers, 1965). Fixed combinations of 1–15 variables were tested, together with all 455 combinations of three variables among 8 rainfall variables, 5 antecedent VWC values and antecedent suction at 15 and 30 cm in the open area. Because choosing the best combination on the same data is optimistic, nested strategies in which the combination with the highest training AUC is selected within each fold were also evaluated; their performance is an unbiased estimate of the selection procedure. The same common set of events (those with all variables available, 39–42 per gauge) was used for all combinations.`));

// ------------------------------------------------------------------ 4 COMPARATIVE ANALYSIS
C.push(H1("4. Comparative analysis: landslide-triggering vs. non-triggering conditions"));
C.push(H2("4.1 Landslide events"));
C.push(P(`Four landslides were documented in the study sector during the monitoring period (Table 6), all along the road network between Salerno and Cetara: L1 on 26 October 2025 at km 47.7 of the SS163 Amalfitana in Vietri sul Mare (time not reported); L2 in the afternoon of 25 November 2025 along Via Fra' Generoso, between Salerno and Vietri sul Mare; L3 at dawn on 6 February 2026 at Fuenti, km 47.3 of the SS163 between Vietri sul Mare and Cetara; and L4 on 12 February 2026, between 13:45 and 14:30, in Via Madonna dell'Arco in Vietri sul Mare, below km 48.3 of the SS163. A landslide was associated with a rainfall event when its time interval (± 12 h for L1, ± 3 h for L2, ± 0.5 h for L3 and L4) overlapped the window [t_{start}, t_{end} + 24 h]. All four landslides were matched to events with E ≥ 10 mm at every gauge. At Albori, Cetara and Cetara S.C. they correspond to four distinct events; at Dragonea and Salerno G.C. the rainfall between 4 and 13 February 2026 was not interrupted by 24 dry hours, so that L3 and L4 fall in the same event. The analysis therefore includes 18 triggering and 186 non-triggering events over the five gauges.`));
C.push(NOTE("[To be completed: landslide type, volume and source of information for L1–L4.]"));
C.push(...table(`Documented landslides and characteristics of the associated rainfall events at Salerno G.C. (closest gauge). Antecedent soil state in the non-vegetated (NV) and vegetated (V) verticals.`,
  ["", "L1", "L2", "L3 + L4", ],
  [["Date", "26/10/2025", "25/11/2025", "06/02/2026; 12/02/2026"],
   ["Location", "SS163 km 47.7, Vietri sul Mare", "Via Fra' Generoso, Salerno–Vietri", "Fuenti, SS163 km 47.3; Via Madonna dell'Arco, Vietri"],
   ["Event start – end", "25/10 20:30 – 28/10 01:30", "24/11 06:40 – 27/11 17:30", "04/02 10:30 – 12/02 21:00"],
   ["D (h) / E (mm)", "53 / 81.8", "83 / 65.0", "203 / 190.6"],
   ["I_{max} (mm h^{-1}) / A_{30d} (mm)", "35.0 / 67", "7.4 / 256", "31.4 / 202"],
   ["VWC_{0} NV 15 / 60 cm", "0.089 / 0.232", "0.106 / 0.264", "0.091 / 0.265"],
   ["VWC_{0} V 60 cm", "0.026", "0.171", "0.168"],
   ["s_{0} NV 15 cm (kPa)", "5.4", "2.0", "14.7"],
   ["Class NV 60 / V 60 cm", "relevant / extreme", "relevant / irrelevant", "relevant / relevant"]],
  [2.2, 2.2, 2.2, 2.6], { size: 19, leftCols: [1, 2, 3] }));
C.push(P(`The triggering events were heterogeneous (Figure 6). L1 followed an intense burst of 6–8 h (I_{max} = 35–46 mm h^{-1} at four gauges, 11.5 mm h^{-1} at Dragonea) that delivered 40–143 mm on a profile still partially dry after the summer. L2 occurred after a long, low-intensity sequence (I_{max} = 7–24 mm h^{-1}) on a wet profile, with 240–290 mm in the preceding 30 days. L3 occurred during the most intense phase of a multi-day storm (E = 148–246 mm), and L4 after a further 60–100 mm on a profile that had not drained since. The mean values of the features differ systematically between the two classes at every gauge (Table 7): triggering events had 3–5 times larger E, 2–3 times longer D and 4–6 times larger A_{7d}, slightly but consistently wetter antecedent profiles, antecedent suction at 15 cm of 5–11 kPa against 210–370 kPa on average, and a deep ΔVWC in the vegetated profile about eight times larger.`));
C.push(...figure("Fig06_rainfall_around_landslides.png", `Cumulative hourly rainfall at the five gauges from 72 h before to 24 h after each landslide: (a) L1, (b) L2, (c) L3 and (d) L4. The shaded band shows the uncertainty of the landslide time (L1: time not reported).`));
C.push(...table(`Mean feature values in landslide-triggering (LS) and non-triggering (no LS) events at each gauge.`,
  ["Feature", "Albori LS / no LS", "Cetara LS / no LS", "Cetara S.C. LS / no LS", "Dragonea LS / no LS", "Salerno G.C. LS / no LS"],
  [["E (mm)", "102.5 / 34.3", "104.7 / 31.3", "165.2 / 31.4", "135.0 / 39.1", "112.5 / 29.5"],
   ["D (h)", "77.8 / 41.0", "76.8 / 36.1", "133.8 / 36.0", "116.1 / 37.8", "112.8 / 34.3"],
   ["I_{max} (mm h^{-1})", "24.9 / 11.2", "26.0 / 11.4", "33.1 / 11.7", "18.6 / 11.9", "24.6 / 10.2"],
   ["A_{7d} (mm)", "106.3 / 16.5", "84.6 / 15.0", "73.9 / 16.2", "107.3 / 20.3", "69.7 / 17.8"],
   ["VWC_{0} NV 15 cm", "0.101 / 0.066", "0.102 / 0.066", "0.091 / 0.067", "0.096 / 0.066", "0.095 / 0.069"],
   ["VWC_{0} NV 60 cm", "0.261 / 0.214", "0.261 / 0.213", "0.250 / 0.214", "0.254 / 0.213", "0.254 / 0.216"],
   ["VWC_{0} V 60 cm", "0.136 / 0.106", "0.136 / 0.106", "0.123 / 0.108", "0.122 / 0.105", "0.122 / 0.109"],
   ["s_{0} NV 15 cm (kPa)", "5.9 / 347", "5.4 / 366", "10.9 / 354", "7.2 / 338", "7.4 / 212"],
   ["ΔVWC NV 60 cm", "0.038 / 0.015", "0.038 / 0.016", "0.051 / 0.013", "0.044 / 0.015", "0.044 / 0.016"],
   ["ΔVWC V 60 cm", "0.032 / 0.005", "0.032 / 0.005", "0.045 / 0.004", "0.041 / 0.005", "0.041 / 0.005"]],
  [1.7, 1.4, 1.4, 1.5, 1.4, 1.5], { size: 18 }));

C.push(H2("4.2 Statistical distribution of predictive features"));
C.push(P(`Figure 7 compares the distributions for the gauge closest to the verticals. Triggering events lie in the upper part of the distributions of all rainfall variables and of ΔVWC at 60 cm in the vegetated profile, which is almost always zero in non-triggering events because the deep forest profile responds only to large storms. Antecedent suction at 15 cm in the open area was 2–15 kPa before all triggering events, below the lower quartile of non-triggering events. Antecedent VWC at 15 cm was above the median of non-triggering events for all landslides, whereas at 60 cm the triggering events overlap the upper half of the non-triggering distribution, reflecting the fact that the deep open-area profile remained wet throughout the winter regardless of whether a landslide occurred.`));
C.push(...figure("Fig07_boxplots_reference_gauge.png", `Distributions of selected features in non-triggering events and landslide-triggering events at Salerno G.C. Boxes: interquartile range and median; whiskers: 1.5 IQR; grey points: non-triggering events; stars: landslide events. AUC* and unadjusted Mann–Whitney p-values are reported for each feature. Suction is shown on a logarithmic axis.`));

C.push(H2("4.3 Discriminant capacity and performance metrics"));
C.push(P(`Table 8 and Figure 8 summarise the discriminant metrics. The event rainfall variables were the strongest single discriminants at every gauge: E (AUC* = 0.88–1.00, median percentile of the landslide events 92–97) and the 6-h maximum P_{6h} (0.92–0.97), followed by D (0.82–0.95) and A_{7d} (0.75–0.96). Among the hydrological variables, ΔVWC at 60 cm in the vegetated profile reached AUC* = 0.90–0.95 (p = 0.004–0.016), and the antecedent state of the shallow open-area profile was consistently informative: s_{0} at 15 cm (AUC* = 0.78–0.90, RB = −0.57 to −0.80) and VWC_{0} at 15 and 30 cm (0.74–0.89). The discriminant power of antecedent VWC decreased with depth, to 0.65–0.80 at 60 cm in the open area and 0.61–0.73 in the vegetated profile. The Youden thresholds of the shallow open-area variables were remarkably stable across gauges (s_{0} ≤ 14.7 kPa at four gauges, ≤ 24.2 kPa at Cetara S.C.; VWC_{0} ≥ 0.089–0.091 m^{3} m^{-3}), with recall equal to 1 at all gauges for s_{0}.`));
C.push(P(`The suction drop Δs behaved opposite to the intuitive expectation: during triggering events the drop was smaller (mean −5 to −11 kPa, against −127 to −170 kPa), because suction was already low at the onset. Δs is therefore a proxy of the antecedent state rather than an independent indicator of instability. With three or four positive events per gauge, unadjusted p-values were below 0.05 for most rainfall variables and for ΔVWC at 60 cm, but after the Holm correction over the 46 features of each gauge only E and P_{3h} at Cetara S.C. remained significant; AUC* and RB should therefore be read primarily as effect sizes.`));
C.push(...table(`Discriminant metrics of selected features: range over the five gauges of AUC*, rank-biserial correlation (RB), unadjusted Mann–Whitney p-value, median percentile of landslide events (π̃; 100 − π̃ for suction) and Youden threshold τ*.`,
  ["Feature", "AUC*", "RB", "p", "π̃", "τ*"],
  [["E (mm)", "0.88–1.00", "0.77–1.00", "< 0.001–0.029", "92–97", "≥ 40–102 mm"],
   ["P_{6h} (mm)", "0.92–0.97", "0.84–0.94", "0.001–0.016", "89–95", "≥ 25–38 mm"],
   ["D (h)", "0.82–0.95", "0.65–0.90", "0.003–0.035", "79–97", "≥ 51–59 h"],
   ["A_{7d} (mm)", "0.75–0.96", "0.49–0.92", "0.003–0.106", "81–98", "≥ 37–59 mm"],
   ["I_{max} (mm h^{-1})", "0.79–0.92", "0.58–0.83", "0.007–0.100", "74–93", "≥ 11–31"],
   ["ΔVWC V 60 cm", "0.90–0.95", "0.80–0.89", "0.004–0.016", "86–94", "≥ 0.007"],
   ["ΔVWC NV 60 cm", "0.83–0.89", "0.67–0.77", "0.013–0.054", "81–85", "≥ 0.018–0.034"],
   ["s_{0} NV 15 cm (kPa)", "0.78–0.90", "−0.80 to −0.57", "0.005–0.067", "77–88", "≤ 14.7–24.2"],
   ["VWC_{0} NV 15 cm", "0.74–0.89", "0.49–0.78", "0.012–0.119", "77–85", "≥ 0.089–0.091"],
   ["VWC_{0} NV 30 cm", "0.74–0.88", "0.48–0.76", "0.014–0.124", "78–87", "≥ 0.180–0.182"],
   ["VWC_{0} NV 60 cm", "0.65–0.80", "0.30–0.60", "0.054–0.333", "65–87", "≥ 0.264"],
   ["VWC_{0} V 60 cm", "0.61–0.73", "0.23–0.45", "0.145–0.493", "70–90", "≥ 0.168"]],
  [2, 1.1, 1.3, 1.4, .8, 1.4]));
C.push(...figure("Fig08_discriminant_synthesis.png", `Synthesis of the discriminant power. (a) AUC* per feature and gauge (asterisk: unadjusted Mann–Whitney p < 0.05). (b) Rank-biserial correlation per gauge (negative values for suction: lower suction in triggering events); dotted lines at |RB| = 0.5.`));

C.push(H2("4.4 Mapping and combined variable interaction"));
C.push(P(`In the space of cumulative rainfall and antecedent shallow VWC (Figure 9), non-triggering events concentrate at E < 60 mm across the whole range of VWC_{0}, whereas landslide events occupy the region where large E coincides with VWC_{0} ≥ 0.09 m^{3} m^{-3}, outside the main density of the non-triggering population at every gauge. Non-triggering events with comparable E (up to 140 mm) occurred with lower antecedent moisture (VWC_{0} ≈ 0.06–0.07), and wet antecedent conditions alone, without large E, were not associated with landslides. The exception is L1 at Dragonea, where the gauge recorded only 40 mm.`));
C.push(...figure("Fig09_E_vs_VWC0_NV15.png", `Rainfall events of each gauge in the space of antecedent VWC at 15 cm in the non-vegetated vertical and cumulative rainfall E. Blue shading: kernel density of non-triggering events; stars: landslide events.`));
C.push(P(`The antecedent vertical profiles (Figure 10) show that, in the open area, the triggering events of L2, L3 and L4 occurred with the whole column wetter than the median non-triggering state, close to or above the upper quartile at 15 and 30 cm and at the upper limit of the IQR at 60 cm; L1 occurred with a moist shallow layer but a deep VWC slightly below the median. In the vegetated profile the contrast is larger: L2–L4 occurred with the deep layers well above the upper quartile, whereas L1 occurred with the driest deep state of the record. The diagnostic depth is therefore not unique: the shallow layer is consistently wet before all landslides, while the deep state distinguishes the winter landslides from the first autumn one.`));
C.push(...figure("Fig10_VWC0_profiles.png", `Antecedent VWC profiles before the landslide events (red) compared with the median (dashed) and interquartile range (shaded) of non-triggering events, Salerno G.C.: (a) non-vegetated and (b) vegetated vertical. VWC at 15 cm in the vegetated vertical is missing for L3 + L4 (sensor gap).`));
C.push(P(`The Mahalanobis distance in the space (E, I_{max}, VWC_{0} NV 60 cm) separated the two classes at four gauges, with median D_{M} of triggering events of 3.0–6.6 against 1.3 for non-triggering events and AUC = 0.89–1.00 (p ≤ 0.004, one-sided); at Dragonea the separation was weaker (AUC = 0.64) because of the low rainfall recorded for L1. Overall, 12 of the 18 triggering events exceeded the χ^{2} threshold, against 15 of the 186 non-triggering events.`));

C.push(H2("4.5 Multi-variable landslide indicator"));
C.push(P(`Table 9 and Figure 11 report the cross-validated performance of the indicator of Eq. (7). Event rainfall alone detected 14 of the 18 triggering events with 29 false alarms (POD = 0.78, POFD = 0.16, TSS = 0.62). Adding the antecedent VWC at 15 cm in the open area detected one more landslide and reduced false alarms to 17 (POD = 0.83, POFD = 0.09, TSS = 0.74); at Cetara and Salerno G.C. this indicator detected all landslides with a single false alarm (TSS = 0.97). The best fixed combination, E + P_{6h} + A_{7d} + VWC_{0} NV 15 cm, detected 16 of 18 landslides with 13 false alarms (TSS = 0.82). Among the 455 three-variable combinations, the best ones paired a short-duration rainfall variable with the shallow soil state, e.g. P_{6h} + VWC_{0} NV 15 cm + s_{0} NV 30 cm (TSS = 0.82) and P_{3h} + A_{7d} + s_{0} NV 30 cm (TSS = 0.81, POFD = 0.03); by type, combinations of two rainfall variables and one suction variable had the highest median TSS (0.66), against 0.64 for rainfall only and 0.32–0.44 for combinations dominated by VWC. The combination including ΔVWC at 60 cm in the vegetated profile, which is available only during the event, had the lowest false alarm ratio (FAR = 0.30).`));
C.push(P(`Two results temper these figures. First, adding more variables did not help: with all 8 rainfall variables TSS was 0.67, and with 15 rainfall and soil variables 0.59, because averaging percentiles dilutes the informative variables; combinations including several VWC depths or both verticals performed worse than rainfall alone. Second, when the combination was selected within each fold, TSS dropped to 0.40–0.53 for all families, indicating that, with three or four landslides per gauge, the choice among many candidate combinations is unstable and that the best fixed combinations are optimistic. The robust finding is the consistent gain obtained by pairing event rainfall with the shallow antecedent soil state of the open-area profile.`));
C.push(...table(`Cross-validated (leave-one-event-out) performance of selected indicators, five gauges pooled (18 triggering and 186 non-triggering events). Combinations marked † include a variable measured during the event; "selected" = combination chosen within each fold.`,
  ["Indicator variables", "k", "TP", "FN", "FP", "POD", "POFD", "FAR", "TSS"],
  [["E", "1", "14", "4", "29", "0.78", "0.16", "0.67", "0.62"],
   ["E + A_{7d}", "2", "14", "4", "14", "0.78", "0.08", "0.50", "0.70"],
   ["E + VWC_{0} NV 15", "2", "15", "3", "17", "0.83", "0.09", "0.53", "0.74"],
   ["E + s_{0} NV 15", "2", "13", "5", "14", "0.72", "0.08", "0.52", "0.65"],
   ["D + P_{6h} + VWC_{0} NV 30", "3", "13", "5", "9", "0.72", "0.05", "0.41", "0.67"],
   ["P_{6h} + VWC_{0} NV 15 + s_{0} NV 30", "3", "16", "2", "13", "0.89", "0.07", "0.45", "0.82"],
   ["P_{3h} + A_{7d} + s_{0} NV 30", "3", "15", "3", "5", "0.83", "0.03", "0.25", "0.81"],
   ["E + P_{6h} + A_{7d} + VWC_{0} NV 15", "4", "16", "2", "13", "0.89", "0.07", "0.45", "0.82"],
   ["All 8 rainfall variables", "8", "13", "5", "9", "0.72", "0.05", "0.41", "0.67"],
   ["All 15 variables", "15", "13", "5", "25", "0.72", "0.13", "0.66", "0.59"],
   ["D + A_{7d} + ΔVWC V 60 †", "3", "14", "4", "6", "0.78", "0.03", "0.30", "0.75"],
   ["Selected: rain + VWC_{0}", "2", "11", "7", "16", "0.61", "0.09", "0.59", "0.53"],
   ["Selected: 2 rain + VWC_{0}", "3", "9", "9", "7", "0.50", "0.04", "0.44", "0.46"]],
  [3.4, .5, .6, .6, .6, .8, .8, .8, .8], { size: 19 }));
C.push(...figure("Fig11_indicator_performance.png", `Cross-validated performance of the multi-variable indicator. (a) POD, POFD and TSS with the five gauges pooled; (b) TSS at each gauge (points) and pooled (vertical bar). VWC_{0} and s_{0}: antecedent water content and suction; NV: non-vegetated vertical; numbers after the site: depth (cm).`));

// ------------------------------------------------------------------ 5 DISCUSSION
C.push(H1("5. Discussion"));
C.push(H2("5.1 Discriminant power of rainfall and hydrological variables"));
C.push(P(`Rainfall during the event was the best single discriminant at all gauges, in agreement with Patton et al. (2023), who found that short-duration totals were the most informative predictors of landslide initiation. The hydrological variables did not outperform rainfall individually, but they carried information that rainfall does not contain: all four landslides occurred during the wet season, after the shallow open-area profile had reached suctions below about 15 kPa and VWC above about 0.09 m^{3} m^{-3}. Comparable storms in late summer and early autumn, when the profile was dry, did not trigger landslides. This seasonal preconditioning is captured most directly by the shallow antecedent state, which explains why the combination of E and VWC_{0} or s_{0} at 15–30 cm reduced false alarms by about 40% in cross-validation.`));
C.push(P(`The initial hypothesis that VWC at 60 cm would be the most diagnostic variable is only partly supported. The deep response during the event (ΔVWC at 60 cm, particularly under forest cover) was one of the strongest discriminants, because the deep profile reacts only to the largest storms: it marks events able to transfer water to the base of the cover, which is where failure surfaces in pyroclastic covers commonly develop. The antecedent deep VWC was instead a weak discriminant, for two reasons. In the open area the deep profile stayed wet through the whole winter, so that it was high before most non-triggering winter events as well; in the forest, the first landslide of the season (L1) occurred when the deep profile was still dry, so that L1 was triggered by an intense burst acting on a wet shallow layer rather than on a saturated column. A non-directional multivariate index such as the Mahalanobis distance can flag such events as anomalous, but a directional indicator correctly assigns them to the rainfall component. Taken together, the results suggest that the shallow antecedent state acts as a seasonal switch and the deep response as a marker of storm severity, while the deep antecedent state is too persistent to separate individual events within the wet season.`));
C.push(P(`The suction drop Δs was smaller during triggering events, a counter-intuitive result that is explained by the low antecedent suction: when the profile is close to saturation, suction cannot decrease much further, and the relevant information is the low level reached rather than the change. Suction variables should therefore enter warning criteria as antecedent states, not as event changes.`));
C.push(H2("5.2 The role of vegetation"));
C.push(P(`The comparison between the two verticals shows a clear buffering effect of forest cover: smaller and less frequent water-content increments, smaller suction drops in the upper 35 cm, a drier deep profile in the wet season and a wetting front that reached 15 cm about 13 h later and propagated through the lower layer five times more slowly than in the open area. These effects are consistent with rainfall interception, root-water uptake and the larger storage of the organic topsoil, and indicate that vegetation reduces the frequency with which the deeper part of the cover approaches saturation. Under forest cover the deep profile responded only to the largest storms, which is precisely why its event response discriminated landslide-triggering events so well. The occasional earlier response of the 35-cm sensor relative to the 15-cm sensor suggests preferential flow along roots, which may locally accelerate the transfer of water to depth and deserves verification in the field.`));
C.push(H2("5.3 Implications and limitations"));
C.push(P(`For territorial LEWS, the results suggest a simple and transparent integration: rainfall thresholds can be modulated by the shallow antecedent soil state measured at a representative open-area site, which in this dataset reduced false alarms by about 40% without losing landslides. Percentile-based indicators are easy to communicate, do not require the estimation of weights and can be updated as new events are recorded.`));
C.push(P(`The main limitation is the number of landslides: four landslides, corresponding to three or four events per gauge, constrain statistical power, so that few differences survive correction for multiple testing, and the selection of the best combination among many candidates is unstable, as shown by the nested cross-validation. The five gauges share the same landslides and the same soil measurements and are therefore not independent replicates. The monitoring covers a single wet season with landslides, and the verticals are representative of the study slope rather than of the exact landslide sites along the road network. Landslide times are uncertain for L1 and L2. Extending the record to further wet seasons and landslides is necessary to confirm the thresholds and the combinations identified here.`));

// ------------------------------------------------------------------ 6 CONCLUSIONS
C.push(H1("6. Conclusions"));
C.push(P(`Twenty-one months of rainfall, soil moisture and suction monitoring on a pyroclastic slope near Salerno were used to quantify how much the soil hydrological state contributes to discriminating landslide-triggering from non-triggering rainfall events. The main findings are:`));
C.push(BUL(`Event rainfall (E, P_{6h}, D) was the strongest single discriminant (AUC* = 0.82–1.00), followed by the deep event response under forest cover (ΔVWC at 60 cm, AUC* = 0.90–0.95).`));
C.push(BUL(`The shallow antecedent state of the open-area profile (suction at 15 cm, AUC* = 0.78–0.90; VWC at 15–30 cm, 0.74–0.89) was the most informative pre-event soil variable, with thresholds stable across gauges (s_{0} ≤ 15 kPa, VWC_{0} ≥ 0.09 m^{3} m^{-3}); antecedent VWC at 60 cm was weaker (0.61–0.80).`));
C.push(BUL(`All landslides occurred in the wet season, when a large storm coincided with a wet shallow profile; wet antecedent conditions alone or large storms on a dry profile were not associated with landslides.`));
C.push(BUL(`Vegetation reduced event water-content increments in 69–97% of events and slowed the propagation of the wetting front below 30 cm (1.8 vs 9.5 cm h^{-1}).`));
C.push(BUL(`In leave-one-event-out cross-validation, combining event rainfall with the shallow antecedent VWC raised TSS from 0.62 to 0.74 and halved false alarms; the best combinations of three or four rainfall and soil-state variables reached TSS = 0.82, whereas adding many variables or selecting combinations automatically did not improve performance.`));
C.push(P(`These results support the integration of shallow soil-state monitoring into rainfall-based landslide early warning, as a modulation of rainfall thresholds rather than as a replacement, and call for longer records with more landslides to consolidate the thresholds identified here.`));
C.push(H1("Data and code availability"));
C.push(P(`The processing pipeline, tables and figures are available at https://github.com/angelounisa/Sustainabilty.`));

// ------------------------------------------------------------------ REFERENCES
C.push(H1("References"));
const REFS = [
  "Adams, B.J., and Papa, F. (2000). Urban Stormwater Management Planning with Analytical Probabilistic Models. Wiley, New York.",
  "Aldaz-Lusarreta, A., Campo-Bescós, M.Á., Virto, I., and Giménez, R. (2023). Toward optimal irrigation management at the plot level: evaluation of commercial water potential sensors. Sensors, 23(22), 9255. https://doi.org/10.3390/s23229255",
  "Bilotta, E., Cascini, L., Foresta, V., and Sorbino, G. (2005). Geotechnical characterisation of pyroclastic soils involved in huge flowslides. Geotechnical and Geological Engineering, 23, 365–402. https://doi.org/10.1007/s10706-004-1607-3",
  "Bovolenta, R., Iacopino, A., Passalacqua, R., and Federici, B. (2020). Field measurements of soil water content at shallow depths for landslide monitoring. Geosciences, 10(10), 409. https://doi.org/10.3390/geosciences10100409",
  "Calvello, M., and Piciullo, L. (2016). Assessing the performance of regional landslide early warning models: the EDuMaP method. Natural Hazards and Earth System Sciences, 16, 103–122. https://doi.org/10.5194/nhess-16-103-2016",
  "Comegna, L., Damiano, E., Greco, R., Guida, A., Olivares, L., and Picarelli, L. (2016). Field hydrological monitoring of a sloping shallow pyroclastic deposit. Canadian Geotechnical Journal, 53(7), 1125–1137. https://doi.org/10.1139/cgj-2015-0344",
  "Cominelli, S., Rivera, L.D., Brown, W.G., Ochsner, T.E., and Patrignani, A. (2024). Calibration of TEROS 10 and TEROS 12 electromagnetic soil moisture sensors. Soil Science Society of America Journal, 88(6), 2104–2122. https://doi.org/10.1002/saj2.20777",
  "Dal Seno, N., Evangelista, D., Piccolomini, E., et al. (2024). Comparative analysis of conventional and machine learning techniques for rainfall threshold evaluation under complex geological conditions. Landslides, 21, 2893–2911.",
  "Dunkerley, D. (2008). Identifying individual rain events from pluviograph records: a review with analysis of data from an Australian dryland site. Hydrological Processes, 22, 5024–5036. https://doi.org/10.1002/hyp.7122",
  "Fiorillo, F., and Wilson, R.C. (2004). Rainfall induced debris flows in pyroclastic deposits, Campania (southern Italy). Engineering Geology, 75(3–4), 263–289. https://doi.org/10.1016/j.enggeo.2004.06.014",
  "Fiorillo, F., Guerriero, L., Capobianco, L., Pagnozzi, M., Revellino, P., Russo, F., and Guadagno, F.M. (2019). Inventory of Vietri-Maiori landslides induced by the storm of October 1954 (southern Italy). Journal of Maps, 15(2), 530–537. https://doi.org/10.1080/17445647.2019.1626777",
  "Forte, G., Pirone, M., Santo, A., Nicotera, M.V., and Urciuoli, G. (2019). Triggering and predisposing factors for flow-like landslides in pyroclastic soils: the case study of the Lattari Mts. (southern Italy). Engineering Geology, 257, 105140. https://doi.org/10.1016/j.enggeo.2019.05.014",
  "Fragkos, A., Loukatos, D., Kargas, G., and Arvanitis, K.G. (2025). Performance evaluation of TEROS 10 sensor in diverse substrates and soils of different electrical conductivity using low-cost microcontroller settings. Land, 14(2), 242. https://doi.org/10.3390/land14020242",
  "Guzzetti, F., Melillo, M., Calvello, M., Pecoraro, G., and Mondini, A.C. (2024). Independent demonstration of a deep-learning system for rainfall-induced landslide forecasting in Italy. Landslides, 21, 2171–2178. https://doi.org/10.1007/s10346-024-02294-w",
  "Hanssen, A.W., and Kuipers, W.J.A. (1965). On the relationship between the frequency of rain and various meteorological parameters. Mededelingen en Verhandelingen, 81, Koninklijk Nederlands Meteorologisch Instituut, De Bilt.",
  "Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6, 65–70.",
  "Kerby, D.S. (2014). The simple difference formula: an approach to teaching nonparametric correlation. Comprehensive Psychology, 3, 11.IT.3.1. https://doi.org/10.2466/11.IT.3.1",
  "Mahalanobis, P.C. (1936). On the generalized distance in statistics. Proceedings of the National Institute of Sciences of India, 2, 49–55.",
  "Mann, H.B., and Whitney, D.R. (1947). On a test of whether one of two random variables is stochastically larger than the other. Annals of Mathematical Statistics, 18, 50–60.",
  "Marino, P., Peres, D.J., Cancelliere, A., Greco, R., and Bogaard, T.A. (2020). Soil moisture information can improve shallow landslide forecasting using the hydrometeorological threshold approach. Landslides, 17, 2041–2054.",
  "METER Group (2018). TEROS 10 manual. https://www.misure.net/sites/default/files/pdf/20788_TEROS10_Manual_Web.pdf",
  "METER Group (2026). TEROS Borehole Installation Tool, product page and installation guidance. https://metergroup.com/products/teros-borehole-installation-tool/",
  "METER Group (2026a). TEROS 10, official product page.",
  "METER Group (2026b). TEROS 21, official product page.",
  "METER Group (2026c). The researcher's complete guide to soil moisture.",
  "METER Group (2026d). The researcher's complete guide to water potential.",
  "Mirus, B.B., Bogaard, T., Greco, R., and Stähli, M. (2025). Invited perspectives: Integrating hydrologic information into the next generation of landslide early warning systems. Natural Hazards and Earth System Sciences, 25, 169–182.",
  "Oguz, E.A., Depina, I., Myhre, B., Devoli, G., Rustad, H., and Thakur, V. (2022). IoT-based hydrological monitoring of water-induced landslides: a case study in central Norway. Bulletin of Engineering Geology and the Environment, 81, 217. https://doi.org/10.1007/s10064-022-02721-z",
  "Oorthuis, R., Hürlimann, M., Vaunat, J., et al. (2023). Monitoring the role of soil hydrologic conditions and rainfall for the triggering of torrential flows in the Rebaixader catchment (Central Pyrenees, Spain). Landslides, 20, 249–269.",
  "Patton, A.I., Luna, L.V., Roering, J.J., Jacobs, A., Korup, O., and Mirus, B.B. (2023). Landslide initiation thresholds in data-sparse regions: application to landslide early warning criteria in Sitka, Alaska, USA. Natural Hazards and Earth System Sciences, 23, 3261–3284. https://doi.org/10.5194/nhess-23-3261-2023",
  "Pecoraro, G., and Calvello, M. (2021). Integrating local pore water pressure monitoring in territorial early warning systems for weather-induced landslides. Landslides, 18, 1191–1207.",
  "Peranić, J., Čeh, N., and Arbanas, Ž. (2022). The use of soil moisture and pore-water pressure sensors for the interpretation of landslide behavior in small-scale physical models. Sensors, 22(19), 7337. https://doi.org/10.3390/s22197337",
  "Piciullo, L., Gariano, S.L., Melillo, M., Brunetti, M.T., Peruccacci, S., Guzzetti, F., and Calvello, M. (2017). Definition and performance of a threshold-based regional early warning model for rainfall-induced landslides. Landslides, 14, 995–1008. https://doi.org/10.1007/s10346-016-0750-2",
  "Piciullo, L., Calvello, M., and Cepeda, J.M. (2018). Territorial early warning systems for rainfall-induced landslides. Earth-Science Reviews, 179, 228–247. https://doi.org/10.1016/j.earscirev.2018.02.013",
  "Piciullo, L., Abraham, M.T., Drøsdal, I.N., and Paulsen, E.S. (2025). An operational IoT-based slope stability forecast using a digital twin. Environmental Modelling & Software, 183, 106228. https://doi.org/10.1016/j.envsoft.2024.106228",
  "Pirone, M., Vitiello, G., Pedone, G., Casini, F., Santo, A., and Urciuoli, G. (2025). The PROMISE Project: an integrated approach for mitigation of flowslide risk – preliminary results from the Salerno Test Site. E3S Web of Conferences, 642, 01009. https://doi.org/10.1051/e3sconf/202564201009",
  "Pota, M., Pecoraro, G., Rianna, G., Reder, A., Calvello, M., and Esposito, M. (2022). Machine learning for the definition of landslide alert models: a case study in Campania region, Italy. Discover Artificial Intelligence, 2, 15. https://doi.org/10.1007/s44163-022-00033-5",
  "Reder, A., and Rianna, G. (2021). Exploring ERA5 reanalysis potentialities for supporting landslide investigations: a test case from Campania Region (Southern Italy). Landslides, 18, 1909–1924. https://doi.org/10.1007/s10346-020-01610-4",
  "Regione Campania (2005). Decreto del Presidente della Giunta Regionale n. 299 del 30 giugno 2005. Il sistema di allertamento regionale per il rischio idrogeologico e idraulico ai fini di protezione civile.",
  "Restrepo-Posada, P.J., and Eagleson, P.S. (1982). Identification of independent rainstorms. Journal of Hydrology, 55, 303–319. https://doi.org/10.1016/0022-1694(82)90136-6",
  "Rianna, G., Reder, A., Mercogliano, P., and Pagano, L. (2017). Evaluation of variations in frequency of landslide events affecting pyroclastic covers in Campania Region under the effect of climate changes. Hydrology, 4(3), 34. https://doi.org/10.3390/hydrology4030034",
  "Rianna, G., Reder, A., and Pagano, L. (2023). From empirically to physically based early warning predictions of rainfall-induced landslides in silty volcanic soils: the Lattari Mountains case study. Bulletin of Engineering Geology and the Environment, 82, 223. https://doi.org/10.1007/s10064-023-03228-x",
  "Sattler, K., Elwood, D., Hendry, M.T., Huntley, D., Holmes, J., Wilkinson, P.B., Chambers, J., Donohue, S., Meldrum, P.I., Macciotta, R., and Bobrowsky, P.T. (2021). Quantifying the contribution of matric suction on changes in stability and displacement rate of a translational landslide in glaciolacustrine clay. Landslides, 18, 1675–1689. https://doi.org/10.1007/s10346-020-01611-3",
  "Scott, D.W. (1992). Multivariate Density Estimation: Theory, Practice, and Visualization. Wiley, New York.",
  "Tagarelli, V., and Cotecchia, F. (2022). Preliminary field data of selected deep-rooted vegetation effects on the slope-vegetation-atmosphere interaction: results from an in-situ test. Rivista Italiana di Geotecnica, 1/2022, 62–83.",
  "Urciuoli, G., Calvello, M., Comegna, L., Esposito, A., Foresta, V., Greco, R., Menichini, R., Pecoraro, G., Picarelli, L., Pirone, M., Ramondini, M., Rianna, G., Santo, A., Sequino, G., Stinca, A., and Tarullo, A.G. (2025). Influence of vegetation on the hydrogeological behaviour of a slope in pyroclastic soils. In: Proceedings of RootS25 – 3rd International Workshop on Soil-Vegetation-Atmosphere Interaction. https://doi.org/10.53243/RootS2025-24",
  "Wicki, A., Lehmann, P., Hauck, C., Seneviratne, S.I., Waldner, P., and Stähli, M. (2020). Assessing the potential of soil moisture measurements for regional landslide early warning. Landslides, 17, 1881–1896. https://doi.org/10.1007/s10346-020-01400-y",
  "Youden, W.J. (1950). Index for rating diagnostic tests. Cancer, 3, 32–35.",
  "Zhang, S., Pecoraro, G., Jiang, Q., et al. (2025). A probabilistic procedure to define multidimensional rainfall thresholds for territorial landslide warning models. Landslides, 22, 1773–1787. https://doi.org/10.1007/s10346-025-02461-7",
];
for (const r of REFS) C.push(new Paragraph({ children: runs(r, { size: 22 }), alignment: AlignmentType.LEFT,
  indent: { left: 360, hanging: 360 }, spacing: { after: 80 } }));

const doc = new Document({
  creator: "Analysis pipeline", title: "Quantitative discrimination of landslide-triggering events",
  styles: {
    default: {
      document: { run: { font: FONT, size: 24 } },
      heading1: { run: { font: FONT, size: 28, bold: true, color: "000000" }, paragraph: { spacing: { before: 360, after: 160 }, keepNext: true } },
      heading2: { run: { font: FONT, size: 26, bold: true, color: "000000" }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true } },
      heading3: { run: { font: FONT, size: 24, bold: true, italics: true, color: "000000" }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true } },
    },
  },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1418, bottom: 1418, left: 1418, right: 1418 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync(path.join(__dirname, "Manuscript_landslide_discrimination.docx"), b);
  console.log("written", figN, "figures,", tabN, "tables");
});
