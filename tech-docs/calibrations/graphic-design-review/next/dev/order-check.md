# The order's methods, checked on a spread like the review's

- 500 draws a scenario, seed 3397; the judges' pairs from 2 judges' documents, the review's spread and noise from 3 runs' (60 documents).
- **The review's spread** on the covered page rules: {'below competent': 12, 'competent': 80, 'professional': 801, 'excellent': 7}.
- **Between runs,** 37 of 385 pairs of runs grade an image on a rule differently (9.6%); each draw moves a grade at 4.9%.
- **judge-1:** spread {'below competent': 41, 'competent': 51, 'professional': 87, 'excellent': 5}; 142 dominant pairs, by page {'1': 31, '2': 40, '3': 37, '4': 34}.
- **judge-2:** spread {'below competent': 21, 'competent': 34, 'professional': 39, 'excellent': 73}; 131 dominant pairs, by page {'1': 31, '2': 36, '3': 33, '4': 31}.

| Method | review-like: kept | tied | inverted | as the judges: kept | tied | inverted |
|---|---|---|---|---|---|---|
| counting | 59.9% | 30.4% | 9.7% | 97.8% | 1.0% | 1.2% |
| counting-weak | 54.1% | 39.6% | 6.3% | 91.3% | 7.5% | 1.2% |
| lowest | 51.1% | 42.9% | 6.0% | 83.5% | 16.1% | 0.4% |
| average | 60.1% | 30.6% | 9.3% | 97.9% | 1.5% | 0.6% |
| lowest-then-average | 61.8% | 28.1% | 10.0% | 98.0% | 1.1% | 0.9% |

**The method the rule chooses:** `lowest`: the fewest inverted pairs in the review-like scenario, then the most kept, then the first plan's.

