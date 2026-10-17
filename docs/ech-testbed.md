# Native ECH Testbed

> Issue #1 — ECH 실험 환경 구축 및 재현성 검증

## 1. 목적

본 testbed는 T10 본 실험 전에 **실제 RFC 9849 ECH 통신을 로컬 Docker 환경에서 반복 생성하고 검증**하기 위한 기반이다.

이번 단계의 목표는 C2/beacon traffic을 아직 생성하는 것이 아니라 다음 사실을 증명하는 것이다.

1. ECH OFF 일반 TLS 요청이 동작한다.
2. ECH ON 요청에서 서버가 ECH를 실제로 `SUCCESS`로 처리한다.
3. ECH OFF packet capture에는 protected SNI가 평문으로 존재한다.
4. ECH ON packet capture에는 protected SNI가 평문으로 노출되지 않는다.
5. protocol-aware parser에서도 ECH ON ClientHello에는 public outer SNI만 보인다.
6. 같은 절차를 반복 재현할 수 있다.

## 2. 버전 고정

| Component | Version |
|---|---:|
| OpenSSL | 4.0.1 |
| NGINX | 1.30.6 |
| curl | 8.20.0 |
| TShark | 4.0.17 |
| TLS | 1.3 |
| ECH | RFC 9849 / ECHConfig version 0xfe0d |

OpenSSL 4.0부터 RFC 9849 ECH가 지원되며, NGINX의 `ssl_ech_file` directive는 1.29.4부터 제공되고 OpenSSL 4.0+가 필요하다.

호스트의 OpenSSL/curl/tshark는 변경하지 않는다. 모든 ECH 및 packet-analysis 의존성은 Docker 이미지 안에 격리한다.

## 3. 테스트 이름

외부 DNS나 실제 도메인을 사용하지 않는다.

- protected inner name: `protected.ech.test`
- public outer name: `public.ech.test`

Docker network alias가 두 이름을 `ech-nginx` container로 해석한다.

Client는 DNS HTTPS RR 대신 실험용 ECH PEM에서 추출한 ECHConfigList를 curl의 `--ech ecl:<base64>` 옵션으로 직접 전달한다. 따라서 DNS 배포 상태와 무관하게 **실제 ECH handshake 자체**를 재현할 수 있다.

## 4. 구성

```text
                     Docker network: ech-lab

  ech-client
      |
      | TLS 1.3
      | ECH OFF / ECH ON
      v
  protected.ech.test:8443
      |
      v
  ech-nginx  <------ packet-capture
      |
      +-- public.ech.test     (outer/public name)
      +-- protected.ech.test  (inner/protected name)

  ech-bootstrap
      |
      +-- self-signed TLS certificate
      +-- OpenSSL ECH PEM / private key
```

## 5. 최초 실행

Issue branch를 최신 상태로 만든다.

```bash
git fetch origin
git switch "#1-ech-testbed"
git pull --ff-only
```

Compose 파일을 명시해서 구문과 service 목록을 확인한다.

```bash
docker compose -f ./docker-compose.yml config
```

```bash
docker compose -f ./docker-compose.yml config --services
```

정상 service 목록:

```text
ech-bootstrap
ech-nginx
ech-client
packet-capture
```

이미지를 빌드한다.

```bash
docker compose -f ./docker-compose.yml build
```

첫 빌드는 OpenSSL, NGINX, curl을 source에서 컴파일하므로 시간이 걸릴 수 있다.

서비스를 시작한다.

```bash
docker compose -f ./docker-compose.yml up -d
```

상태 확인:

```bash
docker compose -f ./docker-compose.yml ps -a
```

정상 상태의 기대값:

- `ech-bootstrap`: `Exited (0)`
- `ech-nginx`: `healthy`
- `ech-client`: `Up`
- `packet-capture`: `Up`

## 6. ECH ON/OFF 검증

```bash
bash scripts/verify-ech.sh
```

검증 스크립트는 다음을 확인한다.

### ECH OFF

예상 응답:

```text
X-ECH-Status: NOT_TRIED
X-TLS-SNI: protected.ech.test
```

### ECH ON

예상 응답:

```text
X-ECH-Status: SUCCESS
X-ECH-Outer-SNI: public.ech.test
X-TLS-SNI: protected.ech.test
```

ECH 성공 여부는 단순히 HTTPS 요청 성공 여부로 판정하지 않는다. NGINX의 `$ssl_ech_status`와 `$ssl_ech_outer_server_name`을 증거로 사용한다.

검증 출력은 다음 위치에 저장된다.

```text
artifacts/evidence/
```

## 7. Packet capture

ECH OFF/ON 요청을 각각 별도 PCAP으로 생성한다.

```bash
bash scripts/capture-ech.sh
```

생성 파일:

```text
artifacts/pcap/plain.pcap
artifacts/pcap/ech.pcap
```

`*.pcap`은 `.gitignore`에 의해 Git에 커밋되지 않는다.

### 7.1 Raw-byte sanity check

`capture-ech.sh`는 캡처 직후 다음을 1차 확인한다.

- `plain.pcap`에서 `protected.ech.test`가 평문으로 검색되어야 한다.
- `ech.pcap`에서 `protected.ech.test`가 평문으로 검색되면 실패한다.
- `ech.pcap`에서 outer name인 `public.ech.test`가 확인되어야 한다.

