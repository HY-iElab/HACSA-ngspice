# Design Philosophy

이 문서는 HACSA prototype의 내부 구조와 확장 원칙을 설명한다. 일반 사용자는 `README.md`의 `AutoCircuit` 사용 절차를 먼저 참고한다.

핵심 원칙은 계층별 책임 분리이다. high-level workflow는 optimizer, circuit adapter, result store를 연결하지만, 각 계층의 내부 책임을 대신 수행하지 않는다.

## 계층별 책임

`Circuit`은 HACSA와 spice simulator 사이의 adapter이다. normalized design vector를 simulator 입력으로 변환하고, simulator 결과를 `spec_batch`와 `fom_batch`로 변환한다.

`AutoCircuit`은 deck 기반 `Circuit` 구현이다. 사용자 입력 규칙은 `README.md`가 담당하며, 이 문서는 해당 입력이 내부 계층으로 연결되는 방식만 다룬다.

`Solver`는 optimization algorithm의 interface이다. public interface는 `ask()`와 `tell(x, fitness)`이다. solver는 simulator 실행 방식이나 결과 저장 형식에 의존하지 않는다.

`Store`는 결과 저장 정책을 담당한다. `StoreParetoFront`는 현재 제공되는 Pareto-front store 구현이다.

## 데이터 흐름

한 iteration의 흐름은 다음과 같다.

1. `solver.ask()`가 normalized candidate batch를 만든다.
2. workflow가 candidate batch를 `circuit.design_batch`에 할당한다.
3. `circuit.evaluateDesign()`이 simulator를 실행하고 `spec_batch`, `fom_batch`를 만든다.
4. `store.updateArchive(...)`가 저장 정책에 따라 design을 보관한다.
5. `solver.tell(circuit.design_batch, circuit.fom_batch)`가 평가 결과를 optimizer에 전달한다.

이 흐름을 유지하면 solver, circuit, store를 독립적으로 교체할 수 있다.

## Temp Folder and Param Files

`Circuit`은 simulator 입출력을 실행 중 생성하는 temp folder 안에서 처리한다. `run_name`이 없으면 `temp`, 있으면 `temp_{run_name}`을 사용한다. 이 폴더는 미리 만들 필요가 없으며, 생성 시 같은 이름의 기존 폴더를 삭제한 뒤 다시 생성한다.

deck이 보조 파일을 참조할 때만, deck과 같은 폴더에 있는 파일의 경로를 `deck_imports`로 명시한다. 지정한 각 파일은 파일명으로 temp folder에 복사된다. 예를 들어 `.include "pdk"`를 사용하면 같은 폴더의 `pdk` 파일이 `deck_imports`에 지정되어 있어야 한다. 보조 파일이 없으면 `deck_imports`를 생략한다.

현재 구현은 원본 deck 파일 자체를 temp folder에 그대로 복사하지 않는다. `reserveDesignBatch()`가 `deck_path`의 prototype deck을 읽고, batch index별 deck 파일을 temp folder에 생성한다.

prototype deck이 다음 placeholder를 포함하는 경우를 예로 든다.

```spice
.include @PARAM_PATH@
echo gain_db $&gain_db > @SPEC_PATH@
```

batch index `0`의 temp deck은 다음 형태로 생성된다.

```spice
.include param_0
echo gain_db $&gain_db > spec_0
```

이 deck 파일은 `temp/0` 또는 `temp_{run_name}/0`에 저장된다. 기본 `simulateCircuit(0)`은 temp folder에서 `<simulator> -b 0`을 실행한다.

이 구조의 목적은 batch별 deck 구조를 준비해 두고, evaluation마다 `param_0`, `param_1`, ... 파일만 다시 작성하는 것이다. `AutoCircuit.writeCircuit()`은 solver가 제안한 design batch를 해당 param 파일들로 저장한다.

## Custom Circuit Contract

`Instance/MyCircuit.py`를 작성할 때는 `Instance/Circuit.py`의 `Circuit`을 상속한다. 예시는 `Instance/MyCircuitSample.py`이다. `__init__`에서는 `spec_names`와 `design_dim`을 정의한 뒤 부모 생성자를 호출한다.

기본 `Circuit.evaluateDesign()`은 다음 method를 사용한다.

- `setSizeFromDesignBatch()`: `self.design_batch`의 normalized 값을 실제 회로 parameter로 변환한다.
- `writeCircuit(folder)`: batch의 각 design을 `param_0`, `param_1`, ... 파일로 저장한다.
- `evaluateSpec(i, folder)`: simulator 결과를 읽어 `self.spec_batch[i]`에 저장한다.

`Circuit.evaluateDesign()`은 위 method들을 호출한 뒤 FoM을 계산한다. 따라서 custom circuit은 solver나 store의 내부 구현에 의존하지 않는다.

최소 구현 예시는 다음과 같다.

