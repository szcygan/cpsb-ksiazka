# Pochodzenie zapisów EKG

G. B. Moody i R. G. Mark, *MIT-BIH Arrhythmia Database* v1.0.0,
PhysioNet, DOI 10.13026/C2F305.
[Rekord bazy i cytowanie](https://physionet.org/content/mitdb/1.0.0/)

Dane są udostępnione na warunkach Open Data Commons Attribution License
v1.0. [Warunki licencji bazy](https://physionet.org/content/mitdb/view-license/1.0.0/)

Wykorzystano pliki NPZ i CSV wyeksportowane przez CPSB i zapisane w
`M8_pakiet_danych_v0_2.zip`. Użyty kanał to MLII w mV przy 360 Hz.
Rekordy 100 i 103 służą do dopasowania, 105 do badań rozwojowych,
a trzy wycinki rekordu 200 do oceny po zamrożeniu. Podział, zakresy
i skróty są w manifestach `ch09_development_manifest.csv` oraz
`ch10_test_manifest.csv`.

Według dokumentacji M8 wycinki 200 powstały z tekstowego lustra sygnału
i adnotacji z przeliczeniem `mV = (digital - 1024) / 200`.
Pliki NPZ i CSV wycinków 200 zachowano bajtowo z M8; dla rozwoju
100/103/105 w D01 poprawiono indeksy adnotacji do oryginalnego WFDB.
Skróty tekstowych plików podane przez M8 zapisano w
`ch10_source_200_sha256.json`. Odnośnik do lustra dokumentuje drogę
danych. Cytowanie i licencja dotyczą pierwotnej bazy PhysioNet.

Do badań odporności wersje półsyntetyczne powstają w czasie wykonania
na podstawie rekordu 105, z zachowaniem indeksów adnotacji.

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
