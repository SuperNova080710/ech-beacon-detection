# ECH Beacon Detection

ALEPH T10 연구 프로젝트.

## Research Topic

**Native ECH 환경에서 Jittered Beacon Traffic 탐지를 위한
경량 다중특징 Flow 기반 탐지기의 설계 및 평가**

**Design and Evaluation of a Lightweight Multi-Feature Flow-Based Detector
for Jittered Beacon Traffic under Native ECH**

## Research Question

Native ECH 환경에서 beacon traffic의 jitter가 증가할 때,
timing-only 탐지와 timing, packet size, directionality, burst 특성을 결합한
경량 다중특징 탐지 방식의 탐지 성능은 어떻게 달라지는가?

## Status

Research design in progress.

아직 실험 결과는 생성하지 않았다.

## Repository Structure

- `docs/` — 연구 질문, 선행연구, 실험 설계, 연구 로그
- `generator/` — 정상 및 beacon traffic 생성
- `detector/` — feature extraction 및 탐지기
- `experiments/` — 반복 실험 실행
- `data/raw/` — 원자료
- `data/processed/` — 전처리된 데이터
- `results/` — 지표 및 그래프
- `references/` — 참고문헌 관련 자료
- `scripts/` — 재현 및 보조 스크립트
