# Sustainabilty — Landslide-triggering vs non-triggering rainfall events: rainfall, soil moisture and suction (Salerno test site, Jan 2025 – Sep 2026)

Analisi a supporto del manoscritto *"Quantitative discrimination of landslide-triggering events: a multi-variable analysis of rainfall intensity and soil hydrological state"*.
La struttura segue la **versione alternativa dell'indice** (Cap. 2 *Study area and monitoring setup* + Cap. 3 *Event characterization and infiltration dynamics* + Cap. 4 *Comparative analysis*), cioè quella su cui sono scritte le bozze dei capitoli 2 e 3. Le analisi del Cap. 4 riprendono le formule della bozza del Cap. 3 (§3.3: AUC*, Mann–Whitney, percentile mediano, Youden, recall, KDE, profilo verticale, Mahalanobis); il confronto tra finestre di accumulo è ispirato a Patton et al. (2023, NHESS).

```
config.yaml            tutti i parametri (IETD, soglie, finestre, ...)
data/raw/              dati originali (5 pluviometri CF Campania, METER V e NV) – non modificati
data/landslides.csv    inventario frane (date fornite dagli autori)
data/processed/        serie pulite in UTC+1, eventi, indici (pickle/csv.gz)
src/                   io_data.py (QC), events.py (IETD + indici), stats_ls.py (statistiche Cap. 4)
run_analysis.py        pipeline -> outputs/tables/*.csv
make_figures.py        figure -> outputs/figures/*.png
run_indicator.py       indicatore frana/no frana con CV -> T19-T21, Fig16-17, docs/indicator.json
make_dashboard.py      esporta dati e figure in docs/ (sito GitHub Pages)
docs/                  dashboard (index.html + data.json + figures/)
```
Riproduzione: `pip install -r requirements.txt && python run_analysis.py && python make_figures.py && python make_dashboard.py`.

**Dashboard interattiva:** https://angelounisa.github.io/Sustainabilty/ (GitHub Pages, cartella `docs/`, generata da `make_dashboard.py`).

---

## Scelte metodologiche e assunzioni (da verificare dagli autori)

| Aspetto | Scelta | Dove |
|---|---|---|
| Orario | Pluviometri in UTC+1 (come da file). Il logger METER salta di +1 h il 29/03/2026 06:10 senza perdita di dati → interpretato come passaggio all'ora legale; i dati successivi sono riportati a UTC+1. Le date delle frane (ora italiana) cadono tutte in CET = UTC+1. | `config.yaml: soil.dst_switch_local` |
| Tempo pluviometri | La colonna "Time UTC+1" è una formula Excel con deriva < 1 s; arrotondata alla griglia di 10 min. I buchi di Albori (foglio "Buchi", 14 intervalli) sono a 0 mm nei file. | `src/io_data.py` |
| Buchi suolo | Unico buco rilevante: **V VWC 15 cm dal 31/01/2026 al 04/03/2026** (764 h) – include gli eventi L3/L4. Il suolo parte il 31/01/2025: gli eventi di gennaio 2025 non hanno indici idrologici. Nessun gap-filling: un indice è NaN se manca anche un solo dato. | `T00_soil_gaps.csv` |
| Eventi | IETD, T_s = 24 h; E ≥ 10 mm. D = t_end − t_start; I_max = massima pioggia su 60 min mobili (mm/h). In più (Patton) massimi su 1/3/6/12/24 h e pioggia antecedente 3/7/14/30 d. | `src/events.py` |
| Indici idrologici | VWC0, s0 = media dei 60 min prima di t_start; VWCpeak, s_min nella finestra [t_start, t_end + 24 h] (per costruzione IETD non piove nelle 24 h dopo t_end, quindi si catturano i picchi ritardati in profondità senza mescolare eventi). ΔVWC = VWCpeak − VWC0; Δs = s_min − s0 (kPa, suzione positiva). | `config.yaml: hydro` |
| Clustering | Come da bozza: irrelevant se ΔVWC < 0.05·VWC0; z-score di ΔVWC sugli eventi rilevanti (per pluviometro, sito e profondità); extreme se z ≥ 1. | `run_analysis.py §3` |
| Velocità infiltrazione | v = Δz/Δt tra i picchi di VWC a profondità successive (bozza §3.4), solo eventi non irrilevanti a entrambe le profondità e Δt > 0. Metrica secondaria: arrivo del fronte (primo istante con VWC ≥ VWC0 + 10% ΔVWC). | `config.yaml: infiltration` |
| Associazione frana–evento | Frana assegnata all'evento la cui finestra [t_start, t_end + 24 h] interseca [t_frana ± incertezza] (L1 ±12 h perché ora ignota; L2 ±3 h "pomeriggio"; L3, L4 ±0.5 h). | `data/landslides.csv` |
| Pluviometro di riferimento Cap. 3 | **Salerno Genio Civile** (il più vicino alle verticali). Le statistiche del Cap. 4 sono calcolate per **tutti e cinque** i pluviometri separatamente. | `config.yaml: hydro.reference_gauge` |
| Direzione AUC | AUC* = max(AUC, 1−AUC). Percentile e soglia di Youden usano la direzione osservata; la colonna `physics_consistent` segnala se coincide con quella attesa (suzione: valori bassi = instabile). | `src/stats_ls.py` |
| Test multipli | p-value Mann–Whitney bilaterali; correzione di Holm sulle 46 variabili di ciascun pluviometro (`p_adj`). | `T11` |
| Mahalanobis | Variabili E, I_max, VWC0 NV 60 cm (come nella figura della bozza), media e covarianza dagli eventi senza frana, soglia √χ²₃(0.95) = 2.80. | `config.yaml: stats` |

