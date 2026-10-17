# PCAP Trial Feature Extractor

> Issue #5 — PCAP 기반 Trial Feature Extractor 구현

## 1. 목적

Native ECH trial PCAP에서 Timing-only 및 Multi-feature detector가 사용할 trial-level feature를 추출한다.

Feature Extractor는 detector가 아니다. raw PCAP을 deterministic processed feature로 변환하고, label과 feature를 분리하며, raw → processed provenance를 유지하는 단계다.

## 2. 입력

각 trial은 다음 두 원자료를 사용한다.

```text
data/raw/<run-tag>/manifests/<trial-id>.json
artifacts/pcap/<run-tag>/<class>/<trial-id>.pcap
```

Feature 값은 PCAP에서 계산한다. Manifest는 다음 검증/metadata 용도로만 사용한다.

- trial ID
- success 상태
- traffic class / jitter / normal profile label
- expected transaction count
- PCAP 경로
- PCAP SHA-256

Generator의 scheduled interval 또는 payload profile을 feature 값으로 직접 사용하지 않는다.

## 3. Flow 정의

대상 traffic:

```text
TCP port 8443
```

방향:

```text
outbound = client -> server = tcp.dstport == 8443
inbound  = server -> client = tcp.srcport == 8443
```

Docker container IP는 feature 정의에 사용하지 않는다.

Flow ID는 TShark `tcp.stream`을 사용한다.

Flow 시작 시각은 각 stream에서 가장 이른 client→server TCP SYN(`SYN=1, ACK=0`) timestamp다.

따라서 detector timing feature는 TLS ClientHello field에 의존하지 않는다.

Pilot-v2에서는 trial당 다음을 요구한다.

```text
flow count       = 30
flow start count = 30
IAT count        = 29
```

## 4. 공통 통계 규칙

- time: seconds
- size: bytes
- standard deviation: population standard deviation (`ddof=0`)
- CV: `population_std / mean`
- MAD: `median(abs(x - median(x)))`, scale factor 없음
- 계산 불가능한 feature는 임의로 `0`으로 대체하지 않음
- missing / non-finite feature는 validation failure

## 5. Timing features

30개 flow-start timestamp에서 29개 IAT를 계산한다.

```text
iat_mean_s
iat_std_s
iat_cv
iat_mad_s
```

Timing-only detector용 기본 subset은 이후 다음 세 값이다.

```text
iat_mean_s
iat_std_s
iat_cv
```

## 6. Packet-size features

Packet size는 capture link type의 영향을 줄이기 위해 `frame.len`이 아니라 IPv4 `ip.len`을 사용한다.

Trial PCAP의 TCP/8443 packet 전체를 포함한다.

```text
packet_size_mean_bytes
packet_size_std_bytes
packet_size_cv
```

Handshake, ACK, encrypted application data, connection teardown packet을 포함한 실제 관측 packet metadata를 대상으로 한다.

## 7. Directionality features

```text
out_in_packet_ratio
byte_asymmetry
direction_change_ratio
```

정의:

```text
out_in_packet_ratio
  = outbound_packet_count / inbound_packet_count

byte_asymmetry
  = (outbound_bytes - inbound_bytes)
    / (outbound_bytes + inbound_bytes)

direction_change_ratio
  = adjacent packet direction changes
    / (directional_packet_count - 1)
```

byte 계산에는 `ip.len`을 사용한다.

## 8. Burst features

Burst는 flow-start sequence를 기준으로 정의한다.

고정 threshold:

```text
0.5 s
```

규칙:

```text
flow-start IAT <= 0.5 s : same burst
flow-start IAT >  0.5 s : new burst
```

출력:

```text
burst_count
burst_mean_size
burst_interval_cv
```

`burst_interval`은 연속 burst의 첫 flow 시작 시각 간 차이다.

## 9. 최종 feature schema

`features.csv`에는 `trial_id`와 13개 feature만 저장한다.

