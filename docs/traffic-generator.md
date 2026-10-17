# Native ECH Traffic Generator

> Issue #3 — Normal 및 Jittered Beacon Traffic Generator 구현

## 1. 목적

이 generator는 Issue #1에서 검증한 Native ECH testbed에서 정상 traffic과 synthetic beacon traffic을 재현 가능하게 생성한다.

실제 malware/C2는 사용하지 않는다. 정상 HTTPS 요청을 반복하여 통신 주기만 재현한다.

이번 단계의 목적은 detector 성능을 측정하는 것이 아니라 이후 실험에 사용할 raw traffic 생성기가 사전 정의된 조건대로 동작하는지 검증하는 것이다.

## 2. Sample 정의

한 sample은 동일 client에서 동일 protected ECH server로 발생한 30개의 short-lived HTTPS flow sequence다.

각 transaction은 별도 curl process를 사용하므로 연결 재사용 없이 새로운 TLS 1.3 + ECH handshake가 발생한다.

```text
trial
 ├─ flow 01: TLS 1.3 + Native ECH + HTTPS
 ├─ flow 02: TLS 1.3 + Native ECH + HTTPS
 ├─ ...
 └─ flow 30: TLS 1.3 + Native ECH + HTTPS
```

## 3. Beacon timing

```text
base interval T = 1.0 s
jitter = 0 / 10 / 30 / 50 / 70%
30 transactions per trial
29 IAT values per trial
20 trials per jitter level
```

공식:

```text
z_i ~ Uniform(-1, 1)
I_i(j) = T × (1 + j × z_i)
```

동일 trial 번호는 모든 jitter level에서 같은 normalized `z_i` sequence와 같은 payload sequence를 사용한다.

따라서 jitter amplitude만 변한다.

## 4. Normal timing

### interactive-burst

- 40 samples
- burst size: 2~5 transactions
- intra-burst IAT: 0.10~0.35 s
- inter-burst idle: 2.0~5.0 s

### irregular-lognormal

- 30 samples
- LogNormal(mu=ln(1.0), sigma=0.8)
- 0.15~6.0 s로 clip

### mixed-activity

- 30 samples
- 70%: 0.20~1.00 s
- 30%: 2.50~6.00 s

## 5. Payload profile

Normal과 Beacon 모두 같은 payload profile 분포를 사용한다.

| Profile | Query payload | Response body | Probability |
|---|---:|---:|---:|
| small | 32 B | 128 B | 0.50 |
| medium | 128 B | 512 B | 0.35 |
| large | 512 B | 2048 B | 0.15 |

응답 body는 NGINX image build 중 `/srv/traffic`에 정확히 128/512/2048 B로 생성하고 `wc -c`로 build-time 검증한다. Generator는 각 transaction의 `Content-Length`도 기대값과 비교한다.

이를 통해 payload 크기 자체가 class label을 직접 나타내는 shortcut이 되는 것을 방지한다.

## 6. Seed

```text
Beacon timing base  = 20261017
Normal timing base  = 20262017
Beacon payload base = 20263017
Normal payload base = 20264017
```

난수는 Python `random.Random(seed).random()`을 기본 primitive로 사용한다.

LogNormal profile은 Box-Muller transform을 코드에 직접 구현하여 derived random API 변경의 영향을 줄인다.

## 7. Raw data

Pilot 기본 run tag:

```text
pilot-v1
```

원자료:

```text
data/raw/pilot-v1/
  manifests/
  flow-metadata/

artifacts/pcap/pilot-v1/
  beacon/
  normal/
```

PCAP은 `.gitignore`에 의해 Git에 커밋되지 않는다.

### Manifest

각 trial JSON에는 다음이 포함된다.

- class / profile / jitter
- timing seed / payload seed
- normalized jitter sequence
- scheduled IAT / scheduled offsets
- payload profile sequence
- transaction별 예정 시각과 실제 generator launch 시각
- HTTP status / Content-Length
- ECH status
- outer SNI / protected TLS SNI
- curl exit code
- PCAP filename / SHA-256 / bytes
- TShark에서 추출한 ClientHello timestamps
- network-observed ClientHello IAT
- scheduled IAT와 network-observed IAT의 차이
- success/failure와 failure reason

