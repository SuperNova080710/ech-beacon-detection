# main-v1 원본 데이터 및 증거자료 보존 기록

## 1. 목적

Native ECH 환경의 main-v1 실험에서 생성된 원본 데이터, 감사 증거 및 성능 측정 기록의 보존 상태를 기록한다.

기존 원본을 수정하거나 누락 자료를 임의로 생성하지 않으며, 확정된 Detector, Calibration, Prediction 및 Evaluation 결과를 변경하지 않는다.

## 2. 원본 수집 자료

경로: `data/raw/main-v1/`

- Manifest: 200개
- Flow Metadata CSV: 200개
- Execution Marker: 200개
- Operator Log: 197개
- 실행 환경 기록: 1개
- 전체 파일: 798개

Operator Log가 없는 Trial은 다음과 같다.

- `beacon-j00-t01`
- `beacon-j00-t02`
- `beacon-j00-t03`

세 Trial 모두 Manifest, Flow Metadata, PCAP이 존재한다.

Operator Log가 없는 정확한 원인은 확정되지 않았다. 해당 로그를 임의 생성하거나 수집 기록을 보정하지 않는다.

## 3. PCAP 무결성 검증

경로: `artifacts/pcap/main-v1/`

- Beacon 및 Normal PCAP: 총 200개
- 각 Manifest에 기록된 PCAP 파일명, 파일 크기 및 SHA-256을 실제 PCAP과 비교
- 결과: 200/200 일치

이 결과는 파일 무결성 검증 결과이다.

기존 `normal-irregular-lognormal-t03`의 TLS Decode-As 예외 때문에 모든 Trial의 기본 TShark ClientHello 파싱이 통과했다고 주장하지 않는다. 일반 검증 199개와 해당 예외에 대한 별도 감사 기록을 구분한다.

PCAP은 `.gitignore` 정책에 따라 일반 Git 커밋에 포함하지 않는다. 2026-10-20 GitHub Release `main-v1-pcap-v1`에 별도로 보존했으며, 재다운로드 후 체크섬 일치를 확인하였다.

## 4. Feature 추출 감사 자료

경로: `artifacts/audit/main-v1/`

보존 파일:

- `feature-extraction.log`
- `normal-irregular-lognormal-t03-decode-as.json`
- `processed-sha256.txt`

`processed-sha256.txt`를 이용한 검사에서 다음 파일 모두 일치하였다.

- `data/processed/main-v1/features.csv`
- `data/processed/main-v1/labels.csv`
- `data/processed/main-v1/provenance.json`

## 5. ECH 통신 증거

기존 Git 추적 경로:

- `artifacts/evidence/ech-request.txt`
- `artifacts/evidence/plain-request.txt`
- `artifacts/evidence/nginx-ech-log.txt`

기존 Git 기록은 2026-10-17 증거로 유지한다.

2026-10-19 자료는 기존 증거를 덮어쓰지 않고 다음 경로에 사본으로 보존한다.

- `artifacts/evidence/2026-10-19/ech-request.txt`
- `artifacts/evidence/2026-10-19/plain-request.txt`
- `artifacts/evidence/2026-10-19/nginx-ech-log.txt`

사본은 로컬의 2026-10-19 증거와 바이트 단위로 일치한다.

사본 SHA-256:

- ECH request: `e28a8cf3702fa9bb570aa1f44fae1ed06f571a84481175aa52f0dd7bc1c93188`
- Plain request: `c19eb9a3cb15a93df1e71747e92daa4c9e311bd34c3a291e4e74489b36a98027`
- Nginx log: `4ccab4ad0b81b2c8de848cffddc17e9fe6d661ff4fc4fd245deb8ae43d5de851`

## 6. 예비 추론 Benchmark

파일: `results/metrics/main-v1/inference-benchmark.json`

이 파일은 최종 Processing-cost Benchmark와 별도로 수행한 예비 측정 결과이다.

- Warmup: 20 batches
- Measurement: 11 rounds
- Repetitions per round: 100
- Trials per batch: 110
- Timing-only median: 약 0.781680 μs/trial
- Multi-feature median: 약 13.195941 μs/trial

다음 참조 파일의 SHA-256 일치를 확인하였다.

- Held-out Test Features
- Held-out Evaluation
- Timing-only Prediction
- Multi-feature Prediction

공식 논문에는 최종 `processing-cost-benchmark.json` 결과를 사용하며 예비 측정 결과로 대체하지 않는다.

## 7. 검증 범위 및 남은 작업

완료:

- Raw Manifest / Flow Metadata / Execution Marker 200개씩 확인
- PCAP 200개에 대한 파일명·크기·SHA-256 일치 확인
- Processed 데이터 3개 SHA-256 일치 확인
- 2026-10-19 ECH 증거 사본 3개 바이트 단위 일치 확인
- 예비 Benchmark 참조 파일 4개 SHA-256 일치 확인

미완료:

- 최종 제출용 재현 ZIP 구성 및 용량 검증
- 실제 악성 C2 트래픽 또는 외부 데이터셋에서의 일반화 검증

본 기록은 파일 무결성 및 보존 상태에 대한 감사 기록이며,
논문 최종 제출이나 모든 재현 절차의 완료를 의미하지 않는다.

## 8. PCAP 원격 보존 및 재다운로드 검증

검증일: 2026-10-20

GitHub Release:

https://github.com/SuperNova080710/ech-beacon-detection/releases/tag/main-v1-pcap-v1

원본 PCAP 200개를 `main-v1-pcap-200.tar.gz`로 묶어
GitHub Release에 보존하였다.

| Release Asset | SHA-256 |
|---|---|
| `main-v1-pcap-200.tar.gz` | `d481c3145eeaaca3b9a0e2d8f9bf26a34e7acade2aaea99c43e9e34de89b16e0` |
| `main-v1-pcap-files.sha256` | `a46aa7b6d7c6eaffbd3ed278f0f24c475a329265b996fa76c782488427e897d3` |
| `main-v1-pcap-release.sha256` | `2f7656e939cb51eee695cd1cb14e772fd5d65d20d249353c7fd123ac92540e24` |

검증 결과:

- 원본 PCAP 200개와 Manifest의 SHA-256 일치
- 압축파일 내부 PCAP 200개 확인
- GitHub Release에서 자산 3개 재다운로드 완료
- 압축파일 및 파일별 SHA-256 목록 검증 통과
- 로컬과 다운로드한 Release 자산의 SHA-256 일치

원본 PCAP은 일반 Git 저장소에 포함하지 않는다.

최종 제출용 8MB 이하 재현 ZIP은 별도로 구성하며,
필요한 경우 위 Release의 원본 PCAP을 참조한다.
