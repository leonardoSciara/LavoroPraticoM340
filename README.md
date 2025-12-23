# Guida all'uso del portale di creazione VM

## Avvio dell'applicazione
1. Avviare il CT e connettersi:  
   **username**: root, **password**: Password&1
2. cd /creazioneVM/
3. source .venv/bin/activate
4. python app.py
5. Aprire il browser e collegarsi al portale:  
   **http://192.168.56.10:5000**

## Creazione di una VM tramite il portale
1. Registrarsi come utente normale sul portale.
2. Effettuare una richiesta di creazione VM tramite l'interfaccia utente.
3. L’amministratore accede al portale e approva la richiesta.
4. Il sistema crea automaticamente il clone del container richiesto.
5. L’utente originale può accedere ai dati d’accesso della nuova macchina usando lo stesso account che ha inviato la richiesta.  

## Accesso SSH alla VM
1. Nei dati d’accesso vengono forniti: **IP**, **username** e **password**.
2. Per connettersi via SSH:  
   **ssh username@IP**
