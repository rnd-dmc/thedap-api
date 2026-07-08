# THEDAP API

- 더답(THEDAP) 미디어믹스 도달률(Reach)/GRP 시뮬레이션, 매체간 중복분석(Copula), 리치커브,
미디어믹스 최적화, 커스텀 모델 분석을 제공하는 FastAPI 모듈


  - 요청/응답은 `thedap_api.py`의 미들웨어(`log_requests`)가 자동으로 로깅함 (stdout은 `PrintLogger`를 통해 전부 `logger.info`로 전달됨).

<br>
<hr>
<br>

## 디렉토리 구조

<br>

```
src/
├── thedap_api.py            # FastAPI 엔트리포인트, 전체 API 라우트 정의
├── CONFIG/
│   ├── config.py             # DB 접속정보 (gitignore 대상, 로컬에서 직접 생성 필요)
│   └── DapData.py            # DB 연결 + 인구(population)/파라미터/분포/N+ 파라미터 DB 로딩 (모든 클래스의 최상위 베이스)
├── THEDAP_UTILS/             # 공통 유틸
│   ├── DapUtils_v4.py / DapUtils_v5.py   # 성별·연령 변환, 타겟 인구, 가중치, round_float, check_coverage 등
│   ├── DapMixClean_v4.py / DapMixClean_v5.py  # input_mix 원본 → 정제된 노출량(Eimp)/도달(Areach) 계산
│   └── DapCustomModel.py     # 커스텀 모델(업로드 데이터 기반 로지스틱 회귀) 분석
├── THEDAP_SIMULATION/        # 도달/GRP 시뮬레이션 본체
│   ├── DapPhase1_v4 → DapPhase2_v4 → DapPhase3_v4 → DapOutput_v4   (BASIC 등급, userGrade == 'B')
│   └── DapPhase1_v5 → … → DapPhase5_v5 → DapOutput_v5              (STANDARD/PREMIUM 등급, userGrade != 'B')
├── THEDAP_REACHCURVE/        # 예산 구간별 리치커브
│   ├── DapCurve_v4.py / DapCurve_v5.py
├── THEDAP_COPULA/
│   └── DapCopula.py           # 매체간 중복(Copula) 통계 모델
├── THEDAP_MIXOPTIM/           # 미디어믹스 최적화
│   ├── DapMixOptimizer.py     # 퍼사드 (opt_type에 따라 아래 클래스로 분기)
│   ├── DapOptPhase1 → DapOptPhase2 → DapOptPhase3   # reach_max / reach_target
│   └── DapSpecPhase1.py       # reach_spectrum (믹스 A/B 비교)
├── THEDAP_REPORT/             # 분석결과를 엑셀(openpyxl)로 내보내는 함수 모음
│   ├── DapMixSample, DapCustomSample                # 입력 양식 생성
│   └── DapReportReachAnalysis, DapReportCopula, DapReportReachCurve,
│       DapReportReachOptimize, DapReportReachSpectrum   # 결과 리포트 생성
├── DATA_BKUP/, DATA_CLEANING/ # DB 파라미터 백업본 및 정제 스크립트
└── test.ipynb                 # 각 API 로직을 셀 단위로 직접 호출해보는 로컬 디버깅 노트북
```

<br>
<hr>
<br>

## 처리 흐름 (핵심 아키텍처)

```
DapData (DB 로딩: 인구/파라미터/분포)
  → DapUtils_v5 (연령·성별 변환, 타겟 인구, 가중치, round_float 등 공통 함수)
  → DapMixClean_v5 (input_mix 정제 → Eimp/Areach 계산)
  → DapPhase1_v5 ~ DapPhase5_v5 (라인별 노출량 → 중복보정 → 도달/GRP 순차 집계)
  → DapOutput_v5 (최종 결과를 API 응답 JSON으로 가공)
```

- `DapCurve_v5`, `DapOptPhase*`, `DapSpecPhase1`도 모두 `DapPhase5_v5`를 상속해 **동일한 시뮬레이션 로직 위에서 예산/조건을 바꿔가며 반복 실행**하는 방식으로 동작.
  
  즉 실제 도달률/GRP 계산 로직은 `DapPhase1_v5~5_v5`에
집중되어 있고, 그 위의 클래스들은 "무엇을 입력으로 몇 번 돌릴지"만 다름.

