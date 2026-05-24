# PyggyBank — note architetturali per il refactor in blocco

> Raccolta delle osservazioni di Giuseppe (1966bc) mentre rilegge il codice 3.0.

## Stato
- ✅ N6 — main ↔ dati: MVP (models/Controller/MainPresenter + MainView), lista virtuale, DI
- ✅ N7 — God Object: export XLS estratto in `exporters.XlsExporter`
- ✅ N2/N3 — dialoghi via Controller (dati per nome, dict); rinominati
  `update_filter`→`lookup_editor`, `filters`→`lookup_manager`
- ✅ N1 — SQL fuori dal codice: `queries.json` caricato da Engine
- ⏳ N4/N5 — filtri sovraccarichi (combo polimorfica, stack filtri)
- ⏳ N7-bis — `GeneratePDF` pesca ancora da `app.engine` (nomi/logo)
- ⏳ docs/test: README 3.0, espandere pytest

## Note raccolte

### N1 — SQL cablato in `Engine.dict_queries`
Le query SQL sono hard-coded in `engine.py`. Il dizionario come *struttura* va bene, ma
i valori (SQL) non devono stare nel sorgente.
**Proposta:** esternalizzare in `queries.json` (dato, non codice), caricato a runtime con
fallback sicuro. Coerente con `config.ini` / `label_templates.json` di inventarium.

### N2 — `update_data.py` è "osceno"
`GetValue()` ritorna una **tupla posizionale di 11 elementi** il cui ordine deve combaciare
*implicitamente* con l'ordine delle colonne di `events` (lo consuma `build_sql`). La view
"conosce" lo schema del DB → accoppiamento presentazione↔persistenza. `OnOpen()` fa la
mappatura inversa a mano (due punti da tenere in sync). Inoltre `__init__` mischia creazione
widget e layout; default `'No'`; rosso cablato.

### N3 — `update_filter.py` non dice cosa fa
Editor **generico** riusato per due entità (categorie e fornitori), pilotato da stringhe
`table`/`pk`. Il nome "filter" è fuorviante: in realtà è un **editor CRUD di una tabella di
lookup** (nome + flag abilitato). Accesso posizionale opaco (`self.values[0/1/2]`).

### N4 — Troppe poche UI: un solo dialog "fa tutto"
`update_data` è un dialog monolitico che gestisce sia insert sia edit, e tutti i campi
dell'evento in un'unica maschera. La granularità delle schermate è troppo bassa: poche UI,
ognuna sovraccarica di responsabilità.
> Da confermare l'intento: vuoi **più schermate focalizzate** (separare add/edit, o
> raggruppare i campi), oppure è la *sovraccaricabilità* di quell'unica maschera il problema?

### N5 — La combo della main fa troppe cose / troppi filtri
Nella main `cbFilter` è **una sola combo** il cui significato cambia in base alla RadioBox
(None/Categories/Suppliers): stesso widget, semantica diversa. In più i filtri sono tanti e
mescolati: 3 checkbox tri-stato (Flow/Settled/Enabled) + RadioBox + combo + data inizio, che
confluiscono tutti in `get_args()`. Il meccanismo di filtro è sovraccarico e poco leggibile.

### N6 — La UI parla direttamente con DBMS  [CONFERMATO]
Concordato con Giuseppe: le view chiamano `wx.GetApp().engine.read/write` con SQL e argomenti,
senza un layer di mezzo. È la causa radice di N1–N3.

### N7 — `MainFrame` è un God Object
La main fa troppe cose: display lista, filtri, CRUD (add/edit/delete), anteprima/stampa PDF,
export XLS. L'export XLS in particolare è ~40 righe di logica openpyxl **inline dentro
`OnClick`**: business logic dentro la view. Una classe sola con troppe responsabilità.
Chiarisce N4: l'orientamento è verso lo **split delle responsabilità**, non solo cosmesi.
> Target: la frame *orchestra*; export/report stanno in servizi dedicati che lavorano su
> dati del Controller (es. `Exporter.to_xlsx(rows)`), non dentro l'handler di un bottone.

## Tema architetturale emergente
Tre problemi di fondo, ricorrenti:
1. **Strutture/SQL cablati nel codice** invece che dati esterni (N1).
2. **Dominio/persistenza filtrano nella GUI** (N2, N3, N6): le view conoscono ordine colonne,
   costruiscono argomenti, incorporano SQL, parlano direttamente a `DBMS`. [CONFERMATO]
3. **Responsabilità sovraccariche nella GUI** (N4, N5, N7): la main è un God Object (CRUD +
   filtri + PDF + XLS); un dialog fa tutto; una combo cambia semantica; troppi filtri
   mescolati; business logic (export) dentro gli event handler.

Manca un **livello di dominio/Controller** tra le view wx e `DBMS`. In inventarium esiste
(`Engine = DBMS + Controller + Tools + Launcher`); qui la GUI parla direttamente al DB.

## Direzione target (bozza)
```
view wx  ──>  Controller (metodi di dominio, dati per nome)  ──>  DBMS (SQL, connessione)
                     │
                     └── SQL da queries.json (data-driven)
```
- Le view chiamano metodi tipo `controller.save_event(record: dict)`,
  `controller.get_flows(filters)`, `controller.list_categories()` — **mai** SQL o tuple.
- `Controller` costruisce gli argomenti e usa `DBMS`/`build_sql`; le query stanno in `queries.json`.
- Nomi onesti per le entità anagrafiche (lookup) al posto di "filter".
- GUI: separare i filtri (no combo polimorfica) e ripensare la granularità delle maschere.

## TODO già in coda (post-refactor)
- Suite pytest sul livello dati.
- README 3.0 + screenshot.
