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

---

## 2026-10-16 — 관련 논문 30편 확장 문헌검토

### 목적

본격적인 실험 전에 ECH/TLS 1.3, encrypted malware/C2, beaconing, encrypted traffic classification, timing·packet size·direction 기반 분석에 관한 실존 논문을 최소 30편 검토하여 추후 인용과 Related Work 작성의 근거를 확보한다.

### 수행 내용

- ECH/TLS 1.3 visibility 관련 연구와 survey
- encrypted malware/C2 및 beacon detection 연구
- timing, packet size, directionality 기반 encrypted traffic classification 연구
- lightweight/online classifier 연구
- QUIC 및 현대 암호화 프로토콜에서 side-channel metadata를 이용한 연구

총 30편의 저자, 연도, 출처, DOI 또는 공식 publication page, 핵심 방법, 주요 결과, 본 연구와의 관련성 및 직접 중복 여부를 검토했다.

### 문서

- 상세 문헌검토: `docs/literature-review-30.md`
- 빠른 인용 목록: `references/citation-library.md`

### 30편 검토 후 결론

문헌 범위를 확대해도 현재 Research Gap은 유지 가능하다고 판단했다. 다만 신규성은 새로운 feature 발명이 아니라 다음 제한된 실험적 기여로 정의한다.

> Native ECH 환경에서 high-jitter beacon을 대상으로 timing-only 방식과 timing·packet size·directionality·burst를 결합한 경량 다중특징 방식을 동일 조건에서 비교하고, jitter 수준별 탐지 성능 저하와 처리 비용을 함께 평가한다.

특히 다음은 기존 연구에 존재하므로 신규 기여로 주장하지 않는다.

- packet size, timing, directionality feature 자체
- ECH가 SNI/ClientHello visibility를 낮춘다는 사실
- encrypted beacon의 timing 기반 탐지
- encrypted C2 traffic classification 자체

### 실험 전 유지 결정

30편 문헌검토가 끝날 때까지 실제 결과 데이터는 생성하지 않았다. 문헌검토 결과를 반영한 뒤 사전 정의된 실험 설계에 따라 testbed 구축을 시작한다.
