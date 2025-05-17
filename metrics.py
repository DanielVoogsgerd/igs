from dataclasses import dataclass


@dataclass
class Metrics:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    def __str__(self):
        total = self.tp + self.tn + self.fp + self.fn
        accuracy = (self.tp + self.tn) / total if total > 0 else 0

        precision_denom = self.tp + self.fp
        precision = self.tp / precision_denom if precision_denom > 0 else 0

        recall_denom = self.tp + self.fn
        recall = self.tp / recall_denom if recall_denom > 0 else 0

        f1_denom = precision + recall
        f1_score = 2 * (precision * recall) / f1_denom if f1_denom > 0 else 0

        return (
            f"Metrics:\n"
            f"          TP: {self.tp:5d} FP: {self.fp:5d}\n"
            f"          FN: {self.fn:5d} TN: {self.tn:5d}\n"
            f"          Accuracy: {accuracy:.3f}\n"
            f"          Precision: {precision:.3f}\n"
            f"          Recall: {recall:.3f}\n"
            f"          F1 Score: {f1_score:.3f}"
        )
