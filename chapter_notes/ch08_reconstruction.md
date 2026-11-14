> Raport źródłowej rekonstrukcji R08. W zintegrowanym pakiecie I01 bieżące dowody wspólnego wykonania znajdują się w `integracja_korpusu_notes.md` i `../review/integration_audit.json`. Oryginalne manifesty i audyty R08 zachowano w `../review/baseline/ch08/data/`.

# Rozdział 8 — odtworzenie pakietu wykonywalnego R08

11 listopada 2026 r. Status: brak techniczny pakietu rozdziału 8 zamknięty
przez rekonstrukcję i kontrolę wyników. Nie odzyskano bajtowo utraconego
modułu. Odtworzono równoważną obliczeniowo implementację według zachowanych
źródeł, parametrów i wyników. Tekst rozdziału po korekcie K01 i redakcji
globalnej pozostaje identyczny. Pilot nie był modyfikowany.

## Podstawa rekonstrukcji

| Materiał | Rola |
|---|---|
| Dokumenty 00 i governance 01–06 | Obowiązujący zakres, hierarchia źródeł, jawność założeń i kontrola wykonania |
| `CPSB_M7_Metody modelowe adaptacyjne.docx` | Kanoniczny zakres pięciu rodzin metod |
| `M7_metody_modelowe_adaptacyjne_homomorficzne_EMD_v.3.ipynb` | Generatory AR/EMD/wzorca/referencji oraz definicje YW, LMS i cepstrum |
| Zachowany `ch08_additional_information.ipynb` | Kolejność 15 doświadczeń, wywołania brakującego modułu, figury i 65 asercji |
| Bieżący tekst i dossier rozdziału | Konwencje znaków, skale, trening Wienera, obsługa reszty, próg i interpretacja wyników |
| 33 kompletne wpisy uciętego archiwum | Odzyskane z kontrolą długości i CRC; w tym raport wyników, paszporty, tabela AR i środowisko |
| `M7_komplet_po_audycie_regresyjnym.zip` | Dodatkowe potwierdzenie źródła; notebook jest identyczny z kanonicznym M7 v.3 |
| Styl figur rozdziału 7 | Odtworzenie `plotting.py`, ze zmianą identyfikatora rozdziału na 8 |

Zachowany raport wyników służy wyłącznie porównaniu po obliczeniach.
Kod eksperymentów nie odczytuje wyników referencyjnych. Obecne w pakiecie
`data/reference/` dokumentują stan pierwotny, a nie aktualne wykonanie.
Nie przejęto kursowego statusu „run-all z shimami” jako walidacji EMD.

## Co odtworzono

- `src/bspsbook/additional_information.py`: generatory, predykcja i PSD AR,
  diagnostyka rzędu, odsiewanie, pełne PyEMD, selekcja modów, korelacja
  i parowanie zdarzeń, Wiener, LMS, cepstrum i lifter.
- `src/bspsbook/plotting.py`, inicjalizację pakietu, plik zależności,
  `scripts/run_ch08.py` i `scripts/audit_ch08.py`.
- Wszystkie 15 par figur PNG/SVG, również brakujące końcowe figury 8.13–8.15.
- Wykonany notebook, bieżące wyniki, paszporty, tabelę i raport środowiska.
- `data/ch08_synthetic_inputs.npz`: 39 tablic wejść i prawdy odniesienia.
  Ten plik jest eksportem doświadczeń; nie jest potrzebny do ich ponownego
  wygenerowania. Nie zawiera danych pacjentów ani próbek nagrania mowy.

Zachowano 17 komórek kodu oraz obliczenia E8.1–E8.15. Do końcowej komórki
dodano wyłącznie eksport wygenerowanych wejść do NPZ. Metody nie zastępują
się wzajemnie: EMD wywołuje `EMD-signal==1.10.0`, DWT wywołuje
`PyWavelets==1.8.0`, a Yule–Walker `statsmodels==0.14.6`.

## Dane i decyzje wykonawcze

| Rodzina kluczy NPZ | Dane i odniesienie | Częstotliwość |
|---|---|---:|
| `ar_*` | 2400 próbek AR(4), mianownik generatora i czas | 200 Hz |
| `emd_step_*` | Sygnał do pojedynczego odsiewania i pełnej dekompozycji | 200 Hz |
| `emd_selection_*` | Zapis zaszumiony, pełny cel, wolny składnik i dwie paczki | 200 Hz |
| `emd_mixing_*` | Mieszanina oraz dwa znane źródła | 200 Hz |
| `matched_*` | Dane, wzorzec 120 próbek, początki w próbkach i środki w sekundach | 500 Hz |
| `reference_*` | Czysty PPG-podobny, kanał główny, referencja, artefakt i dwa tory | 100 Hz |
| `echo_*` | Źródło, pełna obserwacja, tor i opóźnienie 1360 próbek | 16 kHz |
| `periodic_*` | Okresowy przebieg bez echa, okres 640 próbek i czas | 16 kHz |

