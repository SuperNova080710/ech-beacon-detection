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

### 재기동 재현성 검증

Testbed를 종료한 뒤 다시 기동하고 다음 세 검증을 반복했다.

- `bash scripts/verify-ech.sh`
- `bash scripts/capture-ech.sh`
- `bash scripts/verify-pcap.sh`

세 검증 모두 최초 실행과 동일하게 PASS했다.

따라서 Issue #1의 Native ECH testbed는 로컬 Docker 환경에서 재기동 후에도 동일 결과를 재현할 수 있음을 확인했다.

---

## 2026-10-17 — Traffic Generator 사전 조건 고정

### 목적

Issue #3의 generator를 구현하기 전에 결과를 보고 바꾸지 않을 timing, seed, payload, sample 정의를 먼저 고정한다.

### Sample 정의

한 sample은 단일 TCP 5-tuple 하나가 아니라 동일 client에서 동일 protected ECH server로 발생한 **30개의 short-lived HTTPS flow sequence**로 정의한다.

각 transaction은 별도의 curl 프로세스로 새 TLS/ECH 연결을 사용한다.

### Beacon 조건

- base interval: `1.0 s`
- jitter: `0/10/30/50/70%`
- jitter별 `20 trials`
- trial당 `30 transactions`
- scheduled IAT: `29개`

Jitter는 다음으로 고정한다.

```text
z_i ~ Uniform(-1, 1)
I_i(j) = 1.0 × (1 + j × z_i)
```

동일 trial 번호는 jitter level이 달라도 같은 normalized `z_i` sequence를 사용한다. 따라서 jitter amplitude만 달라지는 paired comparison을 수행할 수 있다.

Beacon timing seed는 다음으로 고정한다.

```text
trial_seed = 20261017 + trial_id
```

### Normal 조건

총 100 samples를 다음 세 profile로 나눈다.

- interactive-burst: 40
- irregular-lognormal: 30
- mixed-activity: 30

각 sample은 30 transactions를 포함한다.

Normal timing seed는 beacon과 별도 namespace를 사용한다.

```text
normal timing seed base = 20262017
```

### Payload 조건

Beacon과 Normal은 class label에 payload 크기가 직접 대응하지 않도록 동일한 profile과 선택 확률을 사용한다.

- small: query 32 B / response 128 B / probability 0.50
- medium: query 128 B / response 512 B / probability 0.35
- large: query 512 B / response 2048 B / probability 0.15

Beacon payload seed base는 `20263017`, Normal payload seed base는 `20264017`로 분리한다.

동일 beacon trial 번호는 모든 jitter level에서 같은 payload profile sequence를 사용한다.

### Pilot 원칙

본 실험 200 samples를 바로 생성하지 않는다.

먼저 다음 8 trials만 실행하여 generator 정확성과 재현성을 검증한다.

- Beacon: jitter별 trial 1 → 5 trials
- Normal: 각 profile trial 1 → 3 trials

Pilot 결과는 detector 성능 평가 데이터로 사용하지 않는다.

### 현재 상태

이 기록 시점에는 아직 pilot 결과를 생성하지 않았다. 다음 단계는 generator 코드와 trial capture orchestration을 구현한 뒤 정적 테스트를 통과시키는 것이다.

---

## 2026-10-17 — Traffic Generator 구현 및 pilot 검증

### 구현 완료

Issue #3에서 다음을 구현했다.

- deterministic beacon jitter generator
- Normal traffic 3개 profile
- class-independent payload profile
- Native ECH HTTPS transaction runner
- trial별 manifest 및 flow-metadata CSV
- trial별 PCAP capture와 SHA-256 매핑
- TShark 기반 ClientHello timestamp / outer SNI 추출
- scheduled IAT와 network-observed ClientHello IAT 비교
- 8-trial pilot 자동 검증

정적 generator unit test는 총 10개이며 모두 통과했다.

### 실패 4 — Python minimal image에서 `unittest` 누락

초기 `ech-tools` image에는 `python3-minimal`을 사용했다. 이 image에서 다음 오류가 발생했다.

```text
ModuleNotFoundError: No module named 'unittest'
```

원인은 generator 코드가 아니라 Debian minimal Python package가 전체 표준 라이브러리를 포함하지 않는 것이었다.

수정:

- `python3-minimal` → `python3`
- Docker build 단계에서 `json`, `random`, `statistics`, `unittest` import 검증 추가

수정 후 10개 unit test가 모두 PASS했다.

### 실패 5 — `pilot-v1` 마지막 ClientHello 캡처 누락

최초 8-trial pilot `pilot-v1`에서 generator 관점의 요청은 모두 성공했다.

각 trial:

```text
TRANSACTIONS=30
STATUS=success
```

Native ECH도 정상적으로 `SUCCESS`를 반환했다.

하지만 PCAP finalization 결과 모든 trial의 ClientHello count가 다음처럼 29개였다.

```text
CLIENTHELLO_COUNT=29
```

최종 pilot verifier는 다음 조건에서 실패했다.

```text
expected 30 ClientHello packets, got 29
```

이 실패 데이터는 삭제하지 않고 `pilot-v1` raw data/PCAP으로 보존했다.

### 원인 분리

동일 PCAP에 대해 TShark filter를 두 방식으로 재확인했다.

