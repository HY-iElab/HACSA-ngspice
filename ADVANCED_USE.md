# 고급 사용

기본 사용법은 [README.md](README.md)를 참고한다.

- [Custom optimization loop](#custom-optimization-loop)
- [Custom FoM](#custom-fom)
- [Storing results](#storing-results)
- [Custom solver](#custom-solver)
- [Custom deck or specs](#custom-deck-or-specs)

<a id="전체-실행-흐름"></a>

## Custom optimization loop

다음은 사용자가 `Solver/MySolver.py`를 [구현](#custom-solver)했다고 가정한 예제이다. (코드는 프로젝트 폴더에서 실행한다)

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

이 예제는 target과 weight가 모두 있는 `sample_manual.json`을 사용한다.

- `AutoCircuit(...)`: deck을 읽어 설계 변수와 spec 이름을 파악하고, 시뮬레이션할 회로를 만든다. `deck_path`, `deck_imports`, `run_name`은 README에서 사용한 설정을 그대로 전달한다. (AutoCircuit과 다른 방식을 원한다면 [Custom deck or specs](#custom-deck-or-specs)를 참고 바람)
- `setDesignSpace(...)`: 설계 변수의 탐색 범위를 지정한다.
- `setTargetSpec(...)`: 각 spec의 목표값을 지정한다.
- `setPreWeight(...)`, `setPostWeight(...)`: target 달성 전과 후의 FoM 가중치를 지정한다.

[MyStore](#storing-results)는 사용자가 `Store/MyStore.py`에 구현했다고 가정한 저장 클래스이다.

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

- `store`: `MyStore`에 구현한 기준으로 결과를 보관한다. `circuit.design_dim`과 `circuit.spec_dim`은 각각 설계 변수 수와 spec 수이며, `circuit.temp_folder`는 시뮬레이션 파일이 있는 작업 폴더이다.
- `max_evals`, `early_stop`: JSON의 평가 횟수와 조기 종료 설정이다. `early_stop`을 생략하면 `False`를 사용한다.
- `solver`: `MySolver`에 설계 변수 수를 `dim`으로, 평가 횟수를 `MAX_EVALS`로 전달한다. custom solver이므로 다른 입력도 취할 수 있다.

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

- `candidates`는 `batch_size` 개의 설계안이다.각 설계안은 netlist의 설계변수의 값을 명시한다.
- `candidates`는 `circuit.evaluateDesign()`을 통해 ngspice로 평가된다.
- 평가된 spec은 `Circuit.calculateFoM()`에서 FoM으로 계산되며 solver와 store는 그 결과를 사용한다. FoM 계산식을 바꾸려면 [Custom FoM](#custom-fom)을 참고한다.
- `spec_batch`와 `fom_batch`는 `design_batch`와 같은 설계안 순서를 따른다.
- `solver.tell`은 평가된 `design_batch`를 solver에게 전달한다. 

저장한 결과는 다음처럼 확인한다.

```python
print(circuit.spec_names)
print(store.best_fom)
print(store.spec_container[:store.size])
```

- `circuit.spec_names`: spec 이름과 저장 순서.
- `store.best_fom`: 평가한 설계안 중 최고 FoM.
- `store.spec_container[:store.size]`: 보관한 설계안의 spec 배열. `store.size`는 보관한 설계안 수이며, 각 열은 `circuit.spec_names` 순서이다.

<a id="fom-contract"></a>

## Custom FoM

Python에서는 함수도 저장 가능하다. `config["fom"]`은 FoM 함수를 저정한다. 

```python
from json import load
import numpy as np
from hacsa import run


def my_fom(spec_batch, target_spec, pre_weight, post_weight):
    margins = spec_batch - target_spec
    return np.minimum(margins, 0.0) @ pre_weight


with open("sample_manual.json", encoding="utf-8") as file:
    config = load(file)

config["fom"] = my_fom

circuit, store = run(config)
```

`run(config)`는 최적화와 저장을 마친 뒤 `circuit`, `store`를 반환한다.

한 번에 평가하는 설계안이 N개, spec이 S개일 때 배열 크기는 다음과 같다.

| 이름 | 의미 | NumPy 배열 크기 |
|---|---|---|
| `spec_batch` | 설계안별 spec. 한 행이 한 설계안 | (N, S) |
| `target_spec` | spec별 목표값 | (S,) |
| `pre_weight` | target 달성 전 가중치 | (S,) |
| `post_weight` | target 달성 후 가중치 | (S,) |
| 반환값 | 입력 순서대로 설계안마다 점수 하나 | (N,) |

spec과 세 설정 배열은 **deck의 spec 저장 순서**(`circuit.spec_names`)를 따른다. 사용하지 않는 인자도 함수 정의에는 남겨 둔다.

solver는 점수가 클수록 좋다고 판단한다. `"early_stop": true`이면 최고 FoM이 0 이상일 때 종료하므로, target 미달에는 음수, 모두 달성하면 0 이상을 반환한다. 기본 계산식은 [FoM 정의](README.md#fom-정의)를 참고한다.

### 예: LDO 점수 계산

deck이 `[-T_R, -I_Q, I_LOAD_MAX]` 순서로 spec을 저장한다고 하자. 작을수록 좋은 `T_R`, `I_Q`는 부호를 반전해 저장한다.

$$
\mathrm{LDO\_FoM}
= \frac{T_R \times I_Q}{I_{\mathrm{LOAD\_MAX}}}
$$

target 달성 전에는 부족분을 줄이고, 달성 후에는 위 값의 역수를 키운다. 세 물리량과 모든 `pre_weight` 값은 양수여야 한다.

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

`target_met`은 모든 target을 만족한 설계안을 고른다. 두 음수 spec의 곱은 `T_R × I_Q`이다. 실행 코드에 이 함수를 정의하고 `config["fom"] = ldo_fom`으로 지정한다. JSON도 해당 LDO deck과 spec 순서에 맞춘다.

## Storing results

앞 예제의 `MyStore`를 다음처럼 구현해 `Store/MyStore.py`에 저장한다. 이 구현은 `reject_spec`을 통과한 결과를 모두 보관한다. 기본 저장소인 `StoreParetoFront`의 선별 기준과 결과 파일 사용법은 [Results.md](Results.md)를 참고한다.

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

JSON 설정을 읽은 `config`에 저장 클래스를 지정하고 `hacsa.run`으로 실행한다. 클래스는 JSON에 담을 수 없어 Python에서 지정한다.

```python
from hacsa import run

config["store_type"] = MyStore
circuit, store = run(config)
```

`reject_spec`을 생략하면 `MyStore`는 모든 결과를 보관한다.

다른 저장 기준도 [Store](Store/Store.py)를 상속해 `updateArchive`에 구현한다. 세 입력 배열의 같은 행은 같은 설계안이며, 설계 변수는 0~1로 환산된 값이다.

기본 `saveArchive(circuit)`로 저장하려면 다음 값을 유지한다.

- `self.size`: 보관한 설계안 수
- `self.design_container[:self.size]`: 설계 변수 배열
- `self.spec_container[:self.size]`: spec 배열
- `self.fom_container[:self.size]`: FoM 배열

배열 공간은 `expandContainer()`로 늘린다. 생성자(`__init__`)를 바꾸면 `design_dim`, `spec_dim`, `reject_spec`, `temp_folder`, `run_name`을 이름으로 받아야 한다. 결과 정리를 다른 작업과 동시에 진행한다면 [StoreParetoFront](Store/StoreParetoFront.py)처럼 저장 전에 정리를 끝낸다.

`updateBestFoM()`과 `isTargetAcheived()`는 기본 구현을 쓸 수 있다. 최고 FoM이 갱신되면 `param_i`, `spec_i`를 `best_param`, `best_spec`으로 복사하고 `best_spec`에 FoM을 덧붙인다. 이 기록은 `reject_spec`에 따른 보관 여부와 별개이다.

## Custom solver

기본 제공 solver 중에서 선택하려면 [Solver 선택](README.md#solver-선택)을 참고한다.

[Solver](Solver/Solver.py)를 상속해 `Solver/MySolver.py`에 `MySolver` 클래스를 만들고, JSON에 `"solver": "MySolver"`를 지정한다. 파일 이름과 클래스 이름은 같아야 한다.

| 구현할 부분 | 역할 |
|---|---|
| `__init__(self, dim, MAX_EVALS)` | 설계 변수 수와 평가 횟수 기준을 받는다 |
| `ask()` | 다음에 평가할 설계안 N개를 (N, dim) NumPy 배열로 반환한다. 각 변수는 0~1 범위이다 |
| `tell(x, fitness)` | 평가한 설계안 (N, dim)과 점수 (N,)을 받아 탐색에 반영한다. 점수는 클수록 좋다 |

시뮬레이션과 저장은 실행 코드가 담당한다. 추가 생성자 인자가 필요하면 기본값을 두거나, [Custom optimization loop](#custom-optimization-loop)을 참고해 Python에서 직접 생성한다.

## Custom deck or specs

[hacsa.py](hacsa.py)의 `run(config)` → `optimize(**config)`는 다음 요소를 연결한다.

| 구성 요소 | 역할 |
|---|---|
| `Circuit` | 설계 변수를 시뮬레이터 입력으로 바꾸고 spec과 FoM을 계산한다 |
| `AutoCircuit` | README의 deck 규칙에 맞춰 구현된 `Circuit`이다 |
| `Solver` | 평가할 설계안을 제안하고 점수를 받아 탐색을 진행한다 |
| `Store` | 평가 결과를 보관하고 파일로 저장한다 |

기본 실행은 `AutoCircuit`을 생성한다. 다른 `Circuit`을 쓰려면 객체 생성과 최적화 루프를 Python으로 작성한다.

[Circuit](Instance/Circuit.py)을 상속하고 생성자에서 설계 변수 수 `design_dim`과 spec 이름·순서 `spec_names`를 정한다. FoM 함수를 `fom`으로 받아 부모 생성자에도 전달한다.

기본 `evaluateDesign()`의 실행 순서이다. ‘직접 구현’ 항목을 작성하고, 시뮬레이터 실행 방식이 다르면 `simulateCircuit`도 바꾼다.

| 순서 | 메서드 | 역할 | 구현 |
|---:|---|---|---|
| 1 | `reserveDesignBatch()` | 설계안 수에 맞춰 `batch_size`, 결과 배열, 실행용 deck 파일을 준비한다 | 직접 구현 |
| 2 | `setSizeFromDesignBatch()` | 0~1의 설계 변수 값을 실제 회로 값으로 바꾼다 | 직접 구현 |
| 3 | `writeCircuit(folder)` | 지정 폴더에 `param_0`, `param_1`, …을 쓴다 | 직접 구현 |
| 4 | `renormalizeDesignBatch()` | 반올림 등으로 바뀐 실제 값을 다시 0~1로 환산해 `design_batch`에 반영한다 | 직접 구현 |
| 5 | `simulateCircuit(i)` → `evaluateSpec(i, folder)` | 각 설계안을 실행하고 spec을 읽는다 | spec 읽기 직접 구현 |
| 6 | `calculateFoM()` | 지정한 FoM 함수로 `fom_batch`를 계산한다 | 기본 구현 사용 |

N개 설계안에 대해 `design_batch`는 (N, design_dim), `spec_batch`는 (N, spec_dim) 크기여야 한다. `spec_batch[i]`는 `spec_names` 순서의 실수 값이며, 같은 행의 설계 변수는 실제 시뮬레이션한 값과 일치해야 한다.

기본 `simulateCircuit(i)`는 작업 폴더의 `0`, `1`, … 파일을 ngspice로 실행한다. 기본 최고 FoM 저장에는 `param_i`, `spec_i` 파일이 필요하다. deck 점검 기능을 제공하려면 `testDeck()`도 구현한다.
