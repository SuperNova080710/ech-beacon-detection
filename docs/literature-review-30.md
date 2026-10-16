# T10 관련 논문 30편 문헌검토

> 조사 기준일: 2026-10-16
>
> 목적: 본격적인 실험 전에 ECH/TLS 1.3, encrypted traffic classification, encrypted malware/C2, beaconing, timing·packet size·direction 기반 분석에 직접 관련된 실존 논문을 최소 30편 검토하고, 추후 논문 본문 인용·Related Work·실험 방법 정당화에 재사용할 수 있도록 기록한다.
>
> 주의: 아래의 `검토 수준`은 실제로 확인 가능한 원문 범위를 구분한다. `본문 검토`는 공개 원문 또는 출판사 본문/방법·결과 절을 확인한 경우이고, `초록+서지 검토`는 출판사/학회가 공개한 초록과 공식 메타데이터를 확인한 경우다. 읽지 않은 부분을 읽었다고 간주하지 않는다.

---

## 0. 이 문헌군으로 확인된 큰 흐름

문헌을 30편까지 확장해서 읽어보면 현재 연구는 대략 다음 순서로 발전해 왔다.

1. HTTPS/TLS 암호화로 payload inspection이 어려워짐.
2. packet size, timing, direction, flow statistics 같은 residual metadata를 이용한 분류가 발전함.
3. TLS handshake, SNI, certificate metadata를 이용한 악성 TLS 탐지가 발전함.
4. TLS 1.3과 ECH가 handshake visibility까지 줄이면서 SNI/TLS-field 의존 방식이 약해짐.
5. 최근에는 timing, size, direction, burst, temporal sequence 같은 protocol-agnostic metadata가 다시 중요해짐.
6. encrypted C2/beacon 탐지는 존재하지만 low-jitter 또는 특정 TLS metadata에 의존하는 경우가 많고, **native ECH + high jitter + lightweight multi-feature detector** 조합은 여전히 실험적 검증 여지가 있다.

따라서 본 프로젝트의 신규성은 `packet size/timing/direction을 사용한다`가 아니라 다음 조합에 둔다.

> **Native ECH 환경에서 jitter 증가에 따라 timing-only 탐지 성능이 어떻게 붕괴하는지 측정하고, timing·packet size·directionality·burst를 결합한 경량 detector가 그 성능 저하를 어느 정도 완화하는지 동일 조건에서 정량 비교한다.**

---

# A. ECH / TLS 1.3 가시성 저하 직접 관련 연구

## P01. Discovering Encrypted Client Hello Deployments by Active ECH Probing

- **저자/연도:** Jonas Mücke, Konstantin Gasser, Thomas C. Schmidt, Matthias Wählisch (2026)
- **출처:** ACM Internet Measurement Conference (IMC 2026), pp. 276–286
- **링크:** https://netd.cs.tu-dresden.de/pub/mgsw-dechd-26.html
- **검토 수준:** 공식 publication page의 abstract·실험 개요·서지정보 검토
- **핵심:** DNS에서 ECHConfig가 노출되는 서버만 찾는 기존 측정의 한계를 보완하기 위해 표준 동작을 이용한 active ECH probing 방법을 제안했다. 기존 측정에서 놓친 Meta 등의 실제 ECH deployment를 발견하고 ECH의 latency/privacy 영향을 측정한다.
- **우리 연구에서의 의미:** 실제 ECH가 더 이상 순수한 실험 기능이 아니라 deployment가 진행 중인 기술임을 뒷받침한다. Native ECH testbed를 연구 대상으로 선택한 배경에 인용할 수 있다.
- **중복 여부:** 탐지 연구가 아니라 Internet measurement 연구이므로 본 연구와 직접 중복되지 않는다.

## P02. Encrypted Client Hello Is Coming: A View from Passive Measurements

- **저자/연도:** Gabriele Merlach, Martino Trevisan, Danilo Giordano (2025)
- **출처:** *Network*, 5(3), 29
- **DOI:** 10.3390/network5030029
- **링크:** https://doi.org/10.3390/network5030029
- **검토 수준:** 공개 본문 검토
- **핵심:** 운영 네트워크의 한 달 데이터로 ECH와 HTTPS DNS 사용을 수동 측정했다. QUIC flow의 상당수가 ECH extension을 포함하지만 대부분 GREASE이고 실제 server-side ECH 지원은 제한적이라고 보고했다.
- **우리 연구에서의 의미:** 실제 네트워크에서 ECH/GREASE가 관측되고 있다는 근거다. ECH detection과 실제 ECH acceptance를 구분해야 한다는 실험 주의점도 제공한다.
- **중복 여부:** ECH adoption 측정이며 C2/beacon detection은 수행하지 않는다.

