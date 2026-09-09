# Viewing and reusing results

The optimization results from the following command are saved in `result_fc`.

```bash
python hacsa.py sample_manual.json
```

`sample_manual.json` sets `run_name` to `"fc"`. This guide assumes the default circuit, `AutoCircuit`, and the default store, [StoreParetoFront](#why-save-the-pareto-set).

## Generated folders and files

The folder structure below assumes that some designs are retained. The number of numbered files depends on the evaluation batch size and the number of retained designs.

```text
HACSA-ngspice/
├── sample_manual.json
├── sample/
│   ├── deck_fc
│   └── pdk
├── temp_fc/
│   ├── pdk
│   ├── 0
│   ├── 1
│   ├── ...
│   ├── param_0
│   ├── param_1
│   ├── ...
│   ├── spec_0
│   ├── spec_1
│   ├── ...
│   └── error/
└── result_fc/
    ├── best_param
    ├── best_spec
    ├── param_0
    ├── param_1
    ├── ...
    └── result_spec.csv
```

| File | Contents and purpose |
|---|---|
| `sample_manual.json` | Run configuration, including search ranges, targets, and weights |
| `sample/deck_fc`, `sample/pdk` | Input deck and the model file it includes |
| `temp_fc/pdk` | Model file copied from `deck_imports` into the working folder |
| `temp_fc/0`, `temp_fc/1`, ... | [Runnable copies](#how-files-are-created-during-a-run) of the input deck, named with numbers and no extension |
| `temp_fc/param_i` | Parameters used to simulate design i in the batch |
| `temp_fc/spec_i` | Specs written by the deck during that simulation |
| `temp_fc/error/` | Parameter files for designs whose spec files could not be created |
| `result_fc/best_param`, `result_fc/best_spec` | Parameters and specs of the design with the highest FoM; the last line of `best_spec` also records the FoM |
| `result_fc/param_i` | Parameters of retained design i, corresponding to the CSV row whose `idx` is i |
| `result_fc/result_spec.csv` | [Table of indices, FoMs, and specs](#comparing-designs-in-the-csv) for the retained designs |

The working folder, `temp_fc`, reuses the same numbers for each batch, so it does not contain the full evaluation history. `result_fc` assigns new numbers to retained designs. **Do not assume that `temp_fc/param_0` and `result_fc/param_0` represent the same design.**

`best_param` and `best_spec` are saved whenever the best FoM improves during the run. `result_fc/param_i` and the CSV are saved when optimization finishes. If no designs pass the retention criteria, the CSV contains only column headers and no `param_i` files are saved.

A `run_name` of `"fc"` uses `temp_fc` and `result_fc`; an empty string uses `temp` and `result`. Rerunning with the same `run_name` replaces both folders, so copy any results you want to keep elsewhere before running again.

To simulate a saved design again, use `.include` in your deck to load its `param_i` or `best_param` file, then run the deck directly with SPICE.

## Comparing designs in the CSV

Open `result_fc/result_spec.csv` in a spreadsheet application. If it appears in a single column, set the delimiter to a comma. For `sample/deck_fc`, the first CSV row is:

```csv
idx,fom,negative_total_current_uA,gain_db,log10_ugbw,pm_deg,cmrr_db
```

- `idx`: Number of the corresponding `param_{idx}` file in the same folder. Use this value to find the file, even after sorting, rather than the row number.
- `fom`: Design's FoM; higher is better. The CSV is not sorted by FoM.
- Remaining columns: Specs in the deck's output order. Each row represents one design.

Sort by `fom` or a spec of interest to select candidates, and plot two specs on the X and Y axes of a scatter plot to explore their relationship. For example, a current consumption versus bandwidth plot shows how much current is needed for higher bandwidth.

The CSV preserves the signs and units used by the deck. With the column order above and the first data row at row 2, use these formulas to recover the physical quantities.

| Stored spec | Meaning | Formula for a new column |
|---|---|---|
| `negative_total_current_uA` | Total current consumption with its sign reversed | `=-C2` gives current in µA |
| `log10_ugbw` | Base-10 logarithm of bandwidth in Hz | `=10^E2` gives bandwidth in Hz |

Fill the formulas down the remaining rows and create a scatter plot of the two new columns.

## Why save the Pareto set?

`StoreParetoFront` retains the Pareto set of designs whose specs all meet or exceed `reject_spec`. A design is excluded if another is at least as good in every spec and better in at least one.

In this example, higher values are better for both specs (gain and bandwidth), and the retention thresholds are 50 dB and 5 MHz, respectively.

| Design | Gain (dB) | Bandwidth (MHz) | Retention decision |
|---|---:|---:|---|
| A | 60 | 10 | Retain. Higher bandwidth than B |
| B | 65 | 8 | Retain. Higher gain than A |
| C | 55 | 7 | Exclude. Both specs are lower than those of A and B |
| D | 45 | 15 | Exclude. Gain is below the retention threshold |

A and B show the trade-off between gain and bandwidth. Retaining only these candidates lets you choose a design for the performance you need without reviewing many unnecessary parameter files. If all specs are identical, only one design is retained. Selection uses the specs rather than the FoM.

Pareto selection still applies when `reject_spec` is omitted. `target_spec` sets the targets used for the FoM and early stopping; it is separate from the retention thresholds in `reject_spec`.

`best_param` and `best_spec` are saved independently of `reject_spec`, so their design may not appear in the CSV.

## How files are created during a run

The input deck is copied for each design, with its parameter and spec paths replaced, and the copy is run. For design 0 in a batch, `temp_fc/0` uses the following substitutions.

| Input deck | Runnable copy `temp_fc/0` |
|---|---|
| `.include @PARAM_PATH@` | `.include param_0` |
| `> @SPEC_PATH@` | `> spec_0` |
| `>> @SPEC_PATH@` | `>> spec_0` |

`temp_fc/1` uses `param_1` and `spec_1` in the same places. The circuit and analysis commands come from the input deck. Files in `deck_imports` are copied into the working folder under their original names.

Example `param_i` format:

```spice
.param R0=10k
.param C0=100f
```

The solver's design variable values in 0–1 are converted to actual values using the ranges and increments in `design_space`, then written to the file. ngspice uses the included `.param` values for `{R0}`, `{C0}`, and other variables in the deck. See [Design space definition in the README](README_en.md#design-space-definition) for the conversion rules.

ngspice runs the copied deck from `temp_fc`, and the deck's `echo` commands create `spec_i`. Example spec file format:

```text
negative_total_current_uA -5.2
gain_db 60
```

`>` writes a new file; `>>` appends lines. HACSA reads the values in the deck's spec output order, computes the FoM, and passes the design variables, specs, and FoM to the store. The FoM is recorded separately in `best_spec` and the results CSV.

If a spec file is missing, the corresponding parameter file is moved to a name such as `error/param_0_3`, using the failure file's insertion order and the design's index within the batch. The design's specs are filled with `-1e10`.

After optimization, the retained design variables are used to create `param_i` files in the results folder, and the specs and FoM are written to the CSV under the same indices. The results folder contains `result_spec.csv` instead of a separate `spec_i` file for each design.
