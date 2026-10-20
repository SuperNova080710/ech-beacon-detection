# Results and Discussion Draft

## 1. Held-out Detection Performance

We evaluated two frozen detectors on the held-out `main-v1` test partition consisting of 110 trials: 50 Beacon and 60 Normal. The Timing-only detector achieved TP=50, FP=10, TN=50, and FN=0, while the Multi-feature detector achieved TP=50, FP=7, TN=53, and FN=0. Accordingly, the Timing-only detector recorded Precision 0.8333, Recall 1.0000, F1 0.9091, FPR 0.1667, and FNR 0.0000. The Multi-feature detector recorded Precision 0.8772, Recall 1.0000, F1 0.9346, FPR 0.1167, and FNR 0.0000.

These results show that both detectors successfully identified all Beacon samples in the held-out test set. The Multi-feature detector did not improve Recall over the Timing-only baseline, but it reduced False Positives by three samples, which improved Precision and F1 while lowering FPR.

## 2. Performance under Increasing Jitter

To examine the effect of Beacon jitter, we evaluated each detector across five Beacon jitter levels: 0%, 10%, 30%, 50%, and 70%. Each jitter level contained 10 held-out Beacon trials. For all five jitter levels, both detectors achieved TP=10 and FN=0, corresponding to Recall 1.0000 and FNR 0.0000 in every condition.

This finding does not support the original hypothesis that the Multi-feature detector would maintain Beacon Recall better than the Timing-only detector under increasing jitter. In this experiment, both detectors maintained perfect Recall across all tested jitter conditions.

The conditional F1 values by jitter should be interpreted carefully because each jitter-specific calculation reused the same 60 held-out Normal trials rather than using five independent test sets.

## 3. False Positives by Normal Traffic Profile

We further analyzed False Positives across three Normal traffic profiles: interactive-burst (N=24), irregular-lognormal (N=18), and mixed-activity (N=18). Neither detector produced False Positives on the interactive-burst or mixed-activity profiles. All False Positives were concentrated in the irregular-lognormal profile. Within that profile, the Timing-only detector produced 10 False Positives, while the Multi-feature detector produced 7.

A paired comparison on the same held-out Normal samples showed that 7 samples were misclassified by both detectors, 3 were misclassified only by the Timing-only detector, and 0 were misclassified only by the Multi-feature detector. Therefore, the observed overall improvement of the Multi-feature detector arose entirely from reduced errors on a subset of irregular-lognormal Normal traffic.

## 4. Inference Cost

We measured pure inference cost on the same 110 held-out feature rows using frozen detector parameters. The Timing-only detector recorded a median batch latency of 0.080385 ms and a P95 latency of 0.086857 ms per 110-trial batch, corresponding to a median per-trial latency of 0.730777 us. The Multi-feature detector recorded a median batch latency of 1.408802 ms and a P95 latency of 1.447461 ms, corresponding to a median per-trial latency of 12.807295 us.

Thus, the Multi-feature detector required approximately 17.53 times more inference time than the Timing-only baseline in this Python microbenchmark.

## 5. Training and Calibration Cost

We also measured detector preparation cost. The Timing-only detector calibrates a threshold from 40 Normal calibration samples and recorded a median preparation time of 0.027777 ms (P95 0.032999 ms). The Multi-feature detector trains a logistic regression model on 90 calibration samples and then calibrates a threshold, recording a median preparation time of 199.032131 ms (P95 216.105765 ms).

The observed median preparation-time ratio was approximately 7165.36x. However, this comparison reflects different workloads rather than a like-for-like implementation efficiency comparison. The Timing-only detector only sorts 40 scalar scores, whereas the Multi-feature detector performs 800 epochs of full-batch gradient descent and subsequent threshold calibration.

## 6. Discussion

The main outcome of this study is that the Multi-feature detector did not provide a Recall advantage over the Timing-only baseline under increasing Beacon jitter in the tested Native ECH environment. Both detectors achieved Recall 100% across all held-out Beacon samples, including all jitter levels up to 70%.

However, the Multi-feature detector did reduce False Positives on the held-out Normal set, specifically within the irregular-lognormal profile. This reduction improved Precision and F1 while lowering FPR. Therefore, the practical advantage of the Multi-feature detector in this experiment was improved specificity rather than improved Beacon sensitivity.

This gain came with a substantial processing-cost increase. The Multi-feature detector was roughly 17.53x slower in pure inference and over 7000x slower in model preparation/calibration under the measured Python implementation. Consequently, the results reveal a clear trade-off: modestly improved false-positive behavior at substantially higher computational cost.

## 7. Limitations

This study has several limitations. First, the dataset used synthetic HTTPS Beacon traffic rather than real malware traffic. Second, the Native ECH environment was limited to a single controlled experimental setup. Third, the Beacon interval was fixed at 1.0 s, and only three Normal traffic profiles were included. Fourth, the jitter-level held-out Beacon sample count was limited to 10 per level. Fifth, no statistical significance claim is made for the observed detector differences. Finally, the latency measurements were Python microbenchmarks that excluded feature extraction, packet capture, and file I/O.

## 8. Conclusion

In the evaluated Native ECH setting, the Multi-feature detector did not outperform the Timing-only baseline in Beacon Recall under increasing jitter. Nevertheless, it reduced held-out False Positives and improved overall Precision and F1. This benefit came at a substantially higher computational cost. Therefore, the experimental evidence supports a trade-off interpretation rather than a simple dominance claim: the Multi-feature detector offers improved false-positive behavior, but not improved Recall, and does so with notably higher processing overhead.
