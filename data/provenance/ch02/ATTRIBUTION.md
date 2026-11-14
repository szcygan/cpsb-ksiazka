# Pochodzenie zapisu EKG

G. B. Moody i R. G. Mark, *MIT-BIH Arrhythmia Database*, v1.0.0,
PhysioNet, DOI 10.13026/C2F305.
[Baza i cytowanie](https://physionet.org/content/mitdb/1.0.0/) ·
[Open Data Commons Attribution License v1.0](https://physionet.org/content/mitdb/view-license/1.0.0/).

Współdzielone pliki `100_normal.npz`, `100_normal_annotations.csv` oraz
manifest pochodzą z rozdziału 1. Próbki sygnału zachowano z M8 CPSB;
w D01 zastąpiono położenia adnotacji oryginalnymi indeksami WFDB.
Zawierają kanał MLII w mV przy 360 Hz,
z przedziału \([630,720)\) s rekordu 100. W E2.6 wykorzystano siedem
adnotacji z przedziału \([642,648)\) s i okna wokół tych adnotacji.
Skróty i granice wycinka podaje `ch01_manifest.json`.

E2.1–E2.5 mają wejścia syntetyczne. E2.7 odtwarza dwa wiersze z tabeli 4
dokumentacji ADS1299-x, SBAS499C, warunki 5 V, 4,5 V odniesienia,
PGA 24. [Dokumentacja Texas Instruments](https://www.ti.com/lit/ds/symlink/ads1299.pdf).

## Uzupełnienie audytu B05-01 — stan historyczny

11 listopada 2026 r. Porównanie z oryginalnymi plikami WFDB PhysioNet
potwierdziło zgodność próbek sygnału i symboli uderzeń. Stwierdzono różnice
indeksów adnotacji wycinków rozwojowych 100/103/105; rekord 200 jest zgodny
również co do indeksów. Dotychczasowe pliki zachowano jako wersję historyczną.
Dokładne różnice, skróty oryginałów i zakres proponowanej korekty D01:
`review/b05_01/mitbih_provenance_verification.json` oraz raport B05-01.
Powyższa rozbieżność dotyczy stanu sprzed D01.

## Wykonane D01-A — 12 listopada 2026 r.

Po akceptacji autora zastosowano oryginalne, numerowane od zera indeksy
WFDB `.atr` v1.0.0 we wszystkich wycinkach rozwojowych. Zachowano
sygnały, symbole i liczby uderzeń; pliki testowe rekordu 200 były już zgodne.
Pełne porównanie z odczytem WFDB: `review/d01/provenance_verification.json`
(ścieżka od katalogu głównego). Historia: `review/history/`.
To korekta danych odniesienia, z zachowaniem atrybucji oraz odrębnych
warunków Open Data Commons Attribution License v1.0.
