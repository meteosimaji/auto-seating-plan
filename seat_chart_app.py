"""Tkinter application for shuffling seats and saving charts."""

from __future__ import annotations

import os
import re
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import Dict, List, Tuple

from reportlab.lib import colors

from seat_chart_generator import (
    create_seat_chart,
    simple_shuffle,
    Student,
)
from seat_chart_generator.layout import load_layout, generate_layout
from students import STUDENTS, COMMITTEES


class SeatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        try:
            self.layout = load_layout()
        except Exception:
            self.layout = generate_layout(10, 5)
        self.students_sorted = sorted(STUDENTS, key=lambda d: d["serial"])
        self.student_data = {d["name_kanji"]: d for d in self.students_sorted}
        self.labels: Dict[int, tk.Label] = {}
        self.fixed_seats: set[int] = set()
        self.empty_seats: Dict[int, Tuple[str, str]] = {}
        try:
            shuffled = simple_shuffle(STUDENTS, self.layout)
        except ValueError:
            shuffled = []
        self.assignments: Dict[int, Student] = {s.seat_number: s for s in shuffled}
        self.total_seats = sum(
            1 for row in self.layout for seat in row if isinstance(seat, int)
        )
        self.required_students = sum(1 for s in STUDENTS if s.get("status") == "在籍")
        self.count_var = tk.StringVar()
        # Default background colour for labels (platform dependent)
        tmp_lbl = tk.Label(self.root)
        self.default_bg = tmp_lbl.cget("bg")
        tmp_lbl.destroy()
        self.title_var = tk.StringVar(value="席替え座席表")
        self._build_ui()

    def _format_student(self, student: Student) -> str:
        """Return multiline string with student details."""
        return (
            f"{student.serial}\n"
            f"{student.student_id}\n"
            f"{student.name_kanji}\n"
            f"{student.name_kana}"
        )

    def _build_ui(self) -> None:
        cols = max(len(r) for r in self.layout)
        for r, row in enumerate(self.layout):
            for c, seat in enumerate(row):
                if seat is None or not isinstance(seat, int):
                    continue
                student = self.assignments.get(seat)
                text = self._format_student(student) if student else ""
                colour = "red" if student and student.color == colors.red else "black"
                lbl = tk.Label(self.root, text=text, width=12, fg=colour, justify="center")
                lbl.grid(row=r, column=c, padx=2, pady=2)
                lbl.bind("<Button-1>", lambda e, s=seat: self._select_student(s))
                self.labels[seat] = lbl
                self._style_label(seat)
        title_row = len(self.layout)
        tk.Label(self.root, text="タイトル").grid(row=title_row, column=0, sticky="w")
        tk.Entry(self.root, textvariable=self.title_var, width=20).grid(
            row=title_row, column=1, columnspan=max(1, cols - 1), sticky="we"
        )
        btn_row = title_row + 1
        tk.Button(self.root, text="Shuffle", command=self.shuffle).grid(
            row=btn_row, column=0, pady=5
        )
        tk.Button(self.root, text="Save", command=self.save).grid(row=btn_row, column=1, pady=5)
        tk.Button(self.root, text="すべて削除", command=self.clear_all).grid(
            row=btn_row, column=2, pady=5
        )
        tk.Button(self.root, text="縦変更", command=self.change_rows).grid(row=btn_row, column=3, pady=5)
        tk.Button(self.root, text="横変更", command=self.change_cols).grid(row=btn_row, column=4, pady=5)
        self.count_label = tk.Label(self.root, textvariable=self.count_var)
        self.count_label.grid(
            row=btn_row,
            column=5,
            columnspan=max(1, cols - 5),
            pady=5,
            sticky="w",
        )
        self._update_counts()

    def _select_student(self, seat: int) -> None:
        top = tk.Toplevel(self.root)
        top.title(f"Seat {seat}")
        listbox = tk.Listbox(top, height=15)
        options = []
        if seat in self.empty_seats:
            options.append("空席を解除")
        else:
            options.append("空席にする")
        options.append("テキスト")
        options.extend(d["name_kanji"] for d in self.students_sorted)
        options.extend(["教卓", "補助机"])
        for name in options:
            listbox.insert(tk.END, name)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(top, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=scrollbar.set)

        def choose() -> None:
            if not listbox.curselection():
                return
            name = listbox.get(listbox.curselection())
            top.destroy()
            self._assign_to_seat(seat, name)

        listbox.bind("<Double-Button-1>", lambda e: choose())
        tk.Button(top, text="OK", command=choose).pack()

    def _ask_multiline(self, title: str) -> str | None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        text_widget = tk.Text(dialog, width=20, height=4)
        text_widget.pack(padx=5, pady=5)
        result: list[str] = []

        def ok() -> None:
            result.append(text_widget.get("1.0", tk.END).rstrip("\n"))
            dialog.destroy()

        def cancel() -> None:
            dialog.destroy()

        btn = tk.Frame(dialog)
        btn.pack(pady=5)
        tk.Button(btn, text="OK", command=ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn, text="キャンセル", command=cancel).pack(side=tk.LEFT, padx=5)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result[0] if result else None

    def _assign_to_seat(self, seat: int, name: str) -> None:
        if name == "空席にする":
            if seat in self.assignments:
                del self.assignments[seat]
            self.empty_seats[seat] = ("", "black")
            self.fixed_seats.add(seat)
            self.labels[seat].config(text="", fg="black")
            self._style_label(seat)
            self._update_counts()
            return
        if name == "空席を解除":
            if seat in self.assignments:
                del self.assignments[seat]
            self.fixed_seats.discard(seat)
            self.empty_seats.pop(seat, None)
            self.labels[seat].config(text="", fg="black")
            self._style_label(seat)
            self._update_counts()
            return
        if name == "テキスト":
            if seat in self.assignments:
                del self.assignments[seat]
            text = self._ask_multiline("テキストを入力してください")
            if text is None:
                return
            colour = simpledialog.askstring(
                "文字色", "色名または#RRGGBBを入力してください", initialvalue="black"
            )
            if not colour:
                colour = "black"
            self.empty_seats[seat] = (text, colour)
            self.fixed_seats.add(seat)
            self.labels[seat].config(text=text, fg=colour, justify="left", anchor="w")
            self._style_label(seat)
            self._update_counts()
            return
        if name in ("教卓", "補助机"):
            if seat in self.assignments:
                del self.assignments[seat]
            self.empty_seats[seat] = (name, "black")
            self.fixed_seats.add(seat)
            self.labels[seat].config(text=name, fg="black")
            self._style_label(seat)
            self._update_counts()
            return

        data = self.student_data[name]
        prev_seat = None
        for s, stu in list(self.assignments.items()):
            if stu.name_kanji == name:
                prev_seat = s
                del self.assignments[s]
                self.labels[s].config(text="", fg="black")
                self.fixed_seats.discard(s)
                self.empty_seats.pop(s, None)
                self._style_label(s)
                break
        if seat in self.assignments:
            del self.assignments[seat]
        student = Student(
            seat_number=seat,
            serial=data["serial"],
            student_id=data["student_id"],
            name_kanji=data["name_kanji"],
            name_kana=data["name_kana"],
            gender=data.get("gender", "M"),
            color=colors.red if data.get("status") == "休学" else None,
        )
        self.assignments[seat] = student
        colour = "red" if student.color == colors.red else "black"
        self.labels[seat].config(text=self._format_student(student), fg=colour, justify="center", anchor="center")
        self.fixed_seats.add(seat)
        self.empty_seats.pop(seat, None)
        self._style_label(seat)
        self._update_counts()

    def change_rows(self) -> None:
        current = len(self.layout)
        new_rows = simpledialog.askinteger(
            "行数", "新しい行数を入力", initialvalue=current, minvalue=1
        )
        if not new_rows or new_rows == current:
            return
        cols = max(len(r) for r in self.layout)
        new_layout = generate_layout(new_rows, cols)
        self._reset_layout(new_layout)

    def change_cols(self) -> None:
        current = max(len(r) for r in self.layout)
        new_cols = simpledialog.askinteger(
            "列数", "新しい列数を入力", initialvalue=current, minvalue=1
        )
        if not new_cols or new_cols == current:
            return
        rows = len(self.layout)
        new_layout = generate_layout(rows, new_cols)
        self._reset_layout(new_layout)

    def _reset_layout(self, new_layout: List[List[object]]) -> None:
        self.layout = new_layout
        self.labels.clear()
        self.fixed_seats.clear()
        self.empty_seats.clear()
        self.assignments.clear()
        self.total_seats = sum(
            1 for row in self.layout for seat in row if isinstance(seat, int)
        )
        for widget in self.root.winfo_children():
            widget.destroy()
        self._build_ui()

    def shuffle(self) -> None:
        fixed = {stu.name_kanji: seat for seat, stu in self.assignments.items() if seat in self.fixed_seats}
        try:
            shuffled = simple_shuffle(
                STUDENTS, self.layout, fixed=fixed, empty_seats=list(self.empty_seats.keys())
            )
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.assignments = {s.seat_number: s for s in shuffled}
        self.fixed_seats = set(fixed.values()) | set(self.empty_seats.keys())
        for seat, lbl in self.labels.items():
            student = self.assignments.get(seat)
            if student:
                text = self._format_student(student)
                colour = "red" if student.color == colors.red else "black"
                lbl.config(justify="center", anchor="center")
            elif seat in self.empty_seats:
                text, colour = self.empty_seats[seat]
                lbl.config(
                    justify="left" if text and text not in ("教卓", "補助机") else "center",
                    anchor="w" if text and text not in ("教卓", "補助机") else "center",
                )
            else:
                text = ""
                colour = "black"
            lbl.config(text=text, fg=colour)
            self._style_label(seat)
        self._update_counts()

    def save(self) -> None:
        safe_title = re.sub(r'[\\/:*?"<>|]', "_", self.title_var.get()) or "seat_chart"
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("PNG", "*.png")],
            initialfile=f"{safe_title}.pdf",
        )
        if not path:
            return
        base, ext = os.path.splitext(path)
        if ext.lower() == ".png":
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.close()
            create_seat_chart(
                list(self.assignments.values()),
                seat_rows=self.layout,
                committees=COMMITTEES,
                title=self.title_var.get(),
                output_path=tmp.name,
                image_path=path,
                fixed_seat_numbers=list(self.fixed_seats),
                empty_seat_texts=self.empty_seats,
            )
            os.remove(tmp.name)
            messagebox.showinfo("Saved", f"PNG を保存しました: {path}")
        else:
            create_seat_chart(
                list(self.assignments.values()),
                seat_rows=self.layout,
                committees=COMMITTEES,
                title=self.title_var.get(),
                output_path=path,
                image_path=None,
                fixed_seat_numbers=list(self.fixed_seats),
                empty_seat_texts=self.empty_seats,
            )
            messagebox.showinfo("Saved", f"PDF を保存しました: {path}")

    def clear_all(self) -> None:
        self.assignments.clear()
        self.fixed_seats.clear()
        self.empty_seats.clear()
        for seat, lbl in self.labels.items():
            lbl.config(text="", fg="black")
            self._style_label(seat)
        self._update_counts()

    def _style_label(self, seat: int) -> None:
        lbl = self.labels[seat]
        student = self.assignments.get(seat)
        if seat in self.empty_seats:
            text, _ = self.empty_seats[seat]
            if text in ("教卓", "補助机"):
                lbl.config(
                    bg="white",
                    relief="solid",
                    borderwidth=2,
                    anchor="center",
                    justify="center",
                )
            elif text:
                lbl.config(
                    bg=self.default_bg,
                    relief="flat",
                    borderwidth=0,
                    anchor="w",
                    justify="left",
                )
            else:  # pure empty seat
                lbl.config(
                    bg=self.default_bg,
                    relief="flat",
                    borderwidth=0,
                    anchor="center",
                    justify="center",
                )
        elif student and student.color == colors.red:
            lbl.config(
                bg=self.default_bg,
                relief="flat",
                borderwidth=0,
                anchor="center",
                justify="center",
            )
        else:
            bw = 4 if seat in self.fixed_seats else 2
            lbl.config(
                bg="white",
                relief="solid",
                borderwidth=bw,
                anchor="center",
                justify="center",
            )

    def _update_counts(self) -> None:
        seats_available = self.total_seats - len(self.empty_seats)
        text = f"席数: {seats_available} / 人数: {self.required_students}"
        if seats_available < self.required_students:
            text += " - 席が足りません"
            self.count_label.config(fg="red")
        else:
            self.count_label.config(fg="black")
        self.count_var.set(text)


def main() -> None:
    root = tk.Tk()
    root.title("Seat Shuffler")
    SeatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
