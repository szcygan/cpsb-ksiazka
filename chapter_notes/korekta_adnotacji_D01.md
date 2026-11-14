# Korekta adnotacji EKG — D01-A

12 listopada 2026 r. Autor zaakceptował wariant A: oryginalne położenia
adnotacji WFDB oraz nowa rewizja zależnych wyników. Korektę wykonano
w rozdziałach 1–2 i 9–10, bez zmiany architektury książki i kodu metod.
Poprzednie dane, zamrożenie, notebooki, wyniki i figury pozostają w historii.

## Zakres i mapa źródeł

| Źródło | Rola i wykorzystanie |
|---|---|
| Dokumenty sterujące 00 oraz governance 01–06 | Zachowane zasady, architektura, styl, praca kompletnymi rozdziałami i bramki |
| Zaakceptowany pilot rozdziału 3 | Tekst i notebook zachowane bajtowo; bez redakcji |
| Kanoniczne materiały CPSB dla rozdziałów 1–2 i 9–10 | Merytoryka, doświadczenia, podział danych i parametry metod pozostają zachowane |
| `M8_pakiet_danych_v0_2.zip` | Próbki MLII, osie czasu, maski, granice wycinków i symbole; pierwotny pakiet ma SHA-256 `12f229d8b8a2213a08d57eee10eb93e05fbcf759a5974101b8010d511b65f41b` |
| [MIT-BIH Arrhythmia Database v1.0.0](https://physionet.org/content/mitdb/1.0.0/), rekordy 100, 103, 105 i 200 | Oryginalne `.hea`, `.dat`, `.atr`, odczytane niezależnie przez WFDB 4.3.0; właściwe odniesienie indeksów i symboli |
| Audyt B05-01 | Historyczne rozpoznanie rozbieżności i analiza wpływu przy stałym stanie; nie zastępuje pełnego ponownego dopasowania w D01 |

W sześciu unikalnych wycinkach rozwojowych było 694 adnotacji, z czego
640 miało inne indeksy niż oryginalne `.atr`. Zastosowano indeksy WFDB
numerowane od zera, przeliczone na lokalną oś wycinka. Nie dodawano ani
nie usuwano uderzeń. Zachowano próbki sygnału, osie czasu, maski i symbole.
Kopia `100_normal` dla rozdziałów 1–2 jest zgodna z poprawionym plikiem train.
Trzy wycinki rekordu 200 miały już zgodne 396 adnotacji; ich pliki danych
pozostają bajtowo niezmienione. Dziewięć wycinków obejmuje 297 000 próbek
sygnału i 1090 adnotacji, bez ponownego liczenia kopii `100_normal`.

Ponowna kontrola WFDB potwierdza pełną zgodność sygnału, położeń i symboli
w dziesięciu plikach fizycznych, reprezentujących dziewięć unikalnych wycinków.
Dokładne granice, adresy oryginałów, skróty i różnice poszczególnych plików:
`review/d01/annotation_changes.json` oraz
`review/d01/provenance_verification.json`. Nie przypisano historycznym
różnicom nieudokumentowanej przyczyny technicznej.

## Wykonane zmiany i najważniejsze wyniki

| Miejsce | Poprzednia rewizja | D01 |
|---|---|---|
| E1.2, zakres RR w sześciu sekundach | 0,750–0,806 s | 0,747–0,789 s |
| E2.6, chwila adnotacji w rekordzie 100 | 644,194 s | 644,203 s |
| E2.6, czasy maksimum w fazach 0/1/2 względem adnotacji | 5,56 / 8,33 / 11,11 ms | −2,78 / 0 / 2,78 ms |
| E9.6, wybrane progi energetyczny / wzorcowy | 9 / 3 | 9 / 3 po tym samym przeglądzie na rozwoju |
| E9.6, MAE lokalizacji obu torów na walidacji | 7,21 ms | 0,24 ms |
| E9.6, filtr dopasowany przy k=5 | 4 pominięcia | 3 pominięcia |
| E9.6, filtr dopasowany po odwróceniu polaryzacji | 3 pominięcia | 2 pominięcia |
| E9.7, SQI w oknie z luką, energia / wzorzec | 0,723 / 0,821 | 0,723 / 0,829; oba nadal odmawiają HR z powodu niepełności |
| E9.7, dostępne okna wzorca przy diagnostycznym SQI≥0,85 | 16/18 | 15/18 |
| E10.3, impulsy: dodatkowe detekcje energia / wzorzec | 6 / 4 | 6 / 6 |
| E10.3, luka: F₁ i liczba odniesień w masce | 0,996; 116 | 1,000; 117, w obu torach |
| E10.4, MAE HR przy progach SQI 0,55 / 0,70, energia | 30,48 / 23,75 1/min | 30,39 / 23,53 1/min |
| E10.5, wzorzec na znanym rekordzie 200: MAE czasu | 2,06 ms | 2,48 ms |
| E10.5, wzorzec: średni błąd czasu ze znakiem | −1,26 ms | −1,70 ms |
| E10.5, wzorzec: MAE RR | 4,11 ms | 4,91 ms |
| E10.6, przypadek wzorca o największym błędzie czasu | `200_noise`, 29,903 s | `200_vt`, 83,528 s; błąd nadal −44,44 ms |

Na rekordzie 200 tor energetyczny nadal ma TP/FP/FN = 387/0/1, a wzorcowy
388/0/0. Oba podają HR w 28/28 pełnych okien. Agregowane MAE HR wynoszą
odpowiednio 0,30 i 0,15 1/min. Wszystkie zapisane kryteria dydaktyczne
pozostają spełnione. Pogorszenie lokalizacji wzorca przy zachowanych
licznikach zdarzeń pokazuje, dlaczego trzeba raportować te miary oddzielnie.
Pełne liczby, także dla zakłóceń, są w CSV oraz `results/ch10_run.json`.

## Eksperymenty i figury

Ponownie wykonano całe notebooki rozdziałów, a nie wyłącznie komórki
przypuszczalnie zależne od znaczników. Wygenerowano 22 figury w PNG i SVG;
12 par zmieniło zawartość. Nazwy, numerację, ścieżki względne oraz
przeznaczenie doświadczeń zachowano. Markdown zawiera wyjaśnienia i wyniki;
notebooki pozostają odtwarzalnym uzupełnieniem.

| Rozdział i doświadczenia | Pliki w `figures/generated/` | Zmienione wskutek D01 |
|---|---|---|
| 1, E1.1–E1.6 | `ch01_01_ekg_ppg`, `ch01_02_cykle`, `ch01_03_zaklocenia`, `ch01_04_nasycenie`, `ch01_05_licznik` | `ch01_02_cykle` |
| 2, E2.1–E2.6 | `ch02_01_siatka`, `ch02_02_alias`, `ch02_03_antyalias`, `ch02_04_kwantyzacja`, `ch02_05_ekg` | `ch02_05_ekg` |
| 9, E9.1–E9.8 | `ch09_01_zdarzenia`, `ch09_02_wejscie`, `ch09_03_energia`, `ch09_04_wzorzec`, `ch09_05_tory`, `ch09_06_progi`, `ch09_07_dostepnosc` | Wszystkie poza syntetycznym `ch09_01_zdarzenia` |
| 10, E10.1–E10.8 | `ch10_01_czulosc`, `ch10_02_szum`, `ch10_03_pokrycie`, `ch10_04_test`, `ch10_05_bledy` | Wszystkie poza `ch10_04_test`, który przedstawia zachowane liczniki i pokrycie |

Wzrokowo sprawdzono wszystkie 12 zmienionych figur oraz dwa wykresy
kontrolne. Nie stwierdzono uciętych podpisów, brakujących legend ani
rozbieżności z poprawionymi wartościami i wyborem przypadku E10.6.

## Rewizja zobowiązania i historia

Stan na rekordach 100 i 103 dopasowano ponownie, a progi wybrano z tej samej
siatki wyłącznie na rekordzie 105. Wykonano tylko część rozwojową Ch10,
po czym zapisano nowy protokół `ch10-v0.2-D01`, nowe zobowiązanie i skróty
trzech tabel rozwojowych. Dopiero potem powtórzono ocenę rekordu 200.
Kolejność dokumentuje `review/d01/commitment_created_before_regression.json`.
W zobowiązaniu jawnie zapisano wcześniejszą znajomość testu. D01 nie
przywraca niezależności rekordu 200 i nie jest nową walidacją zewnętrzną.

| Składnik | Nowy zapis |
|---|---|
| Protokół | `config/ch10_protocol.json` |
| Zobowiązanie | `config/ch10_freeze.json` |
| Stan przekazania | `review/frozen_handoff_D01/` |
| Odrębne wyniki odniesienia | `review/reference_D01/` |
| Dane, wyniki i figury sprzed korekty | `review/history/I01_U03_before_D01.zip`, 108 plików z odciskami |
| Pierwotne samodzielne pakiety odniesienia | `review/baseline/`, zachowane |
| Historyczny rejestr bibliograficzny/status | `review/history/B05_01_before_D01/` |

Kod naukowy wszystkich 14 modułów `src/bspsbook` pozostaje bajtowo
identyczny. Ustawienia naukowe protokołu pozostają takie same; zmieniły się
identyfikator rewizji, odcisk nowego przekazania i jawny opis pochodzenia.
Kod komórek czterech notebooków także jest zachowany, a ich wyjścia
odpowiadają nowym danym. Uzupełniono informację o rewizji wejść.
Spośród 18 tekstów czytelniczych zmieniono cztery. Pozostałe 14, w tym
pilot, oraz oryginalny notebook pilota pozostają bajtowo zachowane.

## Audyt wykonania i jego ograniczenia

Pełne wykonanie skryptowe obejmuje 12 notebooków i 132 komórki w osobnych
procesach. `review/integration_audit.json` rozdziela zgodność z nowym
odniesieniem D01, zachowane wyniki pozostałych rozdziałów, historyczne
różnice oraz odtwarzanie w świeżej kopii bez figur i wyników. Starego
wyniku nie nadpisano w celu ukrycia różnic. Audyt obejmuje 11 994 porównań
wartości liczbowych oraz 98 względnych odsyłaczy do istniejących figur.
Powtórzenie zakończyło się poprawnie: 233/233 artefaktów jest identycznych bajtowo w tym środowisku.

Zabezpieczenie przenośności przekazania przeszło 16 prób: akceptuje
nieistotną różnicę float i zapis CRLF po kontroli, tworzy kopię i jest
idempotentne, a odrzuca zmieniony szablon, role, liczniki, progi, kod,
kontrakt i uszkodzoną referencję przed zapisem do danych aktywnych.
To symulowane próby przenośności D01, nie nowy raport z Windows.

### Zamknięcie rzeczywistego testu Jupyter — 13 listopada 2026 r.

Autor przekazał raport z Windows o statusie `passed` dla wszystkich
12 notebooków i 132 komórek. Wykonano teraz rozdziały 1–2 i 9–10,
dodatki i zadania (46 komórek). Zachowano wcześniejsze zaliczenia
niezmienionych rozdziałów 3–8 (86 komórek). Sprawdzono unikatowość
i kompletność listy, statusy, liczby komórek, skróty kodu i wszystkich
wejść oraz ciągłość dowodów wcześniejszych zaliczeń. Wszystko pasuje do D01.

Osobny raport przygotowania 9→10 jest identyczny z osadzonym w raporcie
Jupyter. Wzorzec różnił się między środowiskami najwyżej o 3,10×10⁻¹⁵,
a parametry stanu najwyżej o 2,38×10⁻¹⁴, w dopuszczonej tolerancji.
Role, liczniki, konfiguracja i wyniki kontraktu pozostały zgodne. Skrypt
zachował kopię na komputerze autora i odtworzył zobowiązany stan D01.

Dowody zapisano w `review/jupyter_protocol_D01_windows.json`,
`review/handoff_preparation_D01_windows.json` i `review/jupyter_closeout_D01.json`.
Przesłano raporty, bez wykonanych kopii notebooków i kopii bezpieczeństwa
stanu z Windows; nie przedstawia się ich jako załączonych. Starsze kopie
notebooków z `review/jupyter/` przeniesiono do historii, a wyniki skryptowe
D01 i figury pozostają zachowane. Poprzednia nieudana lokalna próba startu
jądra jest historyczna. Kontrola techniczna jest zamknięta; nie trzeba
ponawiać testu. Nie zmieniano metod ani nie uzyskano nowej niezależnej
walidacji na innym rekordzie.

## Decyzje, bibliografia i styki rozdziałów

D01 jest wykonane i nie wymaga kolejnej decyzji autora. Nie zmieniano
metod, tolerancji 50 ms, podziału rekordów ani zakresu książki. Drobne
decyzje redakcyjne obejmują zaokrąglenia zgodne z dotychczasowymi tabelami,
doprecyzowanie lokalnej osi E1.2 i rozróżnienie sygnału CPSB od oryginalnych
adnotacji WFDB w atrybucji. Zachowano numery doświadczeń, równań i figur.

Podział treści pozostaje taki sam: 1–2 wyjaśniają pomiar i próbkowanie,
9 projektuje tor i wybiera ustawienia, a 10 interpretuje jego ocenę.
Nie dodano nowych powtórzeń definicji. Wcześniej odnotowane styki F₁,
maski i SQI między 9 a 10 pozostają zagadnieniem redakcji globalnej,
bez potrzeby zmiany architektury.

Korekta danych usuwa blokadę trzech punktów B2.4, B9.1 i B10.4.
Ich status to teraz CZĘŚCIOWO: formalne cytowanie, pełne sprawdzenie
zakresu źródeł i kwestie praw pozostają do ukończenia. Pozostałe tematy
do weryfikacji bibliograficznej obejmują metryki i tolerancję dopasowania,
skalowanie MAD, detekcję energetyczną i wzorcową, wpływ morfologii oraz
różnicę między szumem białym a rzeczywistymi artefaktami. Wartości
liczbowe D01 są wynikami tego studium, nie twierdzeniami o skuteczności
klinicznej ani o całej bazie MIT-BIH.

D02 (potwierdzenie uprawnionych) i D03 (wybór licencji własnych utworów)
pozostają otwarte. Zachowano odrębne warunki danych i zależności, bez
nadawania licencji autorowi lub wydawcy. Bramka 5 pozostaje w toku.
