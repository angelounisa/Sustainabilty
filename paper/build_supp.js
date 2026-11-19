// Builds paper/Supplementary_Material.docx  (node paper/build_supp.js)
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, AlignmentType, Footer, PageNumber, LevelFormat, PageBreak } = require("docx");
const S = require("./docx_style.js");
const { runs, P, H1, H2, H3, EQ, BUL, NOTE, figure, table, FONT } = S;
S.setFigDir(path.join(__dirname, "supplementary", "figures"));
S.setPrefix("S", "S");
const D = JSON.parse(fs.readFileSync(path.join(__dirname, "supplementary", "supp_tables.json"), "utf8"));
const G = ["Albori", "Cetara", "Cetara S.C.", "Dragonea", "Salerno G.C."];

const C = [];
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [new TextRun({ text: "Supplementary Material", font: FONT, size: 32, bold: true })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
  children: [new TextRun({ text: "Quantitative discrimination of landslide-triggering events: a multi-variable analysis of rainfall intensity and soil hydrological state", font: FONT, size: 26, italics: true })] }));
C.push(P(`This document complements the main text. It lists acronyms and symbols, the correspondence between the symbols used in the paper and the variable names used in the data tables and in the code repository, the data-processing choices and parameters, the definitions of all statistical metrics, and additional tables and figures. Tables and figures are numbered S1, S2, …; references to Sections, Equations, Tables and Figures without the prefix "S" refer to the main text.`));

// ------------------------------------------------------------------ S1 acronyms
C.push(H1("S1. Acronyms and abbreviations"));
C.push(...table("Acronyms and abbreviations used in the main text, in the tables and in the code repository.",
  ["Acronym", "Meaning"],
  [["A1, A2, C1", "Soil horizons of the local stratigraphy: topsoil (A1), brown silty-sand ash with pumice of the 79 AD eruption (A2), yellowish silty-sand ash predating 79 AD (C1)"],
   ["AUC", "Area under the receiver operating characteristic (ROC) curve; equal to P(X_{1} > X_{0})"],
   ["AUC*", "Direction-invariant AUC, max(AUC, 1 − AUC)"],
   ["Camp-3", "Alert zone 3 of the Campania regional warning system"],
   ["CET / CEST", "Central European Time (UTC+1) / Central European Summer Time (UTC+2)"],
   ["CF", "Centro Funzionale Multirischi di Protezione Civile della Regione Campania (data provider)"],
   ["CSI", "Critical success index, TP/(TP + FN + FP)"],
   ["CV", "Cross-validation (here leave-one-event-out)"],
   ["D_{M}", "Mahalanobis distance"],
   ["FAR", "False alarm ratio, FP/(TP + FP)"],
   ["FN, FP, TN, TP", "False negatives (missed landslides), false positives (false alarms), true negatives, true positives (detected landslides)"],
   ["FPR, TPR", "False positive rate and true positive rate of a threshold rule"],
   ["G.C.", "Genio Civile (rain gauge Salerno Genio Civile)"],
   ["IETD", "Inter-Event Time Definition"],
   ["IQR", "Interquartile range (25th–75th percentile)"],
   ["KDE", "Kernel density estimation"],
   ["L1–L4", "Identifiers of the four documented landslides (Table 6 of the main text)"],
   ["LEWS", "Landslide early warning system(s)"],
   ["LS / no LS", "Landslide-triggering / non-triggering rainfall event"],
   ["MWU", "Mann–Whitney U test"],
   ["NV", "Non-vegetated (open-area) instrumented vertical, logger z6-28531; sensors at 15, 30 and 60 cm"],
   ["POD", "Probability of detection, TP/(TP + FN) (= recall, TPR)"],
   ["POFD", "Probability of false detection, FP/(FP + TN) (= FPR)"],
   ["RB", "Rank-biserial correlation"],
   ["ROC", "Receiver operating characteristic"],
   ["S.C.", "Serbatoio comunale (rain gauge Cetara–Serbatoio comunale)"],
   ["SEL", "Indicator strategy in which the variable combination is selected within each cross-validation fold"],
   ["SS163", "State road 163 \"Amalfitana\""],
   ["TEROS 10 / TEROS 21", "METER Group sensors for volumetric water content / matric potential"],
   ["TSS", "True skill statistic (Hanssen–Kuipers discriminant), POD − POFD"],
   ["UTC+1", "Time reference of all data (Coordinated Universal Time + 1 h, no daylight saving)"],
   ["V", "Vegetated (forest-cover) instrumented vertical, logger z6-28525; sensors at 15, 35 and 60 cm"],
   ["VWC", "Volumetric water content (m^{3} m^{-3})"]],
  [1.6, 6.4], { leftCols: [1] }));

