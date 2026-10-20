# Native ECH 환경에서 지터가 적용된 HTTPS Beacon 트래픽의 경량 메타데이터 기반 탐지 비교

**영문 제목**  Design and Evaluation of a Lightweight Multi-Feature Flow-Based Detector for Jittered Beacon Traffic under Native ECH  
**작성자**  오리온  
**작성일**  2026년 10월 20일  
**연구 유형**  통제된 합성 HTTPS 트래픽을 이용한 비교 실험  
**연구 저장소**  https://github.com/SuperNova080710/ech-beacon-detection  
**원본 PCAP**  https://github.com/SuperNova080710/ech-beacon-detection/releases/tag/main-v1-pcap-v1

---

## 초록

TLS 1.3의 Encrypted Client Hello(ECH)는 ClientHello 내부의 서버 이름 등 일부 핸드셰이크 정보를 보호하여 수동 네트워크 관찰자가 활용할 수 있는 정보를 줄인다. 이에 따라 암호문을 복호화하지 않고 획득할 수 있는 시간·패킷 크기·전송 방향·버스트 관련 메타데이터의 탐지 효용을 평가할 필요가 있다. 본 연구는 Native ECH를 활성화한 통제된 HTTPS 실험 환경에서, 지터가 적용된 합성 Beacon 통신을 Timing-only 탐지기와 경량 Multi-feature 탐지기로 분류하고 탐지 성능과 추론 비용을 비교하였다. 사전 설계에 따라 Beacon 100개와 정상 트래픽 100개, 총 200개 Trial을 수집하였다. 각 Trial은 30개의 단기 HTTPS 연결로 구성하였으며, 90개를 Calibration에, 110개를 고정된 Held-out Test에 사용하였다. Beacon 지터는 0%, 10%, 30%, 50%, 70%로 설정하였다. Test에서 두 탐지기는 모두 Beacon 50개를 탐지하여 모든 지터 수준에서 재현율 1.0000을 기록하였다. 따라서 Multi-feature 탐지기가 높은 지터에서 재현율을 더 잘 유지할 것이라는 사전 가설은 지지되지 않았다. 반면 정상 60개에 대한 오탐은 Timing-only 10개, Multi-feature 7개로 나타났고, 전체 F1-score는 각각 0.9091과 0.9346이었다. 순수 추론의 110-Trial 배치 중앙값은 각각 0.080385 ms와 1.408802 ms였다. 이 결과는 제한된 합성 ECH 조건에서 Multi-feature 방식이 재현율을 추가로 높이지는 못하면서 오탐을 일부 줄였고 더 높은 계산 비용을 요구했음을 보여준다. 실제 악성 C2 및 운영망으로 일반화할 근거는 아직 충분하지 않다.

**주제어:** Encrypted Client Hello, TLS 1.3, HTTPS Beacon, Jitter, 암호화 트래픽 분석, Flow Metadata, 오탐률, 재현성

## 1. 서론

### 1.1 연구 배경

암호화 통신은 이용자의 개인정보와 서비스 통신을 보호하지만, 네트워크 기반 보안 탐지에는 관측 가능한 신호의 축소라는 과제를 남긴다. RFC 9849에 정의된 TLS Encrypted Client Hello(ECH)는 ClientHello 내부 정보를 서버 공개키로 암호화하도록 규정한다[1]. ECH 배포로 인한 SNI 가시성 변화와 네트워크 보안 운영에 대한 영향도 IETF 문서에서 논의되고 있다[2]. 다만 해당 문서는 진행 중인 Internet-Draft이며 확정된 표준과 구분해야 한다.

암호화된 애플리케이션 내용을 보지 않고도 연결 발생 시각, 패킷 길이, 방향 등의 메타데이터를 이용해 트래픽을 분석하는 접근은 기존 연구에서 제시되어 왔다[3,6,7]. Beacon은 주기적으로 발생하는 통신 패턴을 가지므로 연결 간격의 규칙성에 근거해 식별할 수 있지만, 간격에 변동을 주는 지터(jitter)는 규칙성을 낮출 수 있다. SCADA/ICS 환경의 선행연구는 연결 시각 메타데이터와 변동계수(CV)를 활용한 저지터 Beacon 탐지를 실험하였다[4]. 반면 최신 공개 C2 데이터셋에서도 다양한 지터 조건의 활용이 확인된다[5].

