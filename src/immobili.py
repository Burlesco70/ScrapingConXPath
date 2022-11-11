# Versione finale (?)

import requests
import lxml.html as html
import pandas as pd
from datetime import date
import typer
from typing import List
import time

# Valori validi per il sito immobiliare.it
URL_SITO = "https://www.immobiliare.it/"
ELEMENTI_PER_PAGINA = 25
XPATH_NUMERO_PAGINE = '//div[@class="in-pagination__item hideOnMobile in-pagination__item--disabled"][2]/text()'
XPATH_NUMERO_ANNUNCI = '//div[@class="in-searchList__title"]/text()'
XPATH_TITOLI = '//a[@class="in-card__title"]/text()'
XPATH_PREZZI = '//li[@class="nd-list__item in-feat__item in-feat__item--main in-realEstateListCard__features--main"]/text() | //li[@class="nd-list__item in-feat__item in-feat__item--main in-realEstateListCard__features--main in-realEstateListCard__features--mainText"]/text() | //div[@class="in-realEstateListCard__features--range"]/text()'
XPATH_DESCRIZIONI = '//p[@class="in-realEstateListCard__descriptionShort"]/text()|//p[@class="in-realEstateListCard__description"]/text()'


def get_numero_pagine(url_padre: str) -> int:
    """
    Funzione privata, al momento specifica per il sito immobiliare.it, che verifica il numero di pagine
    da analizzare, dato un url_padre. Usata da get_urls.
    Se il numero delle pagine non è presente, viene calcolato in base al numero di elementi
    NOTA: come massimo, il sito limita la ricerca a 80 pagine, 2000 elementi
    """
    r = requests.get(url_padre)
    home = r.content.decode("utf-8")
    parser = html.fromstring(home)
    np = parser.xpath(XPATH_NUMERO_PAGINE)
    if np:
        numero_pagine = int(np[0])
    else:
        numero_el = parser.xpath(XPATH_NUMERO_ANNUNCI)
        if numero_el:
            if numero_el[0].startswith("Nessun risultato"):
                print("Nessun risultato trovato per la ricerca richiesta")
                raise typer.Exit()
            elementi = int(numero_el[0].split(" ")[0].replace(".", ""))
            numero_pagine = elementi // ELEMENTI_PER_PAGINA
            if elementi % ELEMENTI_PER_PAGINA != 0:
                numero_pagine = (elementi // ELEMENTI_PER_PAGINA) + 1
        else:
            print("Nessun risultato trovato per la ricerca richiesta")
            raise typer.Exit()
    return numero_pagine


def get_urls(url_padre: str) -> List[str]:
    """
    Prepara e ritorna la lista di URL da analizzare
    Prepara le URL nel modo più opportuno, simulando la navigazione
    Al momento implementazione specifica per il sito immobiliare.it
    Esempio:
    https://www.immobiliare.it/vendita-case/biella/?criterio=rilevanza&pag2=true&pag=2
    e non
    https://www.immobiliare.it/vendita-case/biella/?criterio=rilevanza&pag=2
    """
    numero_pagine = get_numero_pagine(url_padre) + 1
    lista_urls = []
    lista_urls.append(url_padre)
    for i in range(2, numero_pagine):
        lista_urls.append(url_padre + "&pag" + str(i) + "=true&pag=" + str(i))
    return lista_urls


def parser_content(url: str):
    """
    Analizzatore della pagina
    (specifica per il sito immobiliare.it)
    Popola una variabile globale
    """
    global lista_immobili
    r = requests.get(url)
    home = r.content.decode("utf-8")
    parser = html.fromstring(home)
    if r.status_code == 200:
        # Liste elementi trovati
        tit = parser.xpath(XPATH_TITOLI)
        prezzi_ann = parser.xpath(XPATH_PREZZI)
        descr = parser.xpath(XPATH_DESCRIZIONI)
        # Check presenza tutti elementi della tupla
        disallineamento_tuple = False
        if not (
            len(tit) == len(prezzi_ann)
            and len(tit) == len(descr)
            and len(prezzi_ann) == len(descr)
        ):
            typer.echo(
                f"\nATTENZIONE, nella pagina:\n{url} sono stati trovati {len(prezzi_ann)} prezzi, {len(tit)} titoli, {len(descr)} descrizioni."
            )
            typer.echo(
                f"Consigliamo visita 'manuale' della pagina perchè quegli annunci non saranno presenti in output.\n"
            )
            disallineamento_tuple = True
        # Allineamenti: composizione lista di lista di tuple
        if not disallineamento_tuple:
            lista_immobili.append(list(zip(tit, prezzi_ann, descr)))
    else:
        print("Problemi di connessione ad Internet o sul sito")
        raise typer.Exit()


def affitto_vendita_callback(value: str) -> str:
    if value == "a" or value == "A":
        value = "affitto"
    if value == "v" or value == "V":
        value = "vendita"
    if value != "affitto" and value != "vendita":
        raise typer.BadParameter("Solo 'affitto' o 'vendita' sono ammessi")
    return value


def tipo_immobile_callback(value: str) -> str:
    if value == "c" or value == "C":
        value = "case"
    if value == "n" or value == "N":
        value = "negozi"
    if value != "case" and value != "negozi":
        raise typer.BadParameter("Solo 'case' o 'negozi' sono ammessi")
    return value


def main(
    citta: str,
    affitto_vendita: str = typer.Option(
        ..., "-affitto_vendita", "-av", callback=affitto_vendita_callback
    ),
    case_negozi: str = typer.Option(
        ..., "-case_negozi", "-cn", callback=tipo_immobile_callback
    ),
    verbose: bool = False,
) -> None:
    """
    Progetto a scopo didattico di web scraping con XPath sul sito immobiliare.it
    Cerca nella città fornita come argomento, in affitto o in vendita, case o negozi.
    Output salvato come file Excel.
    Esempio, per cercare case in vendita a Biella:

    python immobili.py -av v -cn c Biella
    """
    # Parsing delle pagine; risultati nella var globale lista_immobili
    # Costruzione url, richiamo parser e costruzione dataframe
    # Gestione città formate da più parole, es Casale Monferrato
    citta_url = citta.replace(" ", "-").lower()
    global lista_immobili
    url_padre = f"{URL_SITO}{affitto_vendita.lower()}-{case_negozi.lower()}/{citta_url}/?criterio=rilevanza"
    lista_pagine = get_urls(url_padre)
    lista_immobili = []
    numero_pagine = len(lista_pagine)
    with typer.progressbar(
        enumerate(lista_pagine),
        label=f"Sto cercando {case_negozi} in {affitto_vendita} a {citta.capitalize()}...",
        length=numero_pagine,
    ) as progress:
        for indx, i in progress:
            if verbose:
                typer.echo(f"Scraping della pagina {i} : {indx+1} di {numero_pagine}")
            parser_content(i)
            # Pausa per simulare comportamento umano
            time.sleep(3)
    # Costruzione data frame per creazione del file Excel XLSX con i dati
    df = pd.DataFrame()
    for j in lista_immobili:
        # Creo un df temporaneo a partire da ciascun elemento lista
        df_uno = pd.DataFrame(j)
        # Append sul df
        df = pd.concat([df, df_uno])
    df.columns = ["Titolo", "Prezzo", "Descrizione"]
    today = date.today()
    # Per evitare nome file e nomi sheet troppo lunghi
    if len(citta) > 10:
        citta_nomefile = citta[0:9]
    else:
        citta_nomefile = citta
    df.to_excel(
        f"{affitto_vendita[0].capitalize()}-{case_negozi[0].capitalize()}-{citta_nomefile.capitalize()}-{today.strftime('%d-%m-%y')}.xlsx",
        index=False,
        sheet_name=f"{affitto_vendita} {case_negozi} a {citta_nomefile.capitalize()}",
    )


if __name__ == "__main__":
    typer.run(main)
