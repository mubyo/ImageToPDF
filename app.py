"""ImageToPDF - フォルダ内の画像からPDFを作るGUIアプリ"""
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from images_to_pdf import collect_images, combine, convert

APP_NAME = "ImageToPDF"


class App:
    def __init__(self, root: TkinterDnD.Tk):
        self.root = root
        self.folders: list[Path] = []
        self.logs: queue.Queue = queue.Queue()
        self.last_output_dir: Path | None = None
        self.done, self.total = 0, 0  # 進捗 (作業スレッドが done を進める)

        root.title(APP_NAME)
        root.geometry("640x560")
        root.minsize(480, 420)

        main = ttk.Frame(root, padding=12)
        main.pack(fill="both", expand=True)

        # --- フォルダ一覧 (ドロップ先) ---
        ttk.Label(main, text="画像フォルダをここにドラッグ&ドロップ (複数可)").pack(anchor="w")
        list_frame = ttk.Frame(main)
        list_frame.pack(fill="both", expand=True, pady=(4, 6))
        self.listbox = tk.Listbox(list_frame, selectmode="extended", height=8)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.listbox.drop_target_register(DND_FILES)
        self.listbox.dnd_bind("<<Drop>>", self.on_drop)

        btns = ttk.Frame(main)
        btns.pack(fill="x")
        ttk.Button(btns, text="フォルダを追加…", command=self.add_folder).pack(side="left")
        ttk.Button(btns, text="選択を削除", command=self.remove_selected).pack(side="left", padx=6)
        ttk.Button(btns, text="すべてクリア", command=self.clear).pack(side="left")

        # --- オプション ---
        opts = ttk.LabelFrame(main, text="作成方法", padding=8)
        opts.pack(fill="x", pady=10)
        self.mode = tk.StringVar(value="each")
        ttk.Radiobutton(opts, text="フォルダごとにPDFを作成 (<フォルダ名>.pdf)",
                        variable=self.mode, value="each").pack(anchor="w")
        ttk.Radiobutton(opts, text="すべての画像を1つのPDFに結合 (<最初のフォルダ名>_compilation.pdf)",
                        variable=self.mode, value="combine").pack(anchor="w")
        self.recursive = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="サブフォルダの画像も含める",
                        variable=self.recursive).pack(anchor="w", pady=(6, 0))

        # --- 実行 ---
        run_row = ttk.Frame(main)
        run_row.pack(fill="x")
        self.run_btn = ttk.Button(run_row, text="PDFを作成", command=self.run)
        self.run_btn.pack(side="left")
        self.open_btn = ttk.Button(run_row, text="保存先を開く", command=self.open_output,
                                   state="disabled")
        self.open_btn.pack(side="left", padx=6)
        self.progress = ttk.Progressbar(run_row, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # --- ログ ---
        self.log_text = tk.Text(main, height=8, state="disabled", wrap="none")
        self.log_text.pack(fill="both", expand=True, pady=(10, 0))

        self.root.after(100, self.flush_logs)

    # ---------- フォルダ一覧の操作 ----------
    def add_paths(self, paths):
        for p in map(Path, paths):
            if not p.is_dir():
                self.log(f"フォルダではないのでスキップ: {p}")
            elif p not in self.folders:
                self.folders.append(p)
                self.listbox.insert("end", str(p))

    def on_drop(self, event):
        self.add_paths(self.root.tk.splitlist(event.data))

    def add_folder(self):
        d = filedialog.askdirectory(title="画像フォルダを選択")
        if d:
            self.add_paths([d])

    def remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)
            del self.folders[i]

    def clear(self):
        self.listbox.delete(0, "end")
        self.folders.clear()

    # ---------- 実行 ----------
    def run(self):
        if not self.folders:
            messagebox.showinfo(APP_NAME, "画像フォルダを追加してください。")
            return
        self.run_btn.configure(state="disabled")
        self.done, self.total = 0, 0
        self.progress.configure(value=0, maximum=1)
        folders, mode, recursive = list(self.folders), self.mode.get(), self.recursive.get()
        threading.Thread(target=self.work, args=(folders, mode, recursive), daemon=True).start()

    def step(self):
        # 作業スレッドから呼ばれる。画面への反映は flush_logs が行う
        self.done += 1

    def work(self, folders, mode, recursive):
        # 進捗の総数 = 画像の枚数 × 2 (読み込み + PDFへの書き込み)
        self.total = 2 * sum(len(collect_images(f, recursive)) for f in folders if f.is_dir())
        try:
            if mode == "combine":
                combine(folders, None, recursive, 150, self.log, self.step)
            else:
                ok = sum(convert(f, None, recursive, 150, self.log, self.step) for f in folders)
                self.log(f"{ok}/{len(folders)} 個のPDFを作成しました")
        except Exception as e:  # メモリ不足などで止まった場合も画面に表示する
            self.log(f"エラー: {e}")
        self.last_output_dir = folders[0].resolve().parent
        self.root.after(0, self.finish)

    def finish(self):
        self.done = self.total  # 途中で止まった場合も、バーは完了の位置にそろえる
        self.update_progress()
        self.run_btn.configure(state="normal")
        self.open_btn.configure(state="normal")
        self.clear()

    def update_progress(self):
        if self.total:
            self.progress.configure(maximum=self.total, value=min(self.done, self.total))

    def open_output(self):
        if self.last_output_dir:
            os.startfile(self.last_output_dir)

    # ---------- ログ (作業スレッドからも安全に書けるようキュー経由) ----------
    def log(self, msg: str):
        self.logs.put(msg)

    def flush_logs(self):
        lines = []
        while not self.logs.empty():
            lines.append(self.logs.get())
        self.update_progress()
        if lines:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", "\n".join(lines) + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(100, self.flush_logs)


def main():
    root = TkinterDnD.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
