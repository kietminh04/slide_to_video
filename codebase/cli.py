"""CLI cho CLSG Script Engine – dùng Typer.

Chú ý: file này nằm NGOÀI clsg/ vì clsg/ là thư viện thuần.
"""

import sys
from pathlib import Path

import typer

# Đảm bảo project root trên sys.path khi chạy trực tiếp
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

app = typer.Typer(help="CLSG Script Engine – sinh kịch bản video bài giảng")


@app.command()
def generate(
    doc_path: Path = typer.Argument(..., help="Đường dẫn tài liệu nguồn"),
    weights: Path = typer.Option(..., "--weights", "-w", help="File trọng số JSON"),
    fake: bool = typer.Option(False, "--fake", help="Dùng FakeLLMProvider (test)"),
    style: str = typer.Option("serious", "--style", "-s", help="Style pack"),
    output: Path = typer.Option(None, "--output", "-o", help="Ghi ra file JSON"),
) -> None:
    """Sinh kịch bản từ tài liệu và trọng số."""
    from codebase.clsg.engine import run_pipeline

    script = run_pipeline(
        doc_path=doc_path,
        weights_path=weights,
        fake=fake,
        style_pack=style,
    )

    script_json = script.model_dump_json(indent=2)

    if output:
        output.write_text(script_json, encoding="utf-8")
        typer.echo(f"✅ Đã ghi kịch bản ra {output}")
    else:
        typer.echo(script_json)

    # Tóm tắt
    total_words = sum(
        len(b.display_text.split())
        for s in script.scenes
        for b in s.beats
    )
    typer.echo(f"\n📊 {len(script.scenes)} scene, {total_words} từ", err=True)


if __name__ == "__main__":
    app()
