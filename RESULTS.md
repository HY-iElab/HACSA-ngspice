# 결과 확인과 재사용

다음 명령의 최적화 결과는 `result_fc` 폴더에서 확인한다.

```bash
python hacsa.py sample_manual.json
```

`sample_manual.json`의 `run_name`은 `"fc"`이다. 기본 회로 `AutoCircuit`과 기본 저장소 [StoreParetoFront](#pareto-set을-저장하는-이유)를 기준으로 설명한다.

## 생성되는 폴더와 파일

보관할 설계안이 있을 때의 폴더 구조이다. 번호가 붙은 파일 수는 평가한 batch 크기와 보관한 설계안 수에 따라 달라진다.

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

| 파일 | 내용과 용도 |
|---|---|
| `sample_manual.json` | 탐색 범위, target, weight 등의 실행 설정 |
| `sample/deck_fc`, `sample/pdk` | 입력 deck과 그 deck이 include하는 모델 파일 |
| `temp_fc/pdk` | `deck_imports`에서 작업 폴더로 복사한 모델 파일 |
| `temp_fc/0`, `temp_fc/1`, ... | 입력 deck의 [실행용 복제본](#실행-중-파일이-만들어지는-과정). 확장자 없이 번호를 이름으로 사용한다 |
| `temp_fc/param_i` | batch의 i번째 설계안을 시뮬레이션할 parameter |
| `temp_fc/spec_i` | 해당 시뮬레이션에서 deck이 기록한 spec |
| `temp_fc/error/` | spec 파일을 만들지 못한 설계안의 param 파일을 보관하는 폴더 |
| `result_fc/best_param`, `result_fc/best_spec` | 최고 FoM을 얻은 설계안의 parameter와 spec. `best_spec` 마지막 줄에는 FoM도 기록한다 |
| `result_fc/param_i` | 최종 보관한 i번째 설계안의 parameter. CSV의 `idx`가 i인 행에 대응한다 |
| `result_fc/result_spec.csv` | 최종 보관한 설계안들의 [index, FoM, spec을 모은 표](#csv로-설계안-비교하기) |

작업 폴더 `temp_fc`는 batch마다 같은 번호를 재사용하므로 전체 평가 이력은 아니다. `result_fc`는 보관한 설계안에 새 번호를 붙인다. **`temp_fc/param_0`와 `result_fc/param_0`는 같은 설계안이라고 볼 수 없다.**

`best_param`·`best_spec`은 실행 중 최고 FoM 갱신 시, `result_fc/param_i`와 CSV는 최적화 완료 시 저장한다. 보관 기준을 통과한 설계안이 없으면 CSV에는 열 이름만 있고 `param_i`는 없다.

`run_name`이 `"fc"`이면 `temp_fc`·`result_fc`, 빈 문자열이면 `temp`·`result` 폴더를 쓴다. 같은 `run_name`으로 재실행하면 두 폴더를 교체하므로, 보관할 결과는 미리 다른 곳으로 복사한다.

저장한 설계안을 다시 시뮬레이션하려면, 사용할 deck에서 해당 `param_i` 또는 `best_param` 파일을 `.include`하고 SPICE로 직접 실행한다.

## CSV로 설계안 비교하기

`result_fc/result_spec.csv`를 스프레드시트 프로그램으로 연다(한 열로 읽히면 구분자를 쉼표로 지정한다). `sample/deck_fc`의 CSV 첫 행은 다음과 같다.

```csv
idx,fom,negative_total_current_uA,gain_db,log10_ugbw,pm_deg,cmrr_db
```

- `idx`: 같은 폴더의 `param_{idx}` 번호. 정렬 후에도 행 번호 대신 이 값으로 찾는다.
- `fom`: 설계안의 FoM(클수록 좋음). CSV는 FoM 순서로 정렬하지 않는다.
- 나머지 열: deck의 저장 순서대로 기록한 spec. 한 행이 한 설계안이다.

`fom`이나 관심 있는 spec으로 정렬해 후보를 고르고, 두 spec을 X·Y축으로 한 산점도로 관계를 살펴본다. 예를 들어 소비 전류·대역폭 산점도에서 대역폭을 높이는 데 필요한 전류를 확인한다.

CSV에는 deck에서 바꾼 부호와 단위가 그대로 저장된다. 위 열 순서에서 첫 데이터가 2행이면 다음 수식으로 물리량을 읽는다.

| 저장된 spec | 의미 | 새 열에 넣을 수식 |
|---|---|---|
| `negative_total_current_uA` | 전체 소비 전류의 부호를 반전한 값 | `=-C2`로 전류를 µA 단위로 읽는다 |
| `log10_ugbw` | Hz 단위 대역폭의 상용로그 | `=10^E2`로 대역폭을 Hz 단위로 읽는다 |

수식을 아래 행에도 적용해 두 열의 산점도를 만든다.

## Pareto set을 저장하는 이유

`StoreParetoFront`는 모든 spec이 `reject_spec` 이상인 설계안 중 Pareto set을 보관한다. 다른 설계안이 모든 spec에서 같거나 더 좋고, 하나 이상에서 더 좋으면 해당 설계안은 제외한다.

두 spec(gain, 대역폭)이 클수록 좋고, 저장 하한이 각각 50 dB, 5 MHz인 예시이다.

| 설계안 | Gain (dB) | 대역폭 (MHz) | 보관 여부 |
|---|---:|---:|---|
| A | 60 | 10 | 보관. B보다 대역폭이 높다 |
| B | 65 | 8 | 보관. A보다 gain이 높다 |
| C | 55 | 7 | 제외. A와 B보다 두 spec이 모두 낮다 |
| D | 45 | 15 | 제외. Gain이 저장 하한에 미달한다 |

A와 B는 gain·대역폭의 trade-off를 보여준다. 이런 후보만 남기면 많은 불필요한 parameter 파일을 살피지 않고 필요한 성능에 따라 설계안을 고를 수 있다. 모든 spec이 같으면 하나만 보관하며, 선별에는 FoM 대신 spec들을 사용한다.

`reject_spec`을 생략해도 Pareto 선별은 적용한다. `target_spec`은 FoM과 조기 종료에 쓰는 목표이며, 저장 하한인 `reject_spec`과 별개이다.

`best_param`·`best_spec`은 `reject_spec`과 무관하게 저장되므로, 해당 설계안이 CSV에 없을 수 있다.

## 실행 중 파일이 만들어지는 과정

입력 deck은 설계안마다 parameter·spec 경로를 바꿔 복제해 실행한다. batch의 0번째 설계안에 쓸 `temp_fc/0`의 치환 예시이다.

| 입력 deck | 실행용 복제본 `temp_fc/0` |
|---|---|
| `.include @PARAM_PATH@` | `.include param_0` |
| `> @SPEC_PATH@` | `> spec_0` |
| `>> @SPEC_PATH@` | `>> spec_0` |

`temp_fc/1`에서는 같은 자리에 `param_1`, `spec_1`을 쓴다. 복제본의 회로·해석 명령은 입력 deck에서 가져온다. `deck_imports`의 파일은 원래 이름으로 작업 폴더에 복사한다.

`param_i`의 형식 예시이다.

```spice
.param R0=10k
.param C0=100f
```

solver의 0~1 설계 변수는 `design_space`의 범위·간격에 맞는 실제 값으로 변환해 기록한다. ngspice는 deck의 `{R0}`, `{C0}` 등에 include한 `.param` 값을 사용한다. 변환 규칙은 [README의 Design Space 정의](README.md#design-space-정의)를 참고한다.

ngspice는 `temp_fc` 안에서 복제본을 실행하고, deck의 `echo` 명령으로 `spec_i`를 만든다. 다음은 spec 파일의 형식 예시이다.

```text
negative_total_current_uA -5.2
gain_db 60
```

`>`는 파일을 새로 쓰고, `>>`는 뒤에 줄을 붙인다. HACSA는 값들을 deck의 spec 저장 순서대로 읽어 FoM을 계산하고, 저장소에 설계 변수·spec·FoM을 전달한다. FoM은 `best_spec`과 결과 CSV에 별도로 기록된다.

spec 파일이 없으면 해당 param을 `error/param_0_3`처럼 실패 파일의 추가 순서와 batch 내 번호를 붙여 옮기고, spec을 `-1e10`으로 채운다.

최적화 후 보관한 설계 변수로 결과 폴더의 `param_i`를 만들고, 같은 번호의 spec·FoM을 CSV에 쓴다. 결과 폴더에는 설계안별 `spec_i` 대신 `result_spec.csv`를 저장한다.
