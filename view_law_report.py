import pandas as pd
from tabulate import tabulate

CSV_FILE = "laws_overview_report.csv"

df = pd.read_csv(CSV_FILE)

print("\n===== THỐNG KÊ DỮ LIỆU PHÁP LUẬT =====\n")

print(
    tabulate(
        df,
        headers="keys",
        tablefmt="grid",
        showindex=False
    )
)