// ------------------------------------------------------------------ S2 notation
C.push(H1("S2. Symbols and variable names"));
C.push(P(`Table S2 links each symbol of the paper to the column name used in the result tables (outputs/tables) and in the code. Hydrological variables are named [site]_[index]_[depth], where [site] is NV or V and [depth] is the sensor depth in cm (15, 30 or 60 for NV; 15, 35 or 60 for V). For example, NV_VWC0_15 is the antecedent volumetric water content at 15 cm in the non-vegetated vertical, and V_dVWC_60 is the event increase of water content at 60 cm in the vegetated vertical. In figure labels and tables the same variables are written as "VWC_{0} NV 15", "ΔVWC V 60", etc. The event identifier combines a gauge code and a progressive number: ALB (Albori), CET (Cetara), CETS (Cetara S.C.), DRA (Dragonea) and SAL (Salerno G.C.), e.g. SAL-018.`));
C.push(...table("Symbols, variable names in the data tables and code, units and definitions.",
  ["Symbol", "Name in tables / code", "Unit", "Definition"],
  [["[i]Rainfall event[/i]", "", "", ""],
   ["t_{start}, t_{end}", "t_start, t_end", "date-time", "Start of the first and end of the last wet 10-min interval of the event (UTC+1)"],
   ["D", "D_h", "h", "Event duration, t_{end} − t_{start}"],
   ["E", "E_mm", "mm", "Cumulative event rainfall"],
   ["I_{max}", "Imax_mmh", "mm h^{-1}", "Maximum 60-min moving rainfall total within the event"],
   ["I_{mean}", "Imean_mmh", "mm h^{-1}", "Mean intensity, E/D"],
   ["P_{1h} … P_{24h}", "P1h_mm … P24h_mm", "mm", "Maximum moving total over 1, 3, 6, 12, 24 h within the event"],
   ["A_{3d} … A_{30d}", "A3d_mm … A30d_mm", "mm", "Rainfall in the 3, 7, 14, 30 days before t_{start}"],
   ["[i]Soil hydrological state (per site and depth)[/i]", "", "", ""],
   ["VWC_{0}", "[site]_VWC0_[z]", "m^{3} m^{-3}", "Mean VWC in the 60 min before t_{start}"],
   ["VWC_{peak}", "[site]_VWCpk_[z]", "m^{3} m^{-3}", "Maximum VWC in [t_{start}, t_{end} + 24 h]"],
   ["ΔVWC", "[site]_dVWC_[z]", "m^{3} m^{-3}", "VWC_{peak} − VWC_{0}"],
   ["t_{peak}", "[site]_tpk_[z]", "date-time", "Time of VWC_{peak}"],
   ["s_{0}", "[site]_s0_[z]", "kPa", "Mean matric suction in the 60 min before t_{start} (s = −ψ > 0)"],
   ["s_{min}", "[site]_smin_[z]", "kPa", "Minimum suction in [t_{start}, t_{end} + 24 h]"],
   ["Δs", "[site]_ds_[z]", "kPa", "s_{min} − s_{0} (negative = suction drop)"],
   ["Z", "[site]_z_[z]", "–", "Standardised ΔVWC of relevant events (Section 3.2.1)"],
   ["class", "[site]_class_[z]", "–", "irrelevant / relevant / extreme"],
   ["[i]Infiltration[/i]", "", "", ""],
   ["Δt_{peak}", "dt_peak_h", "h", "Lag between VWC peaks at two depths (0–15 cm: from the centre of the hour of maximum intensity)"],
   ["v", "v_peak_cmh", "cm h^{-1}", "Peak-lag velocity Δz/Δt_{peak}"],
   ["v_{onset}", "v_onset_cmh", "cm h^{-1}", "Wetting-front velocity from the first exceedance of VWC_{0} + 0.1·ΔVWC"],
   ["[i]Landslides and statistics[/i]", "", "", ""],
   ["Y", "Y", "0/1", "1 if the event is associated with at least one landslide"],
   ["–", "landslide", "–", "Identifiers of the associated landslides (e.g. \"L3,L4\")"],
   ["π̃", "median_pct", "%", "Median percentile of landslide events in the pooled distribution"],
   ["τ*", "threshold", "variable unit", "Youden-optimal threshold; direction ≥ or ≤ in column direction"],
   ["D_{M}", "D_M", "–", "Mahalanobis distance from non-triggering events (Eq. 6)"],
   ["I", "score", "0–100", "Multi-variable indicator: mean oriented percentile (Eq. 7)"],
   ["τ", "tau", "0–100", "Alarm threshold of the indicator (Youden, recomputed in each fold)"]],
  [1.3, 2.0, 1.1, 4.0], { size: 19, leftCols: [1, 3] }));