**Attenzione sulla numerosità.** Le frane sono 4, ma corrispondono a 4 eventi distinti solo ad Albori, Cetara e Cetara S.C.; a Dragonea e Salerno G.C. L3 (06/02) e L4 (12/02) cadono nello stesso evento IETD (non ci sono 24 h asciutte tra i due). Con n = 3–4 eventi positivi su ~40 dopo Holm restano significative solo E e P_3h a Cetara S.C.: AUC e Rank-Biserial vanno letti come misure descrittive dell'effetto, non come test confermativi. I 5 pluviometri non sono campioni indipendenti (stesse frane e stessi dati di suolo).

---

## Risultati principali

### Cap. 2 – Dati (Fig02, T01)
Pioggia gen 2025 – set 2026: 1694 mm (Salerno G.C.) – 2247 mm (Dragonea); 2025: 987–1332 mm. Completezza dei dati di suolo ~100% eccetto V VWC 15 cm (94.8%). Il sito NV è sistematicamente più umido del V (VWC 60 cm mediana 0.213 vs 0.083 m³/m³). Entrambi mostrano un ciclo stagionale netto: essiccamento estivo con suzioni > 10³ kPa, ri-bagnamento da settembre–ottobre 2025, stato quasi saturo (s < 10 kPa) da novembre 2025 a febbraio 2026, periodo in cui cadono tutte e quattro le frane. Nel sito V il ri-bagnamento a 60 cm avviene solo con l'evento del 25–26/10/2025 (L1), circa 5–6 settimane dopo l'NV (metà settembre 2025).

### Cap. 3.1 – Eventi (Fig02b, Fig03, T02–T04)
| Pluviometro | spell IETD | eventi E ≥ 10 mm | D mediana (h) | E mediana (mm) | E max (mm) | I_max max (mm/h) | eventi con frana |
|---|---|---|---|---|---|---|---|
| Albori | 100 | 46 | 34.3 | 31.5 | 174.3 | 38.5 | 4 |
| Cetara | 93 | 44 | 29.8 | 28.2 | 148.2 | 42.6 | 4 |
| Cetara S.C. | 123 | 46 | 35.4 | 30.2 | 226.7 | 48.1 | 4 |
| Dragonea | 113 | 46 | 33.2 | 30.7 | 246.1 | 46.0 | 3 |
| Salerno G.C. | 96 | 44 | 31.4 | 24.2 | 190.6 | 38.2 | 3 |

