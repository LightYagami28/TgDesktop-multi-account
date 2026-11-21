# Domande frequenti

## A cosa serve TgDesktop-multi-account?

Permette di compilare o eseguire Telegram Desktop con un numero esteso di
account simultanei configurabili (fino a 100), mantenendo profili e sessioni
rigorosamente isolati.

## Quali sono i requisiti?

- Python 3.13 o 3.14 (richiede esclusivamente librerie standard).
- Docker (opzionale, consigliato per la compilazione riproducibile dei sorgenti
upstream).

## Come si eseguono i test?

```bash
python -m unittest test_telegram_maker.py -v
```

## Ci sono dipendenze esterne?

No, il progetto è interamente scritto in Python puro senza pacchetti `pip`
aggiuntivi.
