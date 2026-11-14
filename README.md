# Cyfrowe przetwarzanie sygnałów biomedycznych — notebooki

Wykonywalny dodatek do książki Szymona Cygana *Cyfrowe przetwarzanie sygnałów
biomedycznych. Od pomiaru do wiarygodnego wyniku*, Politechnika Warszawska.
Wersja obliczeń: **I01-D01/B05-03**, pakiet repozytorium **G01**.

Repozytorium zawiera 12 notebooków, wspólny kod, wymagania środowiska,
wejścia obliczeń i zapis pochodzenia danych. Pełny rękopis oraz historia
redakcyjna są odrębnym pakietem książki. Figury powstają podczas wykonania.

## Uruchomienie

Pobierz lub sklonuj całe repozytorium. Sam plik `.ipynb` nie wystarcza.
Środowisko odniesienia: **Python 3.12.14**; wersje bibliotek są przypięte
w `requirements.txt`. Z katalogu głównego repozytorium:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 scripts\validate_notebook_bundle.py
.\.venv\Scripts\python.exe -X utf8 scripts\check_jupyter.py --all
```

Linux/macOS:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/validate_notebook_bundle.py
.venv/bin/python -X utf8 scripts/check_jupyter.py --all
```

Ostatnie polecenie uruchamia rzeczywiste jądra Jupyter w kolejności rozdziałów.
Przed rozdziałem 10 sprawdza przekazanie z rozdziału 9 i odtwarza zamrożony
stan D01. Nie nadpisuje źródłowych notebooków. Wyniki wykonania trafiają do
`review/jupyter_protocol.json`, wykonane kopie do `review/jupyter/`, figury
do `figures/`, a tabele i metadane do `results/`, `data/` i `chapter_notes/`.

Notebooki można również otwierać w edytorze obsługującym Jupyter, wybierając
interpreter utworzonego środowiska. Pilot rozdziału 3 należy uruchamiać
z katalogu `notebooks/`; skrypt zbiorczy ustawia ten katalog automatycznie.
Po ręcznym wykonaniu rozdziału 9, przed rozdziałem 10 trzeba wywołać
`python scripts/prepare_frozen_handoff.py`. Do świeżej kopii repozytorium
dołączono już poprawny stan referencyjny.

## Mapa notebooków

| Część książki | Notebook |
|---|---|
| 1 | [ch01_measurement_chain.ipynb](notebooks/ch01_measurement_chain.ipynb) |
| 2 | [ch02_sampling_aliasing.ipynb](notebooks/ch02_sampling_aliasing.ipynb) |
| 3 | [ch03_fourier.ipynb](notebooks/ch03_fourier.ipynb) |
| 4 | [ch04_psd_correlation.ipynb](notebooks/ch04_psd_correlation.ipynb) |
| 5 | [ch05_filtering_resampling.ipynb](notebooks/ch05_filtering_resampling.ipynb) |
| 6 | [ch06_hilbert_complex.ipynb](notebooks/ch06_hilbert_complex.ipynb) |
| 7 | [ch07_time_frequency_wavelets.ipynb](notebooks/ch07_time_frequency_wavelets.ipynb) |
| 8 | [ch08_additional_information.ipynb](notebooks/ch08_additional_information.ipynb) |
| 9 | [ch09_pipeline.ipynb](notebooks/ch09_pipeline.ipynb) |
| 10 | [ch10_validation_reproducibility.ipynb](notebooks/ch10_validation_reproducibility.ipynb) |
| dodatki | [appendices_checks.ipynb](notebooks/appendices_checks.ipynb) |
| zadania | [fala_d_problem_checks.ipynb](notebooks/fala_d_problem_checks.ipynb) |

## Weryfikacja

`validate_notebook_bundle.py` sprawdza kompletność, sumy SHA-256, format
notebooków oraz zobowiązanie zamrożenia rozdziału 10. Nie wykonuje obliczeń.
GitHub Actions uruchamia tę kontrolę przy zmianach. Pełne wykonanie Jupyter
można uruchomić w Actions ręcznie, wybierając `rerun_notebooks`.
Protokół rozróżnia plan, rozpoczęte wykonanie, błąd i faktyczne zaliczenie.
Wcześniejsze wykonanie Windows dotyczy tego samego kodu i wejść; nie jest
przedstawiane jako nowe wykonanie w GitHub Actions.

## Dane, licencje i zakres wnioskowania

Przykłady wykorzystują dane syntetyczne i wycinki publicznej bazy MIT-BIH.
Nie potrzeba pobierania danych podczas wykonania. Pochodzenie i odrębne
warunki danych opisuje [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Własny kod: MIT; tekst notebooków i własna warstwa figur: CC BY 4.0.
Zakres praw: [LICENSE.md](LICENSE.md).

Rekord 200 był już oceniany podczas przygotowania książki. Powtórne
wykonanie stanowi regresję znanego przykładu, a nie nowy niezależny test.
Przykłady dydaktyczne nie są walidowanym oprogramowaniem medycznym.
Przy cytowaniu należy podać pełny SHA użytej wersji oraz źródło danych.
