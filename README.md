# Luci di Casa Mobile

Interfaccia web locale per controllare lampade Shelly e Tapo da Python, anche su Android con Termux.

## Avvio su Termux

```bash
pkg install python curl git
python -m pip install --upgrade python-kasa anyio tzdata
git clone https://github.com/giacomoubaldi/LuciDiCasaMobile.git
cd LuciDiCasaMobile
bash start.sh
```

Il browser del telefono si apre automaticamente. Termux mostra l’indirizzo locale e quello da condividere con gli altri dispositivi sullo stesso Wi-Fi. Lascia il server attivo; Ctrl+C lo arresta. La rete deve consentire comunicazioni tra dispositivi.

## Funzioni della v13

- Comandi individuali o di gruppo, colori, bianco e luminosità.
- Scene salvate ed effetti autonomi supportati dalle lampade.
- Analisi del ritmo da microfono, audio condiviso o file, eseguita nel browser.
- Storico dei consumi e integrazione Tapo tramite python-kasa.
- Dopo tre tentativi falliti, una lampada non raggiungibile viene esclusa; comandi ed effetti continuano sulle altre. Riaccendi la lampada e aggiorna la pagina per riprovare.

La configurazione iniziale usa Shelly `192.168.1.7` e Tapo `192.168.1.8`; adattala ai tuoi dispositivi. Per Tapo configura l’account dal pulsante Account Tapo. Le credenziali sono salvate nella home di Termux, fuori dal repository.

## Limiti

Il server locale non richiede password: chi può raggiungerlo può comandare le lampade. Non esporlo direttamente a Internet.

Microfono e cattura audio richiedono un contesto sicuro nel browser: sul telefono usa il link `http://127.0.0.1:8000`. L’analisi del ritmo non è ancora garantita a schermo spento o con il browser in background.

Le istruzioni dettagliate e lo storico degli aggiornamenti sono in [README.txt](README.txt).
