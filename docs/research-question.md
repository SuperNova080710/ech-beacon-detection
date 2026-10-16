# T10 연구 질문 및 가설

## 1. 관심 분야

네트워크 보안 및 암호화 트래픽 기반 침입 탐지

---

## 2. 검토한 후보 주제

### 후보 1 — Native ECH 환경의 Jittered Beacon Traffic 탐지

Native Encrypted Client Hello(ECH) 환경에서 통신 주기에 jitter를 적용한 beacon traffic을
flow-level 특징을 이용해 탐지하는 방법을 연구한다.

#### 선택 이유

- ECH 적용 이후 SNI와 ClientHello 기반 네트워크 가시성이 감소하는 문제를 다룰 수 있다.
- 암호화 이후에도 남는 timing, packet size, directionality, burst 정보를 활용할 수 있다.
- 기존 timing-only beacon detector와 직접 비교할 수 있다.
- 반복 가능한 synthetic traffic을 직접 생성할 수 있다.
- 탐지 알고리즘을 직접 구현하고 정량 평가할 수 있다.

### 후보 2 — ECHConfig Rotation과 stale DNS cache

ECHConfig 교체 과정에서 DNS cache에 이전 설정이 남았을 때 발생하는 retry 및
연결 지연을 중첩 배포 정책으로 완화하는 방법을 연구한다.

#### 제외 이유

ECHConfig, DNS caching, key rotation 환경을 모두 구성해야 하므로
T10 제한 시간 안에 충분한 반복 실험과 분석까지 수행하기에는 구축 비용이 크다고 판단했다.

### 후보 3 — Post-Quantum DNSSEC와 Compact Denial

Post-Quantum 서명 알고리즘을 DNSSEC에 적용했을 때 RFC 9824 Compact Denial이
응답 크기와 fragmentation을 얼마나 줄이는지 연구한다.

#### 제외 이유

연구 공백은 명확하지만 Post-Quantum DNSSEC authoritative signer와 resolver 지원이
아직 제한적이어서 실험보다 기반 환경 구현에 시간이 과도하게 소비될 가능성이 있다.

---

## 3. 최종 연구 주제

Native ECH 환경에서 Jittered Beacon Traffic 탐지를 위한
경량 다중특징 Flow 기반 탐지기의 설계 및 평가

영문:

Design and Evaluation of a Lightweight Multi-Feature Flow-Based Detector
for Jittered Beacon Traffic under Native ECH

---

## 4. 연구 질문

Native ECH 환경에서 beacon traffic의 jitter가 증가할 때,
timing-only 탐지와 timing, packet size, directionality, burst 특성을 결합한
경량 다중특징 탐지 방식의 탐지 성능은 어떻게 달라지는가?

---

## 5. 최종 가설

Native ECH 환경에서 timing, packet size, directionality, burst 특성을 결합한
경량 다중특징 탐지 방식은 timing-only 탐지 방식보다
jitter가 증가한 beacon traffic의 탐지율을 더 높게 유지할 것이다.

---

## 6. 독립 변수

### 탐지 방식

- Timing-only detector
- Multi-feature detector

### Beacon jitter

- 0%
- 10%
- 30%
- 50%
- 70%

---

## 7. 종속 변수

- Precision
- Recall
- F1 Score
- False Positive Rate
- False Negative Rate
- Detection latency
- Processing time

---

## 8. 측정 방법

Timing-only detector는 inter-arrival time의 평균, 표준편차,
Coefficient of Variation(CV)을 중심으로 beacon 주기성을 판단한다.

Multi-feature detector는 다음 특징을 함께 사용한다.

### Timing

- Mean inter-arrival time
- Inter-arrival CV
- Median Absolute Deviation

### Packet Size

- Mean packet size
- Packet size standard deviation
- Packet size CV

### Directionality

- Outbound / inbound packet ratio
- Byte asymmetry
- Direction-change ratio

### Burst

- Burst count
- Mean burst size
- Burst interval CV

---

## 9. 가설 반증 조건

Jitter 증가 조건에서 Multi-feature detector의 F1 Score 또는 Recall이
Timing-only detector보다 일관되게 높지 않거나,
그 차이가 실질적으로 미미한 경우 가설은 지지되지 않은 것으로 판단한다.

결과가 가설과 반대로 나오더라도 데이터를 제거하거나 실험 조건을 사후 변경하지 않는다.

---

## 10. 데이터 수집 범위

### Traffic class

- Normal
- Beacon

### ECH

- Native ECH enabled

### Jitter

- 0%
- 10%
- 30%
- 50%
- 70%

### 반복 횟수

각 beacon jitter 조건 최소 20회

정상 traffic도 최소 100개 sample을 수집하여 비교한다.

목표 데이터셋 규모는 약 200 samples 이상으로 한다.

---

## 11. 연구 범위

본 연구는 실제 악성 C2 프로그램을 사용하지 않는다.

정상적인 HTTPS 요청을 일정 간격으로 발생시키는 synthetic beacon generator를 사용하여
C2 beacon의 통신 패턴만 재현한다.

따라서 연구 대상은 악성코드 자체가 아니라,
ECH 적용 이후 flow metadata를 이용한 beacon traffic 탐지 가능성이다.

---

## 12. 예상 한계

- 단일 또는 제한된 ECH 구현 환경
- 실제 malware C2가 아닌 synthetic beacon
- 제한된 beacon interval
- 제한된 정상 traffic pattern
- 실제 기업 네트워크 수준의 background traffic을 완전히 재현하지 못함
- Multi-feature detector가 실험 데이터 특성에 과적합될 가능성
