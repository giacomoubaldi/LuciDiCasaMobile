AGGIORNAMENTO LAMPADE NON RAGGIUNGIBILI
Dopo 3 tentativi di lettura falliti, la lampada è esclusa fino al refresh
completo della pagina. Gli aggiornamenti automatici non la riattivano.
Comandi, effetti e scene saltano la lampada esclusa e continuano sulle altre.
Le caselle delle lampade escluse sono disabilitate. Per riprovare, riaccendi
la lampada e aggiorna la pagina nel browser. Lo stato di esclusione è
condiviso dai browser collegati allo stesso server.
Una lampada su OFF nell’app ma alimentata rimane raggiungibile e controllabile.
Le scene salvate mantengono i dati delle lampade escluse quando applicate.

AGGIORNAMENTO ACCESSO WI-FI
Avvio su Termux: bash start.sh
Il terminale mostra il link locale e quello da condividere sullo stesso Wi-Fi.
Il server ascolta su 0.0.0.0:8000 anche avviando python luci_di_casa_mobile.py.
Lascia Termux e il server attivi; Ctrl+C arresta il server.
L’indirizzo può cambiare quando ti riconnetti: riavvia per leggerlo di nuovo.
Se Android impedisce il rilevamento, consulta i dettagli della rete Wi-Fi.
Per il rilevamento tramite API puoi facoltativamente installare Termux:API
(app Android della stessa fonte di Termux) e il pacchetto pkg install termux-api.
I dispositivi devono essere sulla stessa rete senza isolamento client/rete ospiti.
Chi può raggiungere il server può comandare le lampade, senza password.
Da HTTP tramite IP, microfono e cattura audio possono essere bloccati dal browser;
sul telefono usa il link 127.0.0.1. Il caricamento di un brano resta disponibile.
Se la porta 8000 è occupata, arresta prima la vecchia istanza del progetto.

Luci di Casa Mobile per Termux

Installazione:
  pkg install python curl
  python -m pip install --upgrade python-kasa anyio

Metti luci_di_casa_mobile.py, index.html e start.sh nella stessa cartella.
Se esiste già una sottocartella static, aggiorna invece static/index.html.

Ferma il vecchio server prima di avviare la nuova versione:
  pkill -f '[l]uci_di_casa_mobile.py'

Avvio manuale dalla cartella del progetto:
  python luci_di_casa_mobile.py

Apri http://127.0.0.1:8000 nel browser.
Avvio rapido: chmod +x start.sh e poi ./start.sh

UTILIZZO E CONSUMI
Il server registra ogni 15 secondi output, apower e aenergy.total.
Nella scheda della lampadina trovi potenza, tempo acceso oggi e Wh registrati.
Utilizzo e consumi apre grafico della potenza delle ultime 24 ore, consumi
per oggi/7/30 giorni e tabella dei tempi senza dati.
La tariffa configurabile parte da 0,30 €/kWh: sostituiscila con la tua.

Lo storico è conservato per 90 giorni in luci_usage.sqlite3, accanto al
Python. Non cancellare questo file e mantieni il progetto in una cartella
scrivibile. La registrazione comincia al primo avvio di questa versione.
Il server deve rimanere attivo, anche se puoi chiudere la pagina browser.
In Termux puoi usare termux-wake-lock e disattivare l'ottimizzazione della
batteria per Termux; Android potrebbe comunque interrompere il processo.

Il tempo acceso è stimato dai campioni. Intervalli oltre 45 secondi senza
letture sono esclusi da ore e consumi: non vengono considerati luce spenta.
Il consumo registrato può quindi essere parziale. Se il contatore si azzera,
si integra la potenza media tra le due letture, se disponibile.
Le giornate seguono il fuso orario del telefono; imposta quello corretto.
I dati di standby inclusi dipendono da ciò che misura la lampadina.
Configurazione e scene precedenti vengono mantenute.

EFFETTI AUTONOMI SULLA SHELLY
Questa versione contiene anche shelly_effects.js e install_effetti.py:
mettili nella stessa cartella di luci_di_casa_mobile.py.
Ferma il vecchio server prima di sostituire i file; elimina i vecchi processi
Python ancora attivi, per evitare comandi di colore concorrenti.