본 연구는 새로운 ECH 프로토콜이나 새로운 메타데이터 특징 자체를 발명하는 것이 아니다. **Native ECH가 실제로 동작하는 통제된 환경에서 두 경량 탐지 접근을 동일한 평가 분할로 비교하고, 가설과 다른 결과까지 보존하는 실험적 검증**에 목적이 있다.

### 1.2 연구 질문과 사전 가설

연구 질문은 다음과 같다. “Native ECH 환경에서 Beacon 트래픽의 지터가 증가할 때, Timing-only 탐지와 Timing·Packet Size·Directionality·Burst를 결합한 경량 Multi-feature 탐지의 성능은 어떻게 달라지는가?”

실험 전 확정한 가설은 **“Native ECH 환경에서 Timing·Packet Size·Directionality·Burst 특징을 결합한 경량 다중특징 탐지 방식은 Timing-only 방식보다 지터가 증가한 Beacon 트래픽의 탐지율을 더 높게 유지할 것이다.”**이다. 독립적으로 비교하는 주요 요인은 탐지기 종류와 Beacon 지터 수준이며, 1차 결과 변수는 지터 수준별 Beacon 재현율, 보조 결과 변수는 Precision, F1-score, FPR, FNR 및 처리 비용이다. 사전에 정한 반증 조건은 고지터 조건에서 유의미하고 일관된 탐지율 우위가 관찰되지 않는 경우이다. 분석 후 가설을 유리하게 고치지 않는 원칙을 적용하였다.

### 1.3 연구 기여와 범위

본 연구는 (1) Native ECH 기반 합성 HTTPS 트래픽을 200개 Trial로 수집하고, (2) 별도 Calibration과 Held-out Test 분할에 동일한 두 탐지기를 적용하며, (3) 지터별 탐지 성능·정상 프로필별 오탐·추론 비용을 함께 비교한다. 적용 범위는 단일 실험 환경에서 생성한 합성 데이터로 한정하며, 실제 악성코드의 탐지율이나 ECH의 인과적 효과를 직접 추정하지 않는다.

## 2. 관련 연구 및 연구 공백

### 2.1 ECH와 암호화 트래픽의 관측 가능성

RFC 9849는 ECH의 메시지 암호화와 동작 원리를 규정한다[1]. Campling 등은 ECH 배포가 SNI 기반 보안 관리 방식에 미치는 운영상 영향을 논의한다[2]. Abu-Adaiq 등은 TLS 1.3 및 ECH 이후의 암호화 트래픽 탐지 연구를 정리하면서 시간, 길이, 방향과 같은 잔여 메타데이터를 활용하는 접근과 그 한계를 검토한다[3]. 따라서 이러한 메타데이터를 이용하는 발상 자체는 본 연구의 새로운 주장에 해당하지 않는다.

### 2.2 Beacon과 지터 및 메타데이터 기반 탐지

Yilmaz 등의 실험은 SCADA/ICS 유사 환경에서 CV 기반 시간 규칙성과 이상 탐지를 결합해 Beacon 통신을 구분하였다[4]. 이는 Timing-only 방식의 비교 근거를 제공하지만 본 연구의 Native ECH, 높은 지터 범위, 동일 Trial별 다중특징 방식 비교와 동일한 연구 설계는 아니다. Jeon과 Park이 공개한 TQH-C2 버전 1.2.2는 여러 암호화 C2 전송 구성에 0%, 30%, 70% 지터를 포함하는 공개 데이터셋이다[5]. 이 자료는 지터를 연구 변수로 선택할 근거가 되지만, 본 실험에 입력한 데이터는 아니며 ECH 실험 결과로 혼동해서는 안 된다.

### 2.3 다양한 메타데이터 특징과 계산 비용

Yang 등은 패킷 길이·방향·도착 시각을 활용하는 GraphSAGE 기반 암호화 트래픽 분류를 제안하였다[6]. Roy 등은 패킷 크기와 도착 간격을 이용하는 분류 모델을 평가하였다[7]. Li 등은 전역 통계와 패킷 바이트 정보의 융합을 제시하였다[8]. 단, Li 등의 방식은 패킷 바이트 정보까지 사용하므로 본 연구의 순수 Flow 메타데이터 방식과 동일한 입력 제약을 갖지 않는다. 이 연구들은 특징 선택의 배경이지만 Native ECH Beacon 조건에서 본 연구의 결과를 사전에 보증하지는 않는다.

### 2.4 검토 범위 내 연구 공백