### Cap. 3.2 – Clustering e infiltrazione (Fig04, Fig05, T05–T08; Salerno G.C.)
- La risposta si attenua con la profondità: a 60 cm il 72–77% degli eventi con dati è *irrelevant* (NV 28/39, V 30/39), a 15 cm NV nessuno. Gli eventi *extreme* hanno E mediana 48–82 mm e I_max mediana 13–35 mm/h.
- Alcuni eventi "extreme" a 35/60 cm nel sito V (s0 ≈ 1500–1800 kPa) sono il **primo bagnamento autunnale** di un profilo secco: grande ΔVWC partendo da VWC0 bassissimo (es. L1, V 60 cm: 0.026 → 0.121).
- **Effetto vegetazione** (confronto appaiato sugli stessi eventi): ΔVWC nel sito V è minore che in NV nel 97% degli eventi a 15 cm (mediana 0.009 vs 0.080), 90% a 30/35 cm e 69% a 60 cm (Wilcoxon p ≤ 0.001). Anche la caduta di suzione Δs è minore in V a 15 e 30/35 cm (p = 0.010 e 0.004).
- **Infiltrazione 0–15 cm (superficie → primo sensore)**: Δz = 15 cm; Δt = picco VWC a 15 cm − centro dei 60 min di massima intensità di pioggia (picco-picco), oppure arrivo del fronte a 15 cm − inizio pioggia (onset). Mediana picco-picco NV 4.9 cm/h (Δt 1.7 h) vs V 0.9 cm/h (Δt 14.8 h), Mann–Whitney p = 0.031, RB = −0.35; onset NV 3.3 vs V 2.3 cm/h (p = 0.15). Nel sito vegetato il picco a 15 cm arriva molto dopo il picco di pioggia (intercettazione/lettiera, risposta smorzata).
- **Velocità di infiltrazione (picco-picco)**: NV 15→30 cm 4.2 cm/h, 30→60 cm 9.5 cm/h, 15→60 cm 10.6 cm/h; V 15→35 3.0, 35→60 1.8, 15→60 2.4 cm/h. La differenza V–NV è significativa nello strato profondo (35/30→60 cm: RB = −0.80, p = 0.003; 15→60: RB = −0.71, p = 0.014) e non nello strato superficiale (p = 0.53). Con il criterio del fronte di bagnamento le differenze vanno nella stessa direzione ma non sono significative (n = 7–25 per gruppo).
- Nota: nel sito V il sensore a 35 cm risponde spesso prima e più del 15 cm (vedi Fig03, L1) – possibile flusso preferenziale lungo radici o contatto sensore; da verificare in campo.