Caricamento consigliato, da fare una sola volta dalla cartella del progetto:
  python install_effetti.py
Oppure soltanto una lampadina:
  python install_effetti.py --ip 192.168.1.7

L'installazione riutilizza lo slot di "Luci di Casa - Dance v1", se presente,
rinominandolo in "Luci di Casa - Effects v1". Altrimenti crea un nuovo slot.
Non modifica script di altri nomi. Dopo l'installazione resta inattivo.
Il primo PLAY può anche installarlo automaticamente se manca.
Per aggiornare una copia già presente esegui nuovamente install_effetti.py.
I vecchi comandi dance_shelly.py non servono più dopo la conversione.

Avvia quindi il server: python luci_di_casa_mobile.py
Dall'app scegli le lampadine e un effetto, quindi premi PLAY.
Lo script contiene Happy, Dance, Relax, Sunset, Ocean, Aurora, Fireplace,
Pulse, Party e Candle. L'app invia selectEffect(nome) tramite Script.Eval.
Il firmware richiede transizioni >= 0,5 secondi: gli effetti veloci usano
un intervallo minimo di 550 ms. Le lampadine eseguono i cicli autonomamente;
più lampadine non sono sincronizzate con precisione tra loro.

Chiudere la pagina o Termux NON ferma gli effetti.
STOP ferma gli effetti sulle lampadine selezionate, lasciando l'ultimo colore.
Bianco, colore, luminosità, ON/OFF e applicazione di una scena fermano prima
lo script sulle lampadine interessate, poi applicano il nuovo comando.
Leggere lo stato, lo storico o salvare una scena non interrompe l'effetto.
Riavviare il server non interrompe l'effetto: lo stato viene letto dalla Shelly.
Se Termux è fermo, riaprilo per inviare il comando successivo dalla nostra app.
L'avvio automatico al ritorno della corrente resta disabilitato.

La registrazione dello storico dei consumi richiede comunque Termux attivo.

TAPO L535E - LAMPADA CUCINA
La lampadina 192.168.1.8 viene aggiunta automaticamente alla stanza Cucina.
Se esiste il gruppo Casa, viene aggiunta anche lì. I dispositivi e le scene
Shelly già configurati vengono conservati.

Mantieni tapo_adapter.py accanto al backend Python.
Installa le dipendenze sul dispositivo che esegue il server:
  python -m pip install --upgrade python-kasa anyio
Sul laptop usa python3.10 o il comando Python del tuo ambiente.

In Tapo attiva Io/Profilo > Servizi di terze parti > Compatibilità con terze
parti, come verificato con questo firmware.
Nell'app Luci di Casa premi Account Tapo, inserisci email e password
proprietarie e premi Verifica e salva. Il salvataggio avviene soltanto dopo
una connessione riuscita. Le credenziali vengono salvate separatamente dalla
configurazione, in ~/.luci_tapo_credentials.json con permessi 600.
Non vengono restituite all'interfaccia né incluse nel pacchetto del progetto.
Si possono anche usare KASA_USERNAME/KASA_PASSWORD nel processo del server;
una configurazione salvata dall'app ha precedenza sulle variabili ambiente.

Comandi disponibili: ON/OFF, luminosità, bianco 2700-6500 K nell'interfaccia,
spettro colori e scene. La Tapo accetta anche 2500 K tramite la propria API.
Per le azioni della stanza seleziona le lampadine nella sezione Controllo
stanza. Per gli effetti usa le caselle nella sezione Effetti autonomi.
Le selezioni rimangono durante gli aggiornamenti della pagina.

Il menu effetti mostra quelli compatibili con tutte le lampadine selezionate:
- soltanto Shelly: tutti i dieci effetti personalizzati;
- Tapo, sola o insieme a Shelly: Party e Relax.
Sulla Tapo Party e Relax sono le versioni integrate dal produttore; sulla
Shelly sono quelle personalizzate. Non sono identiche né sincronizzate.
Non carichiamo script sulla Tapo e non emuliamo gli altri effetti con Termux.
Un comando manuale interrompe l'effetto Tapo prima di applicare il nuovo stato.

