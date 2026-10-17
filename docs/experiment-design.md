# Experiment Design

> 작성일: 2026-10-16
>
> 원칙: 실험 결과를 보기 전에 조건, 측정값, 비교 기준과 반증 조건을 고정한다. 이후 변경이 필요하면 기존 내용을 삭제하지 않고 `docs/research-log.md`에 변경 이유와 시점을 기록한다.

## 1. 연구 질문

Native ECH 환경에서 beacon traffic의 jitter가 증가할 때, timing-only 탐지와 timing·packet size·directionality·burst 특성을 결합한 경량 다중특징 탐지 방식의 탐지 성능은 어떻게 달라지는가?

## 2. 가설

Native ECH 환경에서 timing, packet size, directionality, burst 특성을 결합한 경량 다중특징 탐지 방식은 timing-only 탐지 방식보다 jitter가 증가한 beacon traffic의 탐지율을 더 높게 유지할 것이다.

## 3. 비교 대상

### Baseline A — Timing-only detector

Inter-arrival time 기반 periodicity를 중심으로 판단한다.

주요 특징:

- mean inter-arrival time
- standard deviation of inter-arrival time
- coefficient of variation (CV)

초기 baseline은 CV 중심의 단순하고 해석 가능한 방식으로 구현한다. Threshold는 실험 데이터의 test set을 보고 임의 조정하지 않는다. 필요하면 calibration용 별도 training/calibration partition에서만 결정한다.

### Proposal B — Lightweight multi-feature detector

다음 네 그룹의 protocol-agnostic flow metadata를 사용한다.

#### Timing

- mean inter-arrival time
- inter-arrival CV
- median absolute deviation (MAD)

#### Packet size

- mean packet size
- packet-size standard deviation
- packet-size CV

#### Directionality

- outbound/inbound packet ratio
- byte asymmetry
- direction-change ratio

#### Burst

- burst count
- mean burst size
- burst-interval CV

첫 구현은 해석 가능한 규칙/통계 기반 score 또는 단순한 경량 모델을 우선한다. 복잡한 딥러닝 모델은 본 연구의 핵심이 아니므로 baseline/proposal 비교가 불명확해질 정도로 확장하지 않는다.

## 4. 독립 변수

### 4.1 Detector

- Timing-only
- Multi-feature

### 4.2 Beacon jitter

- 0%
- 10%
- 30%
- 50%
- 70%

기준 beacon interval은 다음으로 고정한다.

```text
T = 1.0 s
```

각 trial에서 먼저 정규화 jitter vector를 생성한다.

```text
z_i ~ Uniform(-1, 1)
```

jitter 비율을 `j`라고 할 때 scheduled inter-arrival time은 다음으로 정의한다.

```text
I_i(j) = T × (1 + j × z_i)
```

따라서 70% jitter에서 scheduled interval 범위는 다음과 같다.

```text
0.30 s <= I_i <= 1.70 s
```

동일한 beacon trial 번호는 모든 jitter 수준에서 같은 `z_i` sequence를 사용하고 jitter amplitude만 변경한다. 이 paired design으로 jitter 외 난수 sequence 차이를 최소화한다.

Beacon timing seed 정책:

```text
seed_base = 20261017
trial_seed = seed_base + trial_id
trial_id = 1..20
```

실제 seed와 generated interval sequence는 raw manifest에 저장한다.

### 4.3 Traffic class

- Normal
- Beacon

## 5. 통제 변수

가능한 한 다음 조건을 고정한다.

- 동일한 client/server Docker host
- 동일한 ECH server 설정
- 동일한 TLS/ECH 구현 버전
- 동일한 base beacon interval `1.0 s`
- trial당 동일한 HTTPS transaction 수 `30`
- 동일한 payload profile set과 class-independent 선택 확률
- 동일한 packet capture 방식
- 동일한 feature extraction 코드
- 동일한 detector version
- 동일한 experiment host

환경 버전은 실험 실행 전에 `results/environment.txt` 형태로 보존한다.

## 6. 실험 환경

기본 구조:

```text
Traffic Generator
       |
       | HTTPS + native ECH
       v
ECH-enabled Server
       |
       +---- packet capture ----> PCAP
                                  |
                                  v
                          Feature Extractor
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
             Timing-only                  Multi-feature
               detector                      detector
                    |                           |
                    +-------------+-------------+
                                  v
                              Metrics
```

호스트 시스템의 기존 OpenSSL/curl을 교체하지 않는다. ECH client/server는 Docker 컨테이너 안에서 ECH 지원 버전을 사용한다.

