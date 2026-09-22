"""Dịch vụ Thuật ngữ & Glossary sư phạm (Pedagogical Glossary Service).

Sử dụng kho từ vựng chuyên ngành ML (LPMDataset ml-1_vocab.pkl)
để chuẩn hóa thuật ngữ tiếng Anh - Việt và triệt tiêu tiếng Anh bồi (code-switching).
"""

from __future__ import annotations

import pickle
import re
import sys
from pathlib import Path

class Vocabulary(object):
    """Stub class matching LPMDataset Vocabulary structure for pickle unpickling."""
    def __init__(self):
        self.word2idx = {}
        self.idx2word = {}
        self.idx = 0

# Ensure pickle finds Vocabulary even if pickled under __main__
if "__main__" in sys.modules and not hasattr(sys.modules["__main__"], "Vocabulary"):
    sys.modules["__main__"].Vocabulary = Vocabulary

# Đường dẫn mặc định tới bộ từ vựng LPM
LPM_VOCAB_PATH = Path(r"d:\Project\Slide to Video\Dữ Liệu & Hạ Tầng\Bộ Từ Vựng LPM\ml-1_vocab.pkl")

# Danh mục quy chuẩn thuật ngữ bắt buộc
CANONICAL_VIETNAMESE_TERMS = {
    # Thuật ngữ bắt buộc dịch sang tiếng Việt chuẩn sư phạm
    "neural network": "mạng nơ-ron",
    "loss function": "hàm mất mát",
    "cost function": "hàm chi phí",
    "activation function": "hàm kích hoạt",
    "gradient descent": "hạ độ dốc",
    "backpropagation": "lan truyền ngược",
    "weight": "trọng số",
    "bias": "độ chệch",
    "learning rate": "tốc độ học",
    "overfitting": "quá khớp",
    "underfitting": "dưới khớp",
    "dataset": "tập dữ liệu",
    "training set": "tập huấn luyện",
    "test set": "tập kiểm thử",
    "validation set": "tập kiểm định",
    "supervised learning": "học có giám sát",
    "unsupervised learning": "học không giám sát",
    "reinforcement learning": "học tăng cường",
    "convolution": "tích chập",
    "feature map": "bản đồ đặc trưng",
    "pooling": "gộp mẫu",
    "stride": "bước nhảy",
    "padding": "đệm viền",
    "accuracy": "độ chính xác",
    "precision": "độ chuẩn xác",
    "recall": "độ thu hồi",
}

# Thuật ngữ quốc tế giữ nguyên tiếng Anh (không dịch gượng ép)
PRESERVED_ENGLISH_TERMS = {
    "cnn", "rnn", "lstm", "transformer", "bert", "gpt", "resnet", "yolo",
    "kernel", "filter", "stride", "epoch", "batch size", "dropout",
    "attention mechanism", "softmax", "relu", "sigmoid", "cross-entropy",
    "adam", "sgd", "token", "embedding", "latent space", "bounding box",
    "iou", "map", "f1-score", "roc-auc"
}

# Động từ/từ đệm tiếng Anh cấm dùng trong bài giảng tiếng Việt
FORBIDDEN_ENGLISH_VERBS = {
    "train": "huấn luyện",
    "training": "huấn luyện",
    "tune": "tinh chỉnh",
    "fine-tune": "tinh chỉnh",
    "detect": "phát hiện",
    "detection": "phát hiện",
    "predict": "dự đoán",
    "prediction": "dự đoán",
    "visualize": "trực quan hóa",
    "extract": "trích xuất",
    "optimize": "tối ưu hóa",
    "preprocess": "tiền xử lý",
    "evaluate": "đánh giá",
    "apply": "áp dụng",
    "focus": "tập trung",
}


# Tập các từ tiếng Việt không dấu phổ biến cần loại khỏi bộ lọc tiếng Anh
VIETNAMESE_ASCII_WORDS = {
    "trong", "qua", "gian", "hai", "tham", "quan", "sau", "cho", "va", "la", "cua", "co",
    "khi", "vao", "ra", "den", "theo", "ve", "voi", "cac", "nhung", "mot", "ba", "bon",
    "nam", "nay", "do", "ta", "toi", "chung", "ban", "ngay", "duoc", "nguyen", "ly", "lop",
    "vi", "tri", "anh", "so", "bo", "diem", "tu", "nho", "lon", "nhu", "vay", "tien", "thanh",
    "dong", "thuc", "te", "cung", "cap", "hoc", "tap", "phat", "trien", "mo", "hinh", "bai",
    "biet", "se", "dau", "tren", "duoi", "ngoai", "truoc", "da", "ra", "dong", "khung", "kich",
    "ban", "chia", "khoan", "vung", "so", "do", "duong", "ong", "xu", "ly", "chuyen", "dong",
    "song", "song", "phong", "to", "khu", "vuc", "nhan", "chua", "chuan", "hoa", "can", "tinh",
    "toan", "chieu", "khong", "giam", "tang", "nhieu", "it", "cao", "thap", "then", "chot",
    "tao", "nen", "cuoc", "cach", "mang", "linh", "vuc", "thi", "giac", "may", "tinh", "truot",
    "nang", "cao", "co", "ban", "sau", "day", "day", "du", "dung", "sai", "loi", "vi", "pham"
}