## P03. Measuring the Adoption of TLS Encrypted Client Hello Extension and Its Forebear in the Wild

- **저자/연도:** Zisis Tsiatsikas, Georgios Karopoulos, Georgios Kambourakis (2023)
- **출처:** ESORICS 2022 Workshops, LNCS 13785, pp. 177–190
- **DOI:** 10.1007/978-3-031-25460-4_10
- **링크:** https://doi.org/10.1007/978-3-031-25460-4_10
- **검토 수준:** 공개 본문 검토
- **핵심:** Tranco Top 1M을 대상으로 ESNI/ECH 및 encrypted DNS adoption을 능동 측정했다. 당시 ECH deployment가 거의 없었다는 초기 상태를 보여준다.
- **우리 연구에서의 의미:** P01/P02와 함께 ECH deployment가 시간에 따라 빠르게 변화해 왔다는 배경을 구성할 수 있다.
- **중복 여부:** deployment/adoption 연구다.

## P04. Indistinguishability of Traffic by Open TLS Parameters with Encrypted ClientHello

- **저자/연도:** Danil R. Shamsimukhametov, Anton A. Kurapov, Mikhail V. Liubogoshchev, Evgeny M. Khorov (2023)
- **출처:** *Journal of Communications Technology and Electronics*, 68(12), 1523–1529
- **DOI:** 10.1134/S1064226923120173
- **링크:** https://doi.org/10.1134/S1064226923120173
- **검토 수준:** 공식/학술 메타데이터와 공개 abstract 검토
- **핵심:** ECH가 SNI 등 기존 TLS classification에 사용되던 정보를 숨길 때 남아 있는 open TLS parameters만으로 traffic을 얼마나 구분할 수 있는지 분석했다. ECH가 TLS metadata 기반 분류의 구별력을 크게 감소시킴을 문제로 제시한다.
- **우리 연구에서의 의미:** `ECH 이후 handshake metadata만으로는 부족하다 → flow-level residual metadata가 중요하다`는 논리의 직접 근거다.
- **중복 여부:** classification distinguishability 연구이며 beacon/C2 탐지는 아니다.

## P05. Early Traffic Classification With Encrypted ClientHello: A Multi-Country Study

- **저자/연도:** Danil Shamsimukhametov, Anton Kurapov, Mikhail Liubogoshchev, Evgeny Khorov (2024)
- **출처:** *IEEE Access*, 12, 142979–142993
- **DOI:** 10.1109/ACCESS.2024.3469730
- **링크:** https://doi.org/10.1109/ACCESS.2024.3469730
- **검토 수준:** 공개 원문/방법·결과 검토
- **핵심:** ECH 환경을 모사해 visible TLS feature만 사용하는 방식의 성능 저하를 측정하고, 남아 있는 TLS metadata와 초기 flow statistics를 합친 hybrid Random Forest classifier를 제안했다. 다양한 국가에서 수집한 데이터에서 최대 94.6% F-score를 보고한다.
- **우리 연구에서의 의미:** 가장 가까운 선행연구 중 하나다. 특히 `ECH + flow statistics` 조합이 효과적일 수 있다는 강한 근거다.
- **중복 여부:** 일반 서비스 분류이며 native ECH C2/high-jitter beacon 탐지가 아니다. 본 연구는 이 차이를 명확히 써야 한다.

## P06. Challenges and Advances in Analyzing TLS 1.3-Encrypted Traffic: A Comprehensive Survey

- **저자/연도:** Jiuxing Zhou, Wei Fu, Wei Hu, Zhihong Sun, Tao He, Zhihong Zhang (2024)
- **출처:** *Electronics*, 13(20), 4000
- **DOI:** 10.3390/electronics13204000
- **링크:** https://doi.org/10.3390/electronics13204000
- **검토 수준:** 공개 본문 검토
- **핵심:** TLS 1.3 traffic analysis 관련 약 37편의 핵심 연구를 심층 비교하고, TLS 1.3 이후 기존 handshake/payload 기반 분석의 한계와 residual statistical feature 기반 연구 방향을 정리한다.
- **우리 연구에서의 의미:** 서론에서 `TLS 1.3 이후 passive traffic analysis가 왜 어려워졌는가`를 설명하는 survey 근거로 적합하다.