```python
import os
import numpy as np
from .Circuit import Circuit


class MyCircuit(Circuit):
    def __init__(self, deck_path, run_name="", deck_imports=()):
        spec_names = ("gain_db", "pm_deg")
        design_dim = 2
        super().__init__(design_dim, spec_names, run_name=run_name, deck_path=deck_path, deck_imports=deck_imports)

    def setSizeFromDesignBatch(self):
        size = self.design_batch[: self.batch_size]
        self.r = 10.0 ** (size[:, 0] * 3.0 + 3.0)
        self.c = 10.0 + size[:, 1] * 90.0

    def writeCircuit(self, folder):
        for i in range(self.batch_size):
            with open(os.path.join(folder, f"param_{i}"), "w") as file:
                file.write(f".param R0={self.r[i]:.3f}\n")
                file.write(f".param C0={self.c[i]:.3f}f\n")

    def evaluateSpec(self, i, folder):
        self.spec_batch[i] = np.loadtxt(
            os.path.join(folder, f"spec_{i}"),
            dtype=np.float64,
            usecols=1,
            max_rows=self.spec_dim,
            ndmin=1,
        )
```

## Custom Circuit Invariants

custom `Circuit` 구현은 다음 조건을 유지해야 한다.

- `self.design_batch` shape은 `(batch_size, design_dim)`이다.
- `self.spec_batch[i]`에는 `spec_dim`개의 float 값이 들어간다.
- `writeCircuit(folder)`는 simulator deck이 include할 param 파일을 생성한다.
- `evaluateSpec(i, folder)`는 `self.spec_names`와 같은 순서로 spec을 채운다.

## FoM Boundary

FoM 공식은 `README.md`의 사용자 설명에 둔다. 개발자 관점에서 중요한 점은 FoM 계산 책임이 `Circuit.calculateFoM()`에 있다는 것이다.

custom `Circuit`은 `spec_batch`를 채운다. `target_spec`, `pre_weight`, `post_weight`는 기존 setter가 채운다. `Solver`는 계산이 끝난 `fom_batch`를 소비하며 spec을 해석하거나 FoM을 다시 계산하지 않는다. `Store`는 archive 정책을 위해 `spec_batch`를 비교할 수 있지만 FoM을 다시 계산하지 않는다.

새로운 FoM 정책이 필요하면 `Circuit.calculateFoM()`의 책임으로 변경한다. 개별 solver나 store에 동일한 계산을 복사하지 않는다.

## Custom Store Contract

`Store/MyStore.py`를 작성할 때는 `Store/Store.py`의 `Store`를 상속한다. 핵심 method는 `updateArchive(design_batch, spec_batch, fom_batch)`이다.

생성자를 변경하는 경우 `super().__init__(design_dim, spec_dim, reject_spec, temp_folder, run_name)`을 호출해 기본 container와 result folder를 준비한다.

기본 `Store.saveArchive(circuit)`를 그대로 사용하려면 custom store는 다음 상태를 유지해야 한다.

- `self.size`: 저장된 design 개수
- `self.design_container[:self.size]`: 저장된 design vectors
- `self.spec_container[:self.size]`: 저장된 specs
- `self.fom_container[:self.size]`: 저장된 FoMs

container 공간이 부족하면 `expandContainer()`를 호출해 확장한다. 비동기 저장을 사용하는 경우 `saveArchive()` 전에 pending 작업을 완료해야 한다. `StoreParetoFront.saveArchive()`가 이 패턴을 따른다.

`updateBestFoM(fom_batch)`와 `isTargetAcheived()`는 기본 구현을 사용할 수 있다. `updateBestFoM`은 현재 batch의 `param_i`, `spec_i`를 result folder의 `best_param`, `best_spec`으로 복사한다.

모든 reject 기준을 통과한 design을 저장하는 단순한 store 예시는 다음과 같다.

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

## Documentation Boundary

입력 제약과 사용 규칙은 `README.md`의 책임이다. 이 문서는 동일한 규칙을 반복하지 않고, 해당 규칙을 구현하는 계층의 책임만 설명한다.

사용 문서는 사용자가 다음 행동을 결정하는 데 필요한 정보만 남긴다. 설정 설명은 해당 코드나 설정 바로 뒤에 두고, 값의 의미와 실행 결과를 함께 밝힌다. 사용자의 선택에 영향을 주지 않는 구현 과정, 일반론, 이미 설명한 내용의 재진술은 넣지 않는다.

- `AutoCircuit`의 parsing contract가 변경되면 `README.md`의 사용 설명도 함께 변경한다.
- custom `Circuit`은 `spec_names`, `spec_batch`, `target_spec`, `pre_weight`, `post_weight`의 순서를 일관되게 유지한다.
- 잘못된 입력을 조용히 보정하는 fallback은 계층 경계를 흐리므로 추가하지 않는다.

## Extensibility

새 store를 추가할 때는 `Store`의 archive 상태 계약을 따른다. 이 세 경계를 유지하면 각 부분을 독립적으로 교체할 수 있다.
