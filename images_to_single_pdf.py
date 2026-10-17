"""複数フォルダ内の画像をすべて1つのPDFにまとめるツール

使い方:
    python images_to_single_pdf.py <フォルダ> [<フォルダ> ...] [-o 出力.pdf] [-r] [--dpi 150]
    または images_to_single_pdf.bat にフォルダをまとめてドラッグ&ドロップ

フォルダはフォルダ名順 (数字は数値として比較)、各フォルダ内の画像もファイル名順に並べます。
"""
import argparse
import sys
from pathlib import Path

from images_to_pdf import combine


def main():
    ap = argparse.ArgumentParser(description="複数フォルダ内の画像をすべて1つのPDFにまとめる")
    ap.add_argument("folders", type=Path, nargs="+", help="画像が入ったフォルダ (複数可)")
    ap.add_argument("-o", "--output", type=Path, help="出力PDF (既定: 最初のフォルダと同じ場所に <最初のフォルダ名>_compilation.pdf)")
    ap.add_argument("-r", "--recursive", action="store_true", help="サブフォルダも含める")
    ap.add_argument("--dpi", type=float, default=150, help="PDFの解像度 (既定: 150)")
    args = ap.parse_args()

    if not combine(args.folders, args.output, args.recursive, args.dpi):
        sys.exit(1)


if __name__ == "__main__":
    main()