- v4는 동일한 구조를 더 단순한 버전(Phase1~3, 라인/플랫폼/전체 3단계 집계, `input_mix`의 필드 구성도 다름)으로 별도 유지하며, 
  
  **`userGrade`에 따른 등급별 기능 차등 제공**을 위한 경로 (구버전이 아니라 BASIC 등급 전용 로직).

<br>

### userGrade 분기

- `userGrade`는 사용자 등급을 나타내며 `'B'`(BASIC) / 그 외(`'P'` 등, STANDARD·PREMIUM)로 나뉨.

  - `userGrade == 'B'` (BASIC) → v4 로직 (`DapOutput_v4`, `DapCurve_v4`)
  - 그 외 (STANDARD/PREMIUM) → v5 로직 (`DapOutput_v5`, `DapCurve_v5`, `DapMixOptimizer`)
  - `mix_sample`, `report_analysis` 등 리포트/양식 생성 함수도 내부적으로 `userGrade`에 따라 시트·컬럼 구성이 달라짐
  - 미디어믹스 최적화(`/reach_optimize/`)와 커스텀 모델은 등급 분기 없이 전 등급에서 v5(`DapMixOptimizer`)/`DapCustomModel` 로직만 사용

<br>
<hr>
<br>

## API 엔드포인트

<br>

### 공통

<br>

| 엔드포인트 | 설명 | 처리 클래스 |
|---|---|---|
| `POST /mix_sample/` | 매체/상품 목록 기반 미디어믹스 입력 양식 엑셀 다운로드 | `THEDAP_REPORT.DapMixSample(channelVehicleMap, userGrade)` |
| `POST /target_info/` | 성별/연령 조건의 타겟 인구모수 조회 | `DapUtils_v5(pop_only=True).get_target_info(...)` (population DB만 로드, parameter/distribution은 로드 안 함) |
| `GET /get_media_product/` | 등록된 매체·상품 목록 조회 | `CONFIG.DapData.getMediaProduct()` |

<br>

### 통합 Reach 분석

<br>

| 엔드포인트 | 설명 | 처리 클래스 |
|---|---|---|
| `POST /reach_result/` | `input_mix`+타겟+가중치로 도달률/GRP/빈도분포 계산 | `userGrade=='B'` → `DapOutput_v4`, 그 외 → `DapOutput_v5` |
| `POST /report_analysis/` | 통합 Reach 분석 결과를 엑셀로 다운로드 | `DapReportReachAnalysis(reportOption, reportResult, target_pop, userGrade)` |

`/reach_result/` 응답은 `result_overall`, `result_summary`, `heatmap`, `reach_freq` 4종 공통 + (v5만)
`reach_marginal`(플랫폼별 타겟 도달률), `reach_union`(전체 통합 도달률)을 추가로 내려주며, 이 두 값은
그대로 `/reach_copula/`의 입력으로 재사용됨.

<br>

- **주의**: v4용 `input_mix` 라인 스키마(`e_imp`/`e_grp` 필드 사용, `campaign`/`date_start`/`date_end`/`retargeting` 없음)와 
  
  v5용 스키마(`campaign`/`date_start`/`date_end`/`retargeting`/`imp`/`reach`
필드 사용)가 서로 다름 

<br>

### 매체간 중복/도달 (Copula)

<br>

| 엔드포인트 | 설명 | 처리 클래스 |
|---|---|---|
| `POST /reach_copula/` | 플랫폼별 한계 도달률(`reach_marginal`)과 통합 도달률(`reach_union`)로 매체 조합별 합집합/교집합 확률 계산 | `DapCopula` (Gaussian Copula, 상관계수 rho를 통합 도달률에 맞춰 추정) |
| `POST /report_copula/` | 위 결과를 엑셀로 다운로드 | `DapReportCopula` |

응답의 `copula_inter`에는 각 매체 조합의 교집합 확률 외에 `"{매체}_ONLY"`(포함-배제 원리로 계산한 단독 도달)
항목도 함께 포함됨.

<br>

### 리치커브

<br>