검토한 문헌들은 ECH의 관측성 변화, 시간 기반 Beacon 탐지, 지터가 적용된 C2 데이터, 복합 특징의 유용성을 각각 다룬다. 반면 **Native ECH 조건에서 지터를 단계적으로 높이며 Timing-only와 경량 Multi-feature를 같은 고정 평가 집합에서 비교하고 추론 비용까지 동시 보고한 실험**은 검토한 문헌의 범위에서 직접적인 일치 사례가 충분히 확인되지 않았다. 이는 전 세계에 선행연구가 전혀 없다는 뜻이 아니라, 본 연구가 대상으로 삼는 제한된 비교 문제의 정당화이다.

## 3. 연구 방법

### 3.1 사전 설계와 연구 단위

본 연구는 성능 결과를 확인하기 전에 조건, 표본 수, 비교 지표, 분할 원칙과 가설 판단 기준을 문서로 확정하였다. 하나의 Trial은 단일 TCP 연결이 아니라 같은 클라이언트가 같은 ECH 서버에 생성한 **30개의 단기 HTTPS 연결 시퀀스**이며, 연결 사이의 스케줄 간격은 29개이다. 서로 다른 Trial을 평가 단위로 사용하였다. 각 Trial의 시작 시각·실행 결과·PCAP 경로와 SHA-256, Flow Metadata 등을 Raw Manifest로 보존하였다.

**표 1. 사전 확정 실험 구성**

| 항목 | 설정 |
|---|---|
| 네트워크 프로토콜 | TLS 1.3 HTTPS, Native ECH 실험 환경 |
| Beacon Trial | 100개: 지터 5수준 × 수준당 20개 |
| Normal Trial | 100개: interactive-burst 40, irregular-lognormal 30, mixed-activity 30 |
| Trial당 연결 수 | 30개 단기 HTTPS 연결, 스케줄 IAT 29개 |
| Calibration | 90개: Beacon 50 + Normal 40 |
| Held-out Test | 110개: Beacon 50 + Normal 60 |
| 지터 수준 | 0%, 10%, 30%, 50%, 70% |
| 기본 Beacon 간격 | 1.0초 |
| 평가 지표 | TP, FP, TN, FN, Precision, Recall, F1, FPR, FNR |
| 계산 비용 | 순수 추론 및 별도 모델 준비/Calibration 비용 |

### 3.2 ECH 테스트베드와 원자료 생성

ECH를 지원하는 클라이언트와 서버를 Docker 기반 테스트베드에 배치하고 패킷 캡처 환경을 연결하였다. 호스트 기본 OpenSSL 및 curl 설치를 교체하지 않는 방식을 채택하였다. Native ECH 적용 및 비적용 요청에 대한 프로토콜 증거를 별도 기록하고, 본 실험 데이터를 ECH 조건에서 수집하였다. 트래픽은 실제 악성 C2 프로그램으로 생성한 것이 아니라, 반복적인 HTTPS 접속 행위를 모사한 합성 데이터이다.

Beacon의 예정된 연결 간격은 Iᵢ(j) = T × (1 + j × zᵢ)로 정의하였다. 여기서 T = 1.0초, zᵢ는 Uniform(−1, 1) 난수, j는 0.0부터 0.7까지의 지터 비율이다. 따라서 70% 지터의 **예정된** 간격 범위는 0.30~1.70초이다. 동일 Trial 번호에는 지터 수준을 바꾸어도 같은 정규화 난수열과 Payload 프로필열을 적용하는 대응 설계(paired design)를 사용하였다. 실제 측정 간격은 스케줄 값과 다를 수 있어 PCAP 기반 특징을 별도로 추출하였다.

정상 트래픽은 세 가지 생성 프로필을 사용했다. interactive-burst는 짧은 연결 구간과 긴 휴식 구간을 반복한다. irregular-lognormal은 로그정규 간격에 클리핑을 적용하고, mixed-activity는 짧은 활동과 긴 휴식의 혼합 분포를 사용한다. Payload 크기를 트래픽 클래스의 단순 구분 신호로 만들지 않기 위해 Beacon과 Normal에 같은 요청·응답 Payload 프로필의 선택 확률을 적용하였다. Pilot 8개 Trial은 구현 점검 목적으로만 사용하고 본 평가 데이터와 구분했다.

### 3.3 특징 추출과 탐지기

