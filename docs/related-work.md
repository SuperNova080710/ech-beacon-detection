# Related Work 및 Research Gap

> 조사 기준일: 2026-10-16
>
> 목적: T10-C11~C20을 충족하고, 최종 연구 주제의 신규성을 과장하지 않도록 기존 연구가 이미 해결한 부분과 아직 검증이 부족한 부분을 분리한다.

## 1. 조사 범위

본 연구는 다음 질문을 중심으로 선행연구를 검토했다.

1. ECH가 기존 네트워크 보안 관측성에 어떤 변화를 만드는가?
2. 암호화된 C2/beacon traffic은 payload 없이 어떤 metadata로 탐지되어 왔는가?
3. jitter가 적용된 beacon traffic을 다룬 공개 데이터 또는 실험 연구가 존재하는가?
4. packet size, directionality, timing, burst와 같은 특징의 유효성은 이미 검증되었는가?
5. 위 요소를 **native ECH 환경의 high-jitter beacon detection**에 결합하여 timing-only baseline과 비교한 실험 연구가 이미 존재하는가?

검색은 RFC Editor, IETF Datatracker, Springer Nature, MDPI, ScienceDirect/Elsevier, Zenodo의 원문 또는 공식 메타데이터를 우선 확인했다. 검색 결과의 제목·저자·연도·DOI 또는 공식 문서 번호를 원 출처에서 교차 확인했다.

---

## 2. Related Work Matrix

| ID | 문헌 | 유형 | 기존 연구가 확인한 내용 | 본 연구와 연결 | 본 연구와의 차이 / 한계 |
|---|---|---|---|---|---|
| R1 | Rescorla et al. (2026), RFC 9849, *TLS Encrypted Client Hello* | IETF Standards Track RFC | ECH는 서버 공개키를 이용해 TLS ClientHello를 암호화하며 SNI 등 ClientHelloInner의 민감한 정보를 수동 관찰자로부터 숨긴다. | 본 연구에서 사용하는 native ECH 환경의 표준적 근거다. | 탐지 알고리즘이나 C2/beacon detection 성능을 평가하는 연구가 아니다. |
| R2 | Campling et al. (2026), *Encrypted Client Hello Deployment Considerations*, draft-12 | IETF Internet-Draft | ECH에 의한 SNI 가시성 손실이 threat detection, firewall, content filtering 등 네트워크 보안 운영에 영향을 줄 수 있으며 adversary가 ECH를 C2 은닉에 활용할 가능성을 논의한다. | ECH 환경에서 payload/SNI 비의존 탐지가 필요한 운영적 배경을 제공한다. | 해결 알고리즘의 실험적 성능을 제시하는 논문이 아니며 Internet-Draft이므로 진행 중 문서다. |
| R3 | Abu-Adaiq et al. (2026), *Encrypted-Traffic Detection in the TLS 1.3 Era* | Peer-reviewed review | TLS 1.3/ECH 이후에도 timing, packet length, directionality, flow duration, traffic volume, sequence 등은 관측 가능하나 native TLS 1.3 + ECH에서 C2 탐지 robustness가 충분히 확립되지 않았다고 정리한다. timing 단독보다 packet-size, direction, flow-context를 결합하는 behavioural-statistical 방향을 제안한다. | 본 연구의 다중특징 선택과 research gap의 가장 직접적인 문헌 근거다. | 제안 방향은 conceptual research direction이며 native ECH에서 검증된 detector를 제공하지 않는다. |
| R4 | Yilmaz et al. (2026), *Beaconing detection via timing-based flow metadata analysis: implications for SCADA/ICS* | Peer-reviewed experimental article | Zeek connection metadata, CV 기반 periodicity와 Isolation Forest를 결합해 암호화된 SCADA/ICS beacon을 탐지했다. 연구는 주로 low-jitter periodic beacon을 대상으로 하며 CV ≤ 0.2를 강한 periodicity 기준으로 사용한다. | timing-only/periodicity baseline 설계의 직접적인 근거다. | native ECH를 별도로 검증하지 않았으며 high-jitter 회피 상황에서 packet size·direction·burst를 결합한 경량 detector와의 비교가 중심이 아니다. |
| R5 | Jeon & Park (2026), *TQH-C2: An Encrypted Command-and-Control Traffic Dataset Across Protocols and Encryption Layers*, v1.2.2 | Open research dataset | TLS, QUIC, HTTP/AES, HTTP/2-over-TLS의 네 가지 C2 transport에서 0/30/70% jitter와 여러 beacon interval을 포함하는 재현 가능한 데이터셋을 공개했다. | high-jitter encrypted C2가 실제 연구 변수로 사용되고 있음을 확인하며 본 연구의 jitter 범위 선정에 참고가 된다. | native ECH가 포함되지 않으며 특정 detector의 native ECH robustness를 검증한 논문이 아니다. |
| R6 | Yang et al. (2026), *Enhancing Fine-Grained Encrypted Traffic Classification via Temporal Bi-Directional GraphSAGE* | Peer-reviewed experimental article | payload/TLS field 없이 packet size, direction, arrival time 세 가지 protocol-agnostic metadata만으로 암호화 traffic을 분류했고, 세 요소 모두가 분류 성능에 기여함을 실험했다. | packet size + direction + timing을 결합하는 것이 기술적으로 타당하다는 실험 근거다. | 목적이 fine-grained application classification이며 C2 beacon, jitter robustness, native ECH detector 평가가 아니다. 모델도 경량 rule/statistical detector보다 복잡한 GNN이다. |
| R7 | Roy, Shapira & Shavitt (2022), *Fast and lean encrypted Internet traffic classification* | Peer-reviewed experimental article | packet size와 inter-arrival time만으로 암호화 traffic을 빠르게 분류할 수 있음을 실험했으며 payload 없이도 단순 metadata가 유용함을 보였다. | 경량 metadata 기반 접근의 선행 근거이며 processing-cost 비교의 배경이 된다. | C2/beacon detection이 아니며 ECH·jitter·directionality·burst robustness를 다루지 않는다. |
| R8 | Li et al. (2025), *GSPB: a global-statistic and packet-byte fusion framework for encrypted traffic classification* | Peer-reviewed experimental article | packet length와 packet direction pattern 등 payload-independent 특징을 결합해 암호화 traffic을 분류한다. | directionality와 packet-size pattern을 feature 후보로 사용할 근거를 추가한다. | 일반 encrypted traffic classification이며 native ECH에서 jittered C2 beacon을 탐지하는 실험은 아니다. |