### Cap. 4 – Frane vs non frane (Fig06–Fig12, T09–T15)
- **Le variabili di pioggia dell'evento sono le più discriminanti**: E (AUC* 0.88–1.00), P6h–P24h (0.88–0.98), D (0.82–0.95). Seguono ΔVWC V 60 cm (0.90–0.95) e la suzione antecedente a 15 cm nel sito NV (0.78–0.90, direzione fisicamente coerente: suzione più bassa prima delle frane, soglia di Youden ≈ 14.7 kPa, 24 kPa a Cetara S.C.).
- **Δs (caduta di suzione) ha direzione opposta a quella attesa** (`physics_consistent = False`, NV 15 cm AUC* 0.77–0.90): durante gli eventi con frana la suzione cala *meno*, perché parte già bassa (suolo vicino alla saturazione). È un effetto dello stato antecedente, non un indicatore di stabilità.
- **VWC antecedente a 60 cm**: AUC* 0.65–0.80 (NV) e 0.61–0.73 (V), con percentile mediano 65–90 – le frane avvengono a profilo profondo più umido della mediana, ma il segnale da solo è debole perché tutto il periodo invernale ha VWC elevati. L1 (26/10/2025) è l'eccezione: avviene con il profilo V ancora secco (VWC0 60 cm = 0.026) e la sua firma è soprattutto pluviometrica (I_max 35–46 mm/h, tranne Dragonea con 11.5 mm/h).
- **Profilo verticale (Fig10)**: nel sito NV i profili pre-frana di L2–L4 sono più umidi della mediana degli eventi normali a 15 e 30 cm e al limite superiore dell'IQR a 60 cm; L1 è leggermente sotto la mediana a 60 cm. Nel sito V, L1 ha il profilo profondo secco, L3/L4 umido (manca il 15 cm per il buco di febbraio 2026).
- **Mahalanobis (E, I_max, VWC0 NV 60 cm)**: D_M mediana frane 3.0–6.6 vs 1.3 eventi normali; AUC 0.89–1.00 tranne Dragonea (0.64, dove L1 ha solo 40 mm). 2–4 frane su 3–4 superano la soglia χ²₃ 95% (2.80), contro 2–4 falsi positivi su ~37 eventi.
- **Finestre di accumulo (Patton et al., 2023)**: la discriminazione cresce da 1 h (0.79–0.92) a 6 h (0.92–0.97) e resta alta fino all'evento intero; la pioggia antecedente a 7 d è competitiva (0.75–0.96), quella a 3 d e 30 d meno.
- **Multivariata – combinazioni di variabili (Fig13–15, T16–T18; tab *Multivariata* della dashboard)**. Candidati: 8 variabili di pioggia (E, D, I_max, P3h, P6h, P24h, A7d, A30d) × 12 di contenuto d'acqua (VWC0 antecedente e ΔVWC dell'evento, 6 sensori). Famiglie: 1 pioggia + 1 acqua (96), 2 pioggia + 1 acqua (336), 1 pioggia + 2 acqua (528), per ciascun pluviometro. Due punteggi senza parametri stimati sulle frane: **D_M** (Mahalanobis dagli eventi senza frana, leave-one-out, soglia χ²_k 95%; non direzionale) e **PS** (media dei percentili orientati nel verso fisicamente critico). Risultati (AUC medio sui 5 pluviometri, solo combinazioni con dati per tutte le frane):
  | famiglia | migliore con VWC0 antecedente (PS) | migliore con VWC0 (D_M) | migliore con ΔVWC (PS) |
  |---|---|---|---|
  | 1 variabile | E 0.941 (min 0.87) | A7d 0.905 | V ΔVWC 60 0.908 |
  | pioggia + acqua | I_max/P3h/P6h/E + NV VWC0 15 cm 0.954–0.957 (min ≥ 0.93) | E + V VWC0 60 cm 0.940 | A7d + V ΔVWC 60 0.972 |
  | 2 pioggia + acqua | D + P6h + NV VWC0 30 cm 0.975 (min 0.96) | E + A7d + V VWC0 60 cm 0.990 (18/18 frane sopra soglia, FPR 12%) | D + A7d + V ΔVWC 60 0.988 |
  | pioggia + 2 acqua | I_max + NV VWC0 15 + NV VWC0 30 0.943 | E + NV VWC0 15 + V VWC0 60 0.944 | A7d + V ΔVWC 35 + V ΔVWC 60 0.974 |

  Lettura: aggiungere il contenuto d'acqua antecedente superficiale del sito NV (15–30 cm) a una variabile di pioggia aumenta poco la media ma soprattutto il caso peggiore (min AUC da 0.87 a 0.93–0.96), cioè rende la discriminazione più stabile tra pluviometri. Con D_M emerge V VWC0 60 cm, ma in parte perché L1 avviene con profilo profondo **secco** (anomalia "al contrario"): con il punteggio direzionale questa combinazione scende (PS 0.84–0.90). Le combinazioni a 3 variabili arrivano ad AUC 0.97–0.99, ma sono scelte tra ~960 candidati con 3–4 frane per pluviometro: il guadagno rispetto alle coppie è nell'ordine dell'incertezza e va confermato su nuovi eventi. Le combinazioni con V 15 cm sono escluse dal confronto (manca il dato per L3/L4).