PCAP에서 Trial 단위 연결 시퀀스를 구성하고 Flow 시작 시각의 Inter-arrival Time(IAT), 패킷 길이 통계, 송수신 방향 비율·비대칭 및 버스트 관련 통계를 계산하였다. 최종 Multi-feature 모델은 13개 특징을 사용하는 경량 로지스틱 회귀 기반 점수 계산과 Calibration 임계값을 결합하였다. Timing-only Baseline은 IAT 변동계수(`iat_cv`)와 Calibration 임계값에 기초한다. 본 실험의 저장된 판정 임계값은 각각 **0.7667340945734821**(Timing-only) 및 **−1.2556072376827678**(Multi-feature 점수)이다. 두 값은 서로 다른 점수 체계에 속하므로 직접 크기를 비교하지 않는다.

특징 목록과 모델의 상세 구현은 저장소 `detector/`, `data/processed/main-v1/`, Calibration 산출물에 남겼다. 본문에서는 공개된 특징군과 실제 평가에 사용된 최종 모델 유형을 설명하며, 구체적인 재생성 명령은 저장소 스크립트의 실행 도움말과 최종 제출 재현 지침을 따른다. 본 결과를 얻은 뒤 분류기 또는 임계값을 재학습하거나 수정하지 않았다.

### 3.4 분할과 데이터 누수 방지

전체 200개 Trial을 사전에 고정된 Calibration 90개와 Held-out Test 110개로 분할하였다. 두 탐지기는 동일한 Test Feature와 Label을 평가에 사용했다. Test의 정답 Label은 판정 점수를 만드는 데 사용하지 않고 최종 지표 계산에만 이용했다. 단, 같은 Beacon Trial 번호의 서로 다른 지터 수준은 정규화 지터 시퀀스를 공유하는 대응 설계이므로 개별 관측값의 완전한 통계적 독립성을 전제하지 않는다. 또한 지터 수준별 조건부 F1 계산에서는 **같은 정상 표본 60개를 매번 재사용**하였다.

### 3.5 평가 정의 및 처리 시간 측정

Precision = TP/(TP+FP), Recall = TP/(TP+FN), F1 = 2×Precision×Recall/(Precision+Recall), FPR = FP/(FP+TN), FNR = FN/(FN+TP)로 정의한다. 지터별 Recall은 수준당 Beacon 10개로 계산한다. 지터별 조건부 F1은 해당 수준의 Beacon 10개와 동일한 정상 60개를 결합한 70개 관측값에 대한 지표이며, 독립된 평가 집합 다섯 개의 결과가 아니다.

처리 비용 실험은 Python 3.10.12 및 Linux 6.8 환경에서 `time.perf_counter_ns()`로 수행하였다. 순수 추론은 사전에 추출한 동일한 110개 Feature를 이용했고, 20회 워밍업 후 250회 반복했다. 매 반복에서 탐지기 실행 순서를 번갈아 적용하였다. 학습·Calibration 측정은 3회 워밍업 후 15회 반복하였으며 두 탐지기가 수행하는 작업 범위와 Calibration 표본 수가 다르다. 모든 처리 시간은 단일 측정 세션의 요약 통계로, 종단 간 탐지 지연·시스템 처리량을 나타내지 않는다.

### 3.6 원자료 무결성과 예외 관리

200개 PCAP 모두 Raw Manifest에 기록된 파일명·크기·SHA-256과 일치했다. 일반적인 TShark 기반 검사에서는 **199개에 대한 기본 검증과 `normal-irregular-lognormal-t03`에 대한 별도 Decode-As 감사**를 구분하였다. 후자의 경우 포트 기반 TLS 해석이 필요했고, 이를 기본 검증 200개 통과로 바꾸어 기록하지 않았다. Operator Log 세 개(`beacon-j00-t01`, `t02`, `t03`)는 수집 기록상 존재하지 않으며, 누락 원인은 확정하지 않았다. 누락 로그를 인위적으로 생성하지 않았다.

## 4. 연구 결과

### 4.1 전체 Held-out Test 성능

**표 2. Held-out Test 탐지 성능(N = 110)**

| 지표 | Timing-only | Multi-feature |
|---|---:|---:|
| TP / FP / TN / FN | 50 / 10 / 50 / 0 | 50 / 7 / 53 / 0 |
| Precision | 0.8333 | 0.8772 |
| Recall | 1.0000 | 1.0000 |
| F1-score | 0.9091 | 0.9346 |
| FPR | 0.1667 | 0.1167 |
| FNR | 0.0000 | 0.0000 |