// ------------------------------------------------------------------ S3 data processing
C.push(H1("S3. Monitoring data and processing"));
C.push(H2("S3.1 Rain gauges"));
C.push(P(`Rainfall data of the five gauges (Albori, Cetara, Cetara S.C., Dragonea, Salerno G.C.) were provided by the Centro Funzionale of the Campania Region at 10-min resolution from 1 January 2025 00:10 to 30 September 2026 23:50 (UTC+1), i.e. 91,871 records per gauge. The value at time t is the depth fallen in the interval (t − 10 min, t]. In the original files the time column is computed by a spreadsheet formula and carries a floating-point drift below 1 s; timestamps were rounded to the 10-min grid after checking that the correction never exceeded 5 s. No missing values are present in the files; the Albori file lists three gaps of the original record (Table S3), which are stored as 0 mm and were kept as such. None of these gaps falls within a landslide-triggering event.`));
C.push(...table("Gaps of the rainfall record reported in the original files (Albori only).",
  ["Gauge", "First missing interval", "Last missing interval", "Number of 10-min intervals"], D.rain_gaps, [1.5, 2.2, 2.2, 1.8]));
C.push(H2("S3.2 Soil sensors"));
C.push(P(`VWC (TEROS 10) and matric potential (TEROS 21) were recorded every 5 min from 31 January 2025. The TEROS 21 output is reported as positive matric suction s (kPa). Values were checked against physical limits (0 ≤ VWC ≤ 0.6 m^{3} m^{-3}; 0 ≤ s ≤ 10^{5} kPa) and all passed. The minimum reported suction is 0.1 kPa: readings at this level indicate conditions close to saturation, and differences between very low readings should be interpreted qualitatively, according to the manufacturer's specifications on accuracy in the wet range. The logger clock moved forward by 1 h on 29 March 2026 at 06:10 (a 65-min step with no data loss), which was interpreted as a switch to daylight saving time; all subsequent timestamps were shifted back by 1 h to UTC+1. The series were placed on a regular 5-min grid, on which missing samples appear explicitly. Apart from two isolated missing samples, the only gap is listed in Table S4. No gap filling or smoothing was applied; an event index was set to missing when the antecedent window or more than 1% of the response window was missing.`));
C.push(...table("Gaps longer than one sample in the soil-sensor record.",
  ["Vertical", "Variable", "Start (UTC+1)", "End (UTC+1)", "Duration (h)"], D.soil_gaps, [1, 1.3, 2, 2, 1.2]));
C.push(H2("S3.3 Processing parameters"));
C.push(...table("Parameters of the analysis (file config.yaml in the repository).",
  ["Parameter", "Value", "Use"],
  [["Inter-event time definition T_{s}", "24 h", "Separation of independent rainfall events"],
   ["Minimum event rainfall", "10 mm", "Events with E < 10 mm discarded"],
   ["I_{max} window", "60 min (moving)", "Maximum intensity"],
   ["Within-event windows", "1, 3, 6, 12, 24 h", "P_{1h} … P_{24h}"],
   ["Antecedent windows", "3, 7, 14, 30 d", "A_{3d} … A_{30d}"],
   ["Antecedent soil window", "60 min before t_{start}", "VWC_{0}, s_{0}"],
   ["Response window", "[t_{start}, t_{end} + 24 h]", "VWC_{peak}, s_{min}"],
   ["Relevance criterion", "ΔVWC ≥ 0.05·VWC_{0}", "Event classification"],
   ["Extreme criterion", "Z ≥ 1", "Event classification"],
   ["Wetting-front arrival", "VWC ≥ VWC_{0} + 0.1·ΔVWC", "v_{onset}"],
   ["Reference gauge (Chapter 3)", "Salerno G.C.", "Classification, infiltration"],
   ["Landslide–event matching", "time ± uncertainty overlaps [t_{start}, t_{end} + 24 h]", "Definition of Y"],
   ["Multiple-testing correction", "Holm, within each gauge", "p_adj"],
   ["Mahalanobis variables / quantile", "E, I_{max}, VWC_{0} NV 60; χ^{2}_{3} 0.95", "Anomaly index"],
   ["KDE bandwidth", "Scott's rule", "Figure 9"],
   ["Indicator threshold", "Youden index, ties to lower τ", "Alarm rule"],
   ["Validation", "Leave-one-event-out", "Indicator performance"]],
  [2.6, 2.6, 2.4], { leftCols: [1, 2] }));