## P07. A Survey on TLS-Encrypted Malware Network Traffic Analysis Applicable to Security Operations Centers

- **저자/연도:** Chaeyeon Oh, Joonseo Ha, Heejun Roh (2022)
- **출처:** *Applied Sciences*, 12(1), 155
- **DOI:** 10.3390/app12010155
- **링크:** https://doi.org/10.3390/app12010155
- **검토 수준:** 공개 본문 검토
- **핵심:** TLS malware traffic 분석을 TLS interception, cryptographic inspection, passive inspection으로 나누고 SOC에서 실제 사용 가능한 ML pipeline을 정리한다.
- **우리 연구에서의 의미:** payload decrypt 없이 passive inspection을 택하는 연구 설계의 배경과 operational relevance에 인용할 수 있다.

## P08. Encrypted-Traffic Detection in the TLS 1.3 Era: A Comprehensive Review and Future Research Directions

- **저자/연도:** Hazem Abu-Adaiq, Md Israfil Biswas, Ahmad Y. Alnajjar, Sijing Zhang (2026)
- **출처:** *Electronics*, 15(17), 3846
- **DOI:** 10.3390/electronics15173846
- **링크:** https://doi.org/10.3390/electronics15173846
- **검토 수준:** 공개 본문 검토
- **핵심:** TLS 1.3/ECH 이후 남는 timing, packet size, directional asymmetry, burst behavior 등의 residual evidence를 체계적으로 검토한다. 특히 behavioural–statistical fusion이 유망하지만 **통합 framework로 실증 검증이 부족하다**고 지적한다.
- **우리 연구에서의 의미:** 현재 연구 공백을 가장 직접적으로 뒷받침하는 1순위 인용 문헌이다. 본 연구의 timing+size+direction+burst 경량 조합을 정당화할 수 있다.
- **중복 여부:** review에서 방향을 제안할 뿐 실제 native ECH detector를 구현·평가하지 않는다.

## P09. A Survey on Encrypted Network Traffic: A Comprehensive Survey of Identification/Classification Techniques, Challenges, and Future Directions

- **저자/연도:** Adit Sharma, Arash Habibi Lashkari (2025)
- **출처:** *Computer Networks*, 257, 110984
- **DOI:** 10.1016/j.comnet.2024.110984
- **링크:** https://doi.org/10.1016/j.comnet.2024.110984
- **검토 수준:** 출판사 본문/초록·future work 검토
- **핵심:** 82개 기술 논문과 기존 survey를 바탕으로 encrypted traffic detection/classification의 기술, 데이터셋, 분석도구, scalability·adaptability 문제를 종합한다.
- **우리 연구에서의 의미:** lightweight/real-time/새 encryption에 적응하는 모델 필요성을 뒷받침한다.

## P10. A Comprehensive Survey on Encrypted Network Traffic Classification

- **저자/연도:** Shangbin Han, Han Zhang, Mengmeng Lu, Sifang Guo, Boyuan Tian, Jilong Wang (2026)
- **출처:** *Computer Networks*, 287, 112524
- **DOI:** 10.1016/j.comnet.2026.112524
- **링크:** https://doi.org/10.1016/j.comnet.2026.112524
- **검토 수준:** 출판사 공개 본문/초록 검토
- **핵심:** 최신 ETC를 data collection, feature representation, classification method 및 security application 관점으로 정리한다. ECH/QUIC로 plaintext feature 공간이 줄어드는 문제를 명시한다.
- **우리 연구에서의 의미:** 2026년 현재 encrypted traffic classification 연구의 최신 위치를 설명하기 위한 survey reference다.

---

# B. Encrypted malware / C2 / beacon 직접 관련 연구

## P11. Beaconing Detection via Timing-Based Flow Metadata Analysis: Implications for SCADA/ICS

- **저자/연도:** Mustafa Tahsin Yilmaz et al. (2026)
- **출처:** *International Journal of Information Security*, 25, Article 161
- **DOI/링크:** https://link.springer.com/article/10.1007/s10207-026-01335-w
- **검토 수준:** 공개 본문 검토
- **핵심:** Zeek `conn.log`의 connection timing metadata만 이용해 CV 기반 periodicity + Isolation Forest로 encrypted beacon을 탐지한다. 실험은 주로 low-jitter beacon에 초점을 둔다.
- **우리 연구에서의 의미:** **Timing-only baseline의 가장 직접적인 선행연구**다. CV와 timing periodicity를 baseline으로 택할 근거가 된다.
- **중복 여부:** 본 연구와 가장 가까움. 차이는 native ECH, high jitter, multi-feature lightweight detector, jitter별 degradation curve다.