## 7. 데이터 생성

### 7.1 Sample / trial 정의

한 sample은 단일 TCP 5-tuple 하나가 아니라, 동일 client에서 동일 protected ECH server로 발생한 **30개의 short-lived HTTPS flow sequence**로 정의한다.

```text
trial
 ├─ HTTPS/ECH flow 01
 ├─ HTTPS/ECH flow 02
 ├─ ...
 └─ HTTPS/ECH flow 30
```

각 HTTPS transaction은 새 연결을 사용한다. 이후 feature extractor는 trial 단위로 flow sequence를 집계한다.

- Timing: flow/connection 시작 시각 간 IAT
- Packet size: trial 내 packet-size 통계
- Directionality: trial 내 client/server packet·byte 방향 통계
- Burst: flow 시작 시각 기반 burst 통계

각 trial은 정확히 30 transactions를 포함하므로 29개의 scheduled IAT를 가진다.

### 7.2 Beacon traffic

- base interval: `1.0 s`
- jitter: `0/10/30/50/70%`
- 각 jitter 조건: `20 trials`
- 각 trial: `30 HTTPS transactions`
- 동일 trial 번호는 모든 jitter 수준에서 같은 normalized jitter sequence 사용
- 동일 trial 번호는 모든 jitter 수준에서 같은 payload profile sequence 사용

최소 beacon sample 목표:

```text
5 jitter levels × 20 trials = 100 samples
```

### 7.3 Normal traffic

정상 traffic은 총 100 samples, sample당 30 HTTPS transactions로 고정한다.

단일 Uniform random interval 하나만 사용하지 않고 다음 세 profile을 사용한다.

#### Profile A — interactive-burst

- samples: `40`
- burst size: integer Uniform `[2, 5]`
- intra-burst IAT: Uniform `[0.10, 0.35] s`
- inter-burst idle: Uniform `[2.0, 5.0] s`

#### Profile B — irregular-lognormal

- samples: `30`
- IAT: LogNormal(`mu = ln(1.0)`, `sigma = 0.8`)
- 최종 IAT를 `[0.15, 6.0] s` 범위로 clip

#### Profile C — mixed-activity

- samples: `30`
- 각 IAT마다:
  - probability `0.70`: Uniform `[0.20, 1.00] s`
  - probability `0.30`: Uniform `[2.50, 6.00] s`

Normal timing seed는 beacon과 별도 namespace를 사용하고 sample별 seed를 manifest에 저장한다.

### 7.4 Request / payload profile

Packet-size/directionality feature를 계산할 수 있도록 요청과 응답 크기에 제한된 변화를 둔다.

그러나 payload 크기가 class label의 shortcut이 되지 않도록 Beacon과 Normal은 동일한 payload profile과 동일한 선택 확률을 사용한다.

| Profile | Request query payload | Response body | Probability |
|---|---:|---:|---:|
| small | 32 B | 128 B | 0.50 |
| medium | 128 B | 512 B | 0.35 |
| large | 512 B | 2048 B | 0.15 |

동일 beacon trial 번호는 jitter 수준이 달라도 동일한 payload profile sequence를 사용한다.

### 7.5 전체 목표

- Beacon: 100 samples
- Normal: 100 samples
- 전체 목표: 200 samples
- 각 sample: 30 HTTPS transactions
- 실패 sample이 발생하면 삭제하지 않고 실패 이유를 기록한다.

본 실험 200 samples를 바로 생성하지 않는다. Generator 구현 후 먼저 8-trial pilot을 수행한다.

```text
Beacon: jitter별 1 trial = 5 trials
Normal: profile별 1 trial = 3 trials
Total = 8 trials
```

Pilot은 generator의 정확성과 재현성 검증용이며 detector 성능 평가 데이터로 사용하지 않는다.

## 8. Dataset split 및 threshold 원칙

탐지 임계값이나 모델 파라미터를 test 결과에 맞춰 조정하지 않는다.

경량 모델 학습 또는 threshold calibration이 필요할 경우 다음처럼 분리한다.

- calibration/train: 파라미터 결정용
- test: 최종 비교용

동일한 trial 또는 사실상 동일한 flow sequence가 양쪽 partition에 중복되지 않게 한다.

랜덤 분할을 사용할 경우 seed를 고정하고 기록한다.

## 9. 원자료

원자료는 가능한 한 다음 계층으로 보존한다.

```text
data/raw/
  manifests/
  flow-metadata/

artifacts/pcap/
  beacon/
  normal/

data/processed/
  features.csv
  labels.csv

results/
  metrics/
  figures/
```

