# Pochodzenie danych EKG

G. B. Moody i R. G. Mark, *MIT-BIH Arrhythmia Database*, wersja 1.0.0,
PhysioNet, DOI 10.13026/C2F305.
[Rekord bazy i cytowanie](https://physionet.org/content/mitdb/1.0.0/)

Baza jest udostępniona na warunkach Open Data Commons Attribution
License v1.0. Zgodnie z atrybucją źródłową wykorzystano dane PhysioNet.
[Treść licencji](https://physionet.org/content/mitdb/view-license/1.0.0/)

W pakiecie są wyłącznie wycinki rozwojowe rekordu 100, 103 i 105,
w postaci tablic NPZ i plików adnotacji CSV przygotowanych przez CPSB
w `M8_pakiet_danych_v0_2.zip`. Sygnały zachowano bajtowo po odczycie tablic; w D01 poprawiono indeksy adnotacji oraz metadane i skróty plików.
Manifest podaje zakresy w rekordzie, role i skróty SHA-256.
Sygnał to kanał MLII w mV z częstotliwością 360 Hz. Warianty
półsyntetyczne powstają w czasie wykonania z wycinka `105_normal`,
z zachowaniem indeksów adnotacji. Rekord 200 jest odłożony do rozdziału 10.

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