Per Tapo vengono letti direttamente tempi e consumi mediante
get_device_usage. La potenza istantanea non è disponibile da questo endpoint.
La Shelly mantiene i grafici di potenza e consumi già presenti.

AGGIORNAMENTO CONSUMI TAPO
La risposta verificata di get_device_usage contiene:
- time_usage today/past7/past30 in minuti;
- power_usage today/past7/past30 in Wh;
- eventuali campi today_mwh/past7_mwh/past30_mwh in mWh, preferiti se presenti.

La scheda mostra i totali di oggi riportati dalla Tapo. Lo storico permette
oggi/7/30 giorni, con costo stimato dalla tariffa impostata.
La lettura viene aggiornata al massimo una volta al minuto, senza fermare
gli effetti. Il dispositivo mantiene i propri totali anche con Termux chiuso.
La prossima lettura li recupera; i giorni intermedi non vengono ricostruiti
artificialmente dai totali aggregati.

Il grafico giornaliero salva l'ultima lettura di ogni giorno usando la data
locale comunicata dalla Tapo. Giorni senza letture = sconosciuti, non zero.
Se il server era fermo a fine giornata, una lettura di un giorno passato può
essere parziale. Non interpretare la somma delle barre come il riepilogo
Tapo 7/30 giorni: quest'ultimo arriva direttamente dal dispositivo.

saved_power non è il consumo della lampadina e non viene sommato ai Wh usati.
Non deduciamo da get_device_usage che si tratti di una misura hardware:
l'interfaccia usa l'etichetta "energia riportata dalla Tapo".
Il formato verificato non fornisce watt istantanei: niente potenza inventata.
Aggiornamento senza reinstallare gli effetti Shelly né reinserire le
credenziali già salvate. Il database esistente viene aggiornato automaticamente.

GRAFICI DI ENERGIA OGNI 15 MINUTI - SHELLY E TAPO
Apri Utilizzo e consumi: il grafico a 15 minuti è disponibile per entrambe.
Per Tapo usa il selettore data. Per Shelly il dettaglio interno è del giorno
corrente. Scorri orizzontalmente per vedere tutti gli intervalli.
Ogni barra è un incremento di energia in Wh, non una potenza in W.
La tabella espandibile mostra il valore e la copertura di ciascun intervallo.
Barre tratteggiate = dati parziali; vuoti = dati assenti o intervalli futuri.
Uno zero è un incremento osservato pari a zero e viene mantenuto.

Shelly: storico raccolto dallo script nella lampadina; vedi sezione seguente.
Se il monitoraggio interno non è disponibile, si usano i campioni locali.
Tapo: incrementi del contatore giornaliero letto ogni minuto; i campioni
necessari iniziano con questa versione. Non si può ricostruire il passato
in intervalli di 15 minuti dai soli totali oggi/7/30 giorni.

Se il contatore Tapo torna indietro o cambia giorno, l'intervallo viene
escluso. Letture distanti oltre 2 minuti non vengono interpolate per Tapo;
per Shelly resta il limite di 45 secondi.
A cavallo delle frontiere dei 15 minuti, gli incrementi tra due letture
vengono ripartiti proporzionalmente al tempo.
La risoluzione di 1 Wh del firmware Tapo può produrre barre a zero e salti:
non sono necessariamente variazioni reali improvvise del consumo.
Solo per Tapo, Termux deve restare attivo per raccogliere il dettaglio temporale.
I totali aggregati Tapo restano invece recuperabili dalla lampadina.


STORICO AUTONOMO SHELLY - VERSIONE 6
Lo script separato "Luci di Casa - Usage v1" salva nella lampadina:
- 30 giorni di energia e tempo acceso, giorno per giorno (oggi incluso).
- 7 giorni di energia e tempo acceso, a fasce di 2 ore (oggi incluso).
- Il giorno corrente di energia e tempo acceso, ogni 15 minuti.
Ogni valore è relativo al suo giorno/intervallo, non una somma progressiva.
Le somme dei giorni consentono di ottenere i consumi del periodo.