---

## 3. 이미 알려진 사실

다음 항목은 본 연구의 새로운 기여로 주장하지 않는다.

1. **ECH 자체와 SNI 보호**는 RFC 9849에 정의되어 있다.
2. **ECH가 네트워크 보안 관측성을 감소시킬 수 있다는 문제**는 IETF 문서와 최근 review에서 이미 논의되어 있다.
3. **암호화된 beacon을 timing metadata로 탐지할 수 있다는 사실**은 Yilmaz et al. 등의 연구에서 실험되었다.
4. **jitter를 적용한 encrypted C2 traffic** 자체도 TQH-C2 데이터셋에 존재한다.
5. **packet size, direction, arrival time을 이용한 encrypted traffic 분석** 역시 여러 선행연구에서 이미 검증되었다.
6. 따라서 `timing + packet size + direction`을 사용했다는 사실만으로 신규성을 주장하지 않는다.

---

## 4. 확인된 연구 공백

현재 확인한 문헌 범위에서는 다음 조합에 대한 실험적 검증이 충분히 확인되지 않았다.

> **native ECH가 실제 활성화된 환경에서, jitter 증가로 timing periodicity가 약화되는 beacon traffic을 대상으로, timing-only detector와 timing·packet size·directionality·burst를 결합한 경량 다중특징 detector를 동일 조건에서 비교하고, jitter 수준에 따른 탐지 성능 저하 곡선과 처리 비용을 함께 정량 평가하는 연구**

이 공백은 다음 세 문헌을 결합해 도출했다.

- R3은 ECH 하에서도 남는 metadata의 활용 가능성을 정리하지만 해당 behavioural-statistical 조합을 **검증된 detector가 아닌 향후 연구 방향**으로 제시한다.
- R4는 실제 encrypted beacon detection을 실험했지만 **low-jitter timing 중심**이며 native ECH/high-jitter multi-feature robustness가 연구 중심이 아니다.
- R5는 **0/30/70% jitter encrypted C2 데이터**를 제공하지만 native ECH에서 timing-only와 경량 multi-feature detector를 비교하는 연구는 아니다.