```text
tls.handshake.type == 1 && !tcp.analysis.retransmission → 29
tls.handshake.type == 1                            → 29
```

따라서 retransmission filter 때문에 하나가 제외된 것은 아니었다.

또한 10/30/50/70% jitter 조건에서도 scheduled-vs-PCAP IAT 오차가 수 ms 수준으로 작았으므로 첫 ClientHello 누락보다는 마지막 ClientHello가 캡처 종료 시점에 유실된 패턴과 일치했다.

### 수정

`run-traffic-trial.sh`의 capture 종료 절차를 다음처럼 수정했다.

1. generator 종료 후 capture drain 시간 확보
2. tcpdump에 SIGINT 전달
3. tcpdump가 실제 종료했는지 확인
4. zombie 상태를 종료 완료로 판정
5. 종료 이후에만 PCAP SHA-256과 TShark 분석 수행

### `capture-check-v1` 회귀 검증

70% jitter beacon 단일 trial로 회귀 검증했다.

```text
TRANSACTIONS=30
CLIENTHELLO_COUNT=30
MEAN_ABS_IAT_ERROR_S=0.002370569
MAX_ABS_IAT_ERROR_S=0.009560842
PASS: beacon-j70-t01
```

같은 PCAP을 TShark로 별도 읽어도 ClientHello count가 `30`임을 확인했다.

### `pilot-v2` 최종 결과

수정 후 새로운 run tag `pilot-v2`로 8-trial pilot을 다시 실행했다.

모든 Beacon/Normal trial이 다음을 만족했다.

- 30 HTTPS transactions
- 30 protocol-parsed ClientHello
- HTTP 200
- expected Content-Length
- Native ECH `SUCCESS`
- outer SNI `public.ech.test`
- manifest / PCAP SHA-256 mapping
- scheduled / network-observed IAT 보존

trial별 mean absolute scheduled-vs-PCAP IAT error:

```text
beacon-j00-t01                  0.001442054 s
beacon-j10-t01                  0.001286469 s
beacon-j30-t01                  0.001379604 s
beacon-j50-t01                  0.002455262 s
beacon-j70-t01                  0.002432466 s
normal-interactive-burst-t01    0.001929140 s
normal-irregular-lognormal-t01  0.001476971 s
normal-mixed-activity-t01       0.001600079 s
```

최종 verifier:

```text
PASS: all 8 pilot trials satisfy the pre-defined generator conditions
PASS: Native ECH SUCCESS and public outer SNI confirmed for every transaction
PASS: 30 protocol-parsed ClientHello packets confirmed per trial
PASS: scheduled and network-observed ClientHello IAT are both preserved
PASS: paired jitter and payload sequences are deterministic
```

### 현재 결정

Issue #3의 generator 구현과 pilot 검증은 완료했다.

- `pilot-v1`: 실패 원자료 보존
- `capture-check-v1`: capture 종료 수정 회귀 검증
- `pilot-v2`: 최종 성공 pilot

Pilot 데이터는 detector 성능 평가에는 사용하지 않는다.

아직 최종 200+ sample 본 실험은 실행하지 않는다. 다음 단계는 PCAP 기반 feature extractor의 정의와 구현이며, feature 정의를 고정한 뒤 본 실험 데이터를 생성한다.

---

## 2026-10-17 — PCAP Feature Extractor 구현 및 pilot 검증

### 목적

Issue #5에서 Native ECH PCAP을 입력으로 Timing-only / Multi-feature detector가 공통으로 사용할 trial-level feature extractor를 구현하고, detector 구현 전에 feature schema와 계산 방식을 동결한다.

Pilot 데이터는 extractor 자체의 정확성·재현성 검증에만 사용하며 최종 detector 성능 평가에는 사용하지 않는다.

### Feature 정의

Feature Extractor는 generator의 scheduled interval이나 payload profile 값을 feature 계산에 직접 사용하지 않고 실제 PCAP metadata에서 계산한다.

Flow 정의:

```text
protocol       = TCP
server port    = 8443
flow ID        = tcp.stream
flow start     = 최초 client → server SYN (SYN=1, ACK=0)
packet size    = IPv4 ip.len
```


Direction:

```
outbound = tcp.dstport == 8443
inbound  = tcp.srcport == 8443
```

Burst threshold:

```
flow-start IAT <= 0.5 s : same burst
flow-start IAT >  0.5 s : new burst
```

최종 feature schema는 다음 13개로 고정했다.

```
Timing
- iat_mean_s
- iat_std_s
- iat_cv
- iat_mad_s

Packet size
- packet_size_mean_bytes
- packet_size_std_bytes
- packet_size_cv

Directionality
- out_in_packet_ratio
- byte_asymmetry
- direction_change_ratio

Burst
- burst_count
- burst_mean_size
- burst_interval_cv
```

표준편차는 population standard deviation을 사용하고 MAD에는 scale factor를 적용하지 않는다.

### 순수 계산 검증

Feature 계산 unit test 6개를 실행했다.

```
Ran 6 tests in 0.001s
OK
```

검증 대상:

- constant IAT
- population standard deviation
- directionality 계산
- 0.5 s inclusive burst boundary
- denominator가 없는 경우 missing 처리
- NaN/Infinity 검출

