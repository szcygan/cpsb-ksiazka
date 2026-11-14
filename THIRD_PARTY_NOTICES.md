# Dane i składniki osób trzecich

Pakiet zawiera wycinki MLII rekordów 100, 103, 105 i 200 z **MIT-BIH
Arrhythmia Database v1.0.0**, George B. Moody i Roger G. Mark, PhysioNet
(2005), DOI [10.13026/C2F305](https://doi.org/10.13026/C2F305).
Warunki danych: [Open Data Commons Attribution License v1.0](https://physionet.org/content/mitdb/view-license/1.0.0/).
Cytować także: Moody GB, Mark RG (2001), *The impact of the MIT-BIH
Arrhythmia Database*, IEEE Engineering in Medicine and Biology Magazine
20(3), 45–50, [DOI 10.1109/51.932724](https://doi.org/10.1109/51.932724).

Sygnały są wycinkami bazy; część doświadczeń dodaje jawne przekształcenia
syntetyczne. W D01 zastąpiono indeksy adnotacji rozwojowych oryginalnymi
indeksami WFDB `.atr`, zachowując próbki, symbole i liczby uderzeń.
Pochodzenie opisują `data/provenance/`, manifesty wejść i
`review/d01/provenance_verification.json`; zakres korekty opisano w
`chapter_notes/korekta_adnotacji_D01.md`. Historyczne archiwum wskazane
w tych notach należy do pełnego pakietu książki i nie jest tutaj dołączone.

Wymagania instalacyjne nie zawierają kopii bibliotek ani środowiska.
Licencje bezpośrednich zależności: NumPy 2.3.5, SciPy 1.17.0, statsmodels
0.14.6, nbformat 5.10.4, nbclient 0.10.2 i ipykernel 6.30.1 — BSD-3-Clause;
Matplotlib 3.10.8 — licencja Matplotlib oparta na PSF;
EMD-signal 1.10.0 — Apache-2.0; PyWavelets 1.8.0 — MIT.
Biblioteki i ich zależności zachowują własne pełne notices instalacyjne.
WFDB służyło wcześniejszemu audytowi i nie jest zależnością wykonawczą.

Generowane wykresy przedstawiają własne doświadczenia i niekiedy dane
MIT-BIH; należy zachować atrybucję danych. SVG mogą zawierać kontury fontu
DejaVu, którego pełną notę dołączono w `LICENSES/DejaVu.txt`.
Nie dołączono instrukcji ani ilustracji producentów, publikacji PDF,
materiałów Moodle ani prywatnych dokumentów źródłowych autora.