| 엔드포인트 | 설명 | 처리 클래스 |
|---|---|---|
| `POST /reach_curve/` | 0 ~ `input_maxbudget`(억원)을 `input_seq` 구간으로 나눠 구간별 GRP/도달률(1~10회) 계산 | `userGrade=='B'` → `DapCurve_v4()`, 그 외 → `DapCurve_v5(userName, inputModelDate, platform_list)` |
| `POST /report_curve/` | 위 결과를 엑셀로 다운로드 | `DapReportReachCurve` |

<br>

### 미디어믹스 최적화

- `opt_type`(`reach_max` / `reach_target` / `reach_spectrum`)에 따라 요청 필드와 내부 처리 클래스가 완전히 달라짐.

<br>

| opt_type | 설명 | 필요 필드 | 처리 클래스 |
|---|---|---|---|
| `reach_max` | 예산 상한 내에서 도달 극대화 믹스 탐색 | `input_mix`, `opt_maxbudget`, `opt_seq` | `DapOptPhase3` (← `DapOptPhase1`→`2`→`3`) |
| `reach_target` | 목표 도달률(`opt_target`) 달성을 위한 최소 예산 믹스 탐색 | `input_mix`, `opt_target` | `DapOptPhase3`. 실행 전 `DapUtils_v5.check_coverage()`로 달성 가능 여부 검사 — 불가능하면 `{"isSuc": false}`만 반환 |
| `reach_spectrum` | 두 믹스(`input_mixA`/`input_mixB`, `alloc_rat`로 내부 배분)를 예산 구간별로 비교 | `input_mixA`, `input_mixB`, `opt_maxbudget`, `opt_seq` | `DapSpecPhase1` |

<br>

- `POST /reach_optimize/` 응답: `reach_max`/`reach_target`은 `table_viz`(선버스트 트리 구조) + `table_opt`(예산별 최적 믹스 상세) + `table_freq`(예산별 도달빈도), `reach_spectrum`은 `table_plot` + `table_spec`
- `POST /report_optimize/`: 최적화 결과를 엑셀로 다운로드. 

<br>

### 커스텀 모델

<br>

| 엔드포인트 | 설명 | 처리 클래스 |
|---|---|---|
| `POST /custom_sample/` | 커스텀 모델 데이터 업로드 양식 다운로드 | `DapCustomSample()` |
| `POST /reach_custom/` | 업로드 데이터(`grps`/`reach_p` 쌍, 20행 이상 필요)로 도달곡선 파라미터(A/B/C, maxGrps) 추정 | `DapCustomModel(uploadData).getResult()` (`statsmodels` OLS로 로짓 변환 후 회귀) |

<br>

- `uploadData`가 20행 미만이면 `422 RowNumError`를 반환.

<br>
<hr>
<br>


## 핵심 클래스 상세

<br>

### `THEDAP_SIMULATION/DapOutput_v4.py`

- 미디어 믹스 시뮬레이션 결과를 API 응답용 JSON으로 변환하는 BASIC 등급용 출력 클래스.

<br>

**클래스 계층**

```
DapPhase1_v4 → DapPhase2_v4 → DapPhase3_v4 → DapOutput_v4
```

<br>

**생성자**

```python
DapOutput_v4(input_mix, input_age, input_gender, input_weight)
```

<br>

- `input_mix`, `input_age`, `input_gender`, `input_weight`: v5와 동일한 역할 (미디어 믹스 / 타겟 연령·성별 / 도달 가중치)
- `inputModelDate`, `userName`, `platform_list` 파라미터는 없음 (v5 대비 단순화된 버전)
- 생성 시 `self.target`, `self.trans_pop`을 계산하고, 아래 3개 집계를 수행해
  `heatmap1~3`, `summary_line/platform/ovr` 속성으로 저장. (v5는 라인/서브토탈/캠페인/플랫폼/전체 5단계, v4는 라인/플랫폼/전체 3단계로만 집계)

<br>

| heatmap 속성 | summary 속성 | 집계 단위 | 계산 함수 |
|---|---|---|---|
| heatmap1 | summary_line | 라인 | `summary_each_line` |
| heatmap2 | summary_platform | 플랫폼 | `summary_each_platform` |
| heatmap3 | summary_ovr | 전체 | `summary_overall` |

<br>

**주요 메서드**