### Flow metadata CSV

각 transaction을 한 행으로 저장한다.

이 CSV는 generator 관점의 실행 기록이며, 최종 packet/flow feature는 후속 feature-extractor Issue에서 PCAP을 기준으로 생성한다.

## 8. 환경 준비

브랜치:

```bash
git fetch origin
git switch "#3-traffic-generator"
git pull --ff-only
```

Python과 고정-size payload가 image에 추가되었으므로 이미지를 다시 빌드한다.

```bash
docker compose -f ./docker-compose.yml build
```

변경된 mount와 NGINX endpoint를 반영하도록 서비스를 재생성한다.

```bash
docker compose -f ./docker-compose.yml up -d --force-recreate
```

상태 확인:

```bash
docker compose -f ./docker-compose.yml ps -a
```

Python 확인:

```bash
docker compose -f ./docker-compose.yml exec -T ech-client python3 --version
```

## 9. 정적 generator 검증

네트워크 trial을 실행하기 전에 deterministic model test를 수행한다.

```bash
docker compose -f ./docker-compose.yml exec -T ech-client \
  python3 /workspace/generator/test_traffic_model.py
```

검증 항목:

- 0% jitter = 정확히 1.0 s
- jitter 범위
- paired normalized jitter sequence
- paired payload sequence
- Normal profile interval 범위
- 동일 seed 결정성
- payload profile 설정값

실제 response body byte size는 Docker build 단계와 각 Native ECH transaction의 `Content-Length`에서 다시 검증한다.

## 10. 단일 trial 실행

Beacon 예:

```bash
RUN_TAG=pilot-v1 bash scripts/run-traffic-trial.sh beacon 30 1
```

Normal 예:

```bash
RUN_TAG=pilot-v1 bash scripts/run-traffic-trial.sh normal interactive-burst 1
```

기존 raw data를 실수로 덮어쓰지 않도록 같은 `RUN_TAG + trial_id`가 이미 존재하면 실행을 중단한다.

재실행이 필요하면 새 run tag를 사용한다.

```bash
RUN_TAG=pilot-v2 bash scripts/run-traffic-trial.sh beacon 30 1
```

## 11. 8-trial pilot

본 실험 전에 다음 8개만 실행한다.

```text
Beacon: j00/j10/j30/j50/j70 × trial 1
Normal: 3 profiles × trial 1
```

실행:

```bash
RUN_TAG=pilot-v1 bash scripts/run-traffic-pilot.sh
```

스크립트는 다음 순서로 수행한다.

1. 기존 Native ECH testbed 검증
2. deterministic model unit test
3. 각 trial별 tcpdump 시작
4. 30개 Native ECH HTTPS transactions 실행
5. HTTP `Content-Length` 검증
6. PCAP 종료 및 SHA-256 계산
7. TShark로 ClientHello timestamp/SNI 파싱
8. manifest에 network-observed IAT 추가
9. 8개 trial 전체 조건 검증

## 12. Pilot PASS 기준

- 모든 trial이 30 transactions
- 모든 transaction이 HTTP 200
- 모든 response `Content-Length`가 payload profile 기대값과 일치
- 모든 transaction의 ECH status가 `SUCCESS`
- outer SNI가 `public.ech.test`
- protected SNI가 서버 내부에서는 `protected.ech.test`
- PCAP마다 TShark ClientHello 30개
- parsed ClientHello SNI가 모두 `public.ech.test`
- parsed ClientHello에서 protected SNI 비노출
- 0% jitter scheduled IAT가 모두 1.0 s
- 모든 jitter scheduled IAT가 사전 정의 범위 내
- 같은 beacon trial의 normalized jitter/payload sequence가 모든 jitter level에서 동일
- scheduled IAT와 network-observed IAT가 모두 manifest에 보존
- PCAP SHA-256이 manifest와 일치

Pilot은 generator 검증 데이터이며 최종 detector 성능 평가 데이터에 포함하지 않는다.

## 13. 본 실험 실행 금지 시점

Issue #3에서는 최종 200 samples를 생성하지 않는다.

Pilot이 통과하고 generator 조건을 최종 동결한 뒤 후속 feature extractor 설계를 먼저 완료한다.
