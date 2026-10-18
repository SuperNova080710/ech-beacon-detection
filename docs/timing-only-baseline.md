# Timing-only Baseline Detector — 사전 정의

> Issue #7, detector version `1.0.0`, extractor schema `1.0.0`.
> **실험 데이터의 threshold/탐지율 결과를 관찰하기 전에** 점수·분할·calibration 규칙을 고정한다.

## 목적 및 입력

동결된 Feature Extractor의 `features.csv` 중 `iat_cv`만 사용한다. detector는 클래스, jitter, normal profile, trial ID를 입력받지 않는다. `iat_mean_s`/`iat_std_s`는 참고용이고 판정에 사용하지 않는다.

## 판정 수식

```text
score = iat_cv = population_std(29 flow-start IATs) / mean(29 IATs)
beacon (1) if score < threshold; normal (0) otherwise
```

threshold와 score가 같은 경우 normal(0)이다. NaN, Infinity, 누락, 음수 CV는 오류로 취급한다.

## 데이터 분할 규칙

본 실험용 raw/processed dataset 200개에만 적용한다. `pilot-v1`, `capture-check-v1`, `pilot-v2`는 threshold calibration과 최종 test에서 제외한다.

| Class/프로필 | Calibration | Test |
| --- | --- | --- |
| Beacon (5 jitter × 20) | trial 1..10 × 5 = 50 | trial 11..20 × 5 = 50 |
| Normal interactive-burst (40) | 1..16 = 16 | 17..40 = 24 |
| Normal irregular-lognormal (30) | 1..12 = 12 | 13..30 = 18 |
| Normal mixed-activity (30) | 1..12 = 12 | 13..30 = 18 |
| **총합** | **90** | **110** |

Beacon은 **동일 trial 번호가 서로 다른 jitter 수준을 가로질러 같은 partition**에 속한다. Normal calibration 40개만 timing-only threshold 추정에 사용하며 Beacon calibration 50개는 본 baseline의 threshold 추정에서 제외한다.

## Normal-only threshold calibration

```text
normal_calibration_iat_cv 40개를 오름차순으로 정렬:
x_(1) <= x_(2) <= ... <= x_(40)
threshold = x_(3)
prediction = 1 iff CV < threshold
```

따라서 calibration 데이터에서 false positives는 최대 2개/40개(경험적 FPR ≤ 5%)다. ties는 strict `<` 비교 때문에 더 보수적으로 처리된다. **Test FPR은 5%라고 보장하거나 주장하지 않는다.** Test의 결과로 threshold를 조정하지 않는다.

## 독립 평가

최종 held-out dataset은 Beacon 50개와 Normal 60개다. jitter별 평가에는 Beacon positive 10개와 **동일한 Normal negative 60개**를 함께 사용한다. 이 때문에 5개 jitter의 Normal/FPR 결과는 통계적으로 독립인 5개 반복실험이 아니다. 각 jitter의 positive가 10개라는 제한을 결과 해석에 명시한다.

## 구현과 검증

- `detector/timing_only.py`: 순수 CV 검증, strict 비교, x_(3) calibration, 고정 trial-ID 분할 및 카탈로그 검증
- `detector/test_timing_only.py`: synthetic 값만 이용한 단위 테스트. 실제 pilot feature 값으로 threshold를 맞추지 않는다.
- `detector/config.json`: detector version과 변하지 않는 calibration 규칙.

실험 전 정적 검증:

```bash
python3 detector/test_timing_only.py
```

아직 본 실험 200개 dataset의 calibration CV 값이 없으므로 실측 threshold, test precision/recall/F1/FPR/FNR은 **미측정**이다. 향후 calibration/test CLI 및 provenance 기록을 구현하고, 별도 데이터 생성 단계에서 평가한다.

## 변경 규칙

정의·split·threshold 규칙은 결과를 본 뒤 소급 수정하지 않는다. 오류가 발견되면 과거 원자료·문서를 유지하고 research log에 수정 내용과 새 detector version을 남긴다.

## Issue #7: split / calibration / inference CLI

이 CLI는 별도로 수집·검증된 본 실험 데이터 200개가 준비된 후에만 사용한다. 기존 `pilot-v2`는 acceptance 전용이며 사용이 거부된다.

- `split`: extractor schema v1.0.0과 provenance pass, 전체 200개 trial ID/label 대응을 확인한 다음 calibration 90개/test 110개를 분리한다. test feature 분포나 metric을 계산하지 않는다.
- `calibrate`: **calibration_features.csv / calibration_labels.csv만 읽어** Normal 40개 CV의 세 번째 순서통계량 `x_(3)`으로 임계값을 정한다. test CSV는 열지 않는다.
- `predict`: **test_features.csv만 읽어** label 없이 엄격한 `CV < threshold` 규칙으로 110개 예측을 만든다. test label CSV를 읽지 않는다.
- CSV의 13개 feature 순서·숫자 유한성, Normal CV의 비음수 조건, partition SHA-256과 calibration fingerprint를 검증한다.
- split/threshold 파일은 기존 출력을 덮어쓰지 않는다. test label은 후속 평가 Issue에서만 별도로 join한다.

### 실행 절차 — 실제 본 실험 200개 dataset 생성 후

```bash
python3 detector/timing_only_cli.py split \
  --processed-dir data/processed/<final-run-tag> \
  --out-dir results/timing-only/<final-run-tag>/split

python3 detector/timing_only_cli.py calibrate \
  --split-dir results/timing-only/<final-run-tag>/split \
  --output results/timing-only/<final-run-tag>/calibration.json

python3 detector/timing_only_cli.py predict \
  --split-dir results/timing-only/<final-run-tag>/split \
  --calibration results/timing-only/<final-run-tag>/calibration.json \
  --output results/timing-only/<final-run-tag>/predictions.csv
```

`calibration.json`은 실제 threshold, Normal calibration CV 정렬값, empirical calibration FPR, split/input SHA-256, 결정적 fingerprint, 계산시간을 기록한다. `predictions.csv`에는 trial ID/score/0·1 예측/버전/fingerprint만 포함하고 정답은 포함하지 않는다.

### Synthetic offline tests — 지금 실행 가능

```bash
python3 detector/test_timing_only.py
python3 detector/test_timing_only_cli.py
```

200행 synthetic fixture를 임시 디렉터리에 만들고 `split → calibrate → predict`를 검증한다. 90/110 partition, Normal-only threshold, label 비사용, byte-identical prediction, checksum tampering, pilot 차단, version mismatch, 누락·중복 ID, overwrite 거부를 확인한다.

테스트가 성공하더라도 실측 threshold, test Precision/Recall/F1/FPR/FNR이나 실제 본 실험 처리 성능은 **미측정**이다.