## P12. Offloading Encrypted C2 Traffic Mitigation to SmartNICs

- **저자/연도:** Ali Mazloum, Elie Kfoury, Samia Choueiri, Ali AlSabeh, Jose Crichigno (2025)
- **출처:** IEEE BlackSeaCom 2025
- **DOI:** 10.1109/BlackSeaCom65655.2025.11193948
- **링크:** https://doi.org/10.1109/BlackSeaCom65655.2025.11193948
- **검토 수준:** IEEE abstract·공식 저자 publication page 검토
- **핵심:** encrypted C2 ML classifier를 SmartNIC/DPDK에 offload해 50 Gbps 수준에서 동작시키며 높은 accuracy를 보고한다.
- **우리 연구에서의 의미:** `탐지 정확도뿐 아니라 processing overhead/latency를 측정해야 한다`는 근거로 쓸 수 있다.
- **중복 여부:** hardware offload 연구이며 ECH/high-jitter feature robustness 연구는 아니다.

## P13. PETNet: Plaintext-Aware Encrypted Traffic Detection Network for Identifying Cobalt Strike HTTPS Traffics

- **저자/연도:** Xiaodu Yang, Sijie Ruan, Yinliang Yue, Bo Sun (2023)
- **출처:** *Computer Networks*, Article 110120
- **DOI:** 10.1016/j.comnet.2023.110120
- **링크:** https://doi.org/10.1016/j.comnet.2023.110120
- **검토 수준:** 출판사 본문/방법·실험·한계 검토
- **핵심:** Cobalt Strike HTTPS 탐지를 위해 TLS handshake meta-information과 client-server sequential interaction을 wide/deep architecture로 결합한다. open-world evaluation도 수행한다.
- **우리 연구에서의 의미:** C2 탐지에서 handshake metadata와 sequence behavior를 결합한 대표 사례다. 동시에 ECH가 handshake feature를 숨기면 이런 방식의 일부 feature가 약해진다는 비교 근거가 된다.

## P14. Deciphering Malware’s Use of TLS (Without Decryption)

- **저자/연도:** Blake Anderson, Subharthi Paul, David McGrew (2018)
- **출처:** *Journal of Computer Virology and Hacking Techniques*, 14, 195–211
- **DOI:** 10.1007/s11416-017-0306-6
- **링크:** https://doi.org/10.1007/s11416-017-0306-6
- **검토 수준:** 공개 preprint/논문 abstract·결과 검토
- **핵심:** 수백만 TLS flow와 18 malware family를 분석하여 payload 복호화 없이 TLS observable feature로 malware detection/family attribution이 가능함을 보였다.
- **우리 연구에서의 의미:** `encrypted traffic도 metadata로 탐지 가능하다`는 고전적 핵심 근거다.

## P15. Identifying Encrypted Malware Traffic with Contextual Flow Data

- **저자/연도:** Blake Anderson, David A. McGrew (2016)
- **출처:** ACM AISec 2016, pp. 35–46
- **DOI:** 10.1145/2996758.2996768
- **링크:** https://doi.org/10.1145/2996758.2996768
- **검토 수준:** 공식 서지·공개 abstract 검토
- **핵심:** packet length/IAT 같은 flow metadata뿐 아니라 TLS handshake, DNS contextual flow, 주변 HTTP context까지 결합하면 encrypted malicious flow 탐지가 개선됨을 보였다.
- **우리 연구에서의 의미:** 단일 timing feature보다 여러 독립 정보원을 결합하는 것이 유리하다는 근거다.

## P16. Machine Learning for Encrypted Malware Traffic Classification: Accounting for Noisy Labels and Non-Stationarity

- **저자/연도:** Blake Anderson, David A. McGrew (2017)
- **출처:** KDD 2017, pp. 1723–1732
- **DOI:** 10.1145/3097983.3098163
- **링크:** https://doi.org/10.1145/3097983.3098163
- **검토 수준:** 공식 서지·공개 abstract 검토
- **핵심:** malware traffic ML에서 label noise와 non-stationary distribution 때문에 실험실 accuracy가 실제 deployment 성능으로 이어지지 않을 수 있음을 실험적으로 분석한다.
- **우리 연구에서의 의미:** train/test separation, random seed 보존, 과적합 방지, 결과 일반화 한계를 논의할 때 핵심 인용 문헌이다.

