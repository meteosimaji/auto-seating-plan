"""Roster of students used for seat shuffling and chart generation.

This module now uses dummy data for demonstration purposes. Each entry
defines the serial number (整理番号), student ID, name in Kanji and
kana, enrolment status, and gender. Only students with status "在籍" are
used when shuffling seats.
"""

STUDENTS = [
    {
        "serial": serial,
        "student_id": f"{10000 + serial:05}",
        "name_kanji": f"生徒{serial:02}",
        "name_kana": f"せいと{serial:02}",
        "status": "休学" if serial in {27, 43} else "在籍",
        "gender": "F" if serial % 2 == 0 else "M",
    }
    for serial in range(1, 45)
]

COMMITTEES = [
    ("学級委員", ["生徒01", "生徒11"]),
    ("会計委員", ["生徒02", "生徒03"]),
    ("図書委員", ["生徒04"]),
    ("文化委員", ["生徒05"]),
    ("体育委員", ["生徒06", "生徒07"]),
    ("群嶺委員", ["生徒08"]),
    ("新聞委員", ["生徒09", "生徒10"]),
    ("環境委員", ["生徒12", "生徒13"]),
    ("選挙管理委員", ["生徒14"]),
]