이 검사는 빠른 sanity check이며 최종 프로토콜 증거는 다음 TShark 검증을 사용한다.

### 7.2 Protocol-aware ClientHello SNI 검증

TShark는 host가 아니라 `ech-tools` Docker image 안에 포함된다.

버전 확인:

```bash
docker compose -f ./docker-compose.yml exec -T packet-capture tshark --version
```

기존 PCAP의 TLS ClientHello `server_name` extension을 파싱한다.

```bash
bash scripts/verify-pcap.sh
```

검증 기준:

```text
plain.pcap
  tls.handshake.extensions_server_name = protected.ech.test

ech.pcap
  tls.handshake.extensions_server_name = public.ech.test
  protected.ech.test는 파싱된 ClientHello에 나타나지 않아야 함
```

정상 출력의 핵심:

```text
PASS: plain.pcap -> SNI protected.ech.test
PASS: ech.pcap   -> outer SNI public.ech.test
PASS: ech.pcap   -> protected SNI not visible in parsed ClientHello
```

## 8. 인증서/ECHConfig 재생성

기본값은 named volume의 기존 material을 재사용한다.

강제 재생성:

```bash
FORCE_REGENERATE=1 docker compose -f ./docker-compose.yml up --build --force-recreate ech-bootstrap
```

그 후 서버를 다시 생성한다.

```bash
docker compose -f ./docker-compose.yml up -d --force-recreate ech-nginx ech-client packet-capture
```

완전 초기화가 필요한 경우:

```bash
docker compose -f ./docker-compose.yml down -v
```

주의: `-v`는 testbed가 생성한 TLS/ECH named volume을 삭제한다.

## 9. 문제 확인 순서

### Compose 대상 확인

상위 경로의 다른 Compose project를 잘못 실행하지 않도록 항상 파일을 명시한다.

```bash
docker compose -f ./docker-compose.yml config --services
```

### Bootstrap 로그

```bash
docker compose -f ./docker-compose.yml logs --timestamps ech-bootstrap
```

### NGINX configuration

```bash
docker compose -f ./docker-compose.yml exec -T ech-nginx nginx -t
```

### NGINX/OpenSSL build 확인

```bash
docker compose -f ./docker-compose.yml exec -T ech-nginx nginx -V
```

### Client OpenSSL

```bash
docker compose -f ./docker-compose.yml exec -T ech-client openssl version
```

### Client curl

```bash
docker compose -f ./docker-compose.yml exec -T ech-client /opt/curl-ech/bin/curl --version
```

### TShark

```bash
docker compose -f ./docker-compose.yml exec -T packet-capture tshark --version
```

### 전체 로그

```bash
docker compose -f ./docker-compose.yml logs --tail=200 ech-bootstrap ech-nginx
```

## 10. 최종 재현성 확인

모든 기능 검증이 끝난 뒤 testbed를 종료했다가 다시 기동하여 동일한 결과가 나오는지 한 번 더 확인한다.

```bash
docker compose -f ./docker-compose.yml down
```

```bash
docker compose -f ./docker-compose.yml up -d
```

```bash
docker compose -f ./docker-compose.yml ps -a
```

```bash
bash scripts/verify-ech.sh
```

```bash
bash scripts/capture-ech.sh
```

```bash
bash scripts/verify-pcap.sh
```

세 스크립트가 모두 PASS해야 Issue #1의 재현성 완료 조건을 충족한 것으로 기록한다.

2026-10-17 실제 재기동 검증에서 세 스크립트가 모두 동일하게 PASS했다.

## 11. 완료 판정

Issue #1은 다음 결과가 실제 실행으로 확인되어야 완료 처리한다.

- [x] `docker compose -f ./docker-compose.yml config` 성공
- [x] image build 성공
- [x] NGINX healthy
- [x] ECH OFF = `NOT_TRIED`
- [x] ECH ON = `SUCCESS`
- [x] ECH outer SNI = `public.ech.test`
- [x] plain PCAP에 protected SNI 존재
- [x] ECH PCAP에 protected SNI 평문 부재
- [x] TShark에서 plain ClientHello SNI = `protected.ech.test`
- [x] TShark에서 ECH ClientHello outer SNI = `public.ech.test`
- [x] TShark에서 ECH ClientHello에 protected SNI 비노출
- [x] testbed 재기동 후 동일 결과 재현

따라서 Issue #1의 기술적 완료 조건은 충족했다.

실제 검증 결과는 `docs/research-log.md`에 사실 그대로 기록한다. 실패한 결과도 삭제하지 않는다.

## 12. GitHub Actions

GitHub Actions는 로컬 실험의 필수 구성요소가 아니다.

현재 workflow는 자동 push/pull_request trigger 없이 `workflow_dispatch` 수동 실행 전용으로 둔다.

역할:

```text
로컬 Docker = 개발, 디버깅, 실제 실험 및 원자료 생성
GitHub Actions = 필요할 때 수행하는 최종 재현성 검증
```

로컬 검증이 완료된 뒤 필요하면 GitHub Actions를 수동 실행해 별도 환경에서도 동일 절차가 성공하는지 확인한다.

## 13. 이번 Issue에서 하지 않는 것

다음은 후속 Issue 범위다.

- Normal traffic generator
- Beacon/jitter generator
- PCAP → flow feature extraction
- Timing-only detector
- Multi-feature detector
- 본 실험 반복 자동화
- metric/graph 생성