INSTALLAZIONE
Sostituisci i file dell'app con quelli dello ZIP, preservando luci_usage.sqlite3.
Dalla stessa cartella, con la Shelly collegata alla rete:
    python install_monitoraggio.py 192.168.1.7
    python luci_di_casa_mobile.py
Il backend prova anche a installare e avviare il logger automaticamente quando
legge una Shelly. La Tapo non viene modificata. Il firmware Shelly deve essere
almeno 1.5; in caso contrario viene mostrato l'errore e serve aggiornare il
firmware dall'interfaccia Shelly. Python >=3.9; su Termux, se mancano i fusi:
    pip install tzdata
Lo script usa il fuso configurato nella Shelly (preferibilmente Europe/Rome).
Verifica data, ora e fuso nell'interfaccia Shelly prima dell'installazione.
L'orologio deve essere sincronizzato: in attesa di NTP non inventa timestamp.

FUNZIONAMENTO
Il logger parte automaticamente all'alimentazione e rimane separato dagli
effetti: nuovi effetti, bianco, luminosità e OFF dall'app non lo arrestano.
Dopo l'installazione puoi chiudere app e Termux. Quando riapri da un altro
dispositivo nella stessa rete, l'app sincronizza lo storico dalla lampadina.
La sincronizzazione avviene circa ogni minuto, senza sommare due volte dati
locali e remoti. Il database fa da cache; la fonte dello storico è Shelly.
Il grafico della potenza istantanea W resta invece un grafico di campioni
locali: non viene salvato da questo script. Energia Wh e tempo sì.

L'energia è la differenza del contatore RGBCCT.aenergy.total. Il tempo ON è
campionato ogni 10 secondi e ai cambi di accensione. L'energia tra letture
che attraversano un intervallo è distribuita proporzionalmente al tempo.
Dati precedenti all'installazione, intervalli senza orologio, salti di ora,
reset del contatore e interruzioni oltre 30 secondi non sono ricostruiti.
Sono indicati come assenti/parziali, mai come consumi nulli.
Nel cambio d'ora autunnale i valori delle fasce locali ripetute sono sommati;
la copertura delle singole fasce in quel giorno va letta come indicativa.

PERSISTENZA E CAPACITÀ
Formato compatto: 11 chiavi private Script.storage, ciascuna <=1024 byte.
I dati più vecchi vengono sostituiti automaticamente, con le tre risoluzioni
indicate. Il dettaglio di ieri a 15 minuti lascia posto al dettaglio di oggi;
restano le fasce di 2 ore della settimana e i totali dei 30 giorni.
Checkpoint permanente ogni 15 minuti, mentre l'app può leggere dati correnti
in RAM. Se togli corrente, possono perdersi fino a circa 15 minuti recenti;
i checkpoint già salvati sopravvivono. Luce OFF via app lascia il dispositivo
alimentato e il monitoraggio attivo. Senza alimentazione il logger non gira.
Reinstallare nello stesso slot conserva lo storico. Non cancellare lo script:
la cancellazione o il ripristino di fabbrica cancellano il suo Script.storage.

COLLAUDO
Verificati con simulatori: contatori, mezzanotte, retention, OFF, limite delle
chiavi, checkpoint e riavvio, installazione e verifica codice, due client con
DB distinti, isolamento dagli effetti, conversione dei fusi e dei grafici.
Non è stato possibile provare questa versione direttamente sulla lampadina
nella tua rete: il comando di installazione verifica il codice caricato e
controlla che lo script risulti pronto; gli errori vengono mostrati nell'app.

CORREZIONE COMPATIBILITÀ SHELLY - VERSIONE 7
Sostituiti Array.concat e Array.slice nel logger con cicli espliciti, per
interpreti Shelly che non espongono queste funzioni. Per aggiornare lo script
già presente, dalla cartella dell'app esegui:
    python install_monitoraggio.py 192.168.1.7
Poi riavvia luci_di_casa_mobile.py. Il logger viene aggiornato nello stesso
slot, preservando lo storico persistente eventualmente già salvato.

