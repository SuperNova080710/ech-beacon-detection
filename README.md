# Native ECH Beacon Detection

ALEPH T10 연구 프로젝트 · 작성자 **오리온** · 2026-10-20

**연구 제목:** Native ECH 환경에서 지터가 적용된 HTTPS Beacon 트래픽의 경량 메타데이터 기반 탐지 비교  
**English title:** *Design and Evaluation of a Lightweight Multi-Feature Flow-Based Detector for Jittered Beacon Traffic under Native ECH*

> **연구 상태:** `main-v1` 합성 실험 200개 Trial 수집, 두 탐지기 평가 및 결과 분석 완료. 한국어 논문 원고 작성 및 PCAP 원격 보존 완료. **8MB 이하 제출 ZIP(1,882,874바이트)을 생성하여 별도 폴더에서 오프라인 검증을 통과했습니다. ALEPH 플랫폼 제출·승인은 아직 완료되지 않았습니다.**

## 논문 및 연구 자료

- [**한국어 논문 본문 — 오리온**](docs/paper-t10-ko.md): 초록, 서론, 관련 연구, 방법, 결과, 논의, 한계, 결론, 참고문헌 및 부록
- [사전 확정 실험 설계](docs/experiment-design.md) · [연구 결정 및 오류 기록](docs/research-log.md)
- [선행연구 비교](docs/related-work.md) · [30편 문헌검토](docs/literature-review-30.md) · [참고문헌 기록](references/references.md)
- [원본 및 감사 증거 보존 기록](docs/main-v1-evidence-preservation.md) · [T10 평가 기준 51개 점검 및 제출 ZIP 검증 로그](docs/t10-criteria-audit.md)
- [**PCAP 200개 GitHub Release**](https://github.com/SuperNova080710/ech-beacon-detection/releases/tag/main-v1-pcap-v1)

## 연구 질문과 사전 가설

Native ECH 환경에서 Beacon 통신의 지터가 증가할 때, 연결 간격만 사용하는 **Timing-only** 탐지기와 시간·패킷 크기·전송 방향·버스트 특징을 결합하는 **Multi-feature** 탐지기의 분류 성능은 어떻게 달라지는가?

사전 가설은 높은 지터 조건에서 Multi-feature 탐지기가 Timing-only보다 **Beacon 재현율을 더 높게 유지한다**는 것이었다. 아래 결과에서 이 가설은 **지지되지 않았으며**, 평가 후 모델이나 임계값을 변경하지 않았다.

## 실험 구성

| 항목 | main-v1 |
|---|---|
| 프로토콜 | TLS 1.3 HTTPS, Native Encrypted Client Hello(ECH) |
| 원자료 | 200 Trial = Beacon 100 + Normal 100 |
| Trial 구성 | 30개의 단기 HTTPS 연결, 예정된 Inter-arrival Interval 29개 |
| Beacon 지터 | 0%, 10%, 30%, 50%, 70% (수준별 20 Trial) |
| Normal 프로필 | interactive-burst 40, irregular-lognormal 30, mixed-activity 30 |
| Calibration | Beacon 50 + Normal 40 = 90 Trial |
| Held-out Test | Beacon 50 + Normal 60 = 110 Trial |
| 탐지기 | `iat_cv` 임계값 기반 Timing-only, 13개 특징 로지스틱 회귀 기반 Multi-feature |

Calibration/Test는 평가 전 고정했다. 같은 Trial 번호의 지터 수준 간 난수열 공유 및 지터별 F1 계산의 **공통 정상 60개 재사용**을 독립된 반복실험으로 해석하지 않는다.

## 확정된 Held-out Test 결과

| 지표 | Timing-only | Multi-feature |
|---|---:|---:|
| TP / FP / TN / FN | 50 / 10 / 50 / 0 | 50 / 7 / 53 / 0 |
| Precision | 0.8333 | 0.8772 |
| Recall | **1.0000** | **1.0000** |
| F1-score | 0.9091 | 0.9346 |
| FPR | 0.1667 | 0.1167 |
| 순수 추론 Median (110 Trial 배치) | 0.080385 ms | 1.408802 ms |
| 모델 준비·Calibration Median | 0.027777 ms | 199.032131 ms |

- 모든 Beacon 지터(0~70%)에서 두 탐지기 모두 Recall 1.0000: **고지터 Recall 우위 가설을 지지하지 않음**.
- 정상 오탐은 **10건 → 7건**으로 감소했으며, 판정 차이는 모두 `irregular-lognormal` 프로필 정상 표본 3개에서 나타남.
- Multi-feature의 순수 추론 배치 중앙값은 약 **17.53배** 높음. 이는 PCAP 파싱, 특징 추출, 파일 I/O를 제외한 Python 마이크로벤치마크임.
- 모델 준비 시간의 약 **7,165배** 차이는 두 탐지기의 **서로 다른 작업량·학습 절차**를 비교한 수치로, 동일 연산의 속도 비율이 아님.

원천 수치: [Held-out Evaluation](results/metrics/main-v1/heldout-evaluation.json) · [Processing-cost Benchmark](results/metrics/main-v1/processing-cost-benchmark.json) · [결과 그림 6개와 해시](results/figures/main-v1/figure-manifest.json)

## 재현성 및 원자료 보존

| 자료 | 경로 |
|---|---|
| Raw Manifest 200개, Flow Metadata 200개, Marker 200개 등 | [`data/raw/main-v1/`](data/raw/main-v1/) |
| 추출 Feature/Label/Provenance | [`data/processed/main-v1/`](data/processed/main-v1/) |
| Split/Calibration/Prediction | `results/shared-splits/main-v1/`, `results/timing-only/main-v1/`, `results/multi-feature/main-v1/` |
| 평가·추론 비용 | [`results/metrics/main-v1/`](results/metrics/main-v1/) |
| 논문 결과 그림 | [`results/figures/main-v1/`](results/figures/main-v1/) |
| Feature 추출 및 예외 감사 | [`artifacts/audit/main-v1/`](artifacts/audit/main-v1/) |
| ECH 통신 증거 | [`artifacts/evidence/`](artifacts/evidence/) |
| 전체 원본 PCAP | [GitHub Release `main-v1-pcap-v1`](https://github.com/SuperNova080710/ech-beacon-detection/releases/tag/main-v1-pcap-v1) |

PCAP 200개는 일반 Git 커밋에 포함하지 않는다. 원본의 파일명·크기·SHA-256을 200/200 대조했고, GitHub Release 압축파일/해시 목록을 **재다운로드하여 SHA-256 일치**를 검증했다. Release Asset: `main-v1-pcap-200.tar.gz`, `main-v1-pcap-files.sha256`, `main-v1-pcap-release.sha256`.

저장소 루트에서 Processed 파일 3개의 무결성을 확인할 수 있다.

```bash
sha256sum -c artifacts/audit/main-v1/processed-sha256.txt
```

논문 수치는 `heldout-evaluation.json`과 `processing-cost-benchmark.json`에서 확인한다. 결과 그림은 [`scripts/plot_main_results.py`](scripts/plot_main_results.py)로 재생성할 수 있으나, 해당 스크립트는 기존 출력 파일을 덮어쓰지 않도록 구성되어 있으므로 **그림 재생성은 별도의 저장소 복사본에서 수행**한다.

### 감사 예외

- `normal-irregular-lognormal-t03`: 기본 TShark 해석에 예외가 있어 **별도 Decode-As 감사**를 수행했다. 전체 기본 파서 검증을 200/200 성공으로 주장하지 않는다.
- `beacon-j00-t01`, `beacon-j00-t02`, `beacon-j00-t03`: Operator Log는 존재하지 않는다. 누락 이유는 확정하지 않았고, 원자료를 임의 생성하지 않았다.

## 해석의 한계 및 후속 작업

본 연구는 **단일 통제 실험 환경의 합성 HTTPS 트래픽**을 대상으로 한다. 실제 악성 C2 트래픽, 외부 데이터셋, 운영망·다중 호스트의 일반화 성능은 검증하지 않았으며, ECH ON/OFF 간 **탐지 성능의 인과적 비교**도 수행하지 않았다. 특징별 제거 실험과 통계적 우월성 검정도 수행하지 않았다.

최종 ALEPH T10 과제 제출용 **`T10-Orion-main-v1-reproduction.zip`(1,882,874바이트)**은 작성자 로컬 환경에서 별도 폴더 압축 해제와 오프라인 검사(파일 SHA-256 465개, Raw Manifest/Flow Metadata 각 200개, 110개 Held-out Prediction 재계산)를 통과했다. 전체 PCAP 200개는 Release에서 별도 제공한다. **실제 ALEPH 플랫폼 업로드·접수, 선택 URL의 비로그인 접근 및 미충족 과제 항목 보완은 별도 확인이 필요하다.** [Issue #14](https://github.com/SuperNova080710/ech-beacon-detection/issues/14)에서 보존 및 제출 진행 상황을 추적한다.