- **`target_info()`**: 타겟 정보 반환
- **`result_summary()`**: line/platform/overall 요약을 하나의 표로 합쳐 정렬(플랫폼→구분 순) 후 JSON 리스트로 반환
- **`heatmap()`**: 라인 기준·플랫폼 기준·전체 기준 도달 데이터를 성별(F/M) × 연령대 피벗 형태로 변환
- **`reach_freq()`**: 1~10회 빈도별 누적 도달률과 구간별 차이 계산
- **`result_overall()`**: 1회/3회 도달률·인원, GRP, AF 등 핵심 지표 요약
- `get_result()`는 없음 — `thedap_api.py`에서 `result_overall/result_summary/heatmap/reach_freq`를 개별 호출해 dict로 조립

<br>

**사용처**

`thedap_api.py`의 `/reach_result/`에서 `userGrade == 'B'`인 경우에만 사용됨
(리치커브는 `THEDAP_REACHCURVE/DapCurve_v4.py`가 별도 처리).

<br>

### `THEDAP_SIMULATION/DapOutput_v5.py`

- 미디어 믹스 시뮬레이션의 최종 결과(도달/GRP/빈도분포 등)를 API 응답용 JSON으로 변환하는 최상위 출력 클래스.

<br>

**클래스 계층**

```
DapPhase1_v5 → DapPhase2_v5 → DapPhase3_v5 → DapPhase4_v5 → DapPhase5_v5 → DapOutput_v5
```

- 각 Phase가 순차적으로 라인 단위 노출량 계산 → 중복 보정 → 도달/GRP 산출을 담당하며,
`DapOutput_v5`는 `DapPhase5_v5`가 만든 결과를 라인/서브토탈/캠페인/플랫폼/전체 단위로
집계하고 API 응답 스펙에 맞게 가공.

<br>

**생성자**

```python
DapOutput_v5(input_mix, input_age, input_gender, input_weight,
             inputModelDate=오늘 날짜, userName='', platform_list=[])
```

- `input_mix`: 라인별 매체/캠페인/기간/예산 등을 담은 미디어 믹스 (JSON)
- `input_age`, `input_gender`: 타겟 연령/성별 조건
- `input_weight`: 도달 가중치 파라미터
- 생성 시 `self.target`(타겟 정보), `self.trans_pop`(타겟 인구수)을 계산하고,
  아래 5개 집계를 한 번에 수행해 `heatmap1~5`, `summary_line/subtotal/campaign/platform/tot` 속성으로 저장.

<br>

| heatmap 속성 | summary 속성 | 집계 단위 | 계산 함수 |
|---|---|---|---|
| heatmap1 | summary_line | 라인 | `summary_each_line` |
| heatmap2 | summary_subtotal | 서브토탈 | `summary_each_subtotal` |
| heatmap3 | summary_campaign | 캠페인 | `summary_each_campaign` |
| heatmap4 | summary_platform | 플랫폼 | `summary_each_platform` |
| heatmap5 | summary_tot | 전체 | `summary_total` |

<br>

**주요 메서드**

- **`target_info()`**: 타겟 정보(`self.target`) 반환
- **`result_summary()`**: line/subtotal/campaign/platform/total 요약을 하나의 표로 합쳐 정렬(플랫폼→캠페인→구분 순) 후 필요한 컬럼만 골라 JSON 리스트로 반환
- **`heatmap()`**: 라인 기준(heatmap1)·플랫폼 기준(heatmap4)·전체 기준(heatmap5) 도달 데이터를 성별(F/M) × 연령대 피벗 테이블 형태로 변환 (인원수 N, 비율 P, GRP)
- **`reach_freq()`**: 1~10회 빈도별 누적 도달률(`reach_p`)과 구간별 도달률 차이(`reach_p_diff`)를 계산
- **`result_overall()`**: 1회/3회 도달률·인원, GRP, AF(평균 노출빈도) 등 핵심 지표 요약
- **`get_result()`**: 위 4개 메서드 결과를 `result_summary`, `reach_heatmap`, `reach_freq`, `result_overall` 키로 묶어 최종 응답 dict 반환

<br>

**사용처**

- `thedap_api.py`의 `/reach_result/`에서 `userGrade != 'B'`인 경우 사용됨.
`input_mix/input_age/input_gender/input_weight`(+ `userName`, `inputModelDate`, `platform_list`)를 받아 `DapOutput_v5`를 생성하고 `get_result()`를 호출해 응답으로 내려줌.

---