MUSICA DAL MICROFONO - VERSIONE 8
Usa il microfono del telefono o PC da cui apri l'interfaccia. Avvia Python
sullo stesso dispositivo e apri http://localhost:8000 (anche 127.0.0.1 è
normalmente accettato). Su Android usa il browser, non una webview priva di
permessi audio. Non serve installare librerie audio Python o Termux:API.
Nel browser consenti il microfono quando richiesto.

Seleziona le lampadine con le caselle degli effetti, poi premi
"Avvia microfono" nella scheda Musica. Regola sensibilità e luminosità
massima; la selezione viene acquisita all'avvio. Per cambiare lampadine
ferma e riavvia il microfono. La rilevazione confronta l'energia dei bassi
35-220 Hz con una media adattiva: è una reazione ai transienti, non un
riconoscitore perfetto di BPM. Musica, voci e altri suoni possono influenzarla.

L'audio è elaborato localmente con Web Audio: nessun file audio viene scritto
e nessun campione audio viene inviato al server. Viaggiano soltanto valori
di colore/luminosità. L'analisi gira continuamente, ma le richieste sono
seriali e limitate: circa 650 ms per Shelly, 1200 ms se include Tapo; attende
comunque la risposta precedente, quindi può essere più lenta. Shelly usa
transizioni di 0.5 s. Lo scopo è una reazione morbida, non strobo preciso.
La latenza effettiva dipende da microfono, browser, rete e lampadine.

Il browser deve restare aperto in primo piano, con schermo attivo. Passando
in secondo piano, chiudendo la pagina o premendo Ferma, il microfono viene
rilasciato e non vengono inviati nuovi frame. Rimane l'ultimo colore. I
comandi manuali, le scene e gli effetti autonomi interrompono Musica. Un
comando da un altro client interrompe la sessione sui dispositivi coinvolti.
Il logger Shelly è separato e continua. Gli effetti autonomi esistenti
continuano a funzionare senza browser, come prima.

HTTP su un IP di rete 192.168.x.x non è un contesto sicuro per il microfono:
usa localhost sul dispositivo che esegue Python oppure un deployment HTTPS.
Se non vedi la richiesta di permesso, verifica le autorizzazioni microfono
del browser nelle impostazioni Android/Ubuntu. Le cuffie Bluetooth possono
cambiare il microfono predefinito e influenzare la qualità dell'analisi.

Aggiornamento: sostituisci i file conservando luci_usage.sqlite3 e riavvia
Python. Non serve reinstallare gli script Shelly per aggiungere Musica.
Su Termux installa tzdata se non è già presente:
    python -m pip install tzdata

Verificato con microfono simulato: rilevazione colpi, frequenza delle richieste,
stop e rilascio risorse, permesso negato, esclusione frame duplicati/scaduti,
separazione sessioni, invio Shelly/Tapo, e prevalenza del comando manuale
su un frame musicale già in corso. Nessun test dal vivo della sincronizzazione
audio con le lampadine della tua rete: serve la prima prova sul dispositivo.

RILEVATORE MUSICALE ADATTIVO - VERSIONE 9
Il colore ora reagisce agli aumenti di energia spettrale tra 35 e 8000 Hz,
includendo bassi, medi e alti. Non richiede più un basso forte sopra una
soglia assoluta fissa. La sensibilità regola sia l'accesso del segnale debole
sia la soglia adattiva e la risposta agli attacchi. Attende 250 ms iniziali
per assestarsi e separa i colpi di almeno 220 ms. Un suono uniforme non
produce cambi periodici artificiali: servono variazioni reali.
La barra resta un'indicazione del livello audio; il contatore misura gli
attacchi rilevati, non i BPM. Il limite di invio alle lampadine resta quello
della versione precedente: non ogni colpo può produrre un comando distinto.
Sostituisci i file e riavvia Python; non reinstallare gli script Shelly.
Verificati con segnali sintetici: silenzio, tono uniforme, attacchi nei medi
e negli alti con bassi deboli, sensibilità e rilascio delle risorse audio.

