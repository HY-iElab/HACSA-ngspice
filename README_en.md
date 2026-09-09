# HACSA-ngspice

HACSA-ngspice is a Python interface for analog circuit sizing with ngspice.

## Installation

### ngspice

On Windows, download and extract the Windows 64-bit binary from the [ngspice download page](https://ngspice.sourceforge.io/download.html), then add the folder containing `ngspice_con.exe` to `PATH`. Open a new PowerShell window to verify the installation.

```powershell
ngspice_con.exe -v
```

On Debian/Ubuntu, install and verify ngspice as follows.

```bash
sudo apt update
sudo apt install ngspice
ngspice -v
```

### Python dependencies

Python 3.6.2 or later.

```bash
python -m pip install -r requirements.txt
```

## Running an optimization

Pass a JSON configuration file to `hacsa.py`.

```bash
python hacsa.py sample_manual.json
```

This command optimizes `sample/deck_fc` and saves the results in `result_fc`. Any existing `temp_fc` and `result_fc` folders are replaced at the start of the run.

### Configuration file

The following example sets targets and weights manually (see `sample_manual.json`).

```json
{
  "run_name": "fc",
  "deck_path": "sample/deck_fc",
  "deck_imports": ["sample/pdk"],
  "reject_spec": [-100.0, 0.0, 6.0, 40.0, 40.0],
  "max_evals": 20000,
  "early_stop": false,
  "target_spec": [-5.2232, 38.2163, 6.6529, 60.0, 70.4884],
  "pre_weight": [0.02, 0.025, 0.5, 0.015625, 0.025],
  "post_weight": [0.02, 0.025, 0.5, 0.0, 0.025],
  "design_space": {
    "R": [1.0, 1000.0, null, "k", true],
    "C": [10, 1000, null, "f", false],
    "L": [180, 360, 5, "n", false],
    "W": [45, 90, 5, "n", false],
    "M": [1, 60, 1, "", false]
  }
}
```

- `run_name`: Run identifier. An empty string uses `temp` and `result`; `"xxx"` uses `temp_xxx` and `result_xxx`.
- `deck_path`: Path to the deck. Relative paths are resolved from the folder containing `hacsa.py`; absolute paths are also supported.
- `deck_imports`: List of files to copy into the working folder alongside the deck. Use `sample/pdk` for the `.include "pdk"` line in `deck_fc`. List multiple files in order inside `[ ]`, or omit this field if no supporting files are needed.
- `reject_spec`: Lower bounds on the performance metrics (specs) of designs to retain. A design is excluded if any spec falls below its bound. Omitting this field disables this filter. The default store retains the Pareto set of the designs that pass.
- `max_evals`: Evaluation count at which the solver should stop. Evaluations run in batches, so the actual count may be slightly higher.
- `early_stop`: Whether to stop when the targets are met (default: `false`).
- `target_spec`: Minimum target value for each spec (set automatically if omitted).
- `pre_weight`: Positive weights applied to the figure of merit (FoM) when any target is unmet.
- `post_weight`: Nonnegative weights applied to the FoM when all targets are met. If either weight array is omitted, both are set automatically.
- `design_space`: [Search ranges](#design-space-definition) for the deck's design variables. Each array is ordered as `[lower, upper, resolution, unit, is_log]`.

`reject_spec`, `target_spec`, `pre_weight`, and `post_weight` must all follow the order in which the deck writes its specs. The mapping for `sample/deck_fc` is shown below.

| Index | Spec written by the deck | `reject_spec` | `target_spec` | `pre_weight` | `post_weight` |
|---:|---|---:|---:|---:|---:|
| 0 | `negative_total_current_uA` | -100.0 | -5.2232 | 0.02 | 0.02 |
| 1 | `gain_db` | 0.0 | 38.2163 | 0.025 | 0.025 |
| 2 | `log10_ugbw` | 6.0 | 6.6529 | 0.5 | 0.5 |
| 3 | `pm_deg` | 40.0 | 60.0 | 0.015625 | 0.0 |
| 4 | `cmrr_db` | 40.0 | 70.4884 | 0.025 | 0.025 |

Optional JSON fields:

- `solver`: [Solver to use](#choosing-a-solver) (default: `"CMAES"`).
- `auto_fom`: Exponent controlling the number of Sobol samples for automatic configuration (default: `7`). The sample count is `2^auto_fom`.
- `parallel`: How ngspice evaluates designs. `true` evaluates them in parallel (default); `false` evaluates them sequentially.
- `digits`: Maximum number of decimal places for parameters written to the deck (default: `3`, as in 0.xxx). When `resolution` is `null`, the search increment is `10**(-digits)`.

### Choosing a solver

To use a different solver, add `solver` to the JSON configuration.

```json
"solver": "LSHADE"
```

Built-in solvers and their underlying papers:

- `CMAES`: Nikolaus Hansen and Andreas Ostermeier, [*Adapting Arbitrary Normal Mutation Distributions in Evolution Strategies: The Covariance Matrix Adaptation*](https://doi.org/10.1109/ICEC.1996.542381), 1996.
- `LSHADE`: Ryoji Tanabe and Alex S. Fukunaga, [*Improving the Search Performance of SHADE Using Linear Population Size Reduction*](https://doi.org/10.1109/CEC.2014.6900380), 2014.
- `TuRBO`: David Eriksson, Michael Pearce, Jacob Gardner, Ryan D. Turner, Matthias Poloczek, [*Scalable Global Optimization via Local Bayesian Optimization*](https://proceedings.neurips.cc/paper/2019/hash/6c990b7aca7bc7058f5e98ea909e924b-Abstract.html), 2019.

To use a custom solver, implement the `Solver` interface and place it in the `Solver` folder. The file and class names must match (`XXX.py` → `class XXX`).

### Automatic targets and weights

Supplied targets and a complete pair of weight arrays are used as provided. Missing targets or weights are derived by evaluating Sobol samples with ngspice.

| `target_spec` | `pre_weight`, `post_weight` | Behavior |
|---|---|---|
| Provided | Both provided | No automatic sample evaluation |
| Omitted | Both provided | Set targets automatically |
| Provided | One or both omitted | Set both weight arrays automatically |
| Omitted | One or both omitted | Set targets and both weight arrays automatically |

Omit both targets and weights, as in `sample_auto.json`, to use the automatically computed values as a starting point for tuning the FoM.

```bash
python hacsa.py sample_auto.json
```

The contents of `sample_auto.json` are shown below.

```json
{
  "run_name": "ts",
  "deck_path": "sample/deck_ts",
  "deck_imports": ["sample/pdk"],
  "reject_spec": [-100.0, 0.0, 6.0, 40.0],
  "max_evals": 20000,
  "design_space": {
    "I": [1.0, 5.0, null, "u", true],
    "C": [10, 1000, null, "f", false],
    "L": [180, 360, 5, "n", false],
    "W": [45, 90, 5, "n", false],
    "M": [1, 60, 1, "", false],
    "M0": [20, 60, 1, "", false]
  }
}
```

Add `auto_fom` to change the sample count for automatic targets and weights from the default $2^7 = 128$. These evaluations run before the solver starts and do not count toward `max_evals`.

For each spec, the automatic calculation excludes failed measurements and computes the mean, minimum, and maximum. Valid values for other specs from the same design are still included. Each spec must have at least one valid measurement.

## Deck requirements

To use `AutoCircuit`, the deck must meet the following requirements.

### 1. Include the parameter file

```spice
.include @PARAM_PATH@
```

During execution, `@PARAM_PATH@` is replaced with `param_0`, `param_1`, and so on.

### 2. Name the design variables

Use names such as `{L0}`, `{W0}`, and `{M0}` for design variables to tune.

```spice
MN0 out in 0 0 nmos l={L0} w={W0} m={M0}
R0 out n1 {R0}
C0 n1 0 {C0}
```

Naming rules:

- The prefix consists of English letters and underscores: `L`, `W`, `M`, `R`, `C`, `_Aa_Bce_`, `AaaeE_FG`.
- Within each prefix, use consecutive integer suffixes starting at 0, as in `L0`, `L1`, and `L2`. Even a single variable needs a suffix, as in `R0`.

### 3. Write the specs

Compute all specs in the deck and write them to `@SPEC_PATH@`.

```spice
echo negative_total_current_uA $&negative_total_current_uA > @SPEC_PATH@
echo gain_db $&gain_db >> @SPEC_PATH@
echo log10_ugbw $&log10_ugbw >> @SPEC_PATH@
```

`AutoCircuit` reads `negative_total_current_uA`, `gain_db`, and `log10_ugbw` as the spec names in this order. `reject_spec`, `target_spec`, `pre_weight`, and `post_weight` must use the same order.

During execution, `@SPEC_PATH@` is replaced with `spec_0`, `spec_1`, and so on. If SPICE fails to create a spec file, the design's specs are assigned a very low value, and its parameter file is moved to `error` inside the temporary folder.

Write all specs so that higher values are better. For quantities where lower values are better, reverse the sign in the deck.

## Minimal example

This deck has one design variable, `{R0}`, and one spec, `gain_db`.

```spice
.include @PARAM_PATH@

RLOAD out 0 {R0}

.control
let gain_db = 42.0
echo gain_db $&gain_db > @SPEC_PATH@
.endc
.end
```

The corresponding JSON configuration:

```json
{
  "run_name": "minimal",
  "deck_path": "path/to/deck",
  "reject_spec": [0.0],
  "max_evals": 100,
  "target_spec": [40.0],
  "pre_weight": [0.025],
  "post_weight": [0.0],
  "design_space": {
    "R": [1.0, 100.0, 1.0, "k", true]
  }
}
```

`{R0}` in the deck maps to `"R"` in `design_space`. As the only spec, `gain_db` occupies index 0 in all four spec arrays, with a target of 40 dB.

## Design space definition

`design_space` defines a default range for each design variable prefix and any ranges needed for individual variables.

```json
"L": [180, 360, 5, "n", false]
```

Each array contains `[lower, upper, resolution, unit, is_log]`.

- `lower`, `upper`: Lower and upper bounds on the actual value.
- `resolution`: Allowed increment between design variable values. Even when this is `null`, values are written with at most `digits` decimal places.
- `unit`: Unit suffix appended to the value in the parameter file (`""` for none).
- `is_log`: `true` for a logarithmic scale; `false` for a linear scale. Logarithmic scaling requires positive lower and upper bounds.

With this configuration, each `L` value is one of `180n`, `185n`, `190n`, ..., `360n`.

A prefix entry supplies the default for all design variables with that prefix. An individual variable entry overrides the default for that variable only.

```json
"M": [1, 60, 1, "", false],
"M10": [30, 60, 1, "", false]
```

Only `M10` uses the range `30`–`60`; all other `M` variables use `1`–`60`. Each prefix in the deck needs either a default entry or an entry for every individual variable. Entries in `design_space` that do not correspond to variables in the deck are unused.

The solver proposes a value `v` in `[0, 1]`, which is converted to an actual value `x` as follows.

Linear scale:

$$
x = \mathrm{lower} + v(\mathrm{upper} - \mathrm{lower})
$$

Logarithmic scale:

$$
x = 10^{\log_{10}(\mathrm{lower}) + v(\log_{10}(\mathrm{upper}) - \log_{10}(\mathrm{lower}))}
$$

The converted value is rounded to the specified `resolution`. `is_log` does not change the value range, but it can affect solver performance.

## FoM definition

The FoM is the score that the `Solver` maximizes. The default FoM uses separate calculations before and after the targets are met.

While any target remains unmet, only shortfalls contribute to the score.

$$
\mathrm{pre\_FoM}
= \sum_i \min(\mathrm{spec}_i - \mathrm{target}_i, 0)
\times \mathrm{pre\_weight}_i
$$

A design that meets every target has a `pre_FoM` of 0. Unless `early_stop` is `true`, the following score is applied to that design.

$$
\mathrm{post\_FoM}
= \sum_i (\mathrm{spec}_i - \mathrm{target}_i)
\times \mathrm{post\_weight}_i
$$

For a custom FoM, see the [FoM contract](ADVANCED_USE_en.md#fom-contract).

## Result files

Results are saved in `result_{run_name}` (`result` if `run_name` is empty).

The following files are updated whenever the best FoM improves during the run:

- `best_param`: Parameters of the design with the highest FoM.
- `best_spec`: Specs and FoM of that design.

The default store, `StoreParetoFront`, saves the Pareto set of designs whose specs all meet or exceed `reject_spec` in the results folder.

- `param_0`, `param_1`, ...: Parameters of the designs retained in the archive.
- `result_spec.csv`: Index, FoM, and specs of each design.

See [RESULTS_en.md](RESULTS_en.md) for the folder and file structure, Pareto selection criteria, and performance comparisons using the CSV.

## Checklist

- If the deck contains `{L0}`, `design_space` must have an entry for `"L"` or `"L0"`.
- The spec output order must match the order of `reject_spec`, `target_spec`, `pre_weight`, and `post_weight`.
- When setting these arrays manually, each must have as many entries as the deck writes specs.
- Reverse the sign in the deck for specs where lower values are better.
- Before running, check whether you need to keep the existing temporary and results folders for the same `run_name`.

See [ADVANCED_USE_en.md](ADVANCED_USE_en.md) for solver, FoM, and store choices, and for custom `Circuit` implementations.