### `pilot-v2` PCAP extraction 결과

Issue #3의 최종 성공 pilot 8개를 대상으로 extractor를 실행했다.

모든 trial:

```
flow_count       = 30
flow_start_count = 30
iat_count        = 29
packet_count     = 510
validation       = pass
```

최종 검증:

```
PASS: pilot-v2 contains exactly 8 feature rows and 8 label rows
PASS: all 13 features are finite for every pilot trial
PASS: feature and label trial IDs match one-to-one
PASS: all pilot trials contain 30 TCP flows and 29 flow-start IAT values
PASS: provenance validation and extraction timing are complete
PASS: Feature Extractor pilot completed for RUN_TAG=pilot-v2
```

### Feature sanity check

실제 추출 결과에서 다음을 확인했다.

Beacon jitter 증가에 따라 timing variation이 증가했다.

```
jitter 0%  iat_cv ≈ 0.0015
jitter 10% iat_cv ≈ 0.0591
jitter 30% iat_cv ≈ 0.1734
jitter 50% iat_cv ≈ 0.2816
jitter 70% iat_cv ≈ 0.3867
```

Normal interactive-burst는:

```
burst_count     = 9
burst_mean_size = 3.333...
```

로 나타나 generator의 burst 구조가 PCAP 기반 feature에 반영됨을 확인했다.

동일 beacon trial 번호는 paired payload design을 사용하므로 packet-size/directionality 값이 jitter 수준 사이에서 거의 동일하게 나타나는 것도 설계와 일치했다.

### Feature / label 분리

Detector leakage를 방지하기 위해 processed output을 다음처럼 분리했다.

```
features.csv
  trial_id + 13 features

labels.csv
  trial_id
  traffic_class
  label
  jitter_pct
  normal_profile
```

`traffic_class`, `jitter_pct`, `normal_profile`은 feature 입력에 포함하지 않는다.

### 결정성 검증

같은 raw PCAP과 manifest에 extractor를 다시 실행했다.

재추출 전후 SHA-256:

```
features.csv
a9199ee5096748b7c629a498bc7e3859ae510ff5e3a09a0c9151963588323857

labels.csv
da8f9febac90dbb94ab0a7c65a81650adeddf05d91443d68c82c2b5db1518dde
```

두 hash는 재추출 전후 동일했다.

```
PASS: feature output deterministic
```

`provenance.json`은 실행 시각과 처리 시간 측정값을 포함하므로 byte-identical 대상으로 사용하지 않는다.

### Feature schema 동결

Pilot 검증과 deterministic 재추출을 통과했으므로 detector 구현 전에 다음 조건을 동결한다.

```
extractor_schema_version   = 1
feature_definition_version = 1.0.0
server_port                = 8443
expected_flow_count        = 30
burst_gap_threshold_s      = 0.5
feature_count              = 13
```

Detector 결과를 확인한 뒤 feature 정의나 burst threshold를 사후 조정하지 않는다.

향후 구현 오류 때문에 변경이 반드시 필요하면 기존 정의를 덮어쓰지 않고 feature definition version을 올려 별도 기록한다.

### 현재 결정

Issue #5의 Feature Extractor 구현 및 pilot acceptance 검증은 완료했다.

다음 단계에서는 동결된 feature schema `1.0.0`을 그대로 사용해 Timing-only detector와 Multi-feature detector의 설계를 진행한다.

---

## 2026-10-18 — Timing-only Baseline Detector 사전 정의 및 검증

### 목적과 사전 고정 사항

Issue #7에서 Feature Extractor schema `1.0.0`의 `iat_cv` 하나를 사용하는 Timing-only baseline을 구현했다. detector 성능 데이터를 확인하기 전에 점수·판정 연산자·calibration/test split·threshold 선정 방식을 고정했다.

- `score = iat_cv`
- `CV < threshold`이면 Beacon(1), 같거나 크면 Normal(0)
- Beacon trial 번호 `1..10` × jitter 5개 = calibration 50개, `11..20` = held-out test 50개
- Normal calibration: interactive-burst 16개, irregular-lognormal 12개, mixed-activity 12개 = 40개
- Normal test: 24+18+18 = 60개; held-out 전체 110개
- paired jitter 실험에서 동일 Beacon trial 번호는 같은 partition
- threshold는 Normal calibration CV 40개의 세 번째 최솟값 `x_(3)`으로 고정
- strict `<`이므로 ties를 포함해 empirical **calibration** FPR이 최대 2/40=5%; **test** FPR 보장은 아님
- `pilot-v1`, `capture-check-v1`, `pilot-v2`는 threshold calibration과 평가에서 제외

### 구현 내용

- `detector/timing_only.py`: CV 입력 검사, strict boundary, normal-only calibration, 200개 trial catalog와 fixed split
- `detector/timing_only_cli.py`: `split → calibrate → predict` CLI, feature/label 파일 분리, extractor provenance/version 확인, hash 및 calibration fingerprint 검사, overwrite 거부
- `detector/config.json`: detector/feature schema version과 calibration 규칙
- `detector/test_timing_only.py`: 순수 unit tests
- `detector/test_timing_only_cli.py`: 임시 synthetic 200개 sample을 이용한 통합 검증
- `docs/timing-only-baseline.md`: 사전 등록한 수식/분할/실행 절차