따라서 본 연구의 기여는 새로운 암호 프로토콜이나 새로운 metadata feature의 발명이 아니라, **최신 ECH 환경과 adversarial jitter 조건에서 기존에 알려진 residual metadata를 조합한 경량 탐지 전략의 robustness를 재현 가능한 방식으로 검증하는 것**으로 한정한다.

---

## 5. 최종 Research Gap 문장

논문에서는 다음 수준으로 표현한다.

> TLS 1.3과 ECH 이후에도 timing, packet size, directionality와 같은 flow metadata는 수동 관찰자에게 남지만, 최근 문헌은 이러한 특징의 native ECH 환경에서의 C2 탐지 robustness가 충분히 검증되지 않았음을 지적한다. 또한 최근 beacon 연구는 주로 low-jitter timing periodicity에 초점을 두고 있으며, 공개된 encrypted C2 데이터셋에 high-jitter traffic이 존재함에도 native ECH에서 timing-only 방식과 경량 다중특징 방식을 jitter 수준별로 직접 비교한 실험적 근거는 제한적이다. 본 연구는 이 공백을 통제된 실험환경에서 검증한다.

`세계 최초`, `기존 연구가 전혀 없다`와 같은 표현은 사용하지 않는다.

---

## 6. 본 연구의 기여 범위

본 연구가 실제로 주장할 수 있는 기여는 다음 세 가지다.

1. **Native ECH testbed**에서 정상 traffic과 synthetic jittered beacon traffic을 재현 가능한 방식으로 생성한다.
2. **Timing-only baseline**과 timing·packet size·directionality·burst 기반 **경량 Multi-feature detector**를 동일 데이터에서 비교한다.
3. Jitter 0/10/30/50/70% 조건에서 **Precision, Recall, F1, FPR, FNR, detection latency, processing time**을 측정해 보안 탐지 성능과 계산 비용의 trade-off를 제시한다.

---

## 7. 제외하거나 보조자료로만 사용하는 자료

| 자료 | 처리 | 이유 |
|---|---|---|
| GitHub ECH testbed/NGINX lab | 참고 구현 자료로만 사용 | 실험 환경 재현에는 유용하지만 peer-reviewed 연구가 아니므로 research-gap 근거의 핵심 문헌으로 사용하지 않는다. |
| 제품사 블로그 및 일반 기술 블로그 | 핵심 참고문헌에서 제외 | 구현 팁은 얻을 수 있으나 학술적 주장과 신규성 판단의 근거로는 우선순위가 낮다. |
| ECH deployment considerations draft | 배경 문헌으로 유지 | IETF 원문이지만 아직 Internet-Draft이므로 RFC와 동일한 확정 표준으로 표현하지 않는다. |
| TQH-C2 | 데이터셋으로 유지 | peer-reviewed 논문이 아니라 공개 데이터셋이므로 그 지위를 명확히 표기한다. |

---

## 8. 출처 확인 방법

- RFC는 RFC Editor에서 문서 번호·저자·발행월·Standards Track 여부를 확인했다.
- Internet-Draft는 IETF Datatracker에서 최신 revision과 문서 상태를 확인했다.
- 학술 논문은 출판사 페이지에서 제목, 저자, 발표 연도, journal, DOI 및 abstract/방법/결과를 확인했다.
- TQH-C2는 Zenodo 최신 공개 version에서 저자, 버전, DOI, jitter/transport 구성 및 제공 파일을 확인했다.
- 검색 결과의 요약문만으로 세부 주장을 확정하지 않고 가능한 경우 원 출처의 본문 또는 공식 메타데이터를 확인했다.

---

## 9. T10-C11~C20 대응

| 기준 | 대응 |
|---|---|
| C11 참고문헌 목록 | `references/references.md` 및 본 문서 |
| C12 저자·연도 | Related Work Matrix와 참고문헌에 기록 |
| C13 출처 | journal/RFC/IETF/Zenodo와 DOI 또는 공식 URL 기록 |
| C14 가설과 연결 | Matrix의 `본 연구와 연결` 열 |
| C15 제외 문헌 사유 | 7절에 기록 |
| C16 실험·데이터 검증 연구 | R4, R6, R7, R8 및 R5 데이터셋 포함 |
| C17 기존 사실과 새 주장 구분 | 3~6절에서 분리 |
| C18 본문 인용과 참고문헌 일치 | 논문 작성 단계에서 이 목록을 기준으로 교차검증 |
| C19 형식 일관성 | APA 유사 형식으로 통일 |
| C20 확인 방법 | 8절에 기록 |