두 탐지기 모두 Beacon 50개를 전부 탐지했다. Multi-feature는 정상 60개 중 7개를 오탐하여 Timing-only보다 3개 적었다. 이에 따라 Precision은 약 4.39%p, F1-score는 약 2.55%p 높았고, FPR은 16.67%에서 11.67%로 5.00%p 낮았다. 표본 크기와 짝지어진 예측 결과를 고려할 때 이것을 곧바로 모집단 성능 우위 또는 통계적 유의성으로 해석하지 않는다.

### 4.2 지터별 Beacon 재현율

**표 3. 지터 수준별 Beacon 탐지 결과**

| 지터 | Beacon Test 수 | Timing-only TP / FN | Multi-feature TP / FN | 두 탐지기 Recall |
|---|---:|---:|---:|---:|
| 0% | 10 | 10 / 0 | 10 / 0 | 1.0000 |
| 10% | 10 | 10 / 0 | 10 / 0 | 1.0000 |
| 30% | 10 | 10 / 0 | 10 / 0 | 1.0000 |
| 50% | 10 | 10 / 0 | 10 / 0 | 1.0000 |
| 70% | 10 | 10 / 0 | 10 / 0 | 1.0000 |

사전 가설이 초점을 맞춘 높은 지터 50%, 70%에서도 두 탐지기의 Recall은 1.0000으로 같았다. 실험에서 탐지율 하락이 발생하지 않았기 때문에 Multi-feature의 **높은 지터 탐지율 유지 우위는 관찰되지 않았다.** 지터가 70%까지 증가해도 두 탐지기가 모든 Beacon을 탐지했다는 진술은 본 합성 데이터와 평가 분할에만 적용된다.

수준별 Beacon 10개에 같은 정상 표본 60개를 결합하여 계산한 조건부 F1은 모든 지터에서 Timing-only 0.6667, Multi-feature 0.7407이었다. 이는 정상 집합을 반복 사용한 결과이므로 지터별 독립된 다섯 실험으로 간주하지 않는다. 해당 차이는 지터별 Beacon Recall 차이가 아니라 공통 정상 집합의 오탐 차이에 기초한다.

### 4.3 정상 프로필별 오탐

**표 4. 정상 트래픽 유형별 오탐(Normal Test = 60)**

| 유형 | Test 수 | Timing-only FP | Multi-feature FP | Timing FPR | Multi FPR |
|---|---:|---:|---:|---:|---:|
| interactive-burst | 24 | 0 | 0 | 0.0000 | 0.0000 |
| irregular-lognormal | 18 | 10 | 7 | 0.5556 | 0.3889 |
| mixed-activity | 18 | 0 | 0 | 0.0000 | 0.0000 |
| 전체 | 60 | 10 | 7 | 0.1667 | 0.1167 |

모든 오탐은 irregular-lognormal 정상 프로필에 집중되었다. 동일한 정상 샘플을 비교하면 양쪽에서 모두 오탐으로 판정된 표본은 7개, Timing-only에서만 오탐된 표본은 3개, Multi-feature에서만 오탐된 표본은 0개, 두 방식 모두 정상으로 판정한 표본은 50개였다. 이는 관찰된 오탐 감소가 **3개 표본의 판정 차이**에 해당함을 명확히 한다. 어느 특징이 그 차이를 일으켰는지는 Ablation Study를 수행하지 않아 확정할 수 없다.

### 4.4 추론 처리 비용

**표 5. 순수 추론 마이크로벤치마크(110-Trial 배치, 250회)**

| 항목 | Timing-only | Multi-feature |
|---|---:|---:|
| 중앙값 배치 시간(ms) | 0.080385 | 1.408802 |
| P95 배치 시간(ms) | 0.086857 | 1.447461 |
| 중앙값 Trial당 시간(μs) | 0.730777 | 12.807295 |

Multi-feature의 배치 중앙값 추론 시간은 Timing-only의 약 17.53배였다. 이는 전처리된 동일한 Feature에 대한 **순수 Python 판정** 비교이며, PCAP 해석·특징 추출·파일 입출력과 네트워크 전송이 제외되어 있다. 결과를 실서비스 종단 간 처리 지연으로 해석해서는 안 된다.

### 4.5 모델 준비 및 Calibration 비용

**표 6. 모델 준비/Calibration 마이크로벤치마크(15회)**

| 항목 | Timing-only | Multi-feature |
|---|---:|---:|
| 중앙값(ms) | 0.027777 | 199.032131 |
| P95(ms) | 0.032999 | 216.105765 |
| 입력/연산 | 정상 40개로 임계값 보정 | 90개로 800 Epoch 로지스틱 회귀 학습 및 임계값 보정 |