- **Indicatore frana / no frana per pluviometro (`run_indicator.py`, T19–T21, Fig16–17, tab *Indicatore*)**. I = media dei percentili delle variabili rispetto agli eventi senza frana (verso critico; suzione con segno invertito), allarme se I ≥ soglia di Youden; validazione leave-one-event-out (riferimento e soglia ricalcolati senza l'evento testato). Risultati aggregati sui 5 pluviometri (18 eventi con frana, 186 senza):
  | indicatore | POD | POFD | FAR | TSS | AUC CV |
  |---|---|---|---|---|---|
  | E (solo pioggia) | 0.78 | 0.16 | 0.67 | 0.62 | 0.94 |
  | E + A7d (solo pioggia) | 0.78 | 0.08 | 0.50 | 0.70 | 0.98 |
  | **E + NV VWC0 15 cm** | **0.83** | **0.09** | 0.53 | **0.74** | 0.96 |
  | D + P6h + NV VWC0 30 cm | 0.72 | 0.05 | 0.41 | 0.67 | 0.98 |
  | D + A7d + V ΔVWC 60 (risposta durante l'evento) | 0.78 | 0.03 | 0.30 | 0.75 | 0.99 |
  | selezione automatica nel fold, pioggia + VWC0 | 0.61 | 0.09 | 0.59 | 0.53 | 0.90 |

  Aggiungere il VWC antecedente superficiale (NV 15 cm) alla cumulata dimezza i falsi allarmi (29 → 17) senza perdere frane. La selezione automatica della combinazione dentro ogni fold rende meno delle combinazioni fisse: con 3–4 frane per pluviometro scegliere tra molte combinazioni è instabile. Le combinazioni fisse sono state scelte dopo aver visto gli stessi dati, quindi la loro performance è ottimistica e va confermata su eventi futuri.
- **Implicazione per la discussione / LEWS**: in questo dataset le variabili idrologiche non superano l'evento pluviometrico come singolo predittore, ma (i) la suzione superficiale antecedente e il VWC profondo descrivono lo stato di predisposizione invernale in cui cadono tutte le frane, (ii) la combinazione multivariata (Mahalanobis) separa bene le frane dagli eventi normali, e (iii) la vegetazione riduce in modo marcato l'ingresso d'acqua e la velocità di propagazione in profondità.

Nota rispetto all'indice: il punto 5 dell'indice ipotizza che il VWC a 60 cm abbia il potere discriminante maggiore; con i dati 2025–2026 e queste 4 frane ciò vale per ΔVWC a 60 cm (sito V), non per il VWC antecedente a 60 cm.

---

## Figure (`outputs/figures`)
| File | Indice | Contenuto |
|---|---|---|
| Fig02_timeseries_rain_VWC_suction | Ch.2 Fig.2 | Serie storiche pioggia (giornaliera + cumulate 5 pluviometri), VWC e suzione V/NV, frane |
| Fig02b_IETD_event_identification_example | Fig.2 / bozza Fig.4 | Esempio di identificazione eventi (IETD 24 h, E ≥ 10 mm) |
| Fig03_hydrological_index_extraction | Fig.3 | Estrazione indici (VWC0, picco, ΔVWC, s0, s_min) sull'evento di L1 |
| Fig04_ED_space_event_classes | Fig.4 | Eventi nello spazio E–D per classe (irrelevant/relevant/extreme), per sito e profondità |
| Fig05_infiltration_velocity_V_vs_NV | Fig.5 | Velocità picco-picco e fronte di bagnamento V vs NV; ΔVWC V vs NV |
| Fig06_landslide_timeline | Fig.6 | Timeline frane ed eventi per pluviometro |
| Fig06b_rainfall_around_landslides | (Patton Fig.2) | Pioggia cumulata 3 d prima / 1 d dopo ciascuna frana |
| Fig07_boxplots_<pluviometro> | Fig.7 | Boxplot D, E, I_max, VWC0 60, s0 15, ΔVWC 60 (V e NV) frana vs non frana |
| Fig08_ROC_curves | Fig.8 | Curve ROC per pluviometro |
| Fig09_E_vs_VWC0_60_KDE | Fig.9 | E vs VWC0 60 cm NV con KDE degli eventi senza frana |
| Fig10_antecedent_VWC_profiles | Fig.10 | Profili VWC0 pre-evento: frane vs mediana/IQR non frane |
| Fig11_discriminant_synthesis | Fig.11 | Heatmap AUC* (feature × pluviometro) e |RB| |
| Fig12_mahalanobis_and_accumulation_windows | §3.3.4 + Patton | Distanza di Mahalanobis; AUC* vs finestra di accumulo |
| Fig13_multivar_2var_heatmaps | 4.4 | AUC medio di tutte le coppie pioggia × acqua (D_M e PS) |
| Fig14_multivar_best_by_family | 4.4 | Migliore combinazione per famiglia (1, 2, 3 variabili; VWC0 vs ΔVWC) |
| Fig15_multivar_scatter_examples | 4.4 | E vs VWC0 (NV 15, V 60 cm) con ellisse di Mahalanobis 95% |

Fig.1 (mappa) è già nella bozza del Cap. 2 e non è rigenerata.

## Tabelle (`outputs/tables`)
T00 buchi pioggia/suolo · T01 sintesi dati · T02 eventi per pluviometro · T03 indici idrologici di tutti gli eventi · T04 sintesi eventi · T05 classi (Salerno G.C.) · T06 velocità di infiltrazione · T07 V vs NV velocità · T08 V vs NV appaiato per evento · T09 eventi con frana · T10 medie feature frana/no frana · T11 metriche discriminanti complete (AUC, AUC*, RB, U, p, p_adj Holm, percentile mediano, soglia Youden, recall, FPR, TP, FP) · T12 sintesi metriche (variabili dell'indice) · T13 classe di severità degli eventi con frana · T14 Mahalanobis · T15 AUC* per finestra di accumulo · T16 combinazioni multivariate per pluviometro (1var, 2var_R+W, 3var_R+R+W, 3var_R+W+W) · T17 sintesi sui 5 pluviometri · T18 migliori combinazioni per famiglia · `run_provenance.json` versioni e parametri.