## P17. Malware Traffic Classification Using Convolutional Neural Network for Representation Learning

- **저자/연도:** Wei Wang, Ming Zhu, Xuewen Zeng, Xiaozhou Ye, Yiqiang Sheng (2017)
- **출처:** ICOIN 2017, pp. 712–717
- **DOI:** 10.1109/ICOIN.2017.7899588
- **링크:** https://doi.org/10.1109/ICOIN.2017.7899588
- **검토 수준:** 공식 서지·초록 검토
- **핵심:** malware traffic raw representation에 CNN을 적용하여 수동 feature engineering 대신 representation learning을 사용한다.
- **우리 연구에서의 의미:** 복잡한 DL 계열 baseline이 존재하지만 본 연구는 해석 가능한 경량 detector를 목표로 한다는 대비에 사용할 수 있다.

---

# C. Timing / Packet Size / Direction 기반 encrypted traffic 분석

## P18. Characterization of Encrypted and VPN Traffic Using Time-Related Features

- **저자/연도:** Gerard Draper-Gil, Arash Habibi Lashkari, Mohammad Saiful Islam Mamun, Ali A. Ghorbani (2016)
- **출처:** ICISSP 2016, pp. 407–414
- **DOI:** 10.5220/0005740704070414
- **링크:** https://doi.org/10.5220/0005740704070414
- **검토 수준:** 공개 원문/초록 검토
- **핵심:** flow duration, inter-arrival 등 time-related feature만으로 VPN/encrypted traffic category를 C4.5/KNN으로 분류할 수 있음을 보였다.
- **우리 연구에서의 의미:** timing feature가 암호화 이후에도 정보량을 유지한다는 고전적 근거다.

## P19. Practical Evaluation of Encrypted Traffic Classification Based on a Combined Method of Entropy Estimation and Neural Networks

- **저자/연도:** Kun Zhou, Wenyong Wang, Chenhuang Wu, Teng Hu (2020)
- **출처:** *ETRI Journal*, 42(3), 311–323
- **DOI:** 10.4218/etrij.2019-0190
- **링크:** https://doi.org/10.4218/etrij.2019-0190
- **검토 수준:** 공개 본문/초록 검토
- **핵심:** packet size, inter-arrival time, direction을 NN 입력으로 사용해 encrypted traffic을 분류한다.
- **우리 연구에서의 의미:** 본 프로젝트의 핵심 feature 세 가지(size, timing, direction)를 함께 사용하는 직접 선행근거다. 따라서 이 세 feature 자체는 신규 기여로 주장하면 안 된다.

## P20. Fast and Lean Encrypted Internet Traffic Classification

- **저자/연도:** Sangita Roy, Tal Shapira, Yuval Shavitt (2022)
- **출처:** *Computer Communications*, 186, 166–173
- **DOI:** 10.1016/j.comcom.2022.02.003
- **링크:** https://doi.org/10.1016/j.comcom.2022.02.003
- **검토 수준:** 출판사 본문/초록 검토
- **핵심:** packet size와 inter-arrival time 두 feature만 사용해 Neural ODE 기반 빠른 encrypted traffic classification을 수행한다.
- **우리 연구에서의 의미:** 작은 feature set으로도 충분한 성능이 가능하다는 `lightweight` 방향의 근거다.

## P21. Encrypted Internet Traffic Classification Using a Supervised Spiking Neural Network

- **저자/연도:** Ali Rasteh, Florian Delpech, Carlos Aguilar-Melchor, Romain Zimmer, Saeed Bagheri Shouraki, Timothée Masquelier (2022)
- **출처:** *Neurocomputing*, 503, 272–282
- **DOI:** 10.1016/j.neucom.2022.06.055
- **링크:** https://doi.org/10.1016/j.neucom.2022.06.055
- **검토 수준:** 출판사 초록·공개 preprint 검토
- **핵심:** packet size와 arrival time만 사용하고 SNN으로 temporal traffic pattern을 분류한다.
- **우리 연구에서의 의미:** time/size 조합의 유효성과 저전력/효율적 구현 가능성을 뒷받침한다.

## P22. Enhancing Fine-Grained Encrypted Traffic Classification via Temporal Bi-Directional GraphSAGE