중앙값 기준 준비 시간 비율은 약 7,165.36배다. 그러나 두 행의 계산 작업과 입력량이 같지 않으므로 이 값은 동일 연산 구현의 순수 성능 비교가 아니다. 측정은 한 환경의 요약 결과이며 반복별 원시 시간 표본은 저장되지 않았다.

## 5. 논의

### 5.1 사전 가설의 판단

핵심 가설은 높은 지터에서 Multi-feature 방식이 더 높은 Beacon Recall을 유지한다는 것이었다. 그러나 0~70%의 모든 지터 수준에서 두 모델 모두 Recall 1.0000을 기록했다. 따라서 **본 실험의 사전 가설은 지지되지 않았다.** 이는 Multi-feature가 일반적으로 무효하다는 결론도, 모든 Native ECH 환경에서 두 모델 성능이 동등하다는 결론도 아니다. 실험 조건에서 연구가 예측한 재현율 격차를 발견하지 못했다는 정확한 기술이다.

### 5.2 예상과 달랐던 결과의 해석 가능성

데이터가 허용하는 해석은 세 가지 수준으로 구분된다. 첫째, 현재 지터 범위와 Beacon 생성 방식에서 두 모델 모두 충분히 높은 민감도를 보인 것이 관찰된 사실이다. 둘째, Calibration 임계값과 합성 시퀀스의 분포가 두 모델의 판정을 유사하게 만들었을 가능성은 검토할 수 있으나, 별도의 간격 범위 확장 실험을 하지 않았으므로 원인으로 확정하지 않는다. 셋째, Normal의 irregular-lognormal 시간 분포가 Beacon과 부분적으로 비슷한 판정 신호를 발생시켰을 가능성도 합리적인 설명 후보이나, 특징별 제거 실험 없이는 오탐 감소의 인과적 원인을 입증하지 못한다.

### 5.3 오탐 감소와 비용의 절충

Multi-feature의 FPR은 16.67%에서 11.67%로 낮아졌지만, 오탐 감소 건수는 3개이며 모두 하나의 정상 유형에서 발생했다. 반면 순수 추론 중앙값은 약 17.53배였다. 실제 운용에서 어느 탐지기가 더 적합한지는 트래픽 규모, 허용 가능한 오탐 비용, 처리량 및 시스템 제약에 좌우된다. 이번 실험은 이 절충 관계를 관찰했을 뿐 실제 운영망의 비용-효익을 산출하지 않았다.

### 5.4 ECH에 대한 인과적 해석의 경계

본 실험은 Native ECH를 적용한 HTTPS 환경에서 암호문 복호화나 내부 SNI 관찰 없이 Flow 기반 탐지를 수행할 수 있음을 제한적으로 확인한다. 다만 ECH ON/OFF에 대한 탐지기 성능 비교를 실험하지 않았으므로, ECH가 탐지 정확도를 악화 또는 개선한다고 말할 수 없다. 본 연구의 대상은 **ECH가 활성화된 상태에서의 탐지 방식 비교**이지 ECH 자체의 성능 효과 추정이 아니다.

## 6. 연구의 한계

본 연구의 데이터는 통제된 HTTPS 연결을 모사한 합성 트래픽이며 실제 악성 C2가 아니다. 단일 Docker 기반 실험 환경, 고정된 1.0초 기본 Beacon 주기, 다섯 지터 수준, 제한된 Payload 프로필과 Normal 생성 분포를 사용했다. Test에서 지터 수준당 Beacon은 10개, 정상 표본은 총 60개로 외부 일반화에 한계가 있다. 동일 Trial 번호의 대응 난수열과 지터별 공통 정상 60개 재사용 또한 독립 관측값 해석을 제한한다. Multi-feature의 특징별 기여도를 검증한 Ablation Study, 여러 독립 호스트 실험, 통계적 신뢰구간이나 유의성 검정은 수행하지 않았다. 실행 시간은 단일 Python 환경에서 측정한 마이크로벤치마크이며 실제 시스템 처리량·메모리·종단 간 탐지 지연은 포함하지 않는다. Raw 로그 3개의 부재와 TShark Decode-As 예외도 원본 보존 기록에 그대로 남겼다.

추후 연구에서는 다른 기준 주기, 정상 프로필, 실제 운영망 및 공개 외부 데이터셋, 특징 제거 실험, 여러 실행 환경과 반복별 지연 표본을 활용하여 본 결과를 검증할 필요가 있다. 이러한 추가 실험은 이번 Held-out Test에 사후 적용한 재분석과 구분해야 한다.

