"""フォルダ内の画像を1つのPDFにまとめるツール

使い方:
    python images_to_pdf.py <フォルダ> [<フォルダ> ...] [-o 出力.pdf] [-r] [--dpi 150]
    または images_to_pdf.bat にフォルダをドラッグ&ドロップ
"""
import argparse
import re
import sys
from contextlib import contextmanager
from pathlib import Path

from PIL import Image, ImageOps, PdfImagePlugin

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def natural_key(path: Path):
    # "img2" が "img10" より前に来るように数字部分を数値として比較
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def collect_images(folder: Path, recursive: bool):
    pattern = "**/*" if recursive else "*"
    files = [p for p in folder.glob(pattern) if p.is_file() and p.suffix.lower() in EXTS]
    return sorted(files, key=lambda p: (natural_key(p.parent), natural_key(p)))


def load_rgb(path: Path) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # スマホ写真の回転を補正
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])  # 透過部分は白で塗りつぶし
        return bg
    return img.convert("RGB")


@contextmanager
def on_page_written(step):
    """PDF保存中、1ページ書き込むごとに step() を呼ぶ。
    Pillowは保存中の進捗を通知しないので、内部関数 _write_image (1ページ1回呼ばれる) を一時的に包む。
    Pillowの版で関数がなければ何もしない (進捗が保存中に進まないだけ)"""
    orig = getattr(PdfImagePlugin, "_write_image", None)
    if step is None or orig is None:
        yield
        return

    def hooked(*args, **kwargs):
        result = orig(*args, **kwargs)
        step()
        return result

    PdfImagePlugin._write_image = hooked
    try:
        yield
    finally:
        PdfImagePlugin._write_image = orig


def write_pdf(files, output: Path, dpi: float, label, log=print, step=None) -> bool:
    """files: [(表示用の基準フォルダ, 画像パス), ...] を1つのPDFに書き出す。
    step: 進捗通知。画像1枚の読み込みごとと、1ページの書き込みごとに呼ぶ (合計 画像数×2 回)"""
    pages = []
    for i, (base, f) in enumerate(files, 1):
        try:
            pages.append(load_rgb(f))
            log(f"[{i}/{len(files)}] {label(base, f)}")
        except Exception as e:
            log(f"[{i}/{len(files)}] スキップ: {f.name} ({e})")
            if step:
                step()  # 書き込まれない分も進めておく
        if step:
            step()

    if not pages:
        log("読み込める画像がありませんでした\n")
        return False

    log("PDFに書き込み中…")
    with on_page_written(step):
        pages[0].save(output, "PDF", save_all=True, append_images=pages[1:], resolution=dpi)
    log(f"完了: {output} ({len(pages)}ページ)\n")
    return True


def convert(folder: Path, output: Path | None, recursive: bool, dpi: float, log=print, step=None) -> bool:
    """1つのフォルダから1つのPDFを作る"""
    folder = folder.resolve()
    log(f"=== {folder} ===")
    if not folder.is_dir():
        log(f"フォルダが見つかりません: {folder}\n")
        return False

    files = collect_images(folder, recursive)
    if not files:
        log(f"画像がありません: {folder}\n")
        return False

    output = (output or folder.parent / f"{folder.name}.pdf").resolve()
    return write_pdf([(folder, f) for f in files], output, dpi,
                     lambda base, f: str(f.relative_to(base)), log, step)


def combine(folders, output: Path | None, recursive: bool, dpi: float, log=print, step=None) -> bool:
    """複数フォルダの画像をすべて1つのPDFにまとめる"""
    # エクスプローラーからのドロップ順は不定なので、フォルダ名順に並べ直す
    folders = sorted((Path(f).resolve() for f in folders), key=natural_key)

    files = []
    for folder in folders:
        if not folder.is_dir():
            log(f"フォルダが見つかりません (スキップ): {folder}")
            continue
        found = collect_images(folder, recursive)
        log(f"{folder.name}: {len(found)}枚")
        files += [(folder, f) for f in found]

    if not files:
        log("画像がありません")
        return False

    output = (output or folders[0].parent / f"{folders[0].name}_compilation.pdf").resolve()
    log("")
    return write_pdf(files, output, dpi,
                     lambda base, f: f"{base.name}\\{f.relative_to(base)}", log, step)


def main():
    ap = argparse.ArgumentParser(description="フォルダ内の画像からPDFを作成 (フォルダごとに1つのPDF)")
    ap.add_argument("folders", type=Path, nargs="+", help="画像が入ったフォルダ (複数可)")
    ap.add_argument("-o", "--output", type=Path, help="出力PDF (フォルダ1つのときのみ。既定: <フォルダ名>.pdf をフォルダと同じ場所に)")
    ap.add_argument("-r", "--recursive", action="store_true", help="サブフォルダも含める")
    ap.add_argument("--dpi", type=float, default=150, help="PDFの解像度 (既定: 150)")
    args = ap.parse_args()

    if args.output and len(args.folders) > 1:
        sys.exit("-o はフォルダ1つのときだけ指定できます")

    ok = sum(convert(f, args.output, args.recursive, args.dpi) for f in args.folders)
    print(f"{ok}/{len(args.folders)} 個のPDFを作成しました")
    if ok < len(args.folders):
        sys.exit(1)


if __name__ == "__main__":
    main()
