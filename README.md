# HACSA-ngspice

HACSA-ngspice는 ngspice 기반 analog circuit sizing용 Python interface이다.

## 설치

### ngspice

Windows에서는 [ngspice 다운로드 페이지](https://ngspice.sourceforge.io/download.html)에서 Windows 64-bit binary를 받아 압축을 풀고, `ngspice_con.exe`가 있는 폴더를 `PATH`에 추가한다. 새 PowerShell에서 설치를 확인한다.

```powershell
ngspice_con.exe -v
```

Debian/Ubuntu에서는 다음과 같이 설치·확인한다.

```bash
sudo apt update
sudo apt install ngspice
ngspice -v
```

### Python 의존성

Python 3.6.2 이상.

```bash
python -m pip install -r requirements.txt
```

## 실행

`hacsa.py`에 JSON 설정 파일을 전달한다.

```bash
python hacsa.py sample_manual.json
```

이 명령은 `sample/deck_fc`의 최적화 결과를 `result_0`에 저장한다. 실행 시작 시 기존 `temp_0`과 `result_0`은 교체된다.

### 설정 파일

target과 weight를 직접 지정한 설정 예제이다(`sample_manual.json` 참고).

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

- `run_name`: 실행 식별자. 빈 문자열이면 `temp`와 `result`, `"xxx"`이면 `temp_xxx`와 `result_xxx`.
- `deck_path`: deck 경로. 상대 경로는 `hacsa.py` 폴더 기준이며, 절대 경로도 지원.
- `deck_imports`: deck과 같은 실행 폴더에 복사할 파일 경로 목록. deck_fc의 `.include "pdk"`를 위해 `sample/pdk`를 지정한다. 여러 파일은 [ ] 안에 순서대로 나열하고, 보조 파일이 없으면 생략한다.
- `reject_spec`: 보관할 design의 spec 하한. 하나라도 미달하면 design을 제외한다(생략 시 필터 미적용). 기본 저장소는 통과한 design 중 Pareto set을 보관한다.
- `max_evals`: solver의 평가 종료 기준 횟수. batch 단위로 평가하므로 실제 횟수는 조금 넘을 수 있다.
- `early_stop`: target 달성 시 종료 여부(기본값 `false`).
- `target_spec`: 각 spec의 최소 목표값(생략 시 자동 설정).
- `pre_weight`: 하나라도 target 미달일 때 FoM에 적용할 양의 가중치.
- `post_weight`: 모든 target 달성 시 FoM에 적용할 양의 가중치. 두 weight 중 하나라도 생략하면 둘 다 자동 설정.
- `design_space`: deck의 설계 변수별 [탐색 범위](#design-space-정의). 배열 순서는 `[lower, upper, resolution, unit, is_log]`.

`reject_spec`, `target_spec`, `pre_weight`, `post_weight`는 모두 deck의 spec 저장 순서를 따른다(`sample/deck_fc`의 대응은 아래 표 참조).

| index | deck에 저장된 spec | `reject_spec` | `target_spec` | `pre_weight` | `post_weight` |
|---:|---|---:|---:|---:|---:|
| 0 | `negative_total_current_uA` | -100.0 | -5.2232 | 0.02 | 0.02 |
| 1 | `gain_db` | 0.0 | 38.2163 | 0.025 | 0.025 |
| 2 | `log10_ugbw` | 6.0 | 6.6529 | 0.5 | 0.5 |
| 3 | `pm_deg` | 40.0 | 60.0 | 0.015625 | 0.0 |
| 4 | `cmrr_db` | 40.0 | 70.4884 | 0.025 | 0.025 |

JSON에 추가할 수 있는 선택 항목이다.

- `solver`: [사용할 solver](#solver-선택)(기본값 `"CMAES"`).
- `auto_fom`: 자동 설정용 Sobol 표본 수의 지수(기본값 `7`). 표본 수는 `2^auto_fom`.
- `parallel`: ngspice의 design 평가 방식. `true`는 병렬(기본값), `false`는 순차 평가.
- `digits`: deck에 기록할 파라미터의 최대 소수 자릿수(기본값 `3`, 0.xxx). `resolution`이 `null`이면 탐색 간격은 `10**(-digits)`.

### Solver 선택

다른 solver를 사용하려면 JSON에 `solver`를 추가한다.

```json
"solver": "LSHADE"
```

기본 지원 solver와 기반 논문:

- `CMAES`: Nikolaus Hansen and Andreas Ostermeier, [*Adapting Arbitrary Normal Mutation Distributions in Evolution Strategies: The Covariance Matrix Adaptation*](https://doi.org/10.1109/ICEC.1996.542381), 1996.
- `LSHADE`: Ryoji Tanabe and Alex S. Fukunaga, [*Improving the Search Performance of SHADE Using Linear Population Size Reduction*](https://doi.org/10.1109/CEC.2014.6900380), 2014.
- `TuRBO`: David Eriksson, Michael Pearce, Jacob Gardner, Ryan D. Turner, Matthias Poloczek, [*Scalable Global Optimization via Local Bayesian Optimization*](https://proceedings.neurips.cc/paper/2019/hash/6c990b7aca7bc7058f5e98ea909e924b-Abstract.html), 2019.

`Solver` interface를 구현해 `Solver` 폴더에 두면 custom solver를 사용할 수 있다. 파일과 클래스 이름은 같아야 한다(`XXX.py` → `class XXX`).

### Target과 weight 자동 설정

입력한 target과 weight pair는 그대로 쓰고, 빠진 쪽만 ngspice로 Sobol 표본을 평가해 구한다.

| `target_spec` | `pre_weight`, `post_weight` | 동작 |
|---|---|---|
| 입력 | 둘 다 입력 | 자동 표본 평가 없음 |
| 생략 | 둘 다 입력 | target만 자동 설정 |
| 입력 | 하나 이상 생략 | 두 weight을 자동 설정 |
| 생략 | 하나 이상 생략 | target과 두 weight을 모두 자동 설정 |

`sample_auto.json`처럼 target과 weight를 모두 생략하면 자동 설정한 값을 FoM 튜닝의 시작점으로 쓸 수 있다.

```bash
python hacsa.py sample_auto.json
```

`sample_auto.json`은 다음과 같다.

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

`auto_fom`을 추가해 target·weight 자동 설정용 표본 수를 기본 $2^7 = 128$에서 바꾼다.

자동 계산은 각 spec의 측정 실패값만 제외하고 mean/min/max를 구한다. 같은 design의 다른 spec이 정상이면 그 값은 계산에 포함한다. 각 spec에는 정상 측정값이 하나 이상 필요하다.

세부 조정은 [tutorial.ipynb](tutorial.ipynb)를 참고한다.

## Deck 작성 규칙

`AutoCircuit`을 사용하려면 deck이 다음 규칙을 만족해야 한다.

### 1. Param 파일 include

```spice
.include @PARAM_PATH@
```

`@PARAM_PATH@`는 실행 중 `param_0`, `param_1`, ...로 치환된다.

### 2. 설계 변수 이름

튜닝할 설계 변수는 `{L0}`, `{W0}`, `{M0}` 형식으로 지정한다.

```spice
MN0 out in 0 0 nmos l={L0} w={W0} m={M0}
R0 out n1 {R0}
C0 n1 0 {C0}
```

이름 규칙은 다음과 같다.

- prefix는 영문자와 `_`의 조합이다: `L`, `W`, `M`, `R`, `C`, `_Aa_Bce_`, `AaaeE_FG`
- suffix는 `0`부터 시작하는 정수이다.
- 같은 prefix 안에서는 번호를 `L0`, `L1`, `L2`처럼 연속해서 붙인다.
- 변수가 하나여도 `R0`처럼 `0` suffix를 붙인다.

### 3. Spec 저장

모든 spec은 deck에서 계산하고 `@SPEC_PATH@`에 저장한다.

```spice
echo negative_total_current_uA $&negative_total_current_uA > @SPEC_PATH@
echo gain_db $&gain_db >> @SPEC_PATH@
echo log10_ugbw $&log10_ugbw >> @SPEC_PATH@
```

`AutoCircuit`은 이 순서대로 `negative_total_current_uA`, `gain_db`, `log10_ugbw`를 spec 이름으로 읽는다. `reject_spec`, `target_spec`, `pre_weight`, `post_weight`도 반드시 같은 순서를 사용한다.

`@SPEC_PATH@`는 실행 중 `spec_0`, `spec_1`, ...로 치환된다. SPICE가 spec 파일을 만들지 못하면 해당 design의 spec을 매우 작은 값으로 처리하고, param 파일을 temp 폴더의 `error`로 옮긴다.

모든 spec은 클수록 좋게 저장해야 한다. 작을수록 좋은 값은 deck에서 부호를 반전한다.

## 최소 예제

다음 deck은 설계 변수 `{R0}` 하나와 spec `gain_db` 하나를 갖는다.

```spice
.include @PARAM_PATH@

RLOAD out 0 {R0}

.control
let gain_db = 42.0
echo gain_db $&gain_db > @SPEC_PATH@
.endc
.end
```

이 deck에 대응하는 JSON 설정:

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

deck의 `{R0}`는 `design_space`의 `"R"`에 대응한다. `gain_db`는 유일한 spec이므로 네 spec 배열의 index 0에 대응하며 target은 40 dB이다.

## Design Space 정의

`design_space`는 각 설계 변수 prefix의 기본 범위와 필요한 개별 범위를 정의한다.

```json
"L": [180, 360, 5, "n", false]
```

배열의 의미는 `[lower, upper, resolution, unit, is_log]`이다.

- `lower`, `upper`: 실제 값의 하한과 상한
- `resolution`: 설계 변수 값의 허용 간격. `null`이어도 소수점 아래 `digits`자리까지만 표시된다.
- `unit`: param 파일의 값 뒤에 붙일 단위(없으면 `""`).
- `is_log`: log scale이면 `true`, linear scale이면 `false`. log scale의 하한과 상한은 양수여야 한다.

이 설정의 `L` 값은 `180n`, `185n`, `190n`, ..., `360n` 중 하나이다.

prefix 항목은 같은 prefix의 모든 설계 변수에 적용할 기본값이다. 개별 변수 항목은 해당 변수의 기본값만 덮어쓴다.

```json
"M": [1, 60, 1, "", false],
"M10": [30, 60, 1, "", false]
```

`M10`만 `30`~`60`, 나머지 `M` 변수는 `1`~`60`을 사용한다. deck의 각 prefix에는 기본 항목 또는 모든 개별 항목이 필요하다. deck에 없는 `design_space` 항목은 사용하지 않는다.

solver가 제안한 `[0, 1]` 범위의 값 `v`는 실제 값 `x`로 다음처럼 변환된다.

linear scale:

$$
x = \mathrm{lower} + v(\mathrm{upper} - \mathrm{lower})
$$

log scale:

$$
x = 10^{\log_{10}(\mathrm{lower}) + v(\log_{10}(\mathrm{upper}) - \log_{10}(\mathrm{lower}))}
$$

변환한 값은 `resolution`에 맞춰 반올림된다. `is_log`는 값의 범위를 바꾸지 않지만 solver 성능에는 영향을 줄 수 있다.

## FoM 정의

FoM은 `Solver`가 최대화하는 점수이다. 기본 FoM은 target 달성 전과 후를 나누어 계산한다.

target을 만족하지 못한 동안에는 부족분만 반영한다.

$$
\mathrm{pre\_FoM}
= \sum_i \min(\mathrm{spec}_i - \mathrm{target}_i, 0)
\times \mathrm{pre\_weight}_i
$$

모든 target을 만족한 design의 `pre_FoM`은 0이다. `early_stop`이 `true`가 아니면 이 design에 다음 점수를 적용한다.

$$
\mathrm{post\_FoM}
= \sum_i (\mathrm{spec}_i - \mathrm{target}_i)
\times \mathrm{post\_weight}_i
$$



독자적인 FoM 설계는 [ADVANCED_USE.md의 FoM Contract](ADVANCED_USE.md#fom-contract)를 참고한다.

## 결과 파일

결과는 `result_{run_name}` 디렉토리에 저장한다(`run_name`이 비면 `result`).

실행 중 best FoM과 함께 갱신되는 파일:

- `best_param`: FoM이 가장 큰 design의 parameter
- `best_spec`: 해당 design의 spec과 FoM

기본 저장소 `StoreParetoFront`는 모든 spec이 `reject_spec` 이상인 design 중 Pareto set을 result 디렉토리에 저장한다.

- `param_0`, `param_1`, ...: archive에 남은 design의 parameter
- `result_spec.csv`: 각 design의 index, FoM, spec

폴더·파일 구조, Pareto 선별 기준, CSV 성능 비교와 param 재실행은 [Results.md](Results.md)를 참고한다.

## 점검 항목

- deck에 `{L0}`가 있다면 `design_space`에 `"L"`이나 `"L0"` 항목이 있어야 한다.
- spec 저장 순서와 `reject_spec`, `target_spec`, `pre_weight`, `post_weight` 순서가 일치해야 한다.
- 수동 설정에서는 네 spec 배열의 길이가 deck에서 저장하는 spec 개수와 같아야 한다.
- 작을수록 좋은 spec은 deck에서 부호를 반전해야 한다.
- 같은 `run_name`의 기존 temp/result 폴더가 필요한지 확인한 뒤 실행한다.

solver·FoM·store 선택과 custom `Circuit`은 [ADVANCED_USE.md](ADVANCED_USE.md)를 참고한다.