TRE SORGENTI MUSICALI - VERSIONE 10
Nella scheda Musica e luci puoi scegliere:
1. Microfono: analisi del suono ambientale, come nella versione 9.
2. Audio interno: cattura tramite selettore di condivisione del browser.
   Scegli una scheda che sta riproducendo musica e abilita Condividi audio.
   Torna alla pagina Luci di Casa dopo la scelta per mantenere attiva l'analisi.
   Sono richiesti localhost/HTTPS e supporto getDisplayMedia. La possibilità
   di condividere audio di scheda, finestra o sistema dipende da browser e
   sistema operativo; non è garantita su Ubuntu e spesso manca su Android.
   Se la funzione manca o lo stream non include audio viene mostrato l'errore
   e tutte le tracce eventualmente aperte vengono chiuse. Il video richiesto
   dal selettore non viene elaborato, salvato o trasmesso.
3. Canzone dal dispositivo: scegli un MP3, WAV o un altro formato che il
   browser riesce a leggere. Avvia musica apre un lettore con play/pausa,
   posizione e volume. Il file resta locale: nessun upload sul server.
   Il lettore viene collegato direttamente al rilevatore, senza microfono.
   Non è possibile scegliere i download protetti dell'app Spotify.

Cambiare sorgente o file interrompe l'effetto in corso. A fine canzone la
sessione viene chiusa; puoi premere Avvia musica per riascoltarla. Durante
la riproduzione il refresh automatico della pagina è sospeso, evitando di
ricreare il lettore ogni 10 secondi. Tieni la pagina in primo piano.
Il rilevatore su bassi/medi/alti, sensibilità e luminosità è comune alle tre
sorgenti. Gli script effetti e storico Shelly non richiedono aggiornamenti.
Sostituisci i file conservando il DB e riavvia Python. Ricarica il browser.

Test simulati: microfono, file locale e rilascio URL/lettore, cattura interna,
assenza della funzione e dello stream audio, detector e comandi manuali.
Compatibilità della cattura interna e codec dei file da verificare sul tuo
browser reale. In particolare Firefox potrebbe condividere video senza audio.

MUSICA PIÙ DINAMICA - VERSIONE 11
Invii separati per lampadina: Tapo non blocca più Shelly. Una sola richiesta
in corso per ciascuna, senza coda di colpi vecchi: se la rete è lenta si usa
il colore più recente al prossimo invio disponibile.
Il limite minimo richieste è 140 ms Shelly, 500 ms Tapo: sono limiti software,
non una promessa di quella frequenza effettiva. La latenza hardware resta.
Il nuovo contatore Cambi inviati mostra le richieste completate con successo
(totale delle lampadine), distinto dal numero di colpi rilevati.

Colpi separati da almeno 115 ms (prima 220 ms). Gli impulsi luminosi durano
circa 200 ms invece di 550 ms. Gli attacchi forti producono salti di tonalità
e luminosità maggiori, quelli deboli variazioni più piccole. Si invia appena
il canale è disponibile, entro i limiti, oppure quando cambia la luminosità;
un heartbeat mantiene viva la sessione nei periodi senza variazioni.
Shelly non riceve più transition_duration=0.5 per i frame musicali: il
parametro viene omesso, senza usare lo zero che il tuo firmware rifiuta.
Un'eventuale transizione preconfigurata nel dispositivo può ancora influire
e va verificata dal vivo, quindi non garantiamo un cambio istantaneo.
Tapo riceve un solo comando HSV per frame, senza spegnere di nuovo l'effetto,
riaccendere o rileggere tutta la telemetria a ogni colpo. Le letture normali
continuano separatamente e il logger Shelly rimane attivo.

Aggiornamento: sostituisci tutti i file (incluso tapo_adapter.py), conserva
il database, riavvia Python e ricarica il browser. Nessuna reinstallazione
degli script Shelly. Microfono/audio interno/file restano disponibili.
Test simulati: più eventi con attacchi veloci rispetto a quelli lenti, Tapo
lenta in parallelo senza bloccare Shelly, frame Tapo con una sola scrittura,
stop manuale durante RPC, sorgenti audio e memoria Shelly. Serve una prova
con musica vera sulle tue lampadine per valutare la resa e la latenza.
