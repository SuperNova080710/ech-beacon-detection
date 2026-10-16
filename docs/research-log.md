# Research Log

연구 과정에서 내린 결정, 변경 사항, 실패한 실험을 시간순으로 기록한다.

결과를 확인한 뒤 기존 기록을 삭제하거나 유리하게 수정하지 않는다.

---

## 2026-10-16 — 연구 주제 선정

### 검토 분야

- 인증 및 Passkey
- Post-Quantum DNSSEC
- ECH protocol
- Encrypted C2 / Beacon detection
- XDR detection

### 최종 선택

Native ECH 환경에서 Jittered Beacon Traffic 탐지를 위한
경량 다중특징 Flow 기반 탐지기의 설계 및 평가

### 선택 이유

1. 최근 ECH 환경에서 네트워크 가시성 감소 문제가 존재한다.
2. 기존 timing 기반 beacon 탐지를 확장할 수 있다.
3. jitter가 증가했을 때 탐지 성능 변화를 직접 측정할 수 있다.
4. synthetic traffic으로 재현 가능한 원자료를 직접 생성할 수 있다.
5. T10 기간 안에 구현, 반복 실험, 분석까지 수행할 가능성이 높다.

### 현재 가설

Timing, packet size, directionality, burst 특성을 결합한 탐지 방식은
timing-only 방식보다 높은 jitter 조건에서 beacon 탐지 성능을 더 잘 유지할 것이다.

### 현재 결정

아직 실험을 실행하지 않는다.

선행 연구와 실험 설계를 문서로 확정한 후 구현을 시작한다.

---

## 2026-10-16 — 선행연구 검증 완료

### 확인한 핵심 자료

- RFC 9849 — TLS Encrypted Client Hello
- ECH Deployment Considerations Internet-Draft
- TLS 1.3/ECH encrypted-traffic detection review
- timing/CV 기반 encrypted beacon detection 연구
- TQH-C2 high-jitter encrypted C2 공개 데이터셋
- packet size/direction/arrival-time 기반 encrypted traffic classification 연구
- 경량 packet size/inter-arrival 기반 encrypted traffic classification 연구
- packet/global-statistic fusion 기반 encrypted traffic classification 연구

### 확인 결과

다음 내용은 기존 연구에 이미 존재하므로 새로운 기여로 주장하지 않기로 했다.

- ECH가 SNI 등 ClientHello 정보를 숨긴다는 사실
- ECH가 네트워크 보안 가시성을 감소시킬 수 있다는 문제
- timing metadata를 통한 encrypted beacon 탐지
- jittered encrypted C2 traffic 자체
- packet size, directionality, timing metadata를 이용한 encrypted traffic 분석

### Research Gap 한정

본 연구의 신규성 주장은 다음 범위로 제한한다.

> Native ECH가 실제 활성화된 환경에서 high-jitter beacon traffic을 대상으로 timing-only detector와 timing·packet size·directionality·burst를 결합한 경량 detector를 동일 조건에서 비교하고, jitter 증가에 따른 detection-quality degradation과 processing overhead를 함께 정량 평가한다.

`세계 최초`, `기존 연구가 없다`와 같은 과도한 표현은 사용하지 않는다.

세부 내용은 `docs/related-work.md`와 `references/references.md`에 기록했다.

---

## 2026-10-16 — 실험 사전 설계 확정

### 비교 대상

1. Timing-only detector
2. Lightweight multi-feature detector

### Jitter 조건

- 0%
- 10%
- 30%
- 50%
- 70%

### 목표 데이터

- Beacon: jitter 조건별 최소 20 trial, 총 최소 100 samples
- Normal: 최소 100 samples
- 전체 목표: 약 200 samples 이상

### 핵심 지표

- Precision
- Recall
- F1 Score
- FPR
- FNR
- Detection latency
- Feature extraction / detector processing time

### 데이터 누수 방지

Threshold 또는 모델 파라미터가 필요하면 calibration/train partition에서만 결정하고 최종 test 결과에 맞춰 사후 조정하지 않는다.

### 현재 결정

실험 코드를 작성하기 전에 연구 질문, 선행연구, 연구 공백, 비교 방식, 반증 조건까지 문서로 고정했다.

다음 단계는 native ECH testbed의 재현 가능성을 확인하고, 실험 환경을 repository 내부에서 고정하는 것이다.