```text
trial_id
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

Class/condition label은 feature 파일에 넣지 않는다.

## 10. Label schema

`labels.csv`:

```text
trial_id
traffic_class
label
jitter_pct
normal_profile
```

```text
beacon = 1
normal = 0
```

이 분리는 이후 model/detector 코드가 실수로 jitter 값이나 traffic class를 feature로 사용하는 것을 방지하기 위한 것이다.

## 11. Provenance

`provenance.json`은 다음을 보존한다.

- extractor schema version
- feature definition version
- run tag
- TShark version
- server port
- burst threshold
- source manifest
- source PCAP
- 실제 PCAP SHA-256
- packet count
- TCP stream count
- flow-start count
- IAT count
- outbound/inbound packet count
- TShark parse time
- feature compute time
- total extraction time
- validation status/errors

Primary feature-extraction operational cost는 `total_extraction_ms`로 정의하고 parse/compute 시간을 함께 보존한다.

## 12. Output

Pilot-v2 실행 결과:

```text
data/processed/pilot-v2/
├── features.csv
├── labels.csv
└── provenance.json
```

Processed output은 raw PCAP이 아니며 extractor code로 재생성할 수 있다.

기본 실행은 기존 processed output을 덮어쓰지 않는다.

## 13. 실행 준비

Issue #5 branch를 받는다.

```bash
git switch main
git pull --ff-only
git fetch origin
git switch "#5-feature-extractor"
```

`extractor` mount가 추가되었으므로 `ech-client`를 재생성한다. Image rebuild는 필요하지 않다.

```bash
docker compose -f ./docker-compose.yml up -d --force-recreate ech-client
```

상태 확인:

```bash
docker compose -f ./docker-compose.yml ps -a
```

## 14. 순수 계산 unit test

```bash
docker compose -f ./docker-compose.yml exec -T ech-client \
  python3 /workspace/extractor/test_feature_math.py
```

검증 내용:

- constant IAT 통계
- population standard deviation
- direction ratio / byte asymmetry / direction-change ratio
- inclusive 0.5 s burst threshold
- missing denominator 처리
- non-finite validation

## 15. Pilot-v2 batch extraction

Issue #3에서 성공한 8-trial `pilot-v2`만 extractor acceptance dataset으로 사용한다.

```bash
RUN_TAG=pilot-v2 bash scripts/extract-pilot-features.sh
```

스크립트 순서:

1. feature math unit tests
2. 각 manifest/PCAP SHA-256 검증
3. TShark packet metadata parsing
4. TCP stream / first SYN flow start 추출
5. 13 features 계산
6. feature/label 분리 저장
7. provenance 저장
8. exact 8-trial pilot validation

정상 종료 조건:

```text
PASS: pilot-v2 contains exactly 8 feature rows and 8 label rows
PASS: all 13 features are finite for every pilot trial
PASS: feature and label trial IDs match one-to-one
PASS: all pilot trials contain 30 TCP flows and 29 flow-start IAT values
PASS: provenance validation and extraction timing are complete
PASS: Feature Extractor pilot completed for RUN_TAG=pilot-v2
```

## 16. 기존 processed 결과 재검증

Processed output이 이미 존재하면 기본 실행은 overwrite를 거부한다.

코드 수정 후 의도적으로 재생성이 필요한 경우에만 다음을 사용한다.

```bash
OVERWRITE=1 RUN_TAG=pilot-v2 bash scripts/extract-pilot-features.sh
```

Raw PCAP과 raw manifest는 변경하거나 삭제하지 않는다.

## 17. 범위 제외

Issue #5에서는 다음을 하지 않는다.

- detector threshold 결정
- Timing-only detector 구현
- Multi-feature detector 구현
- train/test split
- 본 실험 200 samples 생성
- 최종 성능 지표 계산
- 결과 그래프 생성

Pilot-v2 extractor validation을 통과하고 feature schema를 동결한 뒤 detector 단계로 진행한다.