- **저자/연도:** Junbin Yang, Haihua Shen, Zulong Diao, Yiran He (2026)
- **출처:** *Applied Sciences*, 16(7), 3427
- **DOI:** 10.3390/app16073427
- **링크:** https://doi.org/10.3390/app16073427
- **검토 수준:** 공개 본문 검토
- **핵심:** packet size, direction, arrival time 세 가지 protocol-agnostic metadata를 temporal graph로 모델링하고 directed IAT를 edge feature로 사용한다. VNAT에서 98.57% accuracy를 보고한다.
- **우리 연구에서의 의미:** `timing + size + direction`을 명시적으로 결합하는 최신 연구다. 본 연구의 차별점은 C2 beacon/high jitter/native ECH와 경량 통계 detector다.

## P23. GSPB: A Global-Statistic and Packet-Byte Fusion Framework for Encrypted Traffic Classification

- **저자/연도:** Haiyue Li, Jun Tao, Linxiao Yu, Yuantu Luo, Zuyan Wang (2025)
- **출처:** *Cybersecurity*, 8, Article 120
- **DOI:** 10.1186/s42400-025-00446-6
- **링크:** https://doi.org/10.1186/s42400-025-00446-6
- **검토 수준:** 공개 본문 검토
- **핵심:** packet length sequence와 direction pattern, global statistics를 결합해 payload-independent encrypted traffic classification을 수행한다.
- **우리 연구에서의 의미:** directionality + packet-size distribution을 다중특징 detector에 넣는 근거다.

## P24. MATEC: A Lightweight Neural Network for Online Encrypted Traffic Classification

- **저자/연도:** Jin Cheng, Yulei Wu, Yuepeng E, Junling You, Tong Li, Hui Li, Jingguo Ge (2021)
- **출처:** *Computer Networks*, 199, 108472
- **DOI:** 10.1016/j.comnet.2021.108472
- **링크:** https://doi.org/10.1016/j.comnet.2021.108472
- **검토 수준:** 출판사 초록·방법 개요 검토
- **핵심:** 높은 정확도를 유지하면서 online encrypted traffic classification에 필요한 계산량을 줄이기 위한 lightweight architecture를 제안한다.
- **우리 연구에서의 의미:** accuracy뿐 아니라 inference/processing cost를 실험 지표로 포함하는 이유를 정당화한다.

## P25. FS-Net: A Flow Sequence Network for Encrypted Traffic Classification

- **저자/연도:** Chang Liu, Longtao He, Gang Xiong, Zigang Cao, Zhen Li (2019)
- **출처:** IEEE INFOCOM 2019, pp. 1171–1179
- **DOI:** 10.1109/INFOCOM.2019.8737507
- **링크:** https://doi.org/10.1109/INFOCOM.2019.8737507
- **검토 수준:** 공식 서지·공개 구현 설명/abstract 검토
- **핵심:** handcrafted feature 대신 flow sequence 자체를 encoder-decoder/RNN 계열로 학습한다.
- **우리 연구에서의 의미:** sequence-based detector가 강력하지만 계산·해석 비용이 높다는 비교군을 설명할 때 사용 가능하다.

## P26. FlowPic: Encrypted Internet Traffic Classification Is as Easy as Image Recognition

- **저자/연도:** Tal Shapira, Yuval Shavitt (2019)
- **출처:** IEEE INFOCOM Workshops 2019, pp. 680–687
- **DOI:** 10.1109/INFCOMW.2019.8845315
- **링크:** https://doi.org/10.1109/INFCOMW.2019.8845315
- **검토 수준:** 저자 공개 설명·원문/abstract 검토
- **핵심:** packet size와 inter-arrival time을 2차원 FlowPic으로 변환하고 CNN으로 encrypted/VPN/Tor traffic을 분류한다.
- **우리 연구에서의 의미:** size×time joint distribution이 풍부한 fingerprint를 제공한다는 근거다.

## P27. ET-BERT: A Contextualized Datagram Representation with Pre-Training Transformers for Encrypted Traffic Classification

- **저자/연도:** Xinjie Lin, Gang Xiong, Gaopeng Gou, Zhen Li, Junzheng Shi, Jing Yu (2022)
- **출처:** The Web Conference 2022, pp. 633–642
- **링크:** https://arxiv.org/abs/2202.06335
- **검토 수준:** 공개 preprint·공식 구현/서지 검토
- **핵심:** 대규모 unlabeled traffic으로 transformer를 pretrain하고 다양한 ETC task에 fine-tune해 높은 F1을 달성한다.
- **우리 연구에서의 의미:** 최신 DL 계열의 높은 성능과 비교해 본 연구가 `small data + interpretable + lightweight`를 지향한다는 위치를 잡을 수 있다.

