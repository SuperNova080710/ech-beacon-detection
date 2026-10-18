# Multi-feature Detector — 사전 고정 설계

> Issue #9 · detector version 1.0.0 · extractor feature schema 1.0.0
> 본 실험의 calibration/test 성능을 확인하기 전에 분할·정규화·학습·판정·임계값 규칙을 동결한다.

## 목적

Timing-only Baseline (#7)의 `iat_cv` 단일 점수와 비교할 **13개 특징 결합 경량 이진 분류기**를 구현한다. 사전에 정한 200 sample 본 실험 분할을 그대로 사용하며, 실제 성능을 보고 알고리즘을 바꾸지 않는다.

## 사용 특징 (고정된 순서)

```text
iat_mean_s
iat_std_s
iat_cv
iat_mad_s
packet_size_mean_bytes
packet_size_std_bytes
packet_size_cv
out_in_packet_ratio
byte_asymmetry
direction_change_ratio
burst_count
burst_mean_size
burst_interval_cv
```

Feature는 raw PCAP에서 산출된 extractor 1.0.0의 결과만 사용한다. `traffic_class`, `jitter_pct`, `normal_profile`, `trial_id`는 **모델 feature가 아니다**. `trial_id`는 split과 CSV 1:1 대응에만 사용한다.

## Dataset split

Issue #7의 동일 `split_manifest.json` 및 분할 CSV를 재사용한다.

| Class | Calibration | Held-out test |
| --- | ---: | ---: |
| Beacon (0/10/30/50/70%, 각각 trial 1..10/11..20) | 50 | 50 |
| Normal interactive-burst | 16 | 24 |
| Normal irregular-lognormal | 12 | 18 |
| Normal mixed-activity | 12 | 18 |
| **합계** | **90** | **110** |

동일 Beacon trial 번호의 paired jitter 5개는 반드시 같은 partition에 머문다. `pilot-v1`, `capture-check-v1`, `pilot-v2`는 모델 학습·threshold·최종 평가에서 제외한다.

## Calibration-only 표준화

각 특징 k에서 90개 calibration sample의 mean μ_k 및 population standard deviation σ_k를 계산한다.

```text
scale_k = σ_k if σ_k > 0 else 1
z_k = (x_k − μ_k) / scale_k
```

0 분산 특징은 training sample의 z가 0이므로 가중치 추정에 영향이 없다. **Test 집합의 평균/표준편차를 계산하지 않는다.** 입력의 13개 특징은 모두 finite이어야 하며 누락과 NaN/Infinity를 오류로 처리한다.

## 경량 모델 학습 규칙

추가 library 없이 Python 표준 라이브러리로 L2-regularized logistic regression을 구현한다. 90개 calibration sample 전체를 **trial ID 오름차순**으로 고정해 학습한다. Normal label=0, Beacon label=1.

```text
score(x) = b + Σ_k w_k · z_k(x)  # logit
p(y=1|x) = sigmoid(score(x))
loss = mean( −y·log(p) − (1−y)·log(1−p) ) + (λ/2) · Σ_k w_k²
gradient_w_k = mean( (p−y)·z_k ) + λ·w_k
gradient_b = mean( p−y )
w_k ← w_k − η·gradient_w_k
b ← b − η·gradient_b
```

고정 하이퍼파라미터:

```text
model_version       = 1.0.0
optimizer           = full-batch gradient descent
learning_rate (η)   = 0.1
epochs              = 800
L2 lambda (λ)       = 0.1
initial weights     = 0
initial intercept   = 0
early stopping      = none
feature_count       = 13
```

평균 loss와 gradient 모두 **90개 calibration sample 전체를 동일 가중치**로 계산한다. 학습률, 정규화 계수, epoch 수와 특징 개수를 test 결과를 본 뒤 조정하지 않는다. 높은 상관관계/중복 특징도 임의 제거하지 않고 L2 regularization으로 처리한다.

## Threshold calibration (동결)

90개 calibration으로 학습된 모델의 Normal calibration sample **40개 logit 점수만** 내림차순 정렬한다.

```text
s_(1) ≥ s_(2) ≥ ... ≥ s_(40)
threshold = s_(3)
Beacon(1) iff score(x) > threshold
Normal(0) otherwise  # equality/ties -> normal
```

따라서 학습에 사용한 Normal calibration 40개에서 FP ≤2로 **in-sample empirical calibration FPR ≤5%**가 성립한다. **실제 held-out test FPR은 5%라고 주장하거나 보장하지 않는다.** Test 결과에 맞춰 모델/threshold를 수정하지 않는다.

## 입력·출력·무결성

Baseline CLI의 `split` 명령으로 생성한 90/110 partition과 SHA-256 split manifest를 Multi-feature와 Timing-only가 공유한다.

- `train`: calibration feature+label만 읽고 mean/scale/w/b/Normal scores/threshold를 저장
- `predict`: test feature와 학습 model만 읽고 label 없이 110개 prediction을 출력
- feature/label schema 및 partition, detector/extractor version, calibration CSV SHA-256, split SHA-256, model fingerprint 검증
- 기존 파일 overwrite 금지, 모델 변조 및 비정상 값은 오류
- stable sort/float 처리에 기반한 deterministic model coefficient, threshold, prediction
- 실행 시각·처리시간은 별도 provenance 필드로 남기되 byte-identical 검사에서는 제외

예상 파일 구조:

```text
results/multi-feature/<run-tag>/
  calibration.json
  predictions.csv
```

실제 200개 experiment 데이터가 확보되기 전에는 **synthetic 200 sample 임시 fixture만** 사용해 테스트한다. 최종 calibration threshold, held-out test Precision/Recall/F1/FPR/FNR, processing time 결과는 아직 미측정이다.

## 한계

새 특징의 유효성을 미리 가정하지 않는다. Generator의 class-independent payload 때문에 packet size/directionality가 discriminative하지 않을 수 있고, burst/timing 특징들 사이에는 상관관계가 있다. Multi-feature가 높은 jitter에서 Timing-only보다 개선되지 않더라도 그대로 보고한다. Calibration 90개와 13개 특징은 과적합 위험이 있으므로 held-out 성능과 처리 비용을 함께 제시한다.

## 다음 검증 절차

1. 사전 고정 코드를 구현하고 pure synthetic unit test 진행
2. synthetic 200개 fixture에서 `train → predict`, label isolation, 40 Normal threshold, fingerprint, deterministic 결과 검증
3. 실제 200개 Native ECH 본 실험은 별도 Issue에서 수집
4. 두 detector에 동일한 110 held-out sample을 적용하고 jitter별 지표 평가
