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
      yield {
        "id": linha.css("td:first-child > span::text").get()
      }

#   def parse(self, response):
#     linhas = response.css('table#pokedex > tbody > tr')
#     for linha in linhas:
#       link = linha.css("td:nth-child(2) > a::attr(href)")
#       yield response.follow(link.get(), self.parser_pokemon)
    
#   def parser_pokemon(self, response):
#     peso = response.css('table.vitals-table > tbody > tr:nth-child(5) > td::text')
#     yield {"peso": peso.get()}

#yield {"nome": nome.get()}


# class PokeSpider(scrapy.Spider):
#   name = 'pokespider'
#   start_urls = ['https://pokemondb.net/pokedex/all']

#   def parse(self, response):
#     ### tabela de seletores de CSS
#     tabela_pokedex = "table#pokedex > tbody > tr"

#     linhas = response.css(tabela_pokedex)

#     # Processa uma linha apenas
#     linha = linhas[0]
#     coluna_href = linha.css("td:nth-child(2) > a::attr(href)")
#     yield response.follow(coluna_href.get(), self.parser_pokemon)

#     # Processa todas as linhas
#     for linha in linhas:
#       # coluna_nome = linha.css("td:nth-child(2) > a::text")
#       # coluna_id = linha.css("td:nth-child(1) > span.infocard-cell-data::text")
#       #yield {'id': coluna_id.get(),'nome': coluna_nome.get()}

#       coluna_href = linha.css("td:nth-child(2) > a::attr(href)")
#       yield response.follow(coluna_href.get(), self.parser_pokemon)

#   def parser_pokemon(self, response):
#     id_selector = "table.vitals-table > tbody > tr:nth-child(1) > td > strong::text"
    
#     id = response.css(id_selector)
#     yield {'id': id.get()}
    