PCAP은 Git에 기본 업로드하지 않는다. 대신 trial manifest에는 PCAP filename/hash와 원자료 대응 정보를 남겨 raw → processed 변환을 추적할 수 있게 한다.

각 raw manifest는 최소 다음 값을 보존한다.

```text
trial_id
traffic_class
normal_profile
jitter_pct
base_interval_s
request_count
seed
timing_sequence_s
payload_profile_sequence
scheduled_timestamp
actual_start_timestamp
actual_end_timestamp
http_status
ech_status
outer_sni
pcap_filename
pcap_sha256
success/failure
failure_reason
```

## 10. 주요 측정값

### Detection quality

- True Positive (TP)
- False Positive (FP)
- True Negative (TN)
- False Negative (FN)
- Precision
- Recall
- F1 Score
- False Positive Rate (FPR)
- False Negative Rate (FNR)

### Operational cost

- detection latency
- feature extraction time
- detector processing time

Detection latency의 정확한 산식은 detector 구현 전에 별도 Issue에서 고정한다. Generator 단계에서는 scheduled/actual connection timestamps만 보존한다.

가능하면 각 지표를 jitter 조건별로 보고한다.

## 11. 핵심 비교

최종 결과의 핵심 비교는 다음 표를 기준으로 한다.

| Jitter | Timing Precision | Multi Precision | Timing Recall | Multi Recall | Timing F1 | Multi F1 |
|---:|---:|---:|---:|---:|---:|---:|
| 0% | | | | | | |
| 10% | | | | | | |
| 30% | | | | | | |
| 50% | | | | | | |
| 70% | | | | | | |

추가 그래프:

1. jitter vs F1
2. jitter vs Recall
3. jitter vs FNR
4. detector별 processing time

## 12. 가설 판단 기준

### 가설 지지

Jitter가 증가하는 조건에서 Multi-feature 방식이 Timing-only보다 Recall 또는 F1을 일관되게 더 잘 유지하고, 그 차이가 단순한 측정 오차 수준을 넘어 실질적인 차이로 나타나는 경우 가설을 지지한다고 판단한다.

### 부분 지지

일부 high-jitter 조건에서만 개선이 나타나거나 detection quality는 개선되지만 processing overhead가 크게 증가하는 경우 부분 지지로 판단한다.

### 가설 기각 / 지지되지 않음

다음 중 하나이면 가설이 지지되지 않은 것으로 판단한다.

- Multi-feature의 F1/Recall이 Timing-only보다 일관되게 높지 않음
- 차이가 매우 작아 실질적 개선으로 보기 어려움
- high-jitter에서 두 방식 모두 유사하게 붕괴함
- Multi-feature의 추가 비용이 탐지 개선보다 지나치게 큼

가설에 반하는 결과를 삭제하거나 숨기지 않는다.

## 13. 예상 한계

- 실제 malware C2가 아닌 synthetic beacon
- 제한된 ECH 구현 및 단일 실험 호스트
- base beacon interval `1.0 s`라는 제한된 시간 스케일
- 제한된 정상 traffic 다양성
- 실제 enterprise background traffic을 완전히 재현하지 못함
- 30개의 short-lived HTTPS flow를 하나의 trial sample로 집계하는 실험적 정의
- 실험용 multi-feature score/model이 특정 데이터 생성 방식에 과적합될 가능성

## 14. 설계 변경 규칙

실험 중 다음과 같은 변경이 필요할 수 있다.

- ECH testbed 호환성 문제
- capture 도구 변경
- feature 계산 오류 수정
- 정상 traffic 생성 방식 보완
- detector threshold calibration 절차 보완

변경 자체는 허용하지만 다음을 지킨다.

1. 변경 전 데이터는 삭제하지 않는다.
2. 변경 날짜와 이유를 research log에 기록한다.
3. 변경 전/후 데이터가 섞이지 않도록 experiment version을 구분한다.
4. 결과를 유리하게 만들기 위한 사후 조건 변경은 하지 않는다.

## 15. 재현성 목표

최종적으로 제3자가 다음 순서로 재현할 수 있게 한다.

1. Docker 기반 ECH testbed 시작
2. 정상/beacon traffic 생성
3. packet/flow metadata 수집
4. feature extraction
5. Timing-only detector 실행
6. Multi-feature detector 실행
7. metrics와 figures 재생성

최종 제출 ZIP에는 실행 스크립트와 최소 재현 절차를 포함한다.
