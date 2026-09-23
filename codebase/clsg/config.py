"""Cấu hình pipeline qua biến môi trường và giá trị mặc định."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Cấu hình CLSG pipeline.

    Đọc từ biến môi trường hoặc file .env.
    Tên model đặt theo vai trò, không hard-code.
    """

    model_config = {"env_prefix": "CLSG_", "env_file": ".env", "extra": "ignore"}

    # === Tên model theo vai trò (Ưu tiên gpt-4o-mini tiết kiệm 30x token) ===
    model_generator: str = "gpt-4o-mini"
    model_judge: str = "gpt-4o-mini"
    model_cheap: str = "gpt-4o-mini"

    # === Tham số kịch bản ===
    minutes: float = 5.0
    wpm: int = 140  # tốc độ đọc tiếng Việt, cần đo lại
    overhead_ratio: float = 0.12  # 12% cho mở bài và tóm tắt

    # === Plan ===
    focus: float = 1.5  # số mũ làm sắc trọng số
    w_min: float = 0.05  # sàn trọng số cho chương tiên quyết
    words_per_point: int = 170  # số từ cho một điểm dạy
    min_quiz_questions: int = 3  # chương cần ít nhất n câu quiz mới dùng w_quiz

    # === Guard ===
    pacing_threshold: float = 0.15  # abs(actual - target) / target
    allocation_l1_threshold: float = 0.15
    min_facts_deep: int = 3  # số mục FactSheet tối thiểu cho đoạn deep
    max_guard_rounds: int = 2  # tối đa vòng sửa

    # === Style ===
    max_flavor_ratio: float = 0.20  # beat flavor tối đa 20% số từ

    # === LLM ===
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_cache_dir: str = ".llm_cache"
    usage_log_file: str = "usage_log.jsonl"
    llm_max_retries: int = 1  # retry khi parse lỗi


def get_settings(**overrides) -> Settings:
    """Tạo Settings, cho phép ghi đè cho test."""
    return Settings(**overrides)
