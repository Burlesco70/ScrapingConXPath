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
XPATH_NUMERO_RISULTATI = '//div[@class="in-resultsHeader__title is-listMapLayout"]/text()'

XPATH_TITOLI = '//a[@class="in-reListCard__title"]/text()'
XPATH_LINKS = '//a[@class="in-reListCard__title"]/@href'
XPATH_PREZZI = '//div[@class="in-reListCardPrice"]/span/text()'

def get_numero_pagine(url_padre: str) -> int:
    """
    Funzione privata, al momento specifica per il sito immobiliare.it, che verifica il numero di pagine
    da analizzare, dato un url_padre. Usata da get_urls.
    Il numero delle pagine viene calcolato in base al numero di elementi
    """
    r = requests.get(url_padre)
    home = r.content.decode("utf-8")
    parser = html.fromstring(home)
    nr = parser.xpath(XPATH_NUMERO_RISULTATI)
    if nr:
        if nr[0].startswith("Nessun risultato"):
            typer.echo("Nessun risultato trovato per la ricerca richiesta")
            raise typer.Exit()
        elementi = int(nr[0].split(" ")[0].replace(".", ""))
        numero_pagine = elementi // ELEMENTI_PER_PAGINA
        if elementi % ELEMENTI_PER_PAGINA != 0:
            numero_pagine = (elementi // ELEMENTI_PER_PAGINA) + 1
    else:
        typer.echo("Nessun risultato trovato per la ricerca richiesta")
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
        # Rispetto alla versione precedente è sparita la descrizione
        tit = parser.xpath(XPATH_TITOLI)
        prezzi_ann = parser.xpath(XPATH_PREZZI)
        link = parser.xpath(XPATH_LINKS)
        # Check presenza tutti elementi della tupla
        disallineamento_tuple = False
        if not (
            len(tit) == len(prezzi_ann)
            and len(link) == len(tit)
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
            lista_immobili.append(list(zip(tit, prezzi_ann, link)))
    else:
        typer.echo("Problemi di connessione ad Internet o sul sito")
        raise typer.Exit()


def investimento_callback(value: str) -> str:
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
    if value == "g" or value == "G":
        value = "garage"
    if value == "p" or value == "P":
        value = "palazzi"
    if value == "u" or value == "U":
        value = "uffici"
    if value == "n" or value == "N":
        value = "negozi"
    if value == "m" or value == "M":
        value = "magazzini"
    if value == "cp" or value == "CP":
        value = "capannoni"
    if value != "case" and value != "garage" and value != "palazzi" and value != "uffici" and value != "negozi" and value != "magazzini" and value != "capannoni":
        raise typer.BadParameter("Solo 'case', 'garage', 'palazzi', 'uffici', 'negozi', 'magazzini' o 'capannoni' sono ammessi")
    return value

def main(
    citta: str,
    investimento: str = typer.Option(
        ..., 
        "-I", 
        "--investimento",
        help="Opzioni possibili: 'a' per Affitto o 'v' per Vendita",
        callback=investimento_callback
    ),
    tipologia: str = typer.Option(
        ..., 
        "-T", 
        "--tipologia", 
        help="Opzioni possibili: 'c' per Case, 'g' per Garage, 'p' per Palazzi, 'u' per Uffici, 'n' per Negozi, 'm' per Magazzini', 'cp' per Capannoni",
        callback=tipo_immobile_callback
    ),
    verbose: bool = False,        
) -> None:
    """
    Progetto a scopo didattico di web scraping con XPath sul sito immobiliare.it
    Cerca nella città fornita come argomento, in affitto o in vendita, case o negozi.
    Output salvato come file Excel.
    Esempio, per cercare case in vendita a Biella:

    python immobili.py -I v -T c Biella

    Per cercare capannoni in affitto a Vercelli:

    python immobili.py -I a -T cp Vercelli
    """
    # Parsing delle pagine; risultati nella var globale lista_immobili
    # Costruzione url, richiamo parser e costruzione dataframe
    # Gestione città formate da più parole, es Casale Monferrato
    citta_url = citta.replace(" ", "-").lower()
    global lista_immobili
    url_padre = f"{URL_SITO}{investimento.lower()}-{tipologia.lower()}/{citta_url}/?criterio=rilevanza"
    lista_pagine = get_urls(url_padre)
    lista_immobili = []
    numero_pagine = len(lista_pagine)
    with typer.progressbar(
        enumerate(lista_pagine),
        label=f"Sto cercando {tipologia} in {investimento} a {citta.capitalize()}...",
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
    df.columns = ["Titolo", "Prezzo", "Link"]
    today = date.today()
    # Per evitare nome file e nomi sheet troppo lunghi
    if len(citta) > 10:
        citta_nomefile = citta[0:9]
    else:
        citta_nomefile = citta
    df.to_excel(
        f"{investimento[0].capitalize()}-{tipologia[0].capitalize()}-{citta_nomefile.capitalize()}-{today.strftime('%d-%m-%y')}.xlsx",
        index=False,
        sheet_name=f"{investimento} {tipologia} a {citta_nomefile.capitalize()}",
    )


if __name__ == "__main__":
    typer.run(main)
