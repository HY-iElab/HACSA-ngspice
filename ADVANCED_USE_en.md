# Advanced usage

For basic usage, see [README_en.md](README_en.md).

- [Custom optimization loop](#custom-optimization-loop)
- [Custom FoM](#custom-fom)
- [Storing results](#storing-results)
- [Custom solver](#custom-solver)
- [Custom deck or specs](#custom-deck-or-specs)

In [hacsa.py](hacsa.py), `run(config)` → `optimize(**config)` connects the following components.

| Component | Role |
|---|---|
| `Circuit` | Converts design variables to simulator inputs and computes specs and the FoM |
| `AutoCircuit` | Implements `Circuit` according to the deck requirements in the README |
| `Solver` | Proposes designs to evaluate and uses their scores to guide the search |
| `Store` | Retains evaluation results and saves them to files |

<a id="overall-workflow"></a>

## Custom optimization loop

This example assumes that you have [implemented](#custom-solver) `Solver/MySolver.py`. Run the code from the project folder.

```python
from json import load

from Instance.AutoCircuit import AutoCircuit


with open("sample_manual.json", encoding="utf-8") as file:
    config = load(file)

circuit = AutoCircuit(
    deck_path=config["deck_path"],
    deck_imports=config["deck_imports"],
    run_name=config["run_name"],
)
circuit.setDesignSpace(config["design_space"])
circuit.setTargetSpec(config["target_spec"])
circuit.setPreWeight(config["pre_weight"])
circuit.setPostWeight(config["post_weight"])
```

The example uses `sample_manual.json`, which provides both targets and weights.

- `AutoCircuit(...)`: Reads the deck to identify design variables and spec names, and creates the circuit to simulate. Pass `deck_path`, `deck_imports`, and `run_name` directly from the configuration used in the README. For an approach other than `AutoCircuit`, see [Custom deck or specs](#custom-deck-or-specs).
- `setDesignSpace(...)`: Sets the search ranges for the design variables.
- `setTargetSpec(...)`: Sets the target value for each spec.
- `setPreWeight(...)`, `setPostWeight(...)`: Set the FoM weights before and after the targets are met.

[MyStore](#storing-results) is a storage class that this example assumes you have implemented in `Store/MyStore.py`.

```python
from Store.MyStore import MyStore

store = MyStore(
    design_dim=circuit.design_dim,
    spec_dim=circuit.spec_dim,
    temp_folder=circuit.temp_folder,
    reject_spec=config["reject_spec"],
    run_name=config["run_name"],
)

from Solver.MySolver import MySolver

max_evals = config["max_evals"]
early_stop = config.get("early_stop", False)
solver = MySolver(dim=circuit.design_dim, MAX_EVALS=max_evals)
```

- `store`: Retains results according to the criteria implemented in `MyStore`. `circuit.design_dim` and `circuit.spec_dim` are the numbers of design variables and specs, respectively. `circuit.temp_folder` is the working folder containing the simulation files.
- `max_evals`, `early_stop`: The evaluation count and early stopping setting from the JSON configuration. `early_stop` defaults to `False` if omitted.
- `solver`: Passes the number of design variables as `dim` and the evaluation count as `MAX_EVALS` to `MySolver`. A custom solver may also accept other inputs.

```python
evaluations_done = 0
while evaluations_done < max_evals:
    candidates = solver.ask()
    circuit.design_batch = candidates.copy()
    circuit.evaluateDesign()
    evaluations_done += circuit.batch_size

    store.updateArchive(circuit.design_batch, circuit.spec_batch, circuit.fom_batch)
    if store.updateBestFoM(circuit.fom_batch):
        if early_stop and store.isTargetAcheived():
            break

    solver.tell(circuit.design_batch, circuit.fom_batch)

store.saveArchive(circuit)
```

- `candidates` contains `batch_size` candidate designs. Each design specifies values for the netlist's design variables.
- `circuit.evaluateDesign()` evaluates the candidates with ngspice.
- `Circuit.calculateFoM()` computes the FoM from the evaluated specs, and the solver and store use the results. To change the scoring function, see [Custom FoM](#custom-fom).
- `spec_batch` and `fom_batch` follow the same design order as `design_batch`.
- `solver.tell` passes the evaluated `design_batch` back to the solver.

Inspect the saved results as follows.

```python
print(circuit.spec_names)
print(store.best_fom)
print(store.size)
print(store.result_folder)
print(store.spec_container[:store.size])
```

- `circuit.spec_names`: Spec names and their output order.
- `store.best_fom`: Highest FoM among the evaluated designs.
- `store.result_folder`: Folder containing the [result files](RESULTS_en.md).
- `store.spec_container[:store.size]`: Spec array for the retained designs. `store.size` is the number of retained designs; columns follow `circuit.spec_names`.

<a id="fom-contract"></a>

## Custom FoM

Assign a Python function to `config["fom"]` to customize the FoM calculation.

```python
from json import load
import numpy as np
from hacsa import run


def my_fom(spec_batch, target_spec, pre_weight, post_weight):
    margins = spec_batch - target_spec
    return np.minimum(margins, 0.0) @ pre_weight


with open("sample_manual.json", encoding="utf-8") as file:
    config = load(file)

config["run_name"] = "custom_fom"
config["max_evals"] = 200
config["fom"] = my_fom

circuit, store = run(config)
```

`run(config)` returns `circuit` and `store` after optimization and saving are complete.

For a batch of N designs with S specs, the array shapes are:

| Name | Meaning | NumPy array shape |
|---|---|---|
| `spec_batch` | Specs for each design; one design per row | (N, S) |
| `target_spec` | Target value for each spec | (S,) |
| `pre_weight` | Weights before the targets are met | (S,) |
| `post_weight` | Weights after the targets are met | (S,) |
| Return value | One score per design, in input order | (N,) |

The specs and all three configuration arrays follow **the deck's spec output order** (`circuit.spec_names`). Keep all arguments in the function signature, even if some are unused.

The solver treats higher scores as better. With `"early_stop": true`, the run stops when the best FoM is 0 or greater, so return a negative score when any target is unmet and a nonnegative score when all targets are met. See [FoM definition](README_en.md#fom-definition) for the default calculation.

### Example: LDO scoring

Suppose the deck writes specs in the order `[-T_R, -I_Q, I_LOAD_MAX]`. Since lower `T_R` and `I_Q` values are better, their signs are reversed in the output.

$$
\mathrm{LDO\_FoM}
= \frac{T_R \times I_Q}{I_{\mathrm{LOAD\_MAX}}}
$$

Before the targets are met, reduce the shortfalls. Afterward, maximize the reciprocal of the expression above. All three physical quantities and all `pre_weight` values must be positive.

```python
import numpy as np


def ldo_fom(spec_batch, target_spec, pre_weight, post_weight):
    fom_batch = np.minimum(
        spec_batch - target_spec, 0.0
    ) @ pre_weight

    target_met = fom_batch == 0.0
    negative_t_r = spec_batch[target_met, 0]
    negative_i_q = spec_batch[target_met, 1]
    i_load_max = spec_batch[target_met, 2]

    ldo_fom = negative_t_r * negative_i_q / i_load_max
    fom_batch[target_met] = 1.0 / ldo_fom
    return fom_batch
```

`target_met` selects designs that meet all targets. The product of the two negative specs is `T_R × I_Q`. Define this function in your script and set `config["fom"] = ldo_fom`. Adjust the JSON configuration to match the LDO deck and its spec order.

## Storing results

Implement `MyStore` from the earlier example as follows and save it in `Store/MyStore.py`. This implementation retains every result that passes `reject_spec`. For the default `StoreParetoFront` selection criteria and how to use the result files, see [RESULTS_en.md](RESULTS_en.md).

```python
import numpy as np
from Store.Store import Store


class MyStore(Store):
    def updateArchive(self, design_batch, spec_batch, fom_batch):
        while self.size + spec_batch.shape[0] > self.container_cap:
            self.expandContainer()

        for i in range(spec_batch.shape[0]):
            if np.any(spec_batch[i] < self.reject_spec):
                continue

            idx = self.size
            self.design_container[idx] = design_batch[i]
            self.spec_container[idx] = spec_batch[i]
            self.fom_container[idx] = fom_batch[i]
            self.size += 1
```

After loading the JSON configuration into `config`, assign the storage class and run `hacsa.run`. Classes cannot be stored in JSON, so assign the class in Python.

```python
from hacsa import run

config["store_type"] = MyStore
circuit, store = run(config)
```

If `reject_spec` is omitted, `MyStore` retains all results.

To use other retention criteria, subclass [Store](Store/Store.py) and implement `updateArchive`. Corresponding rows in the three input arrays refer to the same design, and design variable values are normalized to 0–1.

To use the default `saveArchive(circuit)`, maintain the following values:

- `self.size`: Number of retained designs.
- `self.design_container[:self.size]`: Design variable array.
- `self.spec_container[:self.size]`: Spec array.
- `self.fom_container[:self.size]`: FoM array.

Use `expandContainer()` to increase array capacity. If you change the constructor (`__init__`), it must accept `design_dim`, `spec_dim`, `reject_spec`, `temp_folder`, and `run_name` as keyword arguments. If archive updates run concurrently with other work, finish them before saving, as in [StoreParetoFront](Store/StoreParetoFront.py).

You can use the default implementations of `updateBestFoM()` and `isTargetAcheived()`. When the best FoM improves, `param_i` and `spec_i` are copied to `best_param` and `best_spec`, and the FoM is appended to `best_spec`. This record is independent of whether `reject_spec` allows the design into the archive.

## Custom solver

To choose a built-in solver, see [Choosing a solver](README_en.md#choosing-a-solver).

Subclass [Solver](Solver/Solver.py), define `MySolver` in `Solver/MySolver.py`, and set `"solver": "MySolver"` in the JSON configuration. The file and class names must match.

| Method to implement | Role |
|---|---|
| `__init__(self, dim, MAX_EVALS)` | Receives the number of design variables and the evaluation budget |
| `ask()` | Returns the next N candidate designs as an (N, dim) NumPy array, with each variable in the range 0–1 |
| `tell(x, fitness)` | Receives the evaluated designs (N, dim) and scores (N,) and uses them to guide the search; higher scores are better |

The calling code handles simulation and storage. If the constructor needs additional arguments, give them defaults or instantiate the solver directly in Python, as shown in [Custom optimization loop](#custom-optimization-loop).

## Custom deck or specs

The default workflow creates an `AutoCircuit`. To use a different `Circuit`, write the object initialization and optimization loop in Python.

Subclass [Circuit](Instance/Circuit.py) and set the number of design variables, `design_dim`, and the spec names and order, `spec_names`, in the constructor. Accept the FoM function as `fom` and pass it to the parent constructor.

The default `evaluateDesign()` runs in the order below. Implement the methods marked as required, and also override `simulateCircuit` if the simulator must be run differently.

| Order | Method | Role | Implementation |
|---:|---|---|---|
| 1 | `reserveDesignBatch()` | Prepares `batch_size`, result arrays, and runnable deck files for the number of designs | Required |
| 2 | `setSizeFromDesignBatch()` | Converts design variable values from 0–1 to actual circuit values | Required |
| 3 | `writeCircuit(folder)` | Writes `param_0`, `param_1`, … to the specified folder | Required |
| 4 | `renormalizeDesignBatch()` | Converts actual values adjusted by rounding or similar operations back to 0–1 and updates `design_batch` | Required |
| 5 | `simulateCircuit(i)` → `evaluateSpec(i, folder)` | Simulates each design and reads its specs | Spec reading required |
| 6 | `calculateFoM()` | Computes `fom_batch` using the assigned FoM function | Use the default implementation |

For N designs, `design_batch` must have shape (N, design_dim), and `spec_batch` must have shape (N, spec_dim). `spec_batch[i]` contains real values in `spec_names` order, and the design variables in the corresponding row must represent the values actually simulated.

The default `simulateCircuit(i)` runs the files `0`, `1`, … in the working folder with ngspice. The default mechanism for saving the best FoM requires `param_i` and `spec_i` files. To support deck checks, also implement `testDeck()`.