## P28. Encrypted Traffic Classification: The QUIC Case

- **저자/연도:** Jan Luxemburk, Karel Hynek, Tomáš Čejka (2023)
- **출처:** TMA 2023, pp. 1–10
- **DOI:** 10.23919/TMA58422.2023.10199052
- **링크:** https://doi.org/10.23919/TMA58422.2023.10199052
- **검토 수준:** 공개 PDF/본문 검토
- **핵심:** payload 없이 packet size, direction, inter-packet time sequence 및 flow statistics를 사용해 대규모 실제 QUIC traffic의 fine-grained service classification을 수행한다. data drift도 분석한다.
- **우리 연구에서의 의미:** QUIC/ECH처럼 visibility가 제한된 최신 protocol에서도 side-channel metadata가 실용적으로 사용 가능함을 보여준다.

## P29. FlowPrint: Semi-Supervised Mobile-App Fingerprinting on Encrypted Network Traffic

- **저자/연도:** Thijs van Ede, Riccardo Bortolameotti, Andrea Continella, Jingjing Ren, Daniel J. Dubois, Martina Lindorfer, David Choffnes, Maarten van Steen, Andreas Peter (2020)
- **출처:** NDSS 2020
- **링크:** https://www.ndss-symposium.org/ndss-paper/flowprint-semi-supervised-mobile-app-fingerprinting-on-encrypted-network-traffic/
- **검토 수준:** 공개 원문 검토
- **핵심:** destination-related feature와 temporal correlation로 encrypted mobile app fingerprint를 semi-supervised하게 구성한다. unseen app 탐지도 다룬다.
- **우리 연구에서의 의미:** 단일 flow feature가 아니라 여러 connection 간 temporal behavior가 유의미할 수 있음을 보여준다. burst/connection grouping 설계에 참고할 수 있다.

## P30. Fine-Grained Webpage Fingerprinting Using Only Packet Length Information of Encrypted Traffic

- **저자/연도:** Meng Shen, Yiting Liu, Liehuang Zhu, Xiaojiang Du, Jiankun Hu (2021)
- **출처:** *IEEE Transactions on Information Forensics and Security*, 16, 2046–2059
- **DOI:** 10.1109/TIFS.2020.3046876
- **링크:** https://doi.org/10.1109/TIFS.2020.3046876
- **검토 수준:** 공개 본문/출판사 서지 검토
- **핵심:** 같은 사이트 내부의 webpage까지 packet length sequence만으로 구별할 수 있음을 실험한다.
- **우리 연구에서의 의미:** packet length가 암호화 이후에도 상당한 정보량을 누설한다는 강력한 근거다. 다만 privacy fingerprinting 연구이므로 malicious detection과 직접 동일시해서는 안 된다.

---

# 1. 논문별 인용 용도 빠른 색인

| 목적 | 우선 인용 논문 |
|---|---|
| ECH가 SNI/ClientHello 가시성을 줄인다는 배경 | P02, P03, P04, P05 |
| 실제 ECH deployment가 진행 중임 | P01, P02 |
| TLS 1.3/ECH 이후 residual metadata 연구 필요 | P06, P08, P09, P10 |
| encrypted malware/C2를 복호화 없이 탐지 가능 | P13, P14, P15 |
| beacon timing baseline | **P11** |
| label noise / concept drift / 일반화 한계 | P16, P28 |
| timing feature 근거 | P18, P19, P20, P21, P26 |
| packet size feature 근거 | P19, P20, P22, P23, P26, P30 |
| directionality 근거 | P19, P22, P23, P28 |
| temporal/connection grouping 근거 | P25, P28, P29 |
| lightweight/processing cost 중요성 | P12, P20, P24 |
| 복잡한 DL과의 차별화 | P17, P22, P25, P27 |
| native ECH 연구 공백 설명 | **P05, P08, P11** 조합 |

---

# 2. 본 연구와 가장 직접적으로 비교해야 할 핵심 8편

모든 30편을 논문 본문에 같은 비중으로 넣을 필요는 없다. 실제 Related Work에서 가장 직접적으로 비교할 핵심은 다음 8편이다.