## 7. 결론

본 연구는 Native ECH 환경에서 생성한 합성 HTTPS Beacon 및 정상 트래픽 총 200개 Trial을 대상으로 Timing-only와 경량 Multi-feature 탐지 방식을 비교하였다. 사전에 고정한 90개 Calibration과 110개 Held-out Test 분할을 사용했으며, Test의 Beacon 50개에 대해 두 탐지기 모두 모든 지터 수준에서 Recall 1.0000을 기록하였다. 따라서 높은 지터에서 Multi-feature가 재현율을 더 높게 유지할 것이라는 가설은 지지되지 않았다. 다만 Multi-feature는 정상 오탐을 10건에서 7건으로 줄여 전체 F1-score를 0.9091에서 0.9346으로 높였고, 순수 추론 배치 중앙값은 0.080385 ms에서 1.408802 ms로 증가했다. 이 결과는 **특정 합성 ECH 환경에서 오탐 감소와 연산 비용 증가가 동반될 수 있다는 제한된 관찰**이다. 실제 악성 C2 트래픽, 운영망 일반화 및 ECH 자체의 영향은 본 결과로 확정할 수 없다.

## 참고문헌

[1] Rescorla, E., Oku, K., Sullivan, N., & Wood, C. A. (2026). *TLS Encrypted Client Hello* (RFC 9849). RFC Editor. https://www.rfc-editor.org/rfc/rfc9849.html

[2] Campling, A. J., Vixie, P., Wright, D., Taddei, A., & Edwards, S. (2026). *Encrypted Client Hello Deployment Considerations* (Internet-Draft, draft-campling-ech-deployment-considerations-12). IETF Datatracker. https://datatracker.ietf.org/doc/draft-campling-ech-deployment-considerations/

[3] Abu-Adaiq, H., Biswas, M. I., Alnajjar, A. Y., & Zhang, S. (2026). Encrypted-Traffic Detection in the TLS 1.3 Era: A Comprehensive Review and Future Research Directions. *Electronics, 15*(17), 3846. https://doi.org/10.3390/electronics15173846

[4] Yilmaz, M. T., Doğan, F., Söğüt, E., Algül, E., & Aksoy, Ç. (2026). Beaconing detection via timing-based flow metadata analysis: implications for SCADA/ICS. *International Journal of Information Security, 25*, Article 161. https://doi.org/10.1007/s10207-026-01335-w

[5] Jeon, D., & Park, D. (2026). *TQH-C2: An Encrypted Command-and-Control Traffic Dataset Across Protocols and Encryption Layers* (Version 1.2.2) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.22732327

[6] Yang, J., Shen, H., Diao, Z., & He, Y. (2026). Enhancing Fine-Grained Encrypted Traffic Classification via Temporal Bi-Directional GraphSAGE. *Applied Sciences, 16*(7), 3427. https://doi.org/10.3390/app16073427

[7] Roy, S., Shapira, T., & Shavitt, Y. (2022). Fast and lean encrypted Internet traffic classification. *Computer Communications, 186*, 166–173. https://doi.org/10.1016/j.comcom.2022.02.003

[8] Li, H., Tao, J., Yu, L., Luo, Y., & Wang, Z. (2025). GSPB: a global-statistic and packet-byte fusion framework for encrypted traffic classification. *Cybersecurity, 8*, Article 120. https://doi.org/10.1186/s42400-025-00446-6

## 부록 A. 주제 선정 및 AI 지원 과정의 추적성

2026년 10월 16일 연구 로그에는 관심 분야 후보로 **인증 및 Passkey, Post-Quantum DNSSEC, ECH protocol, Encrypted C2/Beacon detection, XDR detection** 다섯 영역이 기록되어 있다. 최종 주제는 Native ECH 조건의 Jittered Beacon 탐지로 선정했다. 당시 기록에 남은 선정 근거는 (1) ECH로 인한 관측성 문제, (2) Timing 기반 탐지의 확장 가능성, (3) 지터 변수의 직접 측정 가능성, (4) 합성 트래픽 원자료의 재현성, (5) 제한된 과제 기간 내 실행 가능성이다.

**기록상 제한:** 탈락 후보별 개별 사유와 AI가 제안한 최초 질문 10개의 원문은 현재 확인된 연구 로그에 없다. 해당 내용을 사후에 창작하여 실험 전 기록으로 소급하지 않는다. T10-C02/C03/C09를 완전하게 증빙하려면 연구자가 실제 토론·선택 과정을 회고하여 별도로 표시해야 한다.

