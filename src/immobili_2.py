# Step 2 di progetto - Introduzione di Typer

import requests
import lxml.html as html
import pandas as pd
from datetime import date
import typer

def get_numero_pagine(url_padre):
    '''
    Funzione privata (specifica per il sito immobiliare.it) che verifica il numero di pagine
    da analizzare, dato un url_padre.
    Usata da get_urls
    Se il numero delle pagine non è presente, viene calcolato in base al numero di elementi
    NOTA: il sito limita la ricerca a 80 pagine, 2000 elementi
    '''
    ELEMENTI_PER_PAGINA=25
    numero_pagine_xpath='//div[@class="in-pagination__item is-mobileHidden in-pagination__item--disabled"][2]/text()'
    r=requests.get(url_padre)
    home=r.content.decode('utf-8')
    parser=html.fromstring(home)
    np=parser.xpath(numero_pagine_xpath)
    if np:
        numero_pagine = int(np[0])    
    else:
        numero_elementi='//div[@class="in-searchList__title is-listMapLayout"]/text()'
        numero_el=parser.xpath(numero_elementi)
        elementi = int(numero_el[0].split(' ')[0].replace(".",""))
        if ( elementi % ELEMENTI_PER_PAGINA == 0 ):
            numero_pagine = elementi // ELEMENTI_PER_PAGINA
        else:
            numero_pagine = (elementi // ELEMENTI_PER_PAGINA) +1            
    return numero_pagine


def get_urls(url_padre):
    '''
    Prepara e ritorna la lista di URL da analizzare 
    Prepara le URL nel modo più opportuno, simulando la navigazione
    (specifica per il sito immobiliare.it)
    Esempio
    https://www.immobiliare.it/vendita-case/biella/?criterio=rilevanza&pag2=true&pag=2
    e non
    https://www.immobiliare.it/vendita-case/biella/?criterio=rilevanza&pag=2
    '''
    numero_pagine=get_numero_pagine(url_padre)+1
    lista_urls = []
    lista_urls.append(url_padre)
    for i in range(2,numero_pagine):
        lista_urls.append(url_padre+'&pag'+str(i)+'=true&pag='+str(i))    
    return lista_urls

def parser_content(url):
    '''
    Analizzatore della pagina
    (specifica per il sito immobiliare.it)
    Popola una variabile globale
    '''
    global lista_immobili
    dati_appartamento={}    
    r=requests.get(url)
    home=r.content.decode('utf-8')
    parser=html.fromstring(home)
    if r.status_code==200:
        # XPATH degli attributi
        titoli='//a[@class="in-card__title"]/text()'
        prezzi_annunci= '//div[@class="in-realEstateListCard__priceOnTop"]/text()|//li[@class="nd-list__item in-feat__item in-feat__item--main in-realEstateListCard__features--main"]/text() | //li[@class="nd-list__item in-feat__item in-feat__item--main in-realEstateListCard__features--main in-realEstateListCard__features--mainText"]/text() | //div[@class="in-realEstateListCard__features--range"]/text()'
        descrizioni='//p[@class="in-realEstateListCard__descriptionShort"]/text()|//p[@class="in-realEstateListCard__description"]/text()'       
        #Liste elementi trovati
        tit = parser.xpath(titoli)
        prezzi_ann = parser.xpath(prezzi_annunci)
        descr = parser.xpath(descrizioni)        
        # Check presenza tutti elementi della tupla
        disallineamento_tuple = False
        if not ( len(tit) == len(prezzi_ann) and len(tit) == len(descr) and len(prezzi_ann) == len(descr) ):        
            typer.echo(f"Nella pagina sono stati trovati {len(prezzi_ann)} prezzi, {len(tit)} titoli, {len(descr)} descrizioni")
            typer.echo(f"ATTENZIONE: A causa di almeno un annuncio non completo, consigliamo visita 'manuale' della pagina: {url}")
            disallineamento_tuple = True            
        #Allineamenti: composizione lista di lista di tuple
        if not disallineamento_tuple:
            lista_immobili.append(list(zip(tit, prezzi_ann, descr)))    


def main(affitto_vendita, tipo_immobile, citta):
    '''
    Parsing delle pagine; risultati nella var globale lista_immobili
    Costruzione url, richiamo parser e costruzione dataframe
    '''
    global lista_immobili
    url_padre = f'https://www.immobiliare.it/{affitto_vendita.lower()}-{tipo_immobile.lower()}/{citta.lower()}/?criterio=rilevanza'
    lista_pagine = get_urls(url_padre)
    lista_immobili = []
    import time
    numero_pagine = len(lista_pagine)
    for indx,i in enumerate(lista_pagine):
        typer.echo(f'Scraping della pagina {i} : {indx+1} di {numero_pagine}')
        parser_content(i)
        # Pausa per simulare comportamento umano
        time.sleep(3)
    # Costruzione data frame per creazione XLSX
    df=pd.DataFrame()
    for j in lista_immobili:
        #Creo un df temporaneo a partire da ciascun elemento lista
        df_uno=pd.DataFrame(j)
        #Append sul df
        df=pd.concat([df,df_uno])
    df.columns = ['Titolo', 'Prezzo', 'Descrizione']
    today = date.today()
    df.to_excel(f"{affitto_vendita.capitalize()}-{tipo_immobile.capitalize()}-{citta.capitalize()}-{today.strftime('%d-%m-%Y')}.xlsx", 
                index=False, sheet_name=f'{affitto_vendita} {tipo_immobile} a {citta.capitalize()}')


if __name__ == '__main__':
    typer.run(main)