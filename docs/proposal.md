# 문서 개선 제안

이 문서는 앞서 제안한 다섯 가지 개선안을 검토하기 위한 자료이다. 각 제안에 국문·영문 파일의 현재 위치, 원문, 개선안을 함께 제시한다. 기존 문서에는 적용하지 않았다.

줄 번호는 이 문서를 작성한 시점의 파일 기준이며, 다른 제안을 적용하기 전의 위치이다. 아래 링크는 해당 절로 연결되고, 실제 교체 범위는 별도로 적은 줄 번호를 따른다. “원문”은 각 파일에 현재 적힌 내용이다.

## 위치 요약

| 제안 | 국문 위치 | 영문 위치 | 변경 범위 |
|---|---|---|---|
| 1. 자동 설정 규칙 | [README.md — Target과 weight 자동 설정](../README.md#ko-target과-weight-자동-설정), 112–119행 | [README_en.md — Automatic targets and weights](../README.md#en-automatic-targets-and-weights), 112–119행 | 도입문과 네 행의 동작 표를 하나의 문단으로 교체 |
| 2. 변수 번호 규칙 | [README.md — 2. 설계 변수 이름](../README.md#ko-2-설계-변수-이름), 176–178행 | [README_en.md — 2. Name the design variables](../README.md#en-2-name-the-design-variables), 176–178행 | suffix 관련 세 목록 항목을 한 항목으로 교체 |
| 3. Custom FoM 도입부 | [ADVANCED_USE.md — Custom FoM](ADVANCED_USE.md#ko-custom-fom), 111행 | [ADVANCED_USE_en.md — Custom FoM](ADVANCED_USE.md#en-custom-fom), 111행 | 도입 문단을 한 문장으로 교체 |
| 4. Pareto 선별 설명 | [RESULTS.md — Pareto set을 저장하는 이유](RESULTS.md#ko-pareto-set을-저장하는-이유), 88행 | [RESULTS_en.md — Why save the Pareto set?](RESULTS.md#en-why-save-the-pareto-set), 88행 | 첫 문단 교체 |
| 5. 구성 요소 표의 위치 | [ADVANCED_USE.md — Custom deck or specs](ADVANCED_USE.md#ko-custom-deck-or-specs), 247–254행 → 현재 11행 앞 | [ADVANCED_USE_en.md — Custom deck or specs](ADVANCED_USE.md#en-custom-deck-or-specs), 247–254행 → 현재 11행 앞 | 도입문과 표를 목차 뒤, 첫 절의 앵커 앞으로 이동 |

## 1. 자동 설정의 조합을 두 가지 규칙으로 설명

**이유:** 사용자는 target과 weight에 대한 규칙을 각각 적용하면 된다. 네 가지 조합을 나열한 표와 도입문을 합쳐 분량을 줄인다.

**보존할 정보:** 입력한 target의 유지, 생략한 target의 자동 설정, 두 weight의 동시 자동 설정, ngspice와 Sobol 표본의 사용, 세 배열을 모두 입력했을 때 표본 평가 생략.

### 국문

**위치:** [README.md — Target과 weight 자동 설정](../README.md#ko-target과-weight-자동-설정), **112–119행 전체**. 절 제목과 121행부터 이어지는 sample 설명은 유지한다.

**원문**

```markdown
입력한 target과 weight pair는 그대로 쓰고, 빠진 쪽만 ngspice로 Sobol 표본을 평가해 구한다.

| `target_spec` | `pre_weight`, `post_weight` | 동작 |
|---|---|---|
| 입력 | 둘 다 입력 | 자동 표본 평가 없음 |
| 생략 | 둘 다 입력 | target만 자동 설정 |
| 입력 | 하나 이상 생략 | 두 weight을 자동 설정 |
| 생략 | 하나 이상 생략 | target과 두 weight을 모두 자동 설정 |
```

**개선안**

```markdown
`target_spec`은 생략한 경우에만 자동 설정한다. `pre_weight`와 `post_weight`는 둘 다 입력하면 그대로 쓰고, 하나라도 생략하면 둘 다 자동 설정한다. 자동 설정에는 ngspice로 평가한 Sobol 표본을 사용하며, 세 배열을 모두 입력하면 이 평가를 생략한다.
```

### 영문

**위치:** [README_en.md — Automatic targets and weights](../README.md#en-automatic-targets-and-weights), **112–119행 전체**. 교체 범위는 국문과 같다.

**원문**

```markdown
Supplied targets and a complete pair of weight arrays are used as provided. Missing targets or weights are derived by evaluating Sobol samples with ngspice.

| `target_spec` | `pre_weight`, `post_weight` | Behavior |
|---|---|---|
| Provided | Both provided | No automatic sample evaluation |
| Omitted | Both provided | Set targets automatically |
| Provided | One or both omitted | Set both weight arrays automatically |
| Omitted | One or both omitted | Set targets and both weight arrays automatically |
```

**개선안**

```markdown
`target_spec` is set automatically only when omitted. `pre_weight` and `post_weight` are used as provided when both are supplied; otherwise, both are set automatically. Automatic settings use Sobol samples evaluated with ngspice. Supplying all three arrays skips this evaluation.
```

## 2. 변수 번호 규칙을 한 목록 항목으로 합치기

**이유:** 시작 번호, 연속성, 단일 변수의 규칙을 함께 설명하면 한 번에 이해할 수 있다.

**보존할 정보:** 정수 suffix, 시작 번호 0, prefix별 연속 번호, 단일 변수에도 번호가 필요하다는 조건, 기존 예시. 175행의 prefix 규칙은 유지한다.

### 국문

**위치:** [README.md — 2. 설계 변수 이름](../README.md#ko-2-설계-변수-이름), **176–178행**.

**원문**

```markdown
- suffix는 `0`부터 시작하는 정수이다.
- 같은 prefix 안에서는 번호를 `L0`, `L1`, `L2`처럼 연속해서 붙인다.
- 변수가 하나여도 `R0`처럼 `0` suffix를 붙인다.
```

**개선안**

```markdown
- 같은 prefix의 변수에는 `L0`, `L1`, `L2`처럼 0부터 연속된 정수 suffix를 붙인다. 변수가 하나여도 `R0`처럼 번호를 붙인다.
```

### 영문

**위치:** [README_en.md — 2. Name the design variables](../README.md#en-2-name-the-design-variables), **176–178행**.

**원문**

```markdown
- The suffix is an integer starting at `0`.
- Within each prefix, use consecutive numbers, such as `L0`, `L1`, and `L2`.
- Even a single variable needs the `0` suffix, as in `R0`.
```

**개선안**

```markdown
- Within each prefix, use consecutive integer suffixes starting at 0, as in `L0`, `L1`, and `L2`. Even a single variable needs a suffix, as in `R0`.
```

## 3. Custom FoM 도입부를 사용자가 할 행동으로 설명

**이유:** Python에서 함수를 값으로 지정할 수 있다는 설명을 실제 사용법에 포함하면 한 문장으로 충분하다.

**보존할 정보:** Python 함수를 사용한다는 점, 지정 위치가 `config["fom"]`이라는 점, 해당 함수로 FoM을 계산한다는 점. 뒤의 코드 예제와 함수 계약은 유지한다.

### 국문

**위치:** [ADVANCED_USE.md — Custom FoM](ADVANCED_USE.md#ko-custom-fom), **111행**.

**원문**

```markdown
Python에서는 함수도 저장 가능하다. `config["fom"]`은 FoM 함수를 저정한다. 
```

**개선안**

```markdown
`config["fom"]`에 Python 함수를 지정해 FoM 계산을 바꾼다.
```

### 영문

**위치:** [ADVANCED_USE_en.md — Custom FoM](ADVANCED_USE.md#en-custom-fom), **111행**.

**원문**

```markdown
Python allows you to store functions as values. Assign the FoM function to `config["fom"]`.
```

**개선안**

```markdown
Assign a Python function to `config["fom"]` to customize the FoM calculation.
```

## 4. Pareto 비교의 주어를 더 좋은 설계안으로 바꾸기

**이유:** 제외할 설계안이 얼마나 나쁜지를 설명하는 대신, 비교 대상이 얼마나 좋은지를 설명해 비교 방향을 쉽게 읽도록 한다.

**보존할 정보:** 모든 spec에 대한 `reject_spec` 하한, 모든 spec에서 같거나 더 좋고 하나 이상에서 더 좋은 설계안이 있을 때 제외한다는 조건, 남은 집합이 Pareto set이라는 점. 뒤의 예시 표, 같은 spec을 가진 설계안의 중복 제거, FoM과의 구분은 유지한다.

### 국문

**위치:** [RESULTS.md — Pareto set을 저장하는 이유](RESULTS.md#ko-pareto-set을-저장하는-이유), **88행**.

**원문**

```markdown
기본 저장소 `StoreParetoFront`는 평가한 설계안 중 모든 spec이 `reject_spec` 이상인 것만 남긴다. 그중 다른 설계안보다 모든 spec이 같거나 나쁘고 하나 이상 더 나쁜 설계안을 제외한다. 남은 집합이 저장할 Pareto set이다.
```

**개선안**

```markdown
`StoreParetoFront`는 모든 spec이 `reject_spec` 이상인 설계안 중 Pareto set을 보관한다. 다른 설계안이 모든 spec에서 같거나 더 좋고, 하나 이상에서 더 좋으면 해당 설계안은 제외한다.
```

### 영문

**위치:** [RESULTS_en.md — Why save the Pareto set?](RESULTS.md#en-why-save-the-pareto-set), **88행**.

**원문**

```markdown
The default store, `StoreParetoFront`, first retains only evaluated designs whose specs all meet or exceed `reject_spec`. It then excludes any design that is no better than another design in every spec and worse in at least one. The remaining designs form the Pareto set to save.
```

**개선안**

```markdown
`StoreParetoFront` retains the Pareto set of designs whose specs all meet or exceed `reject_spec`. A design is excluded if another is at least as good in every spec and better in at least one.
```

## 5. 구성 요소 표를 첫 코드 예제 앞으로 이동

**이유:** 사용자가 `Circuit`, `AutoCircuit`, `Solver`, `Store`의 역할을 먼저 알고 최적화 루프를 읽게 한다. 설명의 내용과 분량은 그대로 유지한다.

**이동 범위:** 표를 가리키는 도입문도 함께 옮겨 기존 위치에 “다음 요소”라는 문장만 남지 않게 한다. 각 파일의 **247–254행을 이동**하며, 복제하지 않는다.

**삽입 위치:** 목차가 끝나는 현재 9행 뒤이자, 첫 절의 앵커가 있는 **현재 11행 바로 앞**이다. 문단 사이에는 빈 줄을 둔다. 앵커와 절 제목은 유지한다.

### 국문

**출발 위치:** [ADVANCED_USE.md — Custom deck or specs](ADVANCED_USE.md#ko-custom-deck-or-specs), **247–254행**.

**도착 위치:** [ADVANCED_USE.md — Custom optimization loop](ADVANCED_USE.md#ko-custom-optimization-loop) 앞, **현재 11행의 `<a id="전체-실행-흐름"></a>` 바로 앞**.

**원문 — 이동할 도입문과 표**

```markdown
[hacsa.py](../hacsa.py)의 `run(config)` → `optimize(**config)`는 다음 요소를 연결한다.

| 구성 요소 | 역할 |
|---|---|
| `Circuit` | 설계 변수를 시뮬레이터 입력으로 바꾸고 spec과 FoM을 계산한다 |
| `AutoCircuit` | README의 deck 규칙에 맞춰 구현된 `Circuit`이다 |
| `Solver` | 평가할 설계안을 제안하고 점수를 받아 탐색을 진행한다 |
| `Store` | 평가 결과를 보관하고 파일로 저장한다 |
```

**개선안 — 목차 다음에 들어갈 내용과 이어지는 첫 절**

```markdown
[hacsa.py](../hacsa.py)의 `run(config)` → `optimize(**config)`는 다음 요소를 연결한다.

| 구성 요소 | 역할 |
|---|---|
| `Circuit` | 설계 변수를 시뮬레이터 입력으로 바꾸고 spec과 FoM을 계산한다 |
| `AutoCircuit` | README의 deck 규칙에 맞춰 구현된 `Circuit`이다 |
| `Solver` | 평가할 설계안을 제안하고 점수를 받아 탐색을 진행한다 |
| `Store` | 평가 결과를 보관하고 파일로 저장한다 |

<a id="전체-실행-흐름"></a>

## Custom optimization loop

다음은 사용자가 `Solver/MySolver.py`를 [구현](#custom-solver)했다고 가정한 예제이다. (코드는 프로젝트 폴더에서 실행한다)
```

**개선안 — 기존 위치에서 도입문과 표를 옮긴 뒤의 내용**

```markdown
## Custom deck or specs

기본 실행은 `AutoCircuit`을 생성한다. 다른 `Circuit`을 쓰려면 객체 생성과 최적화 루프를 Python으로 작성한다.

[Circuit](../Instance/Circuit.py)을 상속하고 생성자에서 설계 변수 수 `design_dim`과 spec 이름·순서 `spec_names`를 정한다. FoM 함수를 `fom`으로 받아 부모 생성자에도 전달한다.
```

### 영문

**출발 위치:** [ADVANCED_USE_en.md — Custom deck or specs](ADVANCED_USE.md#en-custom-deck-or-specs), **247–254행**.

**도착 위치:** [ADVANCED_USE_en.md — Custom optimization loop](ADVANCED_USE.md#en-custom-optimization-loop) 앞, **현재 11행의 `<a id="overall-workflow"></a>` 바로 앞**.

**원문 — 이동할 도입문과 표**

```markdown
In [hacsa.py](../hacsa.py), `run(config)` → `optimize(**config)` connects the following components.

| Component | Role |
|---|---|
| `Circuit` | Converts design variables to simulator inputs and computes specs and the FoM |
| `AutoCircuit` | Implements `Circuit` according to the deck requirements in the README |
| `Solver` | Proposes designs to evaluate and uses their scores to guide the search |
| `Store` | Retains evaluation results and saves them to files |
```

**개선안 — 목차 다음에 들어갈 내용과 이어지는 첫 절**

```markdown
In [hacsa.py](../hacsa.py), `run(config)` → `optimize(**config)` connects the following components.

| Component | Role |
|---|---|
| `Circuit` | Converts design variables to simulator inputs and computes specs and the FoM |
| `AutoCircuit` | Implements `Circuit` according to the deck requirements in the README |
| `Solver` | Proposes designs to evaluate and uses their scores to guide the search |
| `Store` | Retains evaluation results and saves them to files |

<a id="overall-workflow"></a>

## Custom optimization loop

This example assumes that you have [implemented](#custom-solver) `Solver/MySolver.py`. Run the code from the project folder.
```

**개선안 — 기존 위치에서 도입문과 표를 옮긴 뒤의 내용**

```markdown
## Custom deck or specs

The default workflow creates an `AutoCircuit`. To use a different `Circuit`, write the object initialization and optimization loop in Python.

Subclass [Circuit](../Instance/Circuit.py) and set the number of design variables, `design_dim`, and the spec names and order, `spec_names`, in the constructor. Accept the FoM function as `fom` and pass it to the parent constructor.
```
