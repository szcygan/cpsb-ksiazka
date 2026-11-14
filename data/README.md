# Wejścia obliczeń

Wycinki EKG pochodzą z publicznej bazy MIT-BIH Arrhythmia Database v1.0.0
(MLII, mV, 360 Hz). Pochodzenie i licencja: `../THIRD_PARTY_NOTICES.md`.
`ch01_manifest.json` opisuje dane rozdziałów 1–2; manifesty CSV opisują
podział 100/103 — dopasowanie, 105 — wybór parametrów, 200 — znany test.
NPZ zawierają próbki, czas, maski, adnotacje i metadane, bez danych
identyfikujących osoby. Indeksy adnotacji są zgodne z korektą D01.

`ch09_fitted_state.npz` oraz `ch09_run.json` są historycznym zamrożonym
przekazaniem do rozdziału 10. Po ponownym wykonaniu rozdziału 9 skrypt
`prepare_frozen_handoff.py` weryfikuje zgodność i przygotowuje regresję.
Powtórne użycie rekordu 200 nie jest nową niezależną walidacją.
Dane syntetyczne powstają z ustalonych seedów bez pobierania z sieci.
