# Native ECH 200-trial Main Experiment — 수집·검증 운영 규약

> Issue #11, 2026-10-18. 실제 본 실험 데이터는 생성 전이다. 기존 Generator/Extractor 및 두 Detector의 frozen version/threshold/split 조건을 바꾸지 않는다.

## 1. 고정된 200개 trial catalog

| 순번 | 실험 종류 | trial | 건수 |
|---:|---|---|---:|
| 1..20 | Beacon jitter 0% | t01..t20 | 20 |
| 21..40 | Beacon jitter 10% | t01..t20 | 20 |
| 41..60 | Beacon jitter 30% | t01..t20 | 20 |
| 61..80 | Beacon jitter 50% | t01..t20 | 20 |
| 81..100 | Beacon jitter 70% | t01..t20 | 20 |
| 101..140 | Normal interactive-burst | t01..t40 | 40 |
| 141..170 | Normal irregular-lognormal | t01..t30 | 30 |
| 171..200 | Normal mixed-activity | t01..t30 | 30 |
| | **Total** | | **200** |

Trial당 새로운 HTTPS/TLS 1.3 + ECH 연결 30회, flow-start IAT 29개. Generator config의 jitter/seed/payload/profile 조건과 extractor schema `1.0.0`을 유지한다. 동일 Beacon trial 번호는 jitter와 무관하게 같은 normalized random vector·payload sequence를 공유한다.

## 2. 보존 규칙

- 본 실험 태그는 `main-v1`과 같이 새 태그를 사용한다. `pilot-v1`, `capture-check-v1`, `pilot-v2`와 혼용 금지.
- 이미 존재하는 raw manifest/flow CSV/PCAP을 덮어쓰거나 지우지 않는다. 실패 데이터를 제거해 보고서를 유리하게 만들지 않는다.
- 캡처 시작 직전에 `data/raw/<run-tag>/execution-state/<trial-id>.started` 마커를 생성한다. 세 산출물이 없는데 마커만 남았어도 같은 태그에서 재시도하지 않고 실패를 보존한다.
- 스크립트가 재실행될 때 완전한 manifest·flow CSV·PCAP이 존재하면 이 셋을 PCAP SHA·ECH·ClientHello로 재검증하고 나서만 skip한다.
- 세 파일 중 하나라도 누락되거나 검증 FAIL이면 batch를 중단하며, 실패 데이터는 그대로 보존한다. 무작정 해당 trial만 재촬영하여 기존 데이터를 교체하지 않는다. 필요시 별도 run-tag/experiment version에서 처음부터 재생성하고 실패 이유를 연구 로그에 기록한다.
- 동일 Docker `packet-capture` namespace에 병렬 trial을 실행하지 않는다. `flock` lock은 **run-tag가 달라도** 동일 사용자에 대해 batch를 직렬화한다.
- 첫 시작 시 `data/raw/<run-tag>/run-environment.txt`에 실행 환경·generator 소스 SHA-256·ECH material SHA-256을 기록한다. 이후 batch에서 fingerprint가 다르면 중단한다.
- raw PCAP은 `.gitignore`로 Git 커밋 제외. raw manifest, metadata, processed CSV/provenance는 검증 후 보존 정책에 따라 Git 기록 여부 결정. 저장 공간을 먼저 점검한다.

## 3. 사전 검증과 dry-run

호스트에서 repository의 올바른 branch 및 작업 트리 상태를 확인하고 Docker의 기존 Native ECH testbed가 healthy인지 확인한다.

```bash
docker compose -f ./docker-compose.yml ps -a
python3 generator/test_main_experiment.py
python3 extractor/test_main_features.py
```

**기본 동작은 dry-run** 이다. 다음 명령은 200개 ID만 표시하며 캡처하지 않는다.

```bash
RUN_TAG=main-v1 START=1 END=200 bash scripts/run-main-experiment.sh
```

먼저 작은 batch부터 실제로 실행한다. `EXECUTE=1`을 명시하지 않으면 절대로 캡처하지 않는다.

```bash
EXECUTE=1 RUN_TAG=main-v1 START=1 END=2 bash scripts/run-main-experiment.sh
```

해당 2개 검증 결과가 PASS이고 raw manifest·PCAP가 정상인지 확인한 다음 다음 batch로 확대한다.

```bash
EXECUTE=1 RUN_TAG=main-v1 START=3 END=20 bash scripts/run-main-experiment.sh
```

이후 `START`/`END`를 1..200 범위에서 중복 없이 순서대로 증가시켜 실행한다. 재시작 시 이미 완료된 범위를 포함해도 기존 데이터를 덮어쓰지 않고 검증 후 skip한다. **끝 번호 200을 포함한 batch에서는 200개 전체 raw 데이터 검증을 자동 실행한다.**

전체 수집 실패/중단 시 오류 메시지, `run-environment.txt`, 기존 실패 manifest, flow CSV, PCAP를 보존하며 새로운 태그에서 재실험이 필요한지 결정한다. Docker Compose는 반드시 프로젝트의 `-f ./docker-compose.yml`을 명시한다.

## 4. 독립 raw 검증

수집을 모두 마친 후 독립 검증을 다시 수행할 수 있다.

```bash
docker compose -f ./docker-compose.yml exec -T ech-client \
  python3 /workspace/generator/verify_main.py --run-tag main-v1
```

200개 ID exact match, 각 30 success requests, Native ECH SUCCESS/outer SNI, ClientHello PCAP 재파싱, PCAP SHA-256, flow-metadata CSV, deterministic plan, paired beacon payload/jitter를 확인한다.

## 5. 200개 PCAP Feature 추출

Raw 검증 PASS 이후에만 실행한다.

```bash
RUN_TAG=main-v1 bash scripts/extract-main-features.sh
```

스크립트는 기존 Feature Extractor v1.0.0을 사용한다. 본 실험용 출력 경로가 이미 존재하면 기본적으로 **덮어쓰지 않는다**.

```text
data/processed/main-v1/
  features.csv      # trial_id + 13 numeric features, 200 rows
  labels.csv        # class/jitter/profile separated, 200 rows
  provenance.json   # original PCAP hashes, 30 flows/29 IAT, parse/compute time
```

추출 이후 `extractor/verify_main_features.py`가 feature/label 정확히 200행, expected ID·class mapping, 13 finite feature, 30 flows/29 IAT와 PCAP SHA provenance를 검증한다. 이 단계에서는 **어떤 탐지 성능 수치도 보고하지 않는다**.

## 6. 다음 평가 단계와 분리

본 실험 데이터가 모두 PASS이면 **Issue #7/#9에서 동결한** split과 detector를 그대로 적용한다. Calibration 90개(Beacon 50+Normal 40), Test 110개(Beacon 50+Normal 60)를 유지한다. 실제 baseline/multi detector train·calibrate·predict는 후속 평가 단계에서 실행한다.

Test feature/label 값에 맞춰 detector hyperparameter, feature set, threshold 선택 규칙, paired split을 변경하지 않는다. jitter별 metrics와 processing overhead는 그 후 별도 평가 Issue에서 산출한다.

## 7. 실패 기록 방식

각 실패에서 정확한 run-tag, trial ID, 실제 명령, manifest status 및 실패 사유, PCAP SHA/file size, 원인 진단과 수정 커밋/새 run-tag를 시간순으로 `docs/research-log.md`에 기록한다. 이전 실패 데이터를 삭제하지 않는다.

**현 시점:** 실행/검증 자동화 코드를 준비한 상태이며, 실제 본 실험 200개는 아직 수집하지 않았다.