### 로컬 검증 결과

2026-10-18 사용자 로컬 Ubuntu/Python 환경에서 다음을 실행했다.

```text
python3 detector/test_timing_only.py
Ran 10 tests in 0.002s
OK

python3 detector/test_timing_only_cli.py
Ran 13 tests in 0.233s
OK

git diff --check -> 출력 없음
git status --short -> 출력 없음
```

검증 범위에는 threshold 3번째 순서통계량 및 ties, CV 유한값, paired jitter split, 90/110 catalog, pilot 제외, label-free inference, checksum/threshold 변조 거부, 버전 불일치, 중복/누락 trial, 재현 가능한 예측, output overwrite 거부가 포함된다.

### 평가 및 미완료 사항 구분

**23개 테스트는 synthetic fixture 기반 구현 검증이지, 실제 탐지 품질 검증이 아니다.** 실제 calibration threshold는 계산하지 않았고 Native ECH 본 실험 200개 sample의 수집/추출도 아직 수행하지 않았다. 실제 test Precision/Recall/F1/FPR/FNR, jitter별 탐지율, timing overhead의 본 실험 분포는 **미측정**이다.

이후 Multi-feature Detector 설계에서도 동일한 test partition을 사용하며, 결과를 확인한 후 threshold/feature definition을 소급 수정하지 않는다. 규칙 변경이 필요한 오류가 발생하면 별도 버전 및 research log에 기록한다.

---

## 2026-10-18 — Multi-feature Detector 구현 및 synthetic 통합 검증

### 목적과 사전 설계 고정

Issue #9에서 Feature Extractor schema 1.0.0이 제공하는 timing(4), packet size(3), directionality(3), burst(3)의 **13개 특징 전부**를 사용하는 경량 Multi-feature Detector를 구현했다. 학습 파라미터와 threshold 계산 방식은 **실제 200개 본 실험 데이터 관찰 이전**에 `docs/multi-feature-detector.md`로 고정하고 커밋했다.

### 모델과 데이터 분리

- 모델: L2 정규화 이진 로지스틱 회귀, 선형 logit 점수
- 결정적 full-batch gradient descent, learning rate `0.1`, epochs `800`, L2 lambda `0.1`, 초기 파라미터 0, early stopping 없음
- 원본 Feature Extractor v1.0.0의 13개 값을 고정 순서 사용, label/jitter/profile/trial ID는 학습 특징에서 제외
- Timing-only Issue #7과 동일한 split: Calibration Beacon 50+Normal 40, held-out test Beacon 50+Normal 60
- Calibration 90개로만 z-score mean/population std와 가중치/intercept 학습; zero-variance feature의 scale은 1
- Calibration Normal 40개의 logit을 내림차순 정렬하고 세 번째 점수를 threshold로 선택
- `score > threshold`이면 Beacon(1), 동률·미만이면 Normal(0)
- Calibration Normal 40개는 학습과 threshold 추정에 **동시에 포함**되므로 empirical calibration FPR≤5%는 **in-sample 제약**이다. held-out test FPR 보장은 아니다
- Pilot-v1, capture-check-v1, pilot-v2는 detector 학습 및 성능 평가에서 배제

### 구현 파일

- `detector/multi_feature.py`: scaling, L2 logistic training, logit score, Normal-only threshold
- `detector/multi_feature_cli.py`: calibration-only `train`, label-free `predict`, frozen schema 및 SHA-256/fingerprint 검증, 기존 출력 overwrite 거부
- `detector/synthetic_fixture.py`: 실제 traffic data를 사용하지 않는 synthetic 200행 fixture
- `detector/test_multi_feature.py`: 20개 model/CLI unit/integration test
- `docs/multi-feature-detector.md`: 실험 전 동결한 규칙과 후속 재현 절차

### 로컬 검증 (2026-10-18)

```text
python3 detector/test_timing_only.py
Ran 10 tests in 0.002s
OK

python3 detector/test_timing_only_cli.py
Ran 13 tests in 0.234s
OK

python3 detector/test_multi_feature.py
Ran 20 tests in 3.244s
OK

전체 43/43 PASS
git diff --check: 출력 없음
git status --short: 출력 없음
```

검증 범위는 deterministic training, 13특징/0분산, strict threshold 및 동률, 40개 calibration Normal·third-largest threshold, NaN/Infinity 거부, 90/110 split, test label 미사용, test data를 제거해도 학습 fingerprint 동일, prediction CSV byte-identical, model/calibration/test checksum 변조 거부, schema mismatch, output overwrite 차단이다. 누락·중복 trial ID 및 pilot 배제는 재사용하는 Issue #7 shared split 단계의 회귀 테스트로 검증했다.

### 연구상 결과와 미측정 구분

위 43개 PASS는 **synthetic fixture 기반 코드 정합성 검증**만 의미한다. 실제 Native ECH 본 실험 200 trials PCAP/processed feature는 아직 생성되지 않았고, 실제 모델 가중치·threshold, held-out Precision/Recall/F1/FPR/FNR, jitter별 결과와 runtime overhead는 **미측정**이다.