연구 전 과정에서 AI는 문헌 탐색·초안 구성·실험 및 검증 절차의 정리에 보조적으로 참여하였다. 최종 주제 선정, 실험 실행 결과의 사실 여부 확인, 고정된 평가 결과의 해석 및 가설의 지지 여부는 연구 기록과 실제 수치에 따라 결정하였다. AI가 생성한 문장과 수치의 정확성은 원본 문서·평가 JSON 및 공식 출처를 기준으로 대조했다. AI의 제안이 실험 결과를 더 좋게 보이도록 사후 Threshold를 바꾸는 근거로 사용되지 않도록 하였다.

## 부록 B. 데이터·재현·무결성 확인

**연구 저장소:** https://github.com/SuperNova080710/ech-beacon-detection

**PCAP Release:** https://github.com/SuperNova080710/ech-beacon-detection/releases/tag/main-v1-pcap-v1

**주요 기록 경로:** `docs/experiment-design.md`, `docs/research-log.md`, `docs/related-work.md`, `docs/main-v1-evidence-preservation.md`, `data/raw/main-v1/`, `data/processed/main-v1/`, `results/shared-splits/main-v1/`, `results/timing-only/main-v1/`, `results/multi-feature/main-v1/`, `results/metrics/main-v1/`, `results/figures/main-v1/`.

**실험 결과 기준 파일:** `results/metrics/main-v1/heldout-evaluation.json`(SHA-256 `b357dee703565d98b65467b94f488f9681e53f3ed41b1e3153f432279be9f46b`), `results/metrics/main-v1/processing-cost-benchmark.json`(SHA-256 `4d25da1fd02a2b672e42074454239ca1067c2e055090112c732c70391105c3df`). 그림 6개와 대응 SHA-256은 `results/figures/main-v1/figure-manifest.json`에 기록되어 있다.

PCAP 200개는 일반 Git 추적과 분리하여 GitHub Release `main-v1-pcap-v1`에 보존했으며, Release 자산 3개를 다시 내려받아 로컬 검증본과 SHA-256이 일치함을 확인했다. PCAP 압축파일의 SHA-256은 `d481c3145eeaaca3b9a0e2d8f9bf26a34e7acade2aaea99c43e9e34de89b16e0`이다. 자료실의 실험 기록은 Dataset의 무결성과 처리 절차 추적을 가능하게 하지만, 본 원고 작성 시점에 제3자가 새 작업 디렉터리에서 **전체 ECH 트래픽을 처음부터 재생성하는 종단 간 실습을 완료했다고 주장하지 않는다.** 원자료 해시 대조와 기존 평가 수치의 재계산은 구분해 검증해야 한다.

**최소 확인 절차:** (1) 저장소를 내려받아 `sha256sum -c artifacts/audit/main-v1/processed-sha256.txt`로 Processed 3개 파일을 검증한다. (2) `results/metrics/main-v1/heldout-evaluation.json`의 TP·FP·TN·FN을 표 2와 대조하고, `results/metrics/main-v1/processing-cost-benchmark.json`의 중앙값을 표 5·6과 대조한다. (3) 그림 재생성이 필요하다면 원본 저장소가 아닌 별도의 복사본에서 기존 `results/figures/main-v1/` 출력 파일을 보호한 후 `python scripts/plot_main_results.py`를 실행한다. 이 스크립트는 같은 이름의 기존 그림을 덮어쓰지 않도록 구성되어 있다. (4) GitHub Release 자산을 다운로드하여 `sha256sum -c main-v1-pcap-release.sha256`을 실행하고 Archive 내부 PCAP 항목 200개 및 Manifest 해시 목록을 확인한다. 이 과정은 기존 평가 수치의 파일 검증 및 그림 재생성에 관한 것이며, ECH 테스트베드 전체 재수집과 구분한다.

제출용 8MB 이하 ZIP은 별도로 구성해야 하며, ZIP 내부에는 최소한 완성 원고, 제출 가능한 원자료, 고정 평가 결과, 실행 스크립트 또는 간단한 절차 설명이 포함되어야 한다. 전체 PCAP을 ZIP에 다시 포함하지 않는 경우 Release 경로와 체크섬을 함께 제시하고, 평가자가 인증 없이 다운로드할 수 있는지 실제로 확인한다.
