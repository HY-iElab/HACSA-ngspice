# HACSA-ngspice

HACSA-ngscpie는 ngspice로 analog circuit sizing을 실행하기 위한 Python interface이다.

## 설치

### ngspice

Windows에서는 [ngspice 다운로드 페이지](https://ngspice.sourceforge.io/download.html)에서 Windows 64-bit binary를 내려받아 압축을 푼 뒤, `ngspice_con.exe`가 있는 폴더를 `PATH`에 추가한다. 새 PowerShell에서 다음 명령으로 설치를 확인한다.

```powershell
ngspice_con.exe -v
```

Linux(Debian/Ubuntu)에서는 다음 명령으로 설치와 확인을 한다.

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

## 준비 항목

기본 사용 경로는 `AutoCircuit`이다. `AutoCircuit`은 spice deck에서 설계 변수와 spec 이름을 읽고, optimizer가 제안한 normalized design vector를 spice가 실행할 수 있는 param 파일로 변환한다.

일반적인 사용에서는 `Solver`나 `Circuit` class를 수정할 필요가 없다.

## 실행

```bash
python main.py
```


## 기본 설정

`main.py`의 기본 설정 흐름은 다음과 같다.

```python
from Instance.AutoCircuit import AutoCircuit

run_name = 0
circuit = AutoCircuit(run_name=run_name, deck_path="path/to/deck", parallel=True, digits=3)
```

- `run_name`: 실행 중 생성되는 임시 폴더 이름에 붙일 실행 식별자. 빈 문자열이면 `temp`, `run_name=0`이면 `temp_0`, `run_name="test"`이면 `temp_test`를 사용. 
- `deck_path`: deck 파일의 경로. main.py를 기준으로 하는 상대경로와 절대경로 둘 다 가능.
- `deck_imports`: deck이 실행되기 위해 같은 폴더에 있어야 하는 파일들의 경로. 예를 들어 deck이 `.include "pdk"`를 사용하려면, 같은 폴더의 `pdk` 파일이 `deck_imports`에 지정되어야 한다. (그런 제약이 없다면 생략.)
- `parallel`: `True`이면 batch의 design들을 thread pool에서 병렬로 평가하고, `False`이면 하나씩 순차 평가한다. 기본값은 `True`이다.
- `digits`: 설계변수가 param 파일에 기록되는 유효숫자이다. 기본값은 `3`이다.

`AutoCircuit`은 시작 시 기존 임시 폴더를 지우고 새로 만든다. 임시 폴더의 `error`에는 SPICE가 해당 param의 netlist를 정상적으로 측정하지 못했을 때 그 param 파일이 이동한다. 이는 HACSA 오류가 아니라 SPICE 측정 실패 기록이다.


```python
circuit.setTargetSpec([-5.2232, 38.2163, 6.6529, 60.0])
circuit.setPreWeight([1 / 50.0, 1 / 40.0, 1 / 2.0, 1 / 64.0])
circuit.setPostWeight([1 / 50.0, 1 / 40.0, 1 / 2.0, 0.0])
circuit.setDesignSpace({
    # Design Space: (lower, upper, resolution, unit, is_log)
    "I": (1.0, 5.0, None, "u", True),
    "R": (1.0, 1e3, None, "k", True),
    "C": (10, 1000, None, "f", False),
    "L": (180, 360, 5, "n", False),
    "W": (45, 90, 5, "n", False),
    "M": (1, 60, 1, "", False),
})
# circuit.autoFoM(k=7, target=False)
# circuit.testDeck()
```

- `setTargetSpec(...)`: 각 spec의 최소 충족 값 (target)을 정한다. Spec의 순서는 deck에서 spec을 저장한 순서와 같다.
- `setPreWeight(...)`: target을 만족하지 못한 design을 평가할 spec별 가중치를 설정.
- `setPostWeight(...)`: target을 만족한 design에 대한 spec별 가중치를 설정.
- `setDesignSpace(...)`: deck의 설계 변수별 `(lower, upper, resolution, unit, is_log)`를 설정. (자세한 내용은 [여기에](#design-space-정의))
- `testDeck()`: 모든 normalized parameter가 `lowwer`인 netlist와 `upper`인 netlist를 만들고 spice를 수행한다. 디버깅용 함수.

### 자동 가중치 & target 설정

`setDesignSpace(...)` 뒤 `autoFoM(k)`를 호출하면 `2**k`개의 Sobol 표본을 시뮬레이션하여 pre/post weight를 자동 설정한다. 기본값 `target=True`는 설정된 target을 사용하고, `target=False`는 표본 평균을 target으로 설정한다. 이 함수를 통해 얻은 weight과 target은 custom weight, target의 기준점으로 사용할 수 있다.

## Deck 작성 규칙

`AutoCircuit`을 사용하려면 deck이 다음 규칙을 만족해야 한다.

### 1. Param 파일 include

```spice
.include @PARAM_PATH@
```

실행 중 `@PARAM_PATH@`는 `param_0`, `param_1` 등의 파일 이름으로 치환된다.

### 2. 설계 변수 이름

튜닝할 설계 변수는 `{L0}`, `{W0}`, `{M0}` 형식으로 지정한다.

```spice
MN0 out in 0 0 nmos l={L0} w={W0} m={M0}
R0 out n1 {R0}
C0 n1 0 {C0}
```

이름 규칙은 다음과 같다.

- prefix는 영문자와 `_`의 임의 조합이다: `L`, `W`, `M`, `R`, `C`, `_Aa_Bce_`, `AaaeE_FG`
- suffix는 `0`부터 시작하는 정수이다.
- 같은 prefix 안에서는 번호를 `L0`, `L1`, `L2`처럼 연속해서 붙인다.
- 변수가 하나만 있는 경우에도 `R0`처럼 `0` suffix를 붙인다.

### 3. Spec 저장

모든 spec은 deck에서 직접 계산하고 `@SPEC_PATH@`에 저장하게 작성한다.

```spice
echo negative_total_current_uA $&negative_total_current_uA > @SPEC_PATH@
echo gain_db $&gain_db >> @SPEC_PATH@
echo log10_ugbw $&log10_ugbw >> @SPEC_PATH@
```

`AutoCircuit`은 위 deck으로부터 `negative_total_current_uA`, `gain_db`, `log10_ugbw`를 spec 이름으로 읽는다. `setTargetSpec`, `setPreWeight`, `setPostWeight`의 값도 이 순서를 따른다.

실행 중 `@SPEC_PATH@`는 `spec_0`, `spec_1` 등의 파일 이름으로 치환된다.

모든 spec은 클수록 좋은 값으로 저장해야 한다. 작을수록 좋은 값은 deck에서 부호를 반전하여 저장한다.

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

이에 대응하는 `main.py` 설정은 예시는 다음과 같다.

```python
circuit.setTargetSpec([40.0])
circuit.setPreWeight([1 / 40.0])
circuit.setPostWeight([0.0])
circuit.setDesignSpace({
    "R": (1.0, 100.0, 1.0, "k", True),
})
```

대응 관계는 다음과 같다.

- deck의 `{R0}`는 `setDesignSpace`의 `"R"`에 대응.
- deck의 `echo gain_db ...`와 `setTargetSpec([40.0])`는 `gain_db`의 target 값을 40 dB로 설정. 
- spec이 여러 개이면 deck에서 저장한 순서와 target/pre-weight/post-weight 순서를 동일하게 맞춘다.

## Design Space 정의

`setDesignSpace`는 각 설계 변수 prefix의 기본 범위와 필요한 개별 범위를 정의한다.

```python
"L": (180, 360, 5, "n", False)
```

tuple의 의미는 `(lower, upper, resolution, unit, is_log)`이다.

- `lower`, `upper`: 실제 값의 하한과 상한
- `resolution`: 실제 값의 허용 간격. `None`이면 위 `AutoCircuit` 생성자에서 설정한 `10**(-digits)`를 사용한다.
- `unit`: param 파일에서 값 뒤에 붙일 단위 문자열. 없으면 `""`
- `is_log`: log scale이면 `True`, linear scale이면 `False`

예를 들어 위 설정은 `L` 값을 `180n`, `185n`, `190n`, ..., `360n` 중 하나로 사용한다는 뜻이다.

prefix만 적은 항목은 같은 종류의 모든 설계 변수에 적용되는 기본값이다. 특정 설계 변수의 전체 이름을 추가하면 그 변수만 기본값을 덮어쓴다.

```python
circuit.setDesignSpace({
    "M": (1, 60, 1, "", False),
    "M10": (30, 60, 1, "", False),
})
```

위 설정에서는 `M10`만 `30`부터 `60`까지 사용하고, 나머지 `M` 변수는 `1`부터 `60`까지 사용한다. deck에 없는 이름은 오류 없이 무시되므로, 개별 이름을 deck과 정확히 맞춰야 한다.

solver가 제안하는 값 `v`는 항상 `[0, 1]` 범위이다. 실제 값 `x`는 다음과 같이 변환된다.

linear scale:

$$
x = \mathrm{lower} + v(\mathrm{upper} - \mathrm{lower})
$$

log scale:

$$
x = 10^{\log_{10}(\mathrm{lower}) + v(\log_{10}(\mathrm{upper}) - \log_{10}(\mathrm{lower}))}
$$

그 뒤 실제 값은 `resolution`에 맞는 값으로 반올림된다. `resolution=None`이면 param 파일에는 `digits` 자리까지 기록된다.

## FoM 정의

FoM은 `Solver`가 최대화하는 점수이다. 따라서 FoM이 클수록 좋은 회로가 되게 FoM을 설계해야 한다.
HACSA에서 기본제공하는 FoM은 다음과 같다:

`pre_FoM`은 target에 대한 부족분만 점수에 반영한다.

$$
\mathrm{pre\_FoM}
= \sum_i \min(\mathrm{spec}_i - \mathrm{target}_i, 0)
\times \mathrm{pre\_weight}_i
$$

`post_FoM`은 target이 모두 충족한 design에만 적용한다.

$$
\mathrm{post\_FoM}
= \sum_i (\mathrm{spec}_i - \mathrm{target}_i)
\times \mathrm{post\_weight}_i
$$

target 자체가 최종 design goal이고 달성 후 별도 최적화가 필요하지 않다면 `post_weight`를 설정하지 않고 `pre_FoM`만 사용해도 된다.

기본 `main.py`는 target을 모두 달성한 design을 찾으면 반복을 끝낸다. 그 후에도 사용하려면 `if store.isTargetAcheived(): break`를 주석처리해야 한다.


## FoM 설계 팁

`Circuit.py`의 `Circuit.calculateFoM()`에서 FoM을 수정할 수 있다.

`self.spec_batch`의 각 행은 하나의 design이고, 각 열은 하나의 spec이다. 열 순서는 deck에서 spec을 저장한 순서이며, `setTargetSpec()`, `setPreWeight()`, `setPostWeight()`의 입력 순서도 이와 같다.

다음은 LDO spec을 `[-T_R, -I_Q, I_LOAD_MAX]` 순서로 저장했다고 가정한 예이다. $T_R$과 $I_Q$는 작을수록 좋으므로 부호를 반대로 저장했다. 따라서 세 spec 모두 값이 클수록 좋은 방향이 된다.

$$
\mathrm{LDO\_FoM}
= \frac{T_R \times I_Q}{I_{\mathrm{LOAD\_MAX}}}
$$

이 FoM은 작을수록 좋으므로, target을 만족한 design에는 그 역수를 최적화 점수로 사용한다. `calculateFoM()`은 다음과 같이 작성할 수 있다.

```python
def calculateFoM(self):
    self.fom_batch = np.minimum(
        self.spec_batch - self.target_spec, 0.0
    ) @ self.pre_weight

    target_met = self.fom_batch == 0.0
    negative_t_r = self.spec_batch[target_met, 0]
    negative_i_q = self.spec_batch[target_met, 1]
    i_load_max = self.spec_batch[target_met, 2]

    ldo_fom = negative_t_r * negative_i_q / i_load_max
    self.fom_batch[target_met] = 1.0 / ldo_fom
```

`target_met`은 `pre_FoM`이 0인 행을 선택한다. 따라서 `self.spec_batch[target_met, 0]`, `self.spec_batch[target_met, 1]`, `self.spec_batch[target_met, 2]`는 선택된 모든 design의 `-T_R`, `-I_Q`, `I_LOAD_MAX`를 각각 가져온다. `-T_R`과 `-I_Q`를 곱하면 $T_R \times I_Q$가 되며, 이 연산은 선택된 모든 design에 한 번에 적용된다.

# FoM sentinel
만약 한 spec이라도 정상적으로 얻어지지 않았을 경우 그 design의 fom값은 Solver.tell(..., sentinel=-1e-3)에 의해 sentinel로 치환된다. sentinel값은 어떤 정상적인 fom보다 더 작지만, 정상적인 fom의 범위에서 너무 멀어지면 solver의 성능이 감소하 수 있다. 반대로 너무 크면 spec을 정상적으로 구할 수 없는 설계가 정상적인 설계보다 선호될 수도 있다. CMAES는 작은 sentinel의 값에 상대적으로 덜 민감하다.

## 결과 파일

실행 중 best FoM이 갱신되면 result 폴더에 다음 파일이 저장된다.

- `best_param`: FoM이 가장 큰 design의 parameter값을 보관
- `best_spec`: 그 design의 spec과 FoM을 보관

정상 종료 시 `store.saveArchive(circuit)`은 archive에 남은 design들을 저장한다.

- `param_0`, `param_1`, ...: 저장된 design의 param 파일
- `result_spec.csv`: 각 design의 FoM과 spec

현재 main.py는 design들의 [Pareto set](https://ko.wikipedia.org/wiki/%EA%B3%84%EC%95%BD_%EA%B3%A1%EC%84%A0)을 저장하고 있다.

## 점검 항목

- deck에 `{L0}`가 있다면 `setDesignSpace`에 `"L"` 항목이나 `"L0"` 항목이 있어야 한다.
- spec 저장 순서와 `setTargetSpec`, `setPreWeight`, `setPostWeight` 순서가 일치해야 한다.
- 작을수록 좋은 spec은 deck에서 부호를 반전해야 올바르게 Pareto set이 저장된다.
- FoM이 클수록 좋은 design이 되게 설계해야 된다.
- Windows에서 ngspice 실행 파일 경로가 `PATH`에 등록되어 있어야 한다. 또는 `ngspice_con.exe`의 경로를 Circuit.simulator에 등록하면 된다.

고급 확장이 필요한 경우 `philosophy.md`를 참고하여 `MyCircuit` 또는 `Store`를 직접 구성한다.