// ------------------------------------------------------------------ S4 landslides
C.push(H1("S4. Landslide inventory and association with rainfall events"));
C.push(P(`Landslide times are reported in Italian local time; all four dates fall in CET (UTC+1), including 26 October 2025, after the end of daylight saving time at 03:00. Because the exact time is uncertain, a time interval was associated with each landslide: ± 12 h for L1 (time not reported, whole day), ± 3 h for L2 (afternoon, centred at 15:00), ± 0.5 h for L3 (about 05:40) and for L4 (13:45–14:30, centred at 14:08). A landslide was assigned to the rainfall event whose window [t_{start}, t_{end} + 24 h] overlaps this interval. Table S6 lists the resulting associations. All landslides were associated with events of E ≥ 10 mm at every gauge.`));
C.push(...table("Rainfall events associated with each landslide at each gauge.",
  ["Gauge", "Landslide", "Event", "Start", "End", "D (h)", "E (mm)", "I_{max} (mm h^{-1})"], D.ls_match,
  [1.3, 0.9, 1.0, 1.7, 1.7, .8, .8, 1.0], { size: 18 }));

// ------------------------------------------------------------------ S5 metrics
C.push(H1("S5. Statistical metrics"));
C.push(P(`For a feature X and the binary response Y (1 = landslide-triggering event), let n_{1} and n_{0} be the numbers of triggering and non-triggering events of a gauge.`));
C.push(BUL(`[b]AUC[/b] = U/(n_{1} n_{0}) = P(X_{1} > X_{0}) + 0.5·P(X_{1} = X_{0}), where U is the Mann–Whitney statistic of the triggering sample. AUC = 0.5 means no separation, 1 (or 0) complete separation. [b]AUC*[/b] = max(AUC, 1 − AUC) removes the dependence on the direction of the relationship.`));
C.push(BUL(`[b]Mann–Whitney U test[/b]: non-parametric two-sample test of the null hypothesis that the two distributions are equal; two-sided p-values (exact for small samples). With n_{1} = 3–4 the smallest attainable p-values are of the order of 10^{-3}. [b]Holm correction[/b]: step-down adjustment of the p-values for the number of features tested at each gauge (46).`));
C.push(BUL(`[b]Rank-biserial correlation[/b] RB = 2·AUC − 1, in [−1, 1]: positive if triggering events have larger values. Conventional magnitudes: |RB| ≈ 0.1 small, 0.3 medium, 0.5 large.`));
C.push(BUL(`[b]Median percentile[/b] π̃: median over the triggering events of their empirical percentile in the pooled distribution of the gauge; for variables with lower values in triggering events 100 − π̃ is reported, so that π̃ close to 100 always means "extreme in the critical direction".`));
C.push(BUL(`[b]Youden threshold[/b] τ* maximising J = TPR − FPR over the observed values; recall = TPR(τ*). The direction of the rule (≥ or ≤) follows the observed AUC; the column physics_consistent flags whether it agrees with the expected physical direction (higher rainfall, water content and ΔVWC; lower suction).`));
C.push(BUL(`[b]Mahalanobis distance[/b] D_{M} (Eq. 6), with mean vector and covariance matrix estimated from non-triggering events; under multivariate normality D_{M}^{2} follows a χ^{2} distribution with k degrees of freedom, giving the 95% threshold (χ^{2}_{3,0.95})^{1/2} = 2.80. D_{M} is non-directional.`));
C.push(BUL(`[b]Indicator[/b] I (Eq. 7) and alarm rule I ≥ τ. Contingency-table scores: POD = TP/(TP + FN), POFD = FP/(FP + TN), FAR = FP/(TP + FP), TSS = POD − POFD, CSI = TP/(TP + FN + FP). TSS = 1 for a perfect rule and 0 for a rule with no skill.`));
C.push(BUL(`[b]Leave-one-event-out cross-validation[/b]: for each event, the reference distributions of non-triggering events and the threshold are computed without that event, which is then classified. In the SEL strategies the combination of variables is also chosen without the event (highest training AUC among the candidates of the family).`));
C.push(P(`In all tables the 5 gauges are analysed separately. Pooled scores sum the contingency tables of the five gauges; since the gauges share the same landslides and soil data, they are not independent replicates.`));