1. **P08 Abu-Adaiq et al. (2026)** — residual metadata와 behavioural–statistical fusion 연구 공백
2. **P11 Yilmaz et al. (2026)** — timing/CV 기반 beacon detector baseline
3. **P05 Shamsimukhametov et al. (2024)** — ECH 상황에서 flow statistics를 결합한 분류
4. **P04 Shamsimukhametov et al. (2023)** — ECH가 TLS metadata 구별력을 낮춤
5. **P13 Yang et al. (2023)** — encrypted Cobalt Strike detection
6. **P19 Zhou et al. (2020)** — size+IAT+direction 조합
7. **P22 Yang et al. (2026)** — 최신 temporal size/direction/IAT 조합
8. **P28 Luxemburk et al. (2023)** — 최신 encrypted protocol에서 side-channel metadata 및 drift 평가

---

# 3. 이 30편을 읽은 뒤 수정된 Research Gap

30편까지 범위를 넓혀도 다음 표현은 유지할 수 있다.

> 기존 연구는 ECH가 TLS handshake의 식별 정보를 감소시킨다는 점, packet timing·size·direction과 같은 residual metadata가 암호화된 traffic에서도 분류력을 가진다는 점, 그리고 encrypted beacon/C2를 timing 또는 TLS metadata를 이용해 탐지할 수 있다는 점을 각각 보여주었다. 그러나 확인한 문헌 범위에서는 **native ECH 환경에서 high-jitter beacon을 대상으로 timing-only detector와 timing·packet size·directionality·burst를 결합한 경량 detector를 동일한 실험 조건에서 비교하고, jitter 수준별 탐지 성능 저하와 처리 비용을 함께 평가한 연구는 확인하지 못했다.**

다만 다음 표현은 사용하지 않는다.

- `세계 최초`라고 단정
- `기존 연구가 전혀 없다`고 단정
- `packet size/timing/direction을 새롭게 제안했다`고 주장
- synthetic beacon 결과를 실제 malware 전체에 일반화
- ECH-compatible feature를 곧바로 ECH-validated feature라고 표현

---

# 4. 실험 설계에 반영할 문헌 기반 결정

1. **Timing-only baseline은 CV 기반으로 둔다.** — P11, P18
2. **Multi-feature에는 timing + size + direction을 반드시 포함한다.** — P19, P22, P23, P28
3. **Burst/connection-level behavior를 별도 feature군으로 둔다.** — P08, P29
4. **Feature 수를 과도하게 늘리지 않는다.** — P20, P24
5. **F1만 보지 않고 FPR/FNR과 processing time을 함께 측정한다.** — P12, P16, P24
6. **train/calibration과 final test를 분리하고 random seed를 기록한다.** — P16, P28
7. **ECH는 GREASE가 아니라 실제 server acceptance까지 확인한다.** — P01, P02
8. **synthetic beacon이라는 한계를 명확히 밝힌다.** — P11의 controlled lab 접근과 동일하게 proof-of-concept 범위로 한정

---

# 5. 참고문헌 작성 시 사용 규칙

- 본문에서 실제로 인용한 논문만 최종 `References`에 남긴다.
- DOI가 있는 경우 DOI 링크를 우선한다.
- conference paper와 journal article을 구분한다.
- survey에서 재인용하지 말고 가능하면 원 논문을 직접 인용한다.
- 수치나 성능 결과를 인용할 때는 반드시 해당 원 논문의 실험 조건도 함께 확인한다.
- `ECH에서 동작한다`와 `ECH에서도 관측 가능한 feature를 사용한다`를 구분한다.
- 최종 논문 작성 전 이 문서의 30편 중 실제 인용 대상으로 선택된 논문은 다시 한 번 원문 문맥을 확인한다.

---

# 6. 검토 완료 체크

- [x] 실존 여부 확인: 30/30
- [x] 저자·연도 확인: 30/30
- [x] 학술지/학회 또는 DOI/공식 페이지 확인: 30/30
- [x] 연구 목적/방법/결과 또는 공식 abstract 확인: 30/30
- [x] 본 연구와의 관련성 기록: 30/30
- [x] 직접 중복 여부 검토: 30/30
- [x] 링크 기록: 30/30
- [x] Research Gap 재검토

## 결론

이 문헌 검토를 기준으로 현재 T10 주제는 유지한다. 다만 기여 범위는 **새로운 encrypted-traffic feature의 발명**이 아니라, **native ECH + high-jitter beacon이라는 제한된 조건에서 기존 residual metadata를 이용한 경량 다중특징 탐지 전략의 robustness와 비용을 실험적으로 검증하는 것**으로 고정한다.
