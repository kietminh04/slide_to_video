from collections import Counter

from codebase.clsg.schemas import Chunk, Script


def get_words(text: str) -> list[str]:
    """Tách từ đơn giản."""
    return [w.lower() for w in text.replace(".", " ").replace(",", " ").split() if w]


def get_ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    """Tạo tập n-gram từ danh sách từ."""
    return set(tuple(words[i : i + n]) for i in range(len(words) - n + 1))


def allocation_l1(script: Script, chunks: list[Chunk]) -> float:
    """Tính sai số L1 giữa phân bổ từ thực tế và trọng số yêu cầu.
    
    Args:
        script: Kịch bản đã sinh.
        chunks: Danh sách chunk nguồn.
        
    Returns:
        float: L1 distance.
    """
    if not script.meta.weights:
        return 0.0

    # Tính tổng số từ theo chương
    chapter_words: Counter[str] = Counter()
    total_words = 0
    for scene in script.scenes:
        words = 0
        for beat in scene.beats:
            words += len(get_words(beat.display_text))
        chapter_words[scene.chapter] += words
        total_words += words

    if total_words == 0:
        return 2.0  # Lỗi tối đa cho L1 (sum of absolute diffs of 2 dists is max 2)

    l1 = 0.0
    for chapter, expected_w in script.meta.weights.items():
        actual_w = chapter_words[chapter] / total_words
        l1 += abs(expected_w - actual_w)

    return l1


def required_coverage(script: Script, chunks: list[Chunk]) -> float:
    """Tỉ lệ chunk được dẫn nguồn trên tổng số chunk đầu vào.
    Giả định các chunk truyền vào đều là required (được chọn trong blueprint).
    """
    if not chunks:
        return 1.0

    cited_ids = set()
    for scene in script.scenes:
        for beat in scene.beats:
            cited_ids.update(beat.source_ids)

    input_ids = {c.id for c in chunks}
    valid_cited = cited_ids.intersection(input_ids)

    return len(valid_cited) / len(input_ids)


def copy_ratio(script: Script, chunks: list[Chunk]) -> float:
    """Tỉ lệ 5-gram của kịch bản trùng với nguồn."""
    # Lấy 5-gram của nguồn
    source_ngrams = set()
    for chunk in chunks:
        words = get_words(chunk.text)
        source_ngrams.update(get_ngrams(words, 5))

    if not source_ngrams:
        return 0.0

    # Lấy 5-gram của kịch bản
    script_words = []
    for scene in script.scenes:
        for beat in scene.beats:
            script_words.extend(get_words(beat.display_text))

    script_ngrams = get_ngrams(script_words, 5)

    if not script_ngrams:
        return 0.0

    overlap = script_ngrams.intersection(source_ngrams)
    return len(overlap) / len(script_ngrams)


def specificity(script: Script, chunks: list[Chunk]) -> float:
    """Mock metric specificity.
    Đo tỉ lệ các từ khóa cụ thể (ví dụ, con số) trong các cảnh 'deep'.
    """
    deep_words = 0
    specific_hints = 0
    for scene in script.scenes:
        if scene.depth == "deep":
            for beat in scene.beats:
                words = get_words(beat.display_text)
                deep_words += len(words)
                # Đếm số, ví dụ đơn giản
                specific_hints += sum(1 for w in words if any(c.isdigit() for c in w))

    if deep_words == 0:
        return 0.0
    return (specific_hints / deep_words) * 100


def claim_supported_rate(script: Script, chunks: list[Chunk]) -> float:
    """Mock metric claim_supported_rate."""
    # Trả về 1.0 tạm thời, thực tế cần LLM judge
    return 1.0


def why_qa(script: Script, chunks: list[Chunk]) -> float:
    """Mock metric why_qa."""
    return 1.0


def calculate_all_metrics(script: Script, chunks: list[Chunk]) -> dict[str, float]:
    """Tính tất cả các metric cho một kịch bản."""
    return {
        "allocation_l1": allocation_l1(script, chunks),
        "required_coverage": required_coverage(script, chunks),
        "copy_ratio": copy_ratio(script, chunks),
        "specificity": specificity(script, chunks),
        "claim_supported_rate": claim_supported_rate(script, chunks),
        "why_qa": why_qa(script, chunks),
    }
