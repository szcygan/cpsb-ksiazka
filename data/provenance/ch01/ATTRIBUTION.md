# Pochodzenie zapisu EKG

G. B. Moody i R. G. Mark, *MIT-BIH Arrhythmia Database* v1.0.0,
PhysioNet, DOI 10.13026/C2F305.
[Rekord bazy](https://physionet.org/content/mitdb/1.0.0/) ·
[Open Data Commons Attribution License v1.0](https://physionet.org/content/mitdb/view-license/1.0.0/).

Pliki `100_normal.npz` i `100_normal_annotations.csv` odpowiadają
wycinkowi MLII z przedziału \([630,720)\) s rekordu 100. Pochodzą
z pakietu M8 CPSB, w którym sygnał ma jednostkę mV i częstotliwość
360 Hz. Próbki sygnału zachowano; położenia adnotacji skorygowano w D01 do oryginalnego WFDB. Wykresy E1.2–E1.4
wykorzystują sześć sekund od 642 s. Modele addytywny, multiplikatywny
i ograniczenia zakresu powstają z tego samego wycinka w trakcie wykonania.
Skróty i granice przedziału podaje `ch01_manifest.json`.

E1.1 i E1.5 wykorzystują przebiegi syntetyczne. E1.5 odtwarza założenia
skali i licznika na podstawie dokumentacji Cyton.
[OpenBCI, Cyton Data Format](https://docs.openbci.com/Cyton/CytonDataFormat/).

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