Multi-feature가 Timing-only보다 높은 jitter에서 좋은 성능을 얻는지는 확인되지 않았다. 실제 실험 결과가 가설과 다르더라도 저장·보고하며, 본 실험 test 결과를 본 뒤 학습 hyperparameter, feature set, threshold 또는 partition을 사후 변경하지 않는다.

---

## 2026-10-18 — 본 실험 200개 Native ECH trial 수집 자동화 사전 준비

### 상태

Timing-only Baseline (#7) 및 Multi-feature Detector (#9)의 구현과 synthetic 테스트는 완료했으나, **실제 본 실험 PCAP 200개는 아직 수집하지 않았다**. 이 시점에는 본 실험 성능·가중치·threshold 및 jitter별 F1/Recall/FPR/FNR 수치가 없다.

### 고정한 실행 계획

- Generator 기존 config를 그대로 사용해 Beacon 5 jitter × 20 trial = 100개, Normal interactive 40 + lognormal 30 + mixed 30 = 100개
- 1-based 실행 순번 `1..200`을 사전 정의: Beacon j00/j10/j30/j50/j70 각 20개, 이후 Normal profile별 40/30/30개
- Trial마다 30개 HTTPS Native ECH 요청, 30 ClientHello, 29 flow-start IAT 검증
- Paired jitter 난수열 및 payload profile sequence, class-independent payload 설정 유지
- Raw PCAP hash와 manifest, flow-metadata CSV, ECH SUCCESS, outer SNI를 재검증
- 실험 run-tag는 `main-v1`과 같은 새 이름만 허용, pilot/diagnostic run-tag 금지

### 실패·중단 보존 원칙

- 실제 캡처는 실행기가 `EXECUTE=1`을 받았을 때에만 동작하며 기본은 dry-run
- 실행 도중 기존 manifest/PCAP를 삭제하거나 덮어쓰지 않음
- Trial 시작 마커를 먼저 생성하여 파일 생성 전 중단된 경우도 재시도로 덮어쓰지 않음
- 이미 완성된 trial은 PCAP 원자료와 manifest를 재검증한 뒤에만 skip
- Generator 소스 및 ECH material SHA-256을 run environment에 저장하여 동일 run-tag에 변경된 실험 환경을 혼용하지 않음
- 한 번에 한 trial만 캡처하고 중단/실패 증거를 보존

### 코드/문서 상태

- `generator/experiment_plan.py`: 정확한 200개 trial catalog 및 batch/dry-run
- `scripts/run-main-experiment.sh`: `EXECUTE=1` 안전장치, checkpoint, serialized capture, restart verification
- `generator/verify_main.py`: 실제 raw PCAP ClientHello 재파싱 및 generator 조건 검증
- `extractor/verify_main_features.py`: processed 200행, schema 및 PCAP provenance 검증
- `scripts/extract-main-features.sh`: raw 200개 전체 PASS 후 extractor 실행
- `generator/test_main_experiment.py`, `extractor/test_main_features.py`: Docker 트래픽 없는 synthetic/offline 검증
- `docs/main-experiment.md`: 실행·보존·후속 평가 절차

### 다음 게이트

1. 사용자 로컬 Linux에서 신규 unit/offline 테스트와 dry-run이 PASS인지 확인
2. Docker Native ECH 환경 precheck
3. 승인된 작은 batch로 실제 수집 시작, 이후 200개 완료 여부와 원자료 검증 확인
4. 검증된 200개에 대해 extractor 1.0.0 실행 후 feature/label/provenance 검사
5. 후속 분석에서 기존 90/110 calibration/test 분할 및 두 detector를 변경 없이 적용

본 기록은 **실제 실험을 실행했다고 주장하지 않는다**. 실제 실행에서 실패가 발생하면 실패 증거를 삭제하지 않고 별도 항목으로 남긴다.

---

## 2026-10-18 — Issue #11 오프라인 200-trial 계획 검증 결과

본 실험 수집 스크립트 구현 후 사용자 Linux 개발 환경에서 **실제 traffic을 발생시키지 않는** 사전 검증을 수행했다.

```text
python3 generator/test_main_experiment.py
Ran 11 tests in 0.178s
OK

python3 extractor/test_main_features.py
Ran 4 tests in 0.185s
OK

python3 generator/test_traffic_model.py
Ran 10 tests in 0.002s
OK

python3 extractor/test_feature_math.py
Ran 6 tests in 0.001s
OK

총 31/31 test PASS (동시 실행 잠금 보완 이전)
bash -n scripts/run-main-experiment.sh -> 출력 없음
bash -n scripts/extract-main-features.sh -> 출력 없음
git diff --check -> 출력 없음
git status --short -> 출력 없음
```

Dry-run 명령:

```bash
RUN_TAG=main-v1 START=1 END=200 bash scripts/run-main-experiment.sh
```

200개 trial 전체 출력 확인: `001/200 beacon-j00-t01`부터 `200/200 normal-mixed-activity-t30`; 마지막 메시지 `DRY RUN ONLY. Set EXECUTE=1 to collect real Native ECH PCAP.`

검증한 것: trial 200개 정확한 catalog/순서, pilot/invalid tag 거부, paired Beacon random sequence, raw/processed synthetic fixture의 검증 경로, Generator와 Feature Math 회귀 테스트, 실험용 Bash 구문. **Synthetic 200행 출력에 대한 PASS를 실제 raw PCAP/feature 200개 수집 성공으로 해석하지 않는다.**

### 코드 안전성 검토 후 추가 수정

수집 runner의 기존 `flock` 경로가 run-tag별이라 서로 다른 run-tag 사이에서는 공유 packet-capture 환경을 동시에 사용할 위험을 발견했다. `1bec73e` 커밋에서 사용자 단위의 **공통 lock**으로 변경하고 재발 방지 테스트 1개를 추가했다.

이 수정 후 신규 `generator/test_main_experiment.py`의 **12번째 테스트 재실행 결과는 아직 미확인**이며, 실제 ECH Docker precheck 및 Native ECH 실트래픽 본 실험 역시 미실행 상태다. 원격 수정 반영 후 다시 `bash -n`과 12개 테스트를 수행한다.

## 현재 판단

Issue #11의 수집·검증 코드 준비 및 최초 오프라인 검증은 성공했다. 그러나 200개 Native ECH raw/PCAP 수집, 13-feature extraction 200개 검증, 실제 모델 calibration 및 held-out test 성능 측정은 아직 수행하지 않았다. 실패가 발생하면 기존 데이터를 보존하고 본 실험 규칙을 사후 변경하지 않는다.

---

## 2026-10-19 — Issue #11 전체 run-tag 공통 잠금 보완 후 재검증

2026-10-18 커밋 `1bec73e`에서 공통 packet-capture namespace를 서로 다른 run-tag가 동시에 점유하지 못하도록 공유 `flock` 경로를 적용했다. 신규 회귀 테스트가 포함된 코드를 사용자 Linux에서 다시 실행했다.

```text
python3 generator/test_main_experiment.py
Ran 12 tests in 0.175s
OK

python3 extractor/test_main_features.py
Ran 4 tests in 0.183s
OK

bash -n scripts/run-main-experiment.sh -> 출력 없음
bash -n scripts/extract-main-features.sh -> 출력 없음
git diff --check -> 출력 없음
git status --short -> 출력 없음
```

이번에 확인한 `test_global_capture_lock_is_shared_between_run_tags`를 포함해 신규 오프라인 테스트 **16/16 PASS**. 기존 Generator 10개, Feature Math 6개는 앞선 검증에서 통과했으며 이번 재실행 로그에는 포함되지 않았다. 본 실험 dry-run 200개 전체 순서도 앞서 별도로 확인했다.

**현재 완료 범위:** 수집 스크립트·검증기의 synthetic/offline 테스트, Bash 문법, dry-run 확인. 아직 실제 Docker Native ECH preflight는 이번 기록에서 검증되지 않았으며 실제 본 실험 200개 raw PCAP·processed feature 수집은 시작하지 않았다. 탐지 임계값·실험 결과 지표도 미측정이다.

---

## 2026-10-19 — Issue #11 Native ECH 본 실험 완료

### 실험 환경 및 조건

- Run tag: `main-v1`
- 수집 기준 Git commit: `9d4dcb1`
- Native ECH 기반 HTTPS 트래픽 수집
- Beacon 100개: jitter 0/10/30/50/70% × 20개
- Normal 100개: interactive-burst 40개, irregular-lognormal 30개, mixed-activity 30개
- Trial당 HTTPS 트랜잭션 30개, TCP Flow 30개, Flow 시작 시각 기준 IAT 29개
- Generator 및 Extractor의 동결된 실험 조건 유지

### Raw 데이터 수집 및 검증

- 총 200/200개 PCAP, manifest, flow metadata 수집 완료
- 실행 시작 마커 200/200개 확인
- 199개 trial은 기존 `verify_main.py` 독립 검증 PASS
- 1개 trial은 아래 감사형 검증을 통해 별도 확인

### 예외 사건: normal-irregular-lognormal-t03

- 최초 Generator: 30/30 트랜잭션 성공
- 최초 TShark 기본 분석: ClientHello 29개
- 문제 연결: TCP stream 12, 클라이언트 임시 포트 44818
- TShark가 TLS 트래픽을 EtherNet/IP(ENIP)로 오인식
- `-d tcp.port==8443,tls` 적용 후 ClientHello 30개 복원
- 고유 TCP stream 30개, 잘못된 outer SNI 0개
- 교정 평균 절대 IAT 오차: 0.001168807초
- 교정 최대 절대 IAT 오차: 0.006194000초
- 원본 PCAP SHA-256:
  `5403d9d55104452e479fbb429909c99b5fc2fd4f805473db6080d7a33658cc64`
- 원본 PCAP과 manifest는 변경하지 않음
- 별도 감사 증거:
  `artifacts/audit/main-v1/normal-irregular-lognormal-t03-decode-as.json`
- 기존 전체 Raw 검증기는 원본 manifest의 ClientHello 29개 기록 때문에 여전히 FAIL
- 199개 기존 Raw 검증 및 1개 독립 감사 검증으로 전체 200개 검증 완료

### Docker 장애 및 해결

- 호스트에는 Extractor 파일이 존재했으나 실행 중인 ech-client 내부의 마운트 디렉터리가 비어 있었음
- 바인드 마운트 Source 경로 일치 확인
- `ech-client` 컨테이너만 강제 재생성
- Extractor 파일 4개 확인
- Feature Math 테스트 6/6, Feature 검증 테스트 4/4 PASS

### Processed 데이터 검증

- 실제 PCAP 기반 Feature 추출: 200/200 PASS
- features.csv: 200행, 13개 유한한 Feature
- labels.csv: 200행, Beacon 100 / Normal 100
- provenance.json: 200개 trial 전체 검증 PASS
- 모든 trial에서 30 TCP Flow / 29 IAT 확인
- Extractor schema: 1.0.0
- 전체 200개 Label 및 PCAP SHA-256 provenance 검증 PASS
- 기존 전체 Raw 검증 스크립트를 통과했다고 주장하지 않으며,
  완료한 감사형 Raw 검증 후 기존 Extractor를 직접 실행함

### Processed SHA-256

- features.csv:
  `41cc91142320c9c6789495a559fcd6dd8f0e05c3428802039f6fc8494fd95a78`
- labels.csv:
  `8c54a96d276887f1c62fc028cf0251bdb3ea3b916fc01a1f09c8b82bb25981ac`
- provenance.json:
  `3b2c9ecc1b56e9bdd554649a020f6242d6649e20`

`sha256sum -c artifacts/audit/main-v1/processed-sha256.txt`:
3개 파일 모두 성공.

### 보존 및 후속 작업

- `data/raw/main-v1/` 원자료 보존
- `artifacts/pcap/main-v1/` PCAP 보존
- `artifacts/audit/main-v1/` 감사 증거 및 추출 로그 보존
- `data/processed/main-v1/` 결과물 보존
- 실패 사건과 복구 과정 삭제 또는 은폐 없음
- Detector threshold 및 모델 규칙 변경 없음
- Precision, Recall, F1, FPR, FNR 아직 미측정
- 다음 단계: 사전 고정된 calibration 90개와 held-out test
  110개 분할을 이용한 두 탐지기 비교 평가

---

## 2026-10-20 — Held-out Test 평가 및 처리 비용 확정

### 목적

Native ECH 본 실험 `main-v1`의 동결된 Dataset과 Detector를
사용하여 실제 Held-out 탐지 성능, 정상 프로필별 오탐 및
모델 처리 비용을 평가했다.

결과 확인 후 Feature 정의, Dataset Split, 모델 파라미터,
Threshold 또는 원본 PCAP을 변경하지 않았다.

### 회귀 테스트 및 데이터 분할

- Timing-only 단위 테스트: 10/10 PASS
- Timing-only CLI 테스트: 13/13 PASS
- Multi-feature 테스트: 20/20 PASS
- 총 43/43 PASS
- 전체 데이터: Beacon 100개 + Normal 100개
- Calibration: Beacon 50개 + Normal 40개
- Held-out Test: Beacon 50개 + Normal 60개
- 원본 Processed 3개 SHA-256 재검증 PASS
- Split Manifest 및 Trial ID 독립 검증 PASS
- Pilot 데이터 혼입 없음

### Frozen Calibration

Timing-only:

- 입력: Calibration Normal 40개
- 특징: `iat_cv`
- Threshold: `0.7667340945734821`
- Calibration empirical FPR: 0.05

Multi-feature:

- 입력: Calibration Beacon 50개 + Normal 40개
- 특징: 13개
- 모델: L2 Logistic Regression
- Learning rate: 0.1
- Epochs: 800
- L2 lambda: 0.1
- Threshold: `-1.2556072376827678`
- Calibration empirical FPR: 0.05

두 Detector의 모델 Fingerprint 및 Calibration 파일을 검증했다.
이후 모델 재학습이나 Threshold 변경은 수행하지 않았다.

### Held-out Prediction 및 평가

두 Detector 모두 Test Label을 사용하지 않고
110개 Trial에 대한 Prediction을 생성했다.

평가 단계에서만 Test Label을 결합하여 성능을 계산했다.

| 지표 | Timing-only | Multi-feature |
|---|---:|---:|
| TP | 50 | 50 |
| FP | 10 | 7 |
| TN | 50 | 53 |
| FN | 0 | 0 |
| Precision | 0.8333 | 0.8772 |
| Recall | 1.0000 | 1.0000 |
| F1 | 0.9091 | 0.9346 |
| FPR | 0.1667 | 0.1167 |
| FNR | 0.0000 | 0.0000 |

전체 Test 표본은 110개다.

Multi-feature는 Timing-only보다
정상 트래픽 오탐을 3건 적게 기록했다.

### Jitter별 결과

Jitter 조건: 0%, 10%, 30%, 50%, 70%.

각 조건의 Held-out Beacon 표본은 10개다.

모든 Jitter 조건에서 두 Detector 모두:

- TP: 10
- FN: 0
- Recall: 1.0000
- FNR: 0.0000

각 조건의 Precision/F1 비교에는 동일한
Normal Test 60개를 공통으로 사용했다.

따라서 Jitter별 조건부 결과는
독립적인 전체 Test 5회가 아니다.

### Normal 프로필별 오탐

| Normal 프로필 | N | Timing FP | Multi FP |
|---|---:|---:|---:|
| interactive-burst | 24 | 0 | 0 |
| irregular-lognormal | 18 | 10 | 7 |
| mixed-activity | 18 | 0 | 0 |

오탐은 전부 irregular-lognormal 프로필에서 발생했다.

동일 Normal 표본에 대한 판정 비교:

- 두 Detector 모두 오탐: 7
- Timing-only만 오탐: 3
- Multi-feature만 오탐: 0
- 두 Detector 모두 정상: 50

Multi-feature가 해소한 3건의 오탐에 대해
특정 Feature가 개선의 원인이라고 단정하지 않는다.

### 순수 추론 처리 비용

동결된 모델과 동일한 Test Feature 110개를 사용했다.

- Python: 3.10.12
- Linux kernel: 6.8.0-138-generic
- Warmup: 20회
- 본 측정: 250회
- Timer: `time.perf_counter_ns`
- 반복마다 Detector 실행 순서 교대
- 기존 Frozen Prediction 각각 110개와 일치
- Test Label 미사용

| 지표 | Timing-only | Multi-feature |
|---|---:|---:|
| Median batch (ms) | 0.080385 | 1.408802 |
| P95 batch (ms) | 0.086857 | 1.447461 |
| Median/trial (us) | 0.730777 | 12.807295 |

Multi-feature의 Median 추론 시간은
Timing-only 대비 약 17.53배였다.

측정 대상은 사전에 추출된 Feature의 순수 추론이며,
PCAP 파싱, Feature 추출, CSV 파일 I/O 및
학습·Calibration 시간은 포함되지 않는다.

### 학습 및 Calibration 처리 비용

Frozen 모델과 재계산 결과가 일치하는지 확인했다.

- Warmup: 3회
- 본 측정: 15회
- Timer: `time.perf_counter_ns`
- 반복마다 Detector 실행 순서 교대
- 모델 파일 저장 없음
- Test Label 미사용

| 지표 | Timing-only | Multi-feature |
|---|---:|---:|
| Median (ms) | 0.027777 | 199.032131 |
| P95 (ms) | 0.032999 | 216.105765 |

Multi-feature의 Median 준비 시간은
Timing-only 대비 약 7,165.36배였다.

단, 두 모델의 입력 수와 연산 범위가 다르다.

Timing-only는 Normal 40개의 CV 정렬 및
Threshold 계산을 수행한다.

Multi-feature는 90개 Calibration 표본으로
800 Epoch 학습 및 Threshold 계산을 수행한다.

따라서 이 비율은 서로 다른 모델 준비 작업의
관측된 처리 시간 비율이며,
동일 연산의 계산 효율 차이를 뜻하지 않는다.

### 평가 결과 무결성

Held-out Evaluation:

`results/metrics/main-v1/heldout-evaluation.json`

SHA-256:

`b357dee703565d98b65467b94f488f9681e53f3ed41b1e3153f432279be9f46b`

Processing Cost Benchmark:

`results/metrics/main-v1/processing-cost-benchmark.json`

SHA-256:

`4d25da1fd02a2b672e42074454239ca1067c2e055090112c732c70391105c3df`

평가 JSON의 전체 Confusion Matrix, Jitter별 지표,
Normal 프로필별 오탐 및 짝비교 결과를
원본 Test Label과 Prediction으로 독립 재계산하여 검증했다.

Benchmark JSON 생성 과정에서 기존 Calibration,
Prediction 및 Held-out Evaluation의 SHA-256을 재검증했다.

모든 확인 항목 PASS.

### 가설 판단 및 연구 한계

사전 가설은 Multi-feature가 Jitter 증가 시
Timing-only보다 Beacon Recall을 더 잘 유지한다는 것이었다.

그러나 0~70% Jitter의 모든 조건에서
두 Detector 모두 Recall 100%를 기록했다.

따라서 높은 Jitter에서 Multi-feature의
Recall 유지 우위는 관측되지 않았으며,
원 가설의 핵심 주장은 이번 실험에서 지지되지 않는다.

반면 Multi-feature의 전체 Precision/F1 증가와
FPR 감소가 관측되었다.

이러한 개선은 주로 irregular-lognormal
정상 트래픽의 오탐 3건 감소에서 발생했다.

주요 한계:

- 실제 악성코드가 아닌 Synthetic HTTPS Beacon
- Native ECH 단일 실험 환경
- 기준 Beacon 주기 1.0초
- Jitter 조건별 Held-out Beacon 10개
- Normal 프로필 3종으로 제한
- Calibration과 Held-out FPR의 차이
- 성능 차이에 대한 통계적 우월성 미확증
- 처리 비용은 Python 단일 환경의 마이크로벤치마크
- 개별 반복 측정 시간은 저장하지 않고 요약값만 보존
- End-to-end Detection latency는 별도 측정하지 않음

Calibration의 경험적 FPR 0.05는
Held-out FPR 0.1667/0.1167을 보장하지 않았다.

두 Detector의 처리 비용 및 오탐 감소 효과를 함께 고려해야 한다.

### 후속 작업

1. 고정된 평가 결과에서 논문용 표와 그래프 생성
2. 연구 결과·논의 및 한계 작성
3. 선행연구 원문과 서지 최종 검증
4. 완성 논문 작성
5. 원자료 및 재현 절차를 포함하는 제출 패키지 준비
6. 새 디렉터리에서 재현성 및 무결성 검증

이번 평가 과정에서 기존 모델 및 원본 데이터를
성능에 유리하게 변경하지 않았다.
