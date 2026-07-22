# THEDAP_MIXOPTIM 인수인계 문서 — 최적화 방법론

본 문서는 `THEDAP_MIXOPTIM` 모듈의 최적화 로직을 인수인계 드리기 위해 작성하였습니다. 먼저 결론부터 말씀드리면, 이 모듈은 **자체적으로 예측 모델을 학습하는 구조가 아닙니다.** `THEDAP_SIMULATION.DapPhase5_v5`(도달률 시뮬레이터, 내부적으로 도달 중복 보정에 코퓰러 기반 모델을 사용)를 **블랙박스 목적함수**로 두고, 그 위에서 예산 배분이라는 결정변수를 탐색하는 **수치 최적화 계층**으로 이해해 주시면 됩니다.

분류 기준은 `DapMixOptimizer.py`의 진입점인 **`opt_type`** 값입니다. `opt_type`에 따라 내부적으로 호출되는 클래스와 알고리즘이 완전히 다르므로, 아래에서 `opt_type`별로 나누어 정리하였습니다.

```python
if self.opt_type == 'reach_max':
    optimizer_ = DapOptPhase3(...)
    self.op, self.fr = optimizer_.opt_phase2(...)

elif self.opt_type == 'reach_target':
    optimizer_ = DapOptPhase3(...)
    self.op, self.fr = optimizer_.opt_phase3(...)

elif self.opt_type == 'reach_spectrum':
    optimizer_ = DapSpecPhase1(...)
    self.plot, self.spec = optimizer_.spec_phase1(...)
```

---

## 1. `opt_type = 'reach_max'` — 예산 상한 내 도달률 최대화

**호출 경로**: `DapOptPhase3.opt_phase2()` (상속 체인상 `DapOptPhase1 → DapOptPhase2 → DapOptPhase3`이지만, 실제로는 부모 클래스인 `DapOptPhase2.opt_phase2()`를 그대로 사용합니다.)

정해진 최대예산(`opt_maxbudget`) 안에서, 예산 구간을 나누어가며 각 구간마다 "도달률을 최대화하는 매체 배분"을 구하는 방식입니다. 목표 도달률을 역산하는 `reach_target`과 달리, **예산 → 도달률 방향의 단방향 탐색**이라는 점이 핵심 차이입니다.

- **바깥 루프 (`DapOptPhase2.opt_phase2`)**: 최대예산을 `opt_seq` 등분한 `linspace(0, maxbudget, seq+1)` 구간마다 아래 안쪽 최적화를 독립적으로 반복 실행합니다. 그 결과로 **예산 대비 도달률의 한계효용 체감(diminishing returns) 곡선**을 생성합니다.
- **안쪽 최적화 (`DapOptPhase1.get_reach_max`)**: 각 예산 구간에서 매체별 배분 비율을 `scipy.optimize.minimize`의 **SLSQP(Sequential Least Squares Programming)** 로 구합니다.
  - 결정변수: 매체(라인)별 배분 비율 `ratios` (합 1로 정규화)
  - 목적함수: `-target_reach_p` (도달률 최대화 → 최소화 문제로 치환). 내부에서 매번 `summary_total()` 시뮬레이터를 호출하는 블랙박스 함수라 해석적 미분이 없고, `eps` 파라미터로 **유한차분 근사 그래디언트**를 사용합니다.
  - 제약조건: `sum(ratios) == 1`, 경계조건: 라인별 `min_rat` ~ `1.0`
  - 안정화 장치: 예외 발생 시 직전 최고 도달률의 80%를 반환하는 페널티 fallback, `min_rat` 합 여유에 따라 `eps`를 `1e-6`/`1e-2`로 가변 조정, `maxiter=100` 및 `ftol`로 수렴 기준 조절

## 2. `opt_type = 'reach_target'` — 목표 도달률 달성에 필요한 예산 역산

**호출 경로**: `DapOptPhase3.opt_phase3()` (내부에서 위 1번의 `opt_phase2`를 반복 호출하는 상위 레이어입니다.)

`reach_max`가 "예산이 주어졌을 때 도달률을 구하는" 정방향 문제라면, `reach_target`은 그 반대로 "목표 도달률(target_reach)을 만족하는 예산은 얼마인가"를 구하는 **1차원 근 찾기(root-finding) 문제**입니다. 표준 이분탐색 대신 **모멘텀 + 적응적 학습률을 결합한 커스텀 반복 탐색**으로 구현되어 있습니다.

