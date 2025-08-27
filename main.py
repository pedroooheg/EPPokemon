import scrapy

# Exercício:
# Buscar:
# Nome, ID, Tamanho e Peso
# Alguns dados estão dentro da página do Pokemon
# Página do Pokémon deve usar o parser "parser_pokemon"

# Dica: Principais CSS Selectors:
# https://www.w3schools.com/cssref/css_selectors.php

class PokeSpider(scrapy.Spider):
  name = 'pokespider'
  start_urls = ['https://pokemondb.net/pokedex/all']

  def parse(self, response):
    linhas = response.css('table#pokedex > tbody > tr')
    for linha in linhas:
      link = linha.css("td:nth-child(2) > a::attr(href)")
      yield response.follow(link.get(), self.parser_pokemon)

  def parser_pokemon(self, response):
    id = response.css('table.vitals-table:first-of-type tr:nth-child(1) td strong::text').get()
    nome = response.css('h1::text').get()
    peso = response.css("th:contains('Weight') + td::text").get()
    tamanho = response.css("th:contains('Height') + td::text").get()
    habilidades = response.css("th:contains('Abilities') + td a::text").getall()
    habilidades_str = ", ".join(habilidades)
    urls_habilidades = [
      response.urljoin(url) 
      for url in response.css("th:contains('Abilities') + td a::attr(href)").getall()
      ]
    tipos = ",".join(response.css("th:contains('Type') + td a::text").getall())
    url = response.url

    evolucoes = []
    cards = response.css("div.infocard-list-evo > *")
    for i in range(0, len(cards), 2):
        evo = cards[i] 
        arrow = cards[i+1] if i+1 < len(cards) else None 

        nome_evo = evo.css("a.ent-name::text").get()
        url_evo = evo.css("a.ent-name::attr(href)").get()
        poke_id_evo = evo.css("small::text").get()
        tipos_evo = [t.get() for t in evo.css("small a.itype::text")]

        level_item = arrow.css("small::text").get() if arrow else None
        if level_item:
            level_item = level_item.strip("()")

        evolucoes.append({
            "id": poke_id_evo,
            "nome": nome_evo,
            "url": response.urljoin(url_evo),
            "tipos": tipos_evo,
            "level_item": level_item
        })
      
        efetividade = {}
        tipos_ataque = response.css("table.type-table-pokedex tr:nth-child(1) th a::attr(title)").getall()
        valores_celulas = response.css("table.type-table-pokedex tr:nth-child(2) td")

        for i, tipo in enumerate(tipos_ataque):
            celula = valores_celulas[i]
            taxa = celula.css("::text").get()
            if taxa is None or taxa.strip() == "":
                taxa = ""
            efetividade[tipo] = taxa


    yield {
        "id": id,
        "url": url,
        "nome": nome,
        "tamanho": tamanho,
        "peso": peso,
        "tipos": tipos,
        "habilidades":habilidades_str,
        "url_habilidades":urls_habilidades,
        "evolucoes":evolucoes,
        "efetividade": efetividade

    }