// ------------------------------------------------------------------ S6 additional results
C.push(H1("S6. Additional results"));
C.push(H2("S6.1 Rainfall events"));
C.push(...figure("FigS1_event_timeline.png", `Daily rainfall at the five gauges (bars), rainfall events with E ≥ 10 mm (grey) and landslide-triggering events (red); dashed lines: landslides L1–L4.`));
C.push(...figure("FigS2_ED_classes_all_depths.png", `Rainfall events at Salerno G.C. in the D–E space, coloured by the class of the soil-moisture response at each depth of the non-vegetated (a–c) and vegetated (d–f) verticals. Stars: landslide events.`));
C.push(H2("S6.2 Infiltration and vegetation"));
C.push(...table("Infiltration velocity by vertical and layer, Salerno G.C. events. n: events relevant or extreme at both depths; n > 0: events with positive peak lag.",
  ["Vertical", "Layer (cm)", "n", "n > 0", "Median v (cm h^{-1})", "Q25", "Q75", "Median Δt_{peak} (h)", "n onset", "Median v_{onset}"], D.vel,
  [.8, 1, .5, .6, 1.2, .7, .7, 1.2, .7, 1.1], { size: 18 }));
C.push(...table("Paired comparison of event indices between the vegetated (V) and non-vegetated (NV) verticals, Salerno G.C. events (Wilcoxon signed-rank test).",
  ["Index", "Depth V / NV (cm)", "n events", "Median V", "Median NV", "Fraction V < NV", "p"], D.paired,
  [1, 1.4, .9, 1.1, 1.1, 1.2, 1.0]));
C.push(H2("S6.3 Discriminant metrics"));
C.push(...table("AUC* of all features at each gauge (* unadjusted Mann–Whitney p < 0.05). Direction: direction of the Youden rule at Salerno G.C.; physics: agreement with the expected physical direction.",
  ["Feature", ...G, "Dir.", "Physics"], D.auc_matrix, [2.2, .9, .9, 1, 1, 1, .6, .8], { size: 17 }));
C.push(...table("Complete discriminant metrics at Salerno G.C. (n_{1} = 3, n_{0} = 36). p_adj: Holm-adjusted p-value.",
  ["Feature", "Mean LS", "Mean no LS", "AUC*", "RB", "p", "p_adj", "π̃", "τ*", "Recall", "FPR"], D.ref_metrics,
  [2, 1, 1, .7, .7, .8, .8, .5, 1.2, .7, .6], { size: 16 }));
C.push(...table("AUC* of rainfall accumulated over different windows (cf. Patton et al., 2023).",
  ["Window", ...G], D.windows, [2, 1, 1, 1, 1, 1]));
C.push(...figure("FigS3_ROC_curves.png", `ROC curves of selected single features at each gauge. Steps reflect the small number of landslide events (3–4 per gauge).`));
C.push(...figure("FigS4_windows_and_mahalanobis.png", `(a) AUC* of the maximum rainfall over increasing windows within the event and of antecedent rainfall. (b) Mahalanobis distance of each event from the non-triggering distribution (variables E, I_{max}, VWC_{0} NV 60 cm); dashed line: χ^{2}_{3} 95% threshold.`));
C.push(...table("Mahalanobis anomaly index (E, I_{max}, VWC_{0} NV 60 cm) at each gauge.",
  ["Gauge", "n", "n LS", "Median D_{M} LS", "Median D_{M} no LS", "AUC", "p (one-sided)", "LS > threshold", "no LS > threshold"], D.mahal,
  [1.3, .5, .5, 1, 1, .6, .9, 1, 1]));