- **오차 지표**: `mpe = |target_reach - result| / target_reach`
- **스텝 계산식**:
  ```
  momentum = sqrt(iteration + 1)
  step = mpe * direction * momentum * learning_rate
  step = clip(step, -0.4, 2.0)
  budget[t] = budget[t-1] * (1 + step)
  ```
  - `direction`(±1): 직전 결과가 목표 초과 시 -1(예산 감소), 미달 시 +1(예산 증가)
  - **방향 전환 시 `learning_rate`를 0.6배 감쇠** — 목표 주변에서 오버슈트/언더슈트로 지그재그하는 진동을 억제 (경사하강법의 학습률 감쇠 스케줄과 유사)
  - 5회 이상 반복해도 직전 결과 대비 변화가 `0.001` 미만으로 정체되면 `step`을 1.5배로 강제 확대해 정체 구간(local plateau) 탈출
- **종료 조건**: 결과가 `target ± margin`(기본 1%p) 이내이면서 목표 이상일 때 종료, 그렇지 않아도 최대 20회에서 종료
- 반복마다 1번의 `opt_phase2`(및 그 안의 SLSQP 배분 최적화)를 매번 새로 실행하며, 관측된 모든 예산-도달률 쌍 중 **목표와의 오차가 가장 작은 지점**을 최종 해로 채택합니다 (`argmin`).
- 초반 반복(`ind < 10`)은 내부 SLSQP `ftol=1e-03`으로 느슨하게, 이후에는 `1e-04`로 정밀하게 좁혀 탐색 비용을 절감합니다 (coarse-to-fine).

## 3. `opt_type = 'reach_spectrum'` — 두 믹스안 A/B 블렌딩 스펙트럼 분석

**호출 경로**: `DapSpecPhase1.spec_phase1()` (앞의 두 `opt_type`과는 별도 클래스 계열이며, 상속 관계도 없습니다.)

이 유형은 엄밀히는 최적화가 아니라 **그리드 스윕 기반 민감도 분석**입니다. 목표를 최대화/역산하는 것이 아니라, 두 미디어믹스안(A, B)을 섞는 비율을 바꿔가며 도달률이 어떻게 변하는지 그 스펙트럼을 보여주는 용도입니다.

- 두 믹스안의 예산 비중을 `ratio_a = 1 - i/seq` (i = 0..seq)로 0~100% 사이를 균등 분할
- 각 혼합비마다 시뮬레이터로 도달률(1~10회)·GRPs를 계산하여 도달률 변화 곡선(스펙트럼)을 산출
- 결과를 `reach_p`(비율), `reach_n`(인원수), `reach_scaled`(구간 내 최대값 대비 0~100 인덱스) 세 가지로 정규화해 시각화용 데이터로 제공

---

## 4. opt_type별 요약

| opt_type | 문제 유형 | 호출 클래스/메서드 | 알고리즘 |
|---|---|---|---|
| `reach_max` | 예산 상한 내 도달률 최대화 (정방향) | `DapOptPhase3.opt_phase2()` (= `DapOptPhase2.opt_phase2`) | 예산 구간 그리드 × SLSQP 배분 최적화 |
| `reach_target` | 목표 도달률 → 필요 예산 역산 (역방향) | `DapOptPhase3.opt_phase3()` | 모멘텀·적응적 학습률 기반 커스텀 반복 탐색 (내부적으로 `reach_max` 로직을 반복 호출) |
| `reach_spectrum` | 두 믹스 블렌딩 민감도 분석 | `DapSpecPhase1.spec_phase1()` | 균등 그리드 스윕 (최적화 아님) |

## 5. 인수인계 시 참고 부탁드립니다

- 전 과정에서 사용되는 "모델"은 `THEDAP_SIMULATION`/`THEDAP_COPULA`의 도달률 시뮬레이터이며, `THEDAP_MIXOPTIM`은 이를 목적함수로 삼아 예산이라는 결정변수를 탐색하는 최적화 계층입니다. scikit-learn류의 지도학습·비지도학습 모델은 사용되지 않습니다.
- `reach_target`은 `reach_max` 로직(SLSQP 배분 최적화 + 예산 구간 스윕)을 그대로 감싸서 반복 호출하는 구조이므로, 두 opt_type은 완전히 독립된 알고리즘이 아니라 **`reach_target` ⊃ `reach_max`** 관계라는 점을 유의해 주시기 바랍니다.
- `reach_spectrum`만 상속 계열이 다르고(`DapSpecPhase1`), 최적화가 아닌 단순 스윕이므로 유지보수 시 혼동하지 않으시길 바랍니다.
- 향후 유지보수 시에는 "모델 재학습"이 아니라 "최적화 파라미터(`ftol`, `eps`, `learning_rate`, `margin`, `opt_seq` 등) 튜닝" 관점으로 접근해 주시면 될 것 같습니다.