Amplitudy i współczynniki torów mają skalę umowną. Pola `*_time_s`
i `*_centers_s` są w sekundach, a `*_samples` i `*_starts_samples`
w próbkach. Częstotliwości, seedy i parametry są również w paszportach.
NPZ można odczytać przez `numpy.load(..., allow_pickle=False)`.

Nie zmieniono modelu paczki szumu na dostarczone nagranie WAV. Pozwala to
zachować zaakceptowane dane, wyniki i kontrolę odniesienia rozdziału.
WAV nie jest brakującym wejściem książkowych doświadczeń. Moduł M8 kursu
dotyczy innych rozdziałów i także nie jest potrzebny do tej naprawy.

Kontrola LMS sprawdza normę bieżących wag przed obliczeniem następnego
wyjścia. Historia zapisuje wagi po aktualizacji. W wariancie niestabilnym
wiersz zatrzymania 122 odpowiada czasowi 1,33 s; od niego wyjście ma NaN.
Nie obcina się wag i nie podstawia zer. To jawna granica dostępności
wyniku, zgodna z wcześniejszym raportem i tekstem rozdziału.

## Wynik audytu

| Kontrola | Wynik |
|---|---|
| Wszystkie doświadczenia | E8.1–E8.15 wykonane kolejno w nowym procesie |
| Notebook | 17 komórek kodu; 65 asercji zaliczonych; walidacja nbformat |
| Porównanie historyczne | 546 wartości liczbowych, wszystkie zgodne; liczby całkowite wymagają identyczności |
| Tolerancja liczb zmiennoprzecinkowych | `atol=1e-10`, `rtol=1e-8`; największa różnica bezwzględna około `2.99e-13` |
| Paszporty i tabela 8.2 | Identyczne bajtowo z zachowanym odniesieniem |
| Dodatkowy audyt | 18 kontroli, w tym niezależne podstawienie równań 8.4, 8.6 i 8.15 |
| Świeża kopia bez wyników | Ponowne wygenerowanie 36 artefaktów; identyczne bajty figur, wyników, NPZ, paszportów, tabeli, środowiska i notebooka |
| Tekst i odsyłacze | Ten sam tekst; 15 istniejących względnych ścieżek figur; korekta K01 zachowana |
| Figury | Przegląd wszystkich paneli: jednostki, legendy, zakresy i brak ucięcia opisów |

Porównanie z dawnymi obrazami nie było kryterium odzyskania oryginalnego
kodu. Z 12 dostępnych dawnych PNG jedenaście jest mimo to identycznych
bajtowo. Rysunek 8.4 odtworzono i sprawdzono ponownie. Bieżący komplet
ma własne odciski i przechodzi ścisłe porównanie między dwoma wykonaniami.
Szczegóły: `data/ch08_reproducibility.json` i
`data/ch08_reconstruction_manifest.json`.

## Granice potwierdzenia i dalsze decyzje

Wykonano obliczenia we właściwych bibliotekach, bez atrap i bez pobierania
danych. Próby uruchomienia rzeczywistego jądra Jupyter przez TCP i IPC
zakończyły się przed wykonaniem komórek: środowisko nie zezwala na lokalne
gniazda komunikacyjne. Z tego powodu **nie deklarujemy zaliczenia testu
interfejsu Jupyter**. Domyślne wykonanie skryptowe działa i waliduje cały
notebook; opcja `--jupyter` pozostaje do sprawdzenia na docelowym komputerze
lub CI. Raporty odróżniają oba tryby.

Rekonstrukcja nie wymaga nowej decyzji autora o metodach, danych ani
architekturze. Akceptacje bramek 1–4 pozostają w mocy. Do późniejszego
etapu należą integracja wspólnego repozytorium, kontrola Jupyter w jego
środowisku, bibliografia B8.1–B8.10 i warunki publikacji. Nie są to warunki
odtworzenia obecnych danych i figur. Nie wykonywano finalnego składu.

Dokumentację interfejsów sprawdzono pomocniczo, bez rozszerzania zakresu:
[statsmodels 0.14.6 — Yule–Walker](https://www.statsmodels.org/v0.14.6/generated/statsmodels.regression.linear_model.yule_walker.html)
oraz [PyEMD — EMD](https://pyemd.readthedocs.io/en/latest/emd.html).
Nie zastępuje to późniejszego audytu naukowej bibliografii metod.