C.push(H2("S6.4 Multi-variable indicator"));
C.push(...figure("FigS5_indicator_construction.png", `Construction of the indicator for the combination E + VWC_{0} NV 15 cm at Salerno G.C. (all events, for illustration). (a, b) Empirical percentile of each variable among non-triggering events (landslide L1 highlighted). (c) Indicator value I of all events. (d) TPR, FPR and Youden index J as a function of the threshold. In the cross-validation, steps (a)–(d) are repeated without the event being classified.`));
C.push(...table("Cross-validated performance of selected indicators at each gauge.",
  ["Indicator", "Gauge", "n", "n LS", "TP", "FN", "FP", "TN", "TSS", "AUC (CV)"], D.ind_gauge,
  [2.8, 1.2, .5, .5, .45, .45, .45, .5, .6, .8], { size: 16, leftCols: [1] }));
C.push(...table("Cross-validated performance of all tested indicators, five gauges pooled, sorted by TSS. TSS min: lowest TSS among gauges.",
  ["Indicator", "Type", "TP", "FN", "FP", "TN", "POD", "POFD", "FAR", "TSS", "TSS min"], D.ind_all,
  [3.4, 1.3, .4, .4, .4, .5, .55, .55, .55, .55, .6], { size: 15, leftCols: [1] }));
C.push(...figure("FigS6_all_three_variable_indicators.png", `(a) Pooled cross-validated TSS of all 455 three-variable indicators grouped by variable type (R: rainfall, W: antecedent VWC, S: antecedent suction); reference lines: E alone and E + VWC_{0} NV 15. (b) The 15 best combinations with the lowest TSS among gauges. These are selected on the same data and are therefore optimistic.`));
C.push(...table("The 20 best three-variable indicators (pooled, cross-validated).",
  ["Variables", "Type", "TP", "FN", "FP", "POD", "POFD", "TSS", "TSS min"], D.tri,
  [3.6, 1.6, .4, .4, .4, .55, .55, .55, .6], { size: 15, leftCols: [1] }));

// ------------------------------------------------------------------ S7 reproducibility
C.push(H1("S7. Data, code and reproducibility"));
C.push(P(`All processing steps are scripted and parameterised in a single configuration file; raw data are never modified. The repository (https://github.com/angelounisa/Sustainabilty) contains:`));
C.push(BUL(`config.yaml — all parameters of Table S5 and the definition of the tested indicators;`));
C.push(BUL(`data/raw — original rain-gauge and METER files; data/landslides.csv — landslide inventory with time uncertainty; data/processed — cleaned series in UTC+1 and event tables;`));
C.push(BUL(`run_analysis.py — data quality control, event identification, hydrological indices, classification, infiltration velocity, discriminant metrics, Mahalanobis and multivariate combinations (src/io_data.py, src/events.py, src/stats_ls.py, src/multivar.py);`));
C.push(BUL(`run_indicator.py — multi-variable indicator with leave-one-event-out cross-validation (src/indicator.py);`));
C.push(BUL(`make_paper_figures.py and make_supp_figures.py — figures of the main text and of this document; make_figures.py and make_dashboard.py — exploratory figures and interactive dashboard (https://angelounisa.github.io/Sustainabilty/);`));
C.push(BUL(`outputs/tables — all result tables (T00–T23), including those summarised here.`));
C.push(P(`Software: Python 3.13.18 with pandas 3.0.5, NumPy 2.5.3, SciPy 1.18.1, statsmodels 0.15.0 and Matplotlib 3.11.2. All computations are deterministic.`));

const doc = new Document({
  creator: "Analysis pipeline", title: "Supplementary Material",
  styles: { default: {
    document: { run: { font: FONT, size: 24 } },
    heading1: { run: { font: FONT, size: 28, bold: true, color: "000000" }, paragraph: { spacing: { before: 360, after: 160 }, keepNext: true } },
    heading2: { run: { font: FONT, size: 26, bold: true, color: "000000" }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true } },
    heading3: { run: { font: FONT, size: 24, bold: true, italics: true, color: "000000" }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true } },
  } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1418, bottom: 1418, left: 1418, right: 1418 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: ["S", PageNumber.CURRENT], font: FONT, size: 20 })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(path.join(__dirname, "Supplementary_Material.docx"), b); console.log("written"); });