class PedagogicalGlossary:
    """Quản lý và chuẩn hóa thuật ngữ sư phạm."""

    def __init__(self, vocab_path: Path | None = None):
        self.vocab_path = vocab_path or LPM_VOCAB_PATH
        self.lpm_terms: set[str] = set()
        self._load_vocab()

    def _load_vocab(self) -> None:
        """Nạp từ vựng từ file pickle nếu tồn tại."""
        if self.vocab_path.exists():
            try:
                with open(self.vocab_path, "rb") as f:
                    data = pickle.load(f)
                    if hasattr(data, "word2idx"):
                        self.lpm_terms = {str(k).lower().strip() for k in data.word2idx.keys()}
                    elif isinstance(data, list):
                        self.lpm_terms = {str(item).lower().strip() for item in data}
                    elif hasattr(data, "keys"):
                        self.lpm_terms = {str(k).lower().strip() for k in data.keys()}
                    elif hasattr(data, "vocab"):
                        self.lpm_terms = {str(k).lower().strip() for k in data.vocab}
            except Exception as e:
                print(f"[Glossary] Cảnh báo không đọc được {self.vocab_path}: {e}")

    def normalize_sentence(self, text: str) -> tuple[str, list[str]]:
        """Chuẩn hóa một câu: thay thế từ tiếng Anh bồi và giữ lại thuật ngữ chuẩn.

        Returns:
            tuple (câu đã chuẩn hóa, danh sách cảnh báo từ tiếng Anh vi phạm).
        """
        warnings: list[str] = []
        result = text

        # 1. Thay thế các động từ cấm
        for verb, vi_trans in FORBIDDEN_ENGLISH_VERBS.items():
            pattern = re.compile(rf"\b{re.escape(verb)}\b", re.IGNORECASE)
            if pattern.search(result):
                warnings.append(f"Chêm động từ tiếng Anh '{verb}' -> Chuẩn hóa thành '{vi_trans}'")
                result = pattern.sub(vi_trans, result)

        # 2. Thay thế các danh từ bắt buộc dịch
        for en_term, vi_term in CANONICAL_VIETNAMESE_TERMS.items():
            pattern = re.compile(rf"\b{re.escape(en_term)}\b", re.IGNORECASE)
            if pattern.search(result):
                result = pattern.sub(vi_term, result)

        return result, warnings

    def audit_terminology(self, text: str) -> dict[str, any]:
        """Kiểm định mức độ tuân thủ thuật ngữ chuẩn (TCR - Terminology Compliance Rate)."""
        raw_words = re.findall(r"\b[A-Za-z]+\b", text.lower())
        # Lọc bỏ các từ tiếng Việt không dấu
        en_words = [w for w in raw_words if w not in VIETNAMESE_ASCII_WORDS]

        if not en_words:
            return {"tcr_score": 100.0, "violations": [], "passed": True}

        violations = []
        valid_en_count = 0

        # Kiểm tra cụm thuật ngữ chưa dịch trước
        lower_text = text.lower()
        for en_term, vi_term in CANONICAL_VIETNAMESE_TERMS.items():
            if en_term in lower_text:
                violations.append(f"Thuật ngữ chưa dịch '{en_term}' (nên dùng '{vi_term}')")

        for w in en_words:
            if w in PRESERVED_ENGLISH_TERMS or w in self.lpm_terms:
                valid_en_count += 1
            elif w in FORBIDDEN_ENGLISH_VERBS:
                violations.append(f"Động từ tiếng Anh bồi '{w}' (nên dùng '{FORBIDDEN_ENGLISH_VERBS[w]}')")
            elif any(w in term for term in CANONICAL_VIETNAMESE_TERMS):
                pass  # Đã bắt ở vòng lặp cụm từ phía trên
            else:
                # Từ tiếng Anh lạ
                violations.append(f"Từ tiếng Anh chưa kiểm định '{w}'")

        total_tracked = len(en_words)
        if total_tracked > 0:
            tcr = max(0.0, 100.0 - (len(violations) / total_tracked * 100.0))
        else:
            tcr = 100.0

        passed = len(violations) == 0 or tcr >= 85.0

        return {
            "tcr_score": round(tcr, 2),
            "violations": violations,
            "passed": passed
        }

    def get_prompt_guidance(self) -> str:
        """Sinh chỉ dẫn Glossary nhồi vào System Prompt cho Generator Agent."""
        return (
            "QUY TẮC THUẬT NGỮ BẮT BUỘC (GLOSSARY ENFORCEMENT):\n"
            "1. Lời giảng 100% bằng tiếng Việt chuẩn mực sư phạm.\n"
            "2. BẮT BUỘC dùng các thuật ngữ tiếng Việt sau: "
            + ", ".join(f"'{k}' -> '{v}'" for k, v in list(CANONICAL_VIETNAMESE_TERMS.items())[:12])
            + ".\n3. CHỈ ĐƯỢC PHÉP giữ nguyên các thuật ngữ tiếng Anh chuẩn sau: "
            + ", ".join(sorted(list(PRESERVED_ENGLISH_TERMS))[:15])
            + ".\n4. TUYỆT ĐỐI KHÔNG dùng động từ/từ đệm tiếng Anh: "
            + ", ".join(FORBIDDEN_ENGLISH_VERBS.keys())
            + " (phải dùng: huấn luyện, tinh chỉnh, phát hiện, trực quan hóa).\n"
        )
