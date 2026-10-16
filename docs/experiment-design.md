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

Jitter는 기준 beacon interval `T`에 대해 각 요청 간격을 사전에 정의한 범위 내에서 난수화한다. 정확한 난수 공식과 seed 정책은 generator 구현 시 문서화하고 고정한다.

### 4.3 Traffic class

- Normal
- Beacon

## 5. 통제 변수

가능한 한 다음 조건을 고정한다.

- 동일한 client/server Docker host
- 동일한 ECH server 설정
- 동일한 TLS/ECH 구현 버전
- 동일한 base beacon interval
- 동일한 요청 payload 또는 제한된 고정 payload set
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

### 7.1 Beacon traffic

- 기준 interval은 구현 전에 고정한다.
- jitter 조건: 0/10/30/50/70%
- 각 jitter 조건 최소 20 trial
- 각 trial은 detector가 flow-level 특징을 계산할 수 있는 충분한 요청 수를 포함한다.

최소 beacon sample 목표:

```text
5 jitter levels × 20 trials = 100 samples
```

### 7.2 Normal traffic

최소 100 sample을 목표로 한다.

Normal traffic은 완전한 uniform random interval 하나만 사용하지 않는다. 실제 사용자의 burst/idle 특성을 단순화한 여러 정상 패턴을 사용하되, 패턴 종류와 분포는 데이터 생성 전에 고정하고 기록한다.

### 7.3 전체 목표

- 최소 약 200 flow samples
- 실제 수행 과정에서 실패 sample이 발생하면 삭제하지 않고 실패 이유를 기록한다.

## 8. Dataset split 및 threshold 원칙

탐지 임계값이나 모델 파라미터를 test 결과에 맞춰 조정하지 않는다.

경량 모델 학습 또는 threshold calibration이 필요할 경우 다음처럼 분리한다.

- calibration/train: 파라미터 결정용
- test: 최종 비교용

동일한 trial 또는 사실상 동일한 flow가 양쪽 partition에 중복되지 않게 한다.

랜덤 분할을 사용할 경우 seed를 고정하고 기록한다.

## 9. 원자료

원자료는 가능한 한 다음 계층으로 보존한다.

```text
data/raw/
  manifests/
  flow-metadata/
  [pcap은 크기/민감정보를 확인한 뒤 제출 ZIP에 선택적으로 포함]

data/processed/
  features.csv
  labels.csv

results/
  metrics/
  figures/
```

PCAP은 Git에 기본 업로드하지 않는다. 대신 trial manifest에는 PCAP filename/hash 또는 원자료 대응 정보를 남겨 raw → processed 변환을 추적할 수 있게 한다.

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
- 제한된 beacon interval 및 request profile
- 제한된 정상 traffic 다양성
- 실제 enterprise background traffic을 완전히 재현하지 못함
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
