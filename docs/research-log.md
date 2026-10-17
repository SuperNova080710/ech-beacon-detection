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

---

## 2026-10-17 — Native ECH testbed 로컬 구축 및 검증

### 목적

본 실험용 traffic generator와 detector를 구현하기 전에 RFC 9849 Native ECH 통신을 Docker 내부에서 반복 생성하고, 서버 acceptance와 네트워크 관찰자 관점의 SNI 가시성 차이를 검증한다.

이 단계에서 생성한 데이터는 detector 성능을 평가하기 위한 본 실험 결과가 아니라 testbed 자체의 정상 동작을 확인하기 위한 검증 자료다.

### 실행 환경

- Host: Ubuntu 22.04.4 LTS
- Docker: 26.1.4
- Docker Compose: v2.27.1
- OpenSSL: 4.0.1
- curl: 8.20.0, ECH feature enabled
- NGINX: 1.30.6, OpenSSL 4.0.1 linked
- TShark: 4.0.17, Docker image 내부 설치
- TLS: 1.3
- ECHConfig version: `0xfe0d`
- protected inner name: `protected.ech.test`
- public outer name: `public.ech.test`

호스트의 OpenSSL/curl/tshark 패키지는 변경하지 않았다. ECH와 packet-analysis 의존성은 Docker 내부에 격리했다.

### 실패 1 — 잘못된 Compose 파일 선택

처음 로컬 검증을 시작했을 때 `main` branch에는 Issue #1의 `docker-compose.yml`이 없었다. 이 상태에서 파일 경로를 명시하지 않고 `docker compose`를 실행하자 Docker Compose가 상위 경로의 기존 GitLab/Nginx/Certbot Compose를 선택했다.

그 결과 기존 `certbot` container 이름과 충돌하여 다음 유형의 오류가 발생했다.

```text
Conflict. The container name "/certbot" is already in use
```

기존 서버 container는 삭제하지 않았다.

수정:

- `#1-ech-testbed` branch로 전환
- 검증/캡처 스크립트에서 repository의 `docker-compose.yml` 경로를 명시
- 수동 명령도 `docker compose -f ./docker-compose.yml ...` 형태로 사용

### 실패 2 — OpenSSL 설정 파일 누락

첫 ECH bootstrap 실행에서 TLS 인증서 생성 전에 다음 오류가 발생했다.

```text
Can't open "/opt/openssl/openssl.cnf" for reading, No such file or directory
```

원인은 OpenSSL source build에서 `make install_sw`만 실행해 `/opt/openssl/openssl.cnf`가 설치되지 않은 것이었다.

수정:

- `make install_ssldirs` 추가
- Docker build 중 `/opt/openssl/openssl.cnf` 존재 여부 검증 추가

수정 후 다음을 확인했다.

```text
OPENSSLDIR: "/opt/openssl"
openssl.cnf: OK
```

### ECH bootstrap 결과

수정 후 `ech-bootstrap`은 `Exited (0)`으로 정상 종료했고 다음 material을 생성했다.

- self-signed TLS certificate
- SAN: `protected.ech.test`, `public.ech.test`
- RFC 9849 ECHConfig
- ECH public name: `public.ech.test`
- ECH private key 포함 PEM

NGINX는 `healthy` 상태로 기동했다.

### 실패 3 — login shell에서 custom curl PATH 소실

초기 `verify-ech.sh` 실행에서 version check는 성공했으나 `sh -lc` 내부의 요청 단계에서 다음 오류가 발생했다.

```text
sh: 2: curl: not found
```

`curl 8.20.0` 자체는 image에 존재했지만 login shell에서 image의 custom PATH가 유지되지 않은 것이 원인이었다.

수정:

- `verify-ech.sh`와 `capture-ech.sh`에서 `/opt/curl-ech/bin/curl` 절대 경로 사용

### Native ECH ON/OFF 검증 결과

`bash scripts/verify-ech.sh` 실행 결과:

ECH OFF:

```text
X-ECH-Status: NOT_TRIED
X-TLS-SNI: protected.ech.test
```

응답 본문:

```json
{"server":"protected","ech_status":"NOT_TRIED","outer_sni":"","tls_sni":"protected.ech.test"}
```

ECH ON:

```text
X-ECH-Status: SUCCESS
X-ECH-Outer-SNI: public.ech.test
X-TLS-SNI: protected.ech.test
```

응답 본문:

```json
{"server":"protected","ech_status":"SUCCESS","outer_sni":"public.ech.test","tls_sni":"protected.ech.test"}
```

NGINX access log에서도 각각 다음 상태를 확인했다.

```text
ech_status="NOT_TRIED" ech_outer_sni="-"
ech_status="SUCCESS" ech_outer_sni="public.ech.test"
```

따라서 단순 HTTPS 성공 여부가 아니라 서버 측 ECH acceptance가 실제로 `SUCCESS`임을 확인했다.

### ECH ON/OFF packet capture 결과

`bash scripts/capture-ech.sh` 실행으로 다음 파일을 생성했다.

```text
artifacts/pcap/plain.pcap
artifacts/pcap/ech.pcap
```

raw-byte sanity check 결과:

```text
PASS: ECH OFF capture contains protected SNI: protected.ech.test
PASS: ECH ON capture does not contain protected SNI as plaintext
PASS: ECH ON capture contains public outer SNI: public.ech.test
```

### Protocol-aware PCAP 검증

호스트에는 `tshark`가 설치되어 있지 않았으며, 연구 환경 격리 원칙을 유지하기 위해 host에 설치하지 않았다. 대신 `ech-tools` Docker image에 Debian Bookworm의 TShark를 추가했다.

확인 버전:

```text
TShark (Wireshark) 4.0.17
```

`bash scripts/verify-pcap.sh`가 `tls.handshake.extensions_server_name` 필드를 직접 파싱한 결과:

ECH OFF ClientHello:

```text
protected.ech.test
```

ECH ON ClientHello:

```text
public.ech.test
```

최종 결과:

```text
PASS: plain.pcap -> SNI protected.ech.test
PASS: ech.pcap   -> outer SNI public.ech.test
PASS: ech.pcap   -> protected SNI not visible in parsed ClientHello
```

따라서 네트워크 관찰자 관점에서 ECH OFF에는 protected SNI가 노출되고, ECH ON에는 public outer SNI만 노출되며 protected SNI는 파싱된 ClientHello에서 보이지 않는 것을 확인했다.

### GitHub Actions 운영 결정

초기에는 PR의 push/pull_request마다 ECH testbed CI를 자동 실행했으나 source build가 무겁고 로컬 환경에서 직접 디버깅하는 편이 효율적이었다.

현재 역할을 다음과 같이 분리했다.

```text
로컬 Docker = 개발, 디버깅, 실제 실험 및 원자료 생성
GitHub Actions = 필요할 때 실행하는 최종 재현성 검증
```

Workflow는 자동 push/pull_request trigger를 제거하고 `workflow_dispatch` 수동 실행 전용으로 변경했다.

### 최종 재기동 재현성 검증

기능 검증이 끝난 뒤 testbed를 `docker compose down`으로 종료하고 동일 Compose 구성으로 다시 기동했다.

재기동 후 다음 세 검증을 다시 수행했다.

```text
verify-ech.sh
capture-ech.sh
verify-pcap.sh
```

재검증 결과:

```text
PASS: ECH OFF -> NOT_TRIED
PASS: ECH ON  -> SUCCESS
PASS: outer SNI -> public.ech.test
```

```text
PASS: ECH OFF capture contains protected SNI: protected.ech.test
PASS: ECH ON capture does not contain protected SNI as plaintext
PASS: ECH ON capture contains public outer SNI: public.ech.test
```

```text
PASS: plain.pcap -> SNI protected.ech.test
PASS: ech.pcap   -> outer SNI public.ech.test
PASS: ech.pcap   -> protected SNI not visible in parsed ClientHello
```

재기동 후에도 최초 검증과 동일한 결과가 유지되었다.

### 최종 판정

Issue #1에서 정의한 기술적 완료 조건을 모두 충족했다.

- Docker image build 성공
- ECH bootstrap 성공
- NGINX healthy
- ECH OFF `NOT_TRIED`
- ECH ON `SUCCESS`
- outer SNI `public.ech.test`
- ECH OFF PCAP protected SNI 노출
- ECH ON PCAP protected SNI 비노출
- ECH ON PCAP public outer SNI 노출
- TShark protocol-aware ClientHello SNI 검증
- testbed 종료 후 재기동 및 동일 결과 재현

따라서 Native ECH testbed 구축 및 재현성 검증 단계는 완료로 판정한다. 다음 단계부터 Normal/Beacon traffic generator 설계 및 구현으로 진행할 수